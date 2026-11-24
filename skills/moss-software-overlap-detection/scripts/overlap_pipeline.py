#!/usr/bin/env python3
"""Moss - Software Overlap Detection pipeline.

Reads a transaction export, classifies vendors via taxonomy, then detects
three overlap patterns:

  Type 1 - Personal card duplicates: same vendor paid by 2+ employees separately
  Type 2 - Parallel contracts: same vendor, 2+ invoice numbers active simultaneously
  Type 3 - Category overlap: multiple vendors in the same functional category

Types 1, 2 require DATEV format (Buchungstext, Gegenkonto, Belegfeld1 columns).
Type 3 works with any format.

(A former Type 4 - "Shadow IT", personal card charges cross-referenced against
a corporate contract for the same vendor - was removed: it couldn't be
determined reliably from transaction data alone.)

Usage
-----
    python3 overlap_pipeline.py --input FILE --output overlap_report.xlsx \\
                                --taxonomy PATH/vendor_taxonomy.csv \\
                                [--currency EUR] \\
                                [--min-category-vendors 3] \\
                                [--min-category-spend 10000]
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# Imports from sibling scripts
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from match_taxonomy import load_taxonomy, match as taxonomy_match
from extract_candidates import cleanse_segment

# ---------------------------------------------------------------------------
# Feature map helpers (for functional overlap scoring)
# ---------------------------------------------------------------------------

def load_features(path):
    """Return {canonical: frozenset(features)} from vendor_features.csv.

    File format (comments and blank lines ignored):
        canonical,category,features
        Slack,Comms & Collab,chat;channels;video_calls;...
    """
    result = {}
    if not path or not os.path.exists(path):
        return result
    with open(path, newline="", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",", 2)
            if len(parts) < 3 or parts[0].strip() == "canonical":
                continue
            canonical = parts[0].strip()
            feats = frozenset(t.strip() for t in parts[2].split(";") if t.strip())
            if feats:
                result[canonical] = feats
    return result


def _jaccard(a, b):
    """Jaccard similarity between two frozensets. Returns 0 if either is empty."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap_grade(score):
    """Map Jaccard score to LOW / MEDIUM / HIGH / CRITICAL."""
    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.50:
        return "HIGH"
    if score >= 0.25:
        return "MEDIUM"
    return "LOW"


# Feature-tag words that should render as acronyms, not Title Case, when
# humanized for display (e.g. "ats" -> "ATS", not "Ats").
_TAG_ACRONYMS = {
    "ab": "A/B", "ai": "AI", "api": "API", "apm": "APM", "ats": "ATS",
    "cd": "CD", "cdn": "CDN", "ci": "CI", "cms": "CMS", "crm": "CRM",
    "dast": "DAST", "dm": "DM", "erp": "ERP", "etl": "ETL", "gdpr": "GDPR",
    "hris": "HRIS", "iam": "IAM", "it": "IT", "kpi": "KPI", "mdm": "MDM",
    "mfa": "MFA", "ml": "ML", "ocr": "OCR", "roi": "ROI", "saas": "SaaS",
    "seo": "SEO", "sla": "SLA", "sms": "SMS", "soc2": "SOC2", "sql": "SQL",
    "sso": "SSO", "ui": "UI", "ux": "UX", "vpn": "VPN",
}


def _humanize_tag(tag):
    """Turn a snake_case feature-tag code (e.g. 'lead_enrichment') into a
    readable label ('Lead Enrichment') for display, uppercasing recognized
    acronyms ('ats' -> 'ATS') instead of Title-Casing them."""
    words = tag.replace("-", "_").split("_")
    return " ".join(_TAG_ACRONYMS.get(w.lower(), w.capitalize()) for w in words if w)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATEV_GEGEN_CARD    = "7999999"   # credit card / employee expense rows
DATEV_GEGEN_PREPAID = "98001"     # prepaid accrual release rows

# Placeholder shown in cells Claude is expected to overwrite during Pass 3
# (per-vendor Features description, and the three overlap-case write-up
# columns) — never a final answer, just a marker that research is pending.
PENDING_PASS3 = "Pending — added by Claude during Pass 3."

# Pattern: "F. Lastname" or "F.Lastname"
EMPLOYEE_RE = re.compile(r'^([A-ZÄÖÜ]\.\s?[A-ZÄÖÜ][a-zäöüß][a-zäöüßA-Za-z\-]*)$')

# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------

def _read_file(path):
    """Return a pandas DataFrame. Promotes first data row to header if needed
    (handles DATEV Kontoblatt metadata title in row 0)."""
    import pandas as pd
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path, dtype=str, header=0).fillna("")
    else:
        df = pd.read_csv(path, dtype=str, sep=None, engine="python").fillna("")

    if len(df) > 0:
        first_row = df.iloc[0].tolist()
        known_headers = {"Buchungstext", "Date", "Datum", "Description", "BL", "HK"}
        if any(str(v).strip() in known_headers for v in first_row):
            df.columns = [str(v).strip() for v in first_row]
            df = df.iloc[1:].reset_index(drop=True).fillna("")

    return df


def _detect_format(df):
    """Return (is_datev, is_kontoblatt)."""
    cols = set(df.columns)
    if "Buchungstext" not in cols:
        return False, False
    is_kontoblatt = ("HK" in cols and "BSNr." in cols and "Buchungs GUID" not in cols)
    return True, is_kontoblatt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_float(x):
    if not x or str(x).strip() in ("", "nan", "NaN", "-"):
        return None
    s = str(x).strip()
    if re.search(r",\d{2}$", s):          # German: 1.234,56
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    s = re.sub(r"[€£$\s]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(x):
    if not x or str(x).strip() in ("", "nan", "NaN"):
        return None, None
    s = str(x).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.year, dt.month
        except ValueError:
            continue
    return None, None


def _extract_employee(text):
    """Return 'F. Lastname' from 'VENDOR; F. Lastname; description', or None."""
    parts = [p.strip() for p in str(text).split(";")]
    for part in parts[1:]:          # skip first segment (vendor)
        if EMPLOYEE_RE.match(part):
            return part
    return None


# ---------------------------------------------------------------------------
# Load and classify transactions
# ---------------------------------------------------------------------------

def load_and_classify(path, taxonomy):
    """Read file, match each transaction against taxonomy.

    Returns:
        transactions: list of dicts (one per row)
        is_datev: bool
    Each dict: {raw_text, vendor_segment, employee, gegenkonto, belegfeld1,
                kost1, amount, year, month, canonical, category, is_datev}
    """
    df = _read_file(path)
    is_datev, is_kontoblatt = _detect_format(df)

    if is_datev:
        label = "DATEV Kontoblatt" if is_kontoblatt else "DATEV full export"
        print(f"Format detected: {label}")
        date_col = "Datum" if is_kontoblatt else "Belegdatum"
    else:
        print("Format detected: generic CSV/XLSX")
        print("Note: Types 1, 2, 4 require DATEV format — only Type 3 (category overlap) will run.")
        # Auto-detect description/amount/date columns
        cols_lower = {c.lower(): c for c in df.columns}
        desc_col = next((cols_lower[s] for s in
            ["buchungstext","description","transaction description","memo","text","narrative"]
            if s in cols_lower), None)
        amount_col = next((cols_lower[s] for s in
            ["amount","betrag","umsatz","debit","spent","value","sum"]
            if s in cols_lower), None)
        date_col_gen = next((cols_lower[s] for s in
            ["date","datum","buchungsdatum","booking date","transaction date"]
            if s in cols_lower), None)

    transactions = []
    unmatched = {}   # candidate_lower -> {candidate, total, count}

    for _, row in df.iterrows():
        # ── DATEV path ────────────────────────────────────────────────────
        if is_datev:
            text = str(row.get("Buchungstext", "")).strip()
            if not text:
                continue

            amount = _to_float(row.get("Umsatz Soll"))
            if not amount or amount <= 0:
                continue

            year, month = _parse_date(row.get(date_col, ""))
            if not year:
                continue

            gegen    = str(row.get("Gegenkonto", "")).strip()
            belegfeld = str(row.get("Belegfeld1", "")).strip()
            kost1    = str(row.get("KOST1", "")).strip()
            employee = _extract_employee(text)

            # For DATEV prepaid accrual rows (Gegenkonto=98001), the format is:
            # "InvoiceNumber; VendorName; VendorName; Release prepaid exp MM-YYYY"
            # The first segment is an invoice number, not a vendor name.
            # Use the second segment for taxonomy matching.
            segments = text.split(";")
            if gegen == DATEV_GEGEN_PREPAID and len(segments) >= 2:
                vendor_seg = cleanse_segment(segments[1].strip())
                if not vendor_seg and len(segments) >= 1:
                    vendor_seg = cleanse_segment(segments[0].strip())
            else:
                vendor_seg = cleanse_segment(segments[0].strip())

        # ── Generic path ──────────────────────────────────────────────────
        else:
            if not desc_col:
                continue
            text = str(row.get(desc_col, "")).strip()
            if not text:
                continue

            if not amount_col:
                continue
            amount = _to_float(row.get(amount_col))
            if not amount or amount <= 0:
                continue

            year, month = _parse_date(row.get(date_col_gen, "")) if date_col_gen else (None, None)

            gegen    = ""
            belegfeld = ""
            kost1    = ""
            employee = None
            vendor_seg = cleanse_segment(text.split(";")[0].strip())

        if not vendor_seg:
            continue

        # ── Taxonomy match ────────────────────────────────────────────────
        hit = taxonomy_match(vendor_seg.lower(), taxonomy)
        if hit and hit["is_excluded"] == "1":
            continue    # not software

        if hit:
            canonical = hit["canonical"]
            category  = hit["category"]
        else:
            key = vendor_seg.lower()
            if key not in unmatched:
                unmatched[key] = {"candidate": vendor_seg, "total": 0.0, "count": 0}
            unmatched[key]["total"] += amount
            unmatched[key]["count"] += 1
            canonical = None
            category  = None

        transactions.append({
            "raw_text":      text,
            "vendor_segment": vendor_seg,
            "employee":      employee,
            "gegenkonto":    gegen,
            "belegfeld1":    belegfeld,
            "kost1":         kost1,
            "amount":        amount,
            "year":          year,
            "month":         month,
            "canonical":     canonical,
            "category":      category,
            "is_datev":      is_datev,
        })

    classified = sum(1 for t in transactions if t["canonical"])
    print(f"Loaded {len(transactions)} transactions — "
          f"{classified} classified via taxonomy, {len(unmatched)} unmatched")

    # Print unmatched for Claude to review in-context
    if unmatched:
        print("\n--- UNMATCHED CANDIDATES ---")
        for info in sorted(unmatched.values(), key=lambda x: -x["total"]):
            print(f"  {info['candidate']}  "
                  f"(total: {info['total']:,.0f}, {info['count']} transactions)")
        print("--- END UNMATCHED CANDIDATES ---\n")

    return transactions, is_datev


# ---------------------------------------------------------------------------
# Detector 1 — Personal card duplicates
# Same canonical vendor paid by 2+ employees via card (Gegenkonto = 7999999)
# ---------------------------------------------------------------------------

def detect_type1(transactions):
    card_rows = [
        t for t in transactions
        if t["gegenkonto"] == DATEV_GEGEN_CARD
        and t["employee"]
        and t["canonical"]
    ]

    # canonical -> employee -> charges list
    by_vendor = defaultdict(lambda: defaultdict(list))
    for t in card_rows:
        by_vendor[t["canonical"]][t["employee"]].append(
            (t["year"], t["month"], t["amount"], t["kost1"])
        )

    flags = []
    for canonical, employees in by_vendor.items():
        if len(employees) < 2:
            continue

        emp_stats = []
        for emp, charges in employees.items():
            kost1_vals = [k for _, _, _, k in charges if k]
            emp_stats.append({
                "employee":     emp,
                "annual_spend": sum(a for _, _, a, _ in charges),
                "months_active": len({(y, m) for y, m, _, _ in charges}),
                "month_set":    {(y, m) for y, m, _, _ in charges},
                "kost1":        kost1_vals[0] if kost1_vals else "",
            })
        emp_stats.sort(key=lambda e: -e["annual_spend"])

        # Count months where 2+ employees were simultaneously active
        overlap = set(emp_stats[0]["month_set"])
        for e in emp_stats[1:]:
            overlap &= e["month_set"]
        srt = sorted(overlap)

        flags.append({
            "vendor":          canonical,
            "employees":       emp_stats,
            "combined_annual": sum(e["annual_spend"] for e in emp_stats),
            "overlap_months":  len(overlap),
            "overlap_start":   f"{srt[0][0]}-{srt[0][1]:02d}" if srt else None,
            "overlap_end":     f"{srt[-1][0]}-{srt[-1][1]:02d}" if srt else None,
            "action": (
                "Charges suggest that one or more smaller individual licenses may exist "
                "alongside a broader company-wide subscription. Confirm whether these "
                "separate licenses are still needed and consolidate them into the main "
                "plan where possible."
            ),
        })

    return sorted(flags, key=lambda f: -f["combined_annual"])


# ---------------------------------------------------------------------------
# Detector 2 — Parallel contracts
# Same canonical vendor, 2+ invoice numbers active in the same month (Gegenkonto = 98001)
# ---------------------------------------------------------------------------

def detect_type2(transactions):
    prepaid_rows = [
        t for t in transactions
        if t["gegenkonto"] == DATEV_GEGEN_PREPAID
        and t["belegfeld1"]
        and t["canonical"]
    ]

    # canonical -> invoice_num -> {months, total, kost1}
    by_vendor = defaultdict(lambda: defaultdict(lambda: {"months": set(), "total": 0.0, "kost1": ""}))
    for t in prepaid_rows:
        rec = by_vendor[t["canonical"]][t["belegfeld1"]]
        rec["months"].add((t["year"], t["month"]))
        rec["total"] += t["amount"]
        if t["kost1"] and not rec["kost1"]:
            rec["kost1"] = t["kost1"]

    flags = []
    for canonical, invoices in by_vendor.items():
        if len(invoices) < 2:
            continue

        inv_list = []
        for inv_num, data in invoices.items():
            n = len(data["months"])
            inv_list.append({
                "invoice_number": inv_num,
                "months":         data["months"],
                "total":          data["total"],
                "monthly_avg":    data["total"] / n if n else 0.0,
                "kost1":          data["kost1"],
            })
        inv_list.sort(key=lambda i: min(i["months"]) if i["months"] else (9999, 99))

        # Find overlapping months across all invoice pairs
        overlap = set()
        for i in range(len(inv_list)):
            for j in range(i + 1, len(inv_list)):
                shared = inv_list[i]["months"] & inv_list[j]["months"]
                overlap |= shared

        if not overlap:
            continue    # sequential contracts, not parallel — fine

        srt = sorted(overlap)
        overlap_spend = sum(inv["monthly_avg"] for inv in inv_list) * len(overlap)

        flags.append({
            "vendor":         canonical,
            "invoices":       inv_list,
            "overlap_months": len(overlap),
            "overlap_start":  f"{srt[0][0]}-{srt[0][1]:02d}",
            "overlap_end":    f"{srt[-1][0]}-{srt[-1][1]:02d}",
            "overlap_spend":  overlap_spend,
            # Full total across every invoice, not just the overlapping-window
            # subset (overlap_spend) — used where a reader needs "all spend on
            # this vendor via Type 2 entries" (e.g. the Duplicate Vendor
            # Payments sheet's per-vendor total), not just the at-risk slice.
            "total_spend":    sum(inv["total"] for inv in inv_list),
            "action": (
                "Charges suggest that multiple contracts or plans with the same vendor "
                "may be running in parallel. Confirm whether they cover different "
                "services or are valid add-ons before treating them as duplicates, and "
                "consolidate overlapping contracts where appropriate."
            ),
        })

    return sorted(flags, key=lambda f: -f["overlap_spend"])


# ---------------------------------------------------------------------------
# Detector 3 — Category overlap
# Categories with 3+ vendors OR combined spend above threshold
# ---------------------------------------------------------------------------

def _build_overlap_entries(vendors, features, min_pair_spend, max_pairs):
    """Build cluster + pairwise overlap entries for one category.

    Candidacy is decided by materiality (EUR recoverable) alone — NOT by
    whether the vendors happen to have feature tags in vendor_features.csv.
    A vendor missing from that file (the common case for less mainstream
    tools) still becomes a full candidate; it just has no baseline_score.
    This matters because gating on tag data silently hid entire categories
    where nothing was tagged (e.g. "Sales" on the Nufin baseline) from
    analysis entirely — untagged is not the same as "no overlap".

    Two secondary problems this also handles: (1) vendors tagged with an
    identical feature set would otherwise produce N*(N-1)/2 rows that are
    all the same finding restated, and (2) a EUR 500-vendor overlapping a
    EUR 50-vendor would get the same visual weight as two EUR 100k vendors.
    Fixed via:

    - Vendors sharing an identical non-empty feature set (3+ of them) are
      collapsed into a single "cluster" entry instead of exploded pairs.
      This is a display optimization, not a candidacy gate.
    - Every entry (cluster or pair) gets a "materiality" figure — the EUR
      actually recoverable — and entries below `min_pair_spend` are dropped.
    - Remaining entries are ranked by materiality and capped to `max_pairs`,
      so the biggest financial opportunities surface first.

    When both vendors in a pair have feature tags, a `baseline_score`/
    `baseline_grade` is attached as a secondary, optional signal (fallback
    for when live research is inconclusive) — never a filter. Both are
    `None` when either vendor lacks tags.

    Returns (shown_entries, hidden_count).
    """
    by_features = defaultdict(list)
    nodes = []           # comparison units: single vendors or whole clusters
    cluster_entries = []

    for v, s in vendors:
        fset = features.get(v, frozenset())
        if fset:
            by_features[fset].append((v, s))
        else:
            nodes.append({"label": v, "features": fset, "spend": s})

    for fset, members in by_features.items():
        if len(members) >= 3:
            members = sorted(members, key=lambda m: -m[1])
            total = sum(s for _, s in members)
            _, top_spend = members[0]
            shared = sorted(fset)
            cluster_entries.append({
                "kind":            "cluster",
                "members":         [{"vendor": v, "annual_spend": s} for v, s in members],
                "shared":          shared,
                "spend":           total,
                "combined_spend":  total,
                "materiality":     total - top_spend,
                "exact_overlap":         PENDING_PASS3,
                "unique_capabilities":   PENDING_PASS3,
                "recommended_action":    PENDING_PASS3,
            })
            nodes.append({"label": ", ".join(v for v, _ in members), "features": fset, "spend": total})
        else:
            for v, s in members:
                nodes.append({"label": v, "features": fset, "spend": s})

    pair_entries = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            na, nb = nodes[i], nodes[j]
            has_both_tags = bool(na["features"] and nb["features"])

            if has_both_tags:
                score = _jaccard(na["features"], nb["features"])
                grade = _overlap_grade(score)
                shared = sorted(na["features"] & nb["features"])
            else:
                score, grade, shared = None, None, []

            pair_entries.append({
                "kind":            "pair",
                "vendor_a":        na["label"],
                "vendor_b":        nb["label"],
                "baseline_score":  score,
                "baseline_grade":  grade,
                "shared":          shared,
                "spend_a":         na["spend"],
                "spend_b":         nb["spend"],
                "combined_spend":       na["spend"] + nb["spend"],
                "materiality":          min(na["spend"], nb["spend"]),
                "exact_overlap":        PENDING_PASS3,
                "unique_capabilities":  PENDING_PASS3,
                "recommended_action":   PENDING_PASS3,
            })

    material = [e for e in cluster_entries + pair_entries if e["materiality"] >= min_pair_spend]
    material.sort(key=lambda e: -e["materiality"])

    shown = material[:max_pairs]
    hidden = len(material) - len(shown)
    return shown, hidden


def detect_type3(transactions, min_vendors=3, min_spend=10000, features=None,
                  min_pair_spend=2000, max_pairs_per_category=5):
    """Detect category overlap.

    For each flagged category also builds a materiality-ranked candidate list
    for Claude's functional overlap analysis — see `_build_overlap_entries`
    for how identical-tag clusters are collapsed and low-materiality entries
    are filtered before being surfaced. Candidacy depends only on spend, not
    on whether vendor_features.csv (if provided) happens to tag either
    vendor; a Jaccard-based baseline score is attached as an optional
    secondary signal when both vendors are tagged.

    Each flag includes a ``pairs`` list (clusters and/or pairs, ranked by EUR
    recoverable, capped to `max_pairs_per_category`) and a ``hidden_pairs``
    count for overlaps that existed but were below the materiality floor.
    """
    features = features or {}

    vendor_category = {}
    vendor_spend     = defaultdict(float)
    vendor_kost1     = defaultdict(lambda: defaultdict(float))  # canonical -> kost1 -> spend

    for t in transactions:
        if not t["canonical"] or not t["category"]:
            continue
        vendor_category[t["canonical"]] = t["category"]
        vendor_spend[t["canonical"]] += t["amount"]
        kost1 = t.get("kost1") or "Unknown"
        vendor_kost1[t["canonical"]][kost1] += t["amount"]

    # category -> [(vendor, spend)]
    by_category = defaultdict(list)
    for vendor, category in vendor_category.items():
        by_category[category].append((vendor, vendor_spend[vendor]))

    flags = []
    for category, vendors in by_category.items():
        vendors.sort(key=lambda v: -v[1])
        combined = sum(s for _, s in vendors)
        if len(vendors) >= min_vendors or combined >= min_spend:

            pairs, hidden_pairs = _build_overlap_entries(
                vendors, features, min_pair_spend, max_pairs_per_category
            )

            # ── Department breakdown per vendor ────────────────────────────
            # Helps distinguish "two teams intentionally use different tools"
            # from "accidental duplicate purchase by the same team".
            vendor_depts = {}
            for v, s in vendors:
                depts = vendor_kost1.get(v, {})
                total = sum(depts.values()) or 1.0
                ranked = sorted(depts.items(), key=lambda kv: -kv[1])
                vendor_depts[v] = [
                    {"kost1": k, "share": amount / total} for k, amount in ranked
                ]

            flags.append({
                "category":     category,
                "vendors":      [
                    {"vendor": v, "annual_spend": s, "departments": vendor_depts[v]}
                    for v, s in vendors
                ],
                "vendor_count": len(vendors),
                "combined":     combined,
                "pairs":        pairs,
                "hidden_pairs": hidden_pairs,
                "action": "Review which teams use each tool — see functional overlap pairs below.",
            })

    return sorted(flags, key=lambda f: -f["combined"])


# ---------------------------------------------------------------------------
# Write Excel report
# ---------------------------------------------------------------------------

def write_report(path, t1, t2, t3, transactions, currency, subtitle=""):  # noqa: too-many-args
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        sys.exit("openpyxl required: pip install openpyxl --break-system-packages")

    wb = Workbook()

    # ── Style constants ───────────────────────────────────────────────────
    GREEN_DARK  = "1A3C34"
    # Row-banding tint only — kept deliberately subtle so it reads as plain
    # visual separation (odd/even rows), not as a "this row is good/correct"
    # signal. Previous value (D8F3DC) was saturated enough that some readers
    # mistook it for a status indicator.
    GREEN_LIGHT = "EAF6EC"
    GREEN_TEXT  = "2D6A4F"
    GRAY_TEXT   = "666666"
    YELLOW_BG   = "FFFDE7"
    WHITE       = "FFFFFF"

    HDR_FILL    = PatternFill("solid", fgColor=GREEN_DARK)
    HDR_FONT    = Font(bold=True, color=WHITE, size=10)
    DATA_FILL   = PatternFill("solid", fgColor=GREEN_LIGHT)
    WHITE_FILL  = PatternFill("solid", fgColor=WHITE)
    AMT_FMT     = f'#,##0 "{currency}"'

    CELL_BORDER = Border(
        top=Side(style="thin", color="DDDDDD"),
        bottom=Side(style="thin", color="DDDDDD"),
        left=Side(style="thin", color="DDDDDD"),
        right=Side(style="thin", color="DDDDDD"),
    )

    def set_widths(ws, widths):
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    def no_gridlines(ws):
        ws.sheet_view.showGridLines = False

    def row_height(ws, vals, min_height=18, line_height=14, pad=22):
        """Estimate the row height needed for wrapped text to fully display,
        based on each cell's actual column width (already set via
        set_widths) — avoids clipped text without manual per-row heights.
        Adds a small top/bottom padding so wrapped text isn't flush against
        the row border.

        Deliberately conservative (assumes fewer characters fit per line
        than a tight estimate would): a report was seen with a 512-char
        cell clipped to ~3 visible lines because the height came out too
        short. Overestimating height just leaves a little blank space at
        the bottom of a row — harmless. Underestimating hides real content —
        not harmless. When in doubt, this errs toward "too tall."
        """
        chars_per_unit = 0.75   # conservative chars-per-Excel-width-unit
        max_lines = 1
        for i, v in enumerate(vals, 1):
            if not v:
                continue
            width = ws.column_dimensions[get_column_letter(i)].width or 10
            chars_per_line = max(1, int(width * chars_per_unit))
            lines = sum(-(-len(line) // chars_per_line) or 1
                        for line in str(v).split("\n"))
            max_lines = max(max_lines, lines)
        return max(min_height, max_lines * line_height + pad)

    def write_title(ws, text, ncols, height=36):
        """Merged title row — dark green bg, white centered text."""
        ws.append([text])
        r = ws.max_row
        ws.row_dimensions[r].height = height
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
        c = ws.cell(row=r, column=1)
        c.font = Font(bold=True, size=14, color=WHITE)
        c.fill = HDR_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")

    def write_subtitle(ws, text, ncols, height=22):
        """Merged subtitle row — white bg, gray centered text."""
        ws.append([text])
        r = ws.max_row
        ws.row_dimensions[r].height = height
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
        c = ws.cell(row=r, column=1)
        c.font = Font(size=10, color=GRAY_TEXT)
        c.fill = WHITE_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")

    def write_note(ws, text, ncols, spacer_before=6, height=20):
        """Merged note row — pale yellow bg, italic gray text, left-aligned.
        Used for the manual-verification banners and the Overview footnote —
        anything that should read as a caveat rather than data."""
        ws.append([None])
        ws.row_dimensions[ws.max_row].height = spacer_before
        ws.append([text])
        r = ws.max_row
        ws.row_dimensions[r].height = height
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
        c = ws.cell(row=r, column=1)
        c.font = Font(italic=True, color=GRAY_TEXT, size=9)
        c.fill = PatternFill("solid", fgColor=YELLOW_BG)
        c.alignment = Alignment(vertical="center", wrap_text=True)

    def write_hdr(ws, cols, height=24):
        """Column header row — dark green bg, white bold text. Freezes
        everything above and including this row, so the column names stay
        visible when scrolling through the data below."""
        ws.append([None])   # spacer
        ws.row_dimensions[ws.max_row].height = 6
        ws.append(cols)
        r = ws.max_row
        ws.row_dimensions[r].height = height
        for i in range(1, len(cols) + 1):
            c = ws.cell(row=r, column=i)
            c.fill = HDR_FILL
            c.font = HDR_FONT
            c.border = CELL_BORDER
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.freeze_panes = f"A{r + 1}"

    def write_row(ws, vals, green=False, vendor_col=None, amt_cols=None, bold_cols=None, height=None):
        """Data row — green or white alternating. vendor_col gets green bold text.
        Row height auto-sizes to the longest wrapped cell (e.g. Recommended
        Action) unless an explicit height is passed."""
        ws.append(vals)
        r = ws.max_row
        ws.row_dimensions[r].height = height if height is not None else row_height(ws, vals)
        amt_cols  = amt_cols  or set()
        bold_cols = bold_cols or set()
        fill = DATA_FILL if green else WHITE_FILL
        for i, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=i)
            c.fill = fill
            c.border = CELL_BORDER
            is_center = i in amt_cols or i in bold_cols
            c.alignment = Alignment(
                vertical="center",
                wrap_text=True,
                horizontal="center" if is_center else "left",
            )
            if vendor_col and i == vendor_col and v:
                c.font = Font(bold=True, color=GREEN_TEXT, size=10)
            elif i in bold_cols:
                c.font = Font(bold=True, size=10)
            if i in amt_cols and isinstance(v, (int, float)):
                c.number_format = AMT_FMT

    def amt(v):
        return round(v) if v else 0

    def top_vendors(flags, n=5):
        return ", ".join(f.get("vendor") or f.get("category", "") for f in flags[:n])

    # ── Overview ──────────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Overview"
    NCOLS = 6
    set_widths(ws, [12, 48, 8, 20, 38, 42])
    no_gridlines(ws)

    write_title(ws, "Moss — Software Overlap Detection", NCOLS, height=50)
    write_subtitle(ws, subtitle or "Software spend overlap analysis", NCOLS, height=22)

    # Column headers (write_hdr already adds a spacer row internally)
    write_hdr(ws, ["Type", "Description", "Flags", "Savings Potential (EUR)", "Key Vendors", "Recommended Action"])

    total_flags = len(t1) + len(t2) + len(t3)
    total_risk  = (
        sum(f["combined_annual"] for f in t1) +
        sum(f["overlap_spend"]   for f in t2) +
        sum(f["combined"]        for f in t3)
    )

    summary = [
        ("Type 1", "Potential individual or smaller subscriptions alongside a company-wide plan",
         len(t1), sum(f["combined_annual"] for f in t1), top_vendors(t1),
         "Confirm whether additional individual or smaller subscriptions are needed "
         "alongside the company-wide plan. Where the same access is already covered "
         "centrally, consolidate the subscriptions into the company-wide plan."),
        ("Type 2", "Potential parallel contracts or duplicate plans with the same vendor",
         len(t2), sum(f["overlap_spend"] for f in t2), top_vendors(t2),
         "Check whether the overlapping charges relate to separate services, add-ons "
         "or additional usage, or whether the same service is being paid for more than "
         "once. Where the scope overlaps, consolidate the contracts or remove the "
         "redundant spend."),
        ("Type 3", "Multiple vendors serving the same function and offering similar product capabilities",
         len(t3), sum(f["combined"] for f in t3), top_vendors(t3),
         "Review the tools currently used for the same function and compare the "
         "capabilities each one provides. Where tools cover substantially the same "
         "use case, assess whether the company can consolidate onto fewer solutions."),
    ]
    for idx, (type_label, desc, count, spend, vendors, action) in enumerate(summary):
        write_row(ws, [type_label, desc, count, amt(spend), vendors, action],
                  green=(idx % 2 == 0), vendor_col=1, amt_cols={4}, bold_cols={3, 4})

    # TOTAL row
    ws.append([None])
    ws.row_dimensions[ws.max_row].height = 4
    ws.append(["TOTAL", "", total_flags, amt(total_risk), "", ""])
    r = ws.max_row
    ws.row_dimensions[r].height = 24
    for i in range(1, NCOLS + 1):
        c = ws.cell(row=r, column=i)
        c.fill = HDR_FILL
        c.font = Font(bold=True, color=WHITE, size=10)
        c.border = CELL_BORDER
        c.alignment = Alignment(vertical="center")
        if i == 4:
            c.number_format = AMT_FMT

    write_note(
        ws,
        "Note: 'Savings Potential' reflects candidate amounts for review — not confirmed waste. "
        "Some overlap may be intentional. Every finding in this report needs a manual check "
        "before action — see the 'Reviewed' column on each detail sheet.",
        NCOLS,
    )

    # ── Duplicate Vendor Payments (Types 1 & 2, merged) ─────────────────────
    # Personal card duplicates (Type 1) and parallel contracts (Type 2) are
    # both "same vendor, duplicate payment stream" findings — just with a
    # different pair of payers (employee×employee vs. contract×contract).
    # Grouping by vendor means a vendor hit by both shows up once, with both
    # findings adjacent, instead of split across two tabs.
    #
    # Layout: a colored "Vendor Total" row first (the sum of every entry
    # below it — not any single invoice/employee's amount), then one row per
    # underlying transaction/contract. No entry is treated as "the primary"
    # one — every row gets its own Spend, Months Active, and Overlap Period,
    # computed the same way regardless of position in the list.
    ws2 = wb.create_sheet("Duplicate Vendor Payments")
    NCOLS2 = 10
    set_widths(ws2, [22, 16, 16, 12, 14, 12, 16, 12, 44, 10])
    no_gridlines(ws2)

    write_title(ws2, "Type 1 & 2 — Duplicate Vendor Payments (personal card duplicates + parallel contracts)", NCOLS2)
    t1_by_vendor = {f["vendor"]: f for f in t1}
    t2_by_vendor = {f["vendor"]: f for f in t2}
    dup_vendors  = list(t1_by_vendor) + [v for v in t2_by_vendor if v not in t1_by_vendor]

    def _vendor_total(v):
        total = 0.0
        if v in t1_by_vendor:
            total += t1_by_vendor[v]["combined_annual"]
        if v in t2_by_vendor:
            total += t2_by_vendor[v]["total_spend"]
        return total

    dup_vendors.sort(key=lambda v: -_vendor_total(v))
    dup_spend = sum(_vendor_total(v) for v in dup_vendors)

    write_subtitle(ws2,
        f"{len(t1) + len(t2)} flags across {len(dup_vendors)} vendors — {currency} {dup_spend:,.0f} at risk.",
        NCOLS2)
    write_note(ws2,
        "These are automatically detected candidates based on transaction account codes — "
        "not confirmed duplicates (transaction data alone can't prove duplication). Verify "
        "with the employees/vendor involved before taking action; the decision is Finance's "
        "to make. Mark the Reviewed column once checked.",
        NCOLS2)

    if not dup_vendors:
        ws2.append(["No personal card duplicates or parallel contracts detected."])
    else:
        write_hdr(ws2, ["Vendor", "Invoice Number", "Employee", "Cost Center",
                        "Spend (EUR)", "Months Active", "Overlap Period", "Duplicate Type",
                        "Recommended Action", "Reviewed"])
        for vendor in dup_vendors:
            t1_flag = t1_by_vendor.get(vendor)
            t2_flag = t2_by_vendor.get(vendor)

            # ── Vendor Total row — first and colored, sums everything below ──
            month_sets = []
            types_present = []
            if t1_flag:
                month_sets += [emp["month_set"] for emp in t1_flag["employees"]]
                types_present.append("Type 1")
            if t2_flag:
                month_sets += [inv["months"] for inv in t2_flag["invoices"]]
                types_present.append("Type 2")
            all_months = set().union(*month_sets) if month_sets else set()
            if all_months:
                srt_all = sorted(all_months)
                overall_period = f"{srt_all[0][0]}-{srt_all[0][1]:02d} → {srt_all[-1][0]}-{srt_all[-1][1]:02d}"
            else:
                overall_period = "—"

            write_row(ws2, [
                vendor,
                "—",
                "—",
                "—",
                amt(_vendor_total(vendor)),
                "—",
                overall_period,
                " & ".join(types_present),
                "—",
                "",
            ], green=True, vendor_col=1, amt_cols={5})

            # ── Type 1 entries — one row per employee, every field per-row ──
            if t1_flag:
                overlap_period = (
                    f"{t1_flag['overlap_start']} → {t1_flag['overlap_end']}"
                    if t1_flag.get("overlap_start") else "Not simultaneous"
                )
                for emp in t1_flag["employees"]:
                    write_row(ws2, [
                        "",
                        "—",
                        emp["employee"],
                        emp.get("kost1", "") or "—",
                        amt(emp["annual_spend"]),
                        emp["months_active"],
                        overlap_period,
                        "Type 1",
                        t1_flag["action"],
                        "",
                    ], green=False, vendor_col=1, amt_cols={5})

            # ── Type 2 entries — one row per invoice, every field per-row ───
            if t2_flag:
                overlap_period = f"{t2_flag['overlap_start']} → {t2_flag['overlap_end']}"
                for inv in t2_flag["invoices"]:
                    write_row(ws2, [
                        "",
                        inv["invoice_number"],
                        "—",
                        inv.get("kost1", "") or "—",
                        amt(inv["total"]),
                        len(inv["months"]),
                        overlap_period,
                        "Type 2",
                        t2_flag["action"],
                        "",
                    ], green=False, vendor_col=1, amt_cols={5})

            # Thin spacer row between vendors
            ws2.append([None])
            ws2.row_dimensions[ws2.max_row].height = 4

    # ── Category Overlap ──────────────────────────────────────────────────
    ws4 = wb.create_sheet("Category Overlap")
    NCOLS4 = 11
    set_widths(ws4, [16, 26, 14, 34, 13, 16, 18, 30, 30, 32, 10])
    no_gridlines(ws4)

    # Overlap row colours. Baseline pair rows (not yet reviewed by Claude)
    # deliberately do NOT use a red/orange/yellow urgency scale — a raw
    # Jaccard score is a hypothesis, not a verdict, and colouring it like a
    # confirmed critical duplicate overstates its reliability. All baseline
    # pairs (any grade, or none) get one neutral tone; only Claude's Pass-3
    # verdict (patched directly into these same cells, see SKILL.md) earns
    # the strong colours. CLUSTER stays visually distinct — it's a different
    # kind of finding ("N vendors look interchangeable by tag"), not a grade.
    GRADE_FILL = {
        "CLUSTER":  PatternFill("solid", fgColor="D1C4E9"),   # light purple
        "BASELINE": PatternFill("solid", fgColor="EEF1F5"),   # neutral gray-blue — unverified
    }
    GRADE_FONT = {
        "CLUSTER":  Font(bold=True, color="4527A0", size=9),
        "BASELINE": Font(bold=False, color="5C6BC0", size=9),
    }
    NOTE_FONT = Font(italic=True, size=9, color="999999")
    # Category summary row — its own distinct tone, stronger than the plain
    # white vendor rows below it, so it reads as a section header rather than
    # "just another vendor" (the old design overloaded the first vendor row
    # with the category total, which read as if that vendor were special).
    CATEGORY_FILL = PatternFill("solid", fgColor="CFE8D5")
    CATEGORY_FONT = Font(bold=True, color=GREEN_TEXT, size=10)
    SUBHDR_FONT   = Font(bold=True, italic=True, size=9, color=GREEN_TEXT)
    OVERLAP_CASE_COLS = {3, 4, 5, 6, 7, 11}  # centered: —, —, grade, amounts, Reviewed

    write_title(ws4, "Type 3 — Category Overlap (multiple vendors in the same function)", NCOLS4)
    t3_spend = sum(f["combined"] for f in t3)
    write_subtitle(ws4,
        f"{len(t3)} categories flagged — {currency} {t3_spend:,.0f} combined. Every vendor in "
        f"a flagged category is listed with its own spend and features; top overlaps per "
        f"category follow, ranked by EUR potentially recoverable — not every pairwise match, "
        f"and low-impact overlaps are hidden (see note per category).",
        NCOLS4)
    write_note(ws4,
        "These overlap findings are candidates for review, not confirmed duplicates — the "
        "baseline signal and (once patched) Claude's research are both starting points for a "
        "human decision, not a verdict. Mark the Reviewed column once a finding's been checked.",
        NCOLS4)

    if not t3:
        ws4.append(["No category overlap detected."])
    else:
        write_hdr(ws4, ["Category", "Vendor / Overlap Case", "Annual Spend (EUR)", "Features",
                        "Overlap", "Combined Spend (EUR)", "Potential Recoverable Spend (EUR)",
                        "Exact Feature Overlap", "Unique Capabilities", "Recommended Action",
                        "Reviewed"])
        for flag in t3:
            # ── Category summary row — tool count + total annual spend, ───
            # standing on its own rather than riding on the first vendor.
            summary_vals = [flag["category"], f"{len(flag['vendors'])} tools",
                             amt(flag["combined"]), "", "", "", "", "", "", "", ""]
            ws4.append(summary_vals)
            r = ws4.max_row
            ws4.row_dimensions[r].height = row_height(ws4, summary_vals)
            for col in range(1, NCOLS4 + 1):
                c = ws4.cell(row=r, column=col)
                c.fill = CATEGORY_FILL
                c.border = CELL_BORDER
                c.font = CATEGORY_FONT
                c.alignment = Alignment(vertical="center", wrap_text=True,
                                        horizontal="center" if col == 3 else "left")

            # ── Vendor rows — one per vendor, plain (the summary row above ──
            # is now the sole visual anchor for the category).
            for v in flag["vendors"]:
                write_row(ws4, [
                    "", v["vendor"], amt(v["annual_spend"]), PENDING_PASS3,
                    "", "", "", "", "", "", "",
                ], vendor_col=2, amt_cols={3})

            # ── Overlap section — only after every vendor has been listed ──
            entries = flag.get("pairs", [])
            ws4.append(["", "Potential overlaps in this category" if entries else
                        "No overlaps meeting the materiality threshold in this category."])
            r = ws4.max_row
            ws4.merge_cells(start_row=r, start_column=2, end_row=r, end_column=NCOLS4)
            ws4.cell(row=r, column=2).font = SUBHDR_FONT if entries else NOTE_FONT

            # Overlap rows — clusters and/or pairs, ranked by EUR potentially
            # recoverable (materiality), capped upstream to the most
            # actionable few. See _build_overlap_entries.
            for entry in entries:
                if entry["kind"] == "cluster":
                    label       = ", ".join(m["vendor"] for m in entry["members"])
                    overlap_str = f"DUPLICATE CLUSTER · {len(entry['members'])} vendors"
                    grade_key   = "CLUSTER"
                else:
                    label     = f"{entry['vendor_a']}  ×  {entry['vendor_b']}"
                    grade_key = "BASELINE"
                    if entry.get("baseline_grade") is not None:
                        overlap_str = f"{entry['baseline_grade']} · {entry['baseline_score']:.0%}"
                    else:
                        overlap_str = "No baseline data — pending research"

                row_vals = ["", label, "—", "—", overlap_str,
                            amt(entry["combined_spend"]), amt(entry["materiality"]),
                            entry["exact_overlap"], entry["unique_capabilities"],
                            entry["recommended_action"], ""]
                ws4.append(row_vals)
                r = ws4.max_row
                ws4.row_dimensions[r].height = row_height(ws4, row_vals)
                fill = GRADE_FILL.get(grade_key, WHITE_FILL)
                gfont = GRADE_FONT.get(grade_key, Font(size=9))
                for col in range(1, NCOLS4 + 1):
                    c = ws4.cell(row=r, column=col)
                    c.fill = fill
                    c.border = CELL_BORDER
                    c.alignment = Alignment(vertical="center", wrap_text=True,
                                            horizontal="center" if col in OVERLAP_CASE_COLS else "left")
                # Label — italic to visually distinguish from vendor rows
                ws4.cell(row=r, column=2).font = Font(italic=True, size=9)
                # Grade cell — bold coloured
                ws4.cell(row=r, column=5).font = gfont

            hidden = flag.get("hidden_pairs", 0)
            if hidden:
                ws4.append(["", f"+ {hidden} more lower-impact overlap"
                            f"{'s' if hidden != 1 else ''} not shown "
                            f"(below the materiality threshold or ranked lower)"])
                r = ws4.max_row
                ws4.merge_cells(start_row=r, start_column=2, end_row=r, end_column=NCOLS4)
                ws4.cell(row=r, column=2).font = NOTE_FONT

            # Spacer between categories
            ws4.append([None])
            ws4.row_dimensions[ws4.max_row].height = 4

    # ── Transactions ──────────────────────────────────────────────────────
    ws6 = wb.create_sheet("Transactions")
    set_widths(ws6, [24, 20, 16, 12, 10, 12, 12, 8, 8, 60])
    no_gridlines(ws6)

    write_hdr(ws6, ["Vendor", "Category", "Employee", "Gegenkonto", "Invoice #",
                    "Cost Center", "Amount", "Year", "Month", "Raw Text"])

    classified = sorted(
        [t for t in transactions if t["canonical"]],
        key=lambda t: (t["canonical"] or "", t["year"] or 0, t["month"] or 0)
    )
    for idx, t in enumerate(classified):
        write_row(ws6, [
            t["canonical"],
            t["category"] or "",
            t["employee"] or "",
            t["gegenkonto"],
            t["belegfeld1"],
            t["kost1"],
            round(t["amount"], 2),
            t["year"],
            t["month"],
            t["raw_text"][:150],
        ], green=(idx % 2 == 0), amt_cols={7}, height=16)

    wb.save(path)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Moss — Software Overlap Detection")
    ap.add_argument("--input",    required=True,  help="Transaction file (XLSX, CSV, PDF)")
    ap.add_argument("--output",   default="")
    ap.add_argument("--taxonomy", required=True,  help="Path to vendor_taxonomy.csv")
    ap.add_argument("--currency", default="EUR")
    ap.add_argument("--min-category-vendors", type=int,   default=3,
                    help="Min vendors in a category to flag (default: 3)")
    ap.add_argument("--min-category-spend",   type=float, default=10000,
                    help="Min combined annual spend in a category to flag (default: 10000)")
    ap.add_argument("--subtitle", default="",
                    help="Company name / file description shown under the title (e.g. 'Nufin GmbH — Aufwendungen für Lizenzen 2025')")
    ap.add_argument("--features", default="",
                    help="Path to vendor_features.csv for functional overlap scoring. "
                         "Defaults to vendor_features.csv next to --taxonomy.")
    ap.add_argument("--min-pair-spend", type=float, default=2000,
                    help="Min EUR recoverable (smaller vendor's spend, or cluster's "
                         "combined spend minus its top vendor) for an overlap to be "
                         "shown at all — filters out immaterial pairs (default: 2000)")
    ap.add_argument("--max-pairs-per-category", type=int, default=5,
                    help="Max overlap entries (pairs + clusters) shown per category, "
                         "ranked by EUR recoverable (default: 5)")
    args = ap.parse_args()

    print("Loading taxonomy...")
    taxonomy = load_taxonomy(args.taxonomy)
    print(f"  {len(taxonomy)} patterns loaded")

    # Load feature map (optional — gracefully skipped if file not found)
    features_path = args.features or os.path.join(
        os.path.dirname(args.taxonomy), "vendor_features.csv"
    )
    print("Loading feature map...")
    features = load_features(features_path)
    if features:
        print(f"  {len(features)} vendors with feature tags loaded")
    else:
        print("  No vendor_features.csv found — overlap grades will not be shown")

    print("Loading and classifying transactions...")
    transactions, is_datev = load_and_classify(args.input, taxonomy)

    print("Running overlap detectors...")
    if is_datev:
        t1 = detect_type1(transactions)
        t2 = detect_type2(transactions)
        print(f"  Type 1 — Personal card duplicates:  {len(t1)} flags")
        print(f"  Type 2 — Parallel contracts:        {len(t2)} flags")
    else:
        t1, t2 = [], []
        print("  Types 1, 2 — skipped (DATEV format required)")

    t3 = detect_type3(transactions, args.min_category_vendors, args.min_category_spend,
                      features=features, min_pair_spend=args.min_pair_spend,
                      max_pairs_per_category=args.max_pairs_per_category)
    print(f"  Type 3 — Category overlap:          {len(t3)} flags")

    total = len(t1) + len(t2) + len(t3)
    print(f"\nTotal flags: {total}")

    # Derive year from transaction data — use the most common year in the file
    from collections import Counter
    year_counts = Counter(t["year"] for t in transactions if t.get("year"))
    year_suffix = str(year_counts.most_common(1)[0][0]) if year_counts else "report"

    output = args.output if args.output else f"Moss_Overlap_Report_{year_suffix}.xlsx"

    print("Writing report...")
    write_report(output, t1, t2, t3, transactions, args.currency, subtitle=args.subtitle)
    print("Done.")

    # ── Pass 3 — Functional overlap analysis block for Claude ─────────────
    # Print a structured block for Claude to analyse in-context.
    # Claude reads this, assesses replacement coverage per vendor pair,
    # and patches the Category Overlap sheet with its findings.
    if t3:
        print("\n--- FUNCTIONAL OVERLAP ANALYSIS REQUEST ---")
        print(f"Report file: {output}")
        print(f"Currency: {args.currency}")
        print()
        print("For each category below, analyse vendor pairs and determine")
        print("whether any vendor can functionally replace another.")
        print()
        print("Your PRIMARY method is real research per candidate: look up each")
        print("vendor's product/pricing page, search for 'A vs B' comparison")
        print("content, and search for migration/switching articles ('switching")
        print("from A to B'). Combine that with your own product knowledge.")
        print()
        print("Entries marked 'no baseline tag data' are NORMAL and EXPECTED — most")
        print("vendors are not in the internal feature-tag reference file, and that")
        print("is not evidence of no overlap. Research them exactly like any other")
        print("entry. Where a baseline score IS shown, treat it as a SECONDARY,")
        print("fallback signal — lean on it more only when research is inconclusive")
        print("or unavailable, never as a substitute for actually checking.")
        print()
        print("Department breakdown is shown per vendor. If two vendors in the")
        print("same category are used almost exclusively by different departments,")
        print("treat that as a signal the split may be intentional (different team")
        print("needs) rather than an accidental duplicate — say so explicitly rather")
        print("than defaulting to 'cancel the smaller one'.")
        print()
        print("EVERY vendor listed below (not just the overlap candidates) needs a")
        print("short, plain-English Features description — what the tool actually")
        print("does, ~8-12 words, no marketing language. The Excel report lists")
        print("every vendor individually; this is what fills that column in.")
        print()
        print("Only the top few overlaps per category are listed below, ranked by")
        print("EUR recoverable — low-materiality pairs were already filtered out,")
        print("don't try to reconstruct or add more from your own knowledge. A")
        print("'Cluster' entry means 3+ vendors share an identical feature-tag set")
        print("— analyse it as one group (how many of them should realistically be")
        print("kept?), not as separate pairs.")
        print()
        for flag in t3:
            vcount = flag["vendor_count"]
            combined = flag["combined"]
            print(f"Category: {flag['category']}  ({vcount} vendors  |  {args.currency} {combined:,.0f} combined/yr)")
            for v in flag["vendors"]:
                depts = v.get("departments") or []
                dept_str = ", ".join(f"{d['kost1']} {d['share']:.0%}" for d in depts[:3])
                print(f"  - {v['vendor']}: {args.currency} {v['annual_spend']:,.0f}/yr"
                      f"  [depts: {dept_str or 'unknown'}]")
            entries = flag.get("pairs") or []
            if entries:
                print("  Top candidates for research (ranked by EUR recoverable):")
                for e in entries:
                    shared_str = ", ".join(_humanize_tag(t) for t in e["shared"][:5])
                    if e["kind"] == "cluster":
                        names = ", ".join(m["vendor"] for m in e["members"])
                        print(f"    - CLUSTER ({len(e['members'])} vendors, identical tags): "
                              f"{names} — {args.currency} {e['spend']:,.0f}/yr combined, "
                              f"{args.currency} {e['materiality']:,.0f} recoverable if consolidated "
                              f"— shared: {shared_str or 'n/a'}")
                    elif e.get("baseline_grade") is not None:
                        print(f"    - {e['vendor_a']} × {e['vendor_b']}: "
                              f"baseline signal {e['baseline_grade']} ({e['baseline_score']:.0%}) — "
                              f"{args.currency} {e['materiality']:,.0f} recoverable — "
                              f"shared: {shared_str or 'n/a'}")
                    else:
                        print(f"    - {e['vendor_a']} × {e['vendor_b']}: "
                              f"no baseline tag data — research required — "
                              f"{args.currency} {e['materiality']:,.0f} recoverable")
            hidden = flag.get("hidden_pairs", 0)
            if hidden:
                print(f"  (+{hidden} more lower-impact overlaps not shown)")
            print()
        print("--- END FUNCTIONAL OVERLAP ANALYSIS REQUEST ---")


if __name__ == "__main__":
    main()
