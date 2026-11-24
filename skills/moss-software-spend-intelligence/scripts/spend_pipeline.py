#!/usr/bin/env python3
"""Moss - Software Spend Intelligence: single-pass pipeline.

Takes any transaction file → produces spend_report.xlsx with amounts per
vendor per month. No intermediate files needed.

Architecture
------------
1. normalize()      - detect format, extract (description, amount, date, guid, gegen)
2. deduplicate()    - DATEV: one row per GUID; bank: one row per line
3. extract_candidates() - clean & deduplicate description strings
4. match_taxonomy() - deterministic Pass 1 (~87% hit rate)
5. llm_classify()   - Pass 2 for unmatched candidates (LLM via Anthropic API)
6. aggregate()      - sum spend per canonical vendor per month
7. write_report()   - Excel with 3 sheets

Usage
-----
    python3 spend_pipeline.py --input FILE [--output spend_report.xlsx]
                              [--taxonomy PATH_TO_vendor_taxonomy.csv]
                              [--currency EUR]
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Transactions above this threshold are likely intercompany transfers, revenue
# collection flows, or payment infrastructure operations - not software subscriptions.
# Adjust per client if needed (e.g. enterprise Datadog/Salesforce can be >100k).
MAX_TRANSACTION_EUR = 200_000

# ---------------------------------------------------------------------------
# 1. NORMALIZE - detect format, extract rows
# ---------------------------------------------------------------------------

DATEV_DESCRIPTION_COL = "Buchungstext"
DATEV_GUID_COL        = "Buchungs GUID"
DATEV_GEGEN_COL       = "Gegenkonto"
DATEV_SOLL_COL        = "Umsatz Soll"
DATEV_HABEN_COL       = "Umsatz Haben"
DATEV_DATE_COL        = "Belegdatum"

# Synonyms for description / amount / date in generic formats.
# Merged from spend-surface normalize.py + Xero/DATEV specifics.
DESC_SYNONYMS = [
    "buchungstext", "transaction description", "description", "memo", "narrative",
    "details", "transaction details", "omschrijving", "libellé", "riferimento",
    "concepto", "text", "booking text", "particulars", "merchant", "vendor",
    "payee", "beneficiary", "remittance info", "verwendungszweck",
    "zahlungsreferenz", "referenz",
]
AMOUNT_SYNONYMS = [
    "betrag", "amount", "umsatz", "bedrag", "montant", "importe",
    "debit amount", "credit amount", "debit", "credit", "soll", "haben",
    "value", "sum", "total", "spent",
]
DATE_SYNONYMS = [
    "buchungsdatum", "datum", "date", "booking date", "transaction date",
    "posting date", "value date", "valuta", "wertstellung",
    "fecha", "data", "datum der buchung",
]

# Counterpart accounts that signal a real cash payment in DATEV
DATEV_PAYMENT_GEGEN = {"160000", "7999999", "150011", "150013", "121003", "121706"}


def _best_col(columns, synonyms):
    lc = {c.lower(): c for c in columns}
    for s in synonyms:
        if s in lc:
            return lc[s]
    return None


def _to_float(x):
    if x is None:
        return None
    s = str(x).strip()
    if s in ("", "nan", "NaN", "-"):
        return None
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


def _read_file(path):
    """Return (columns, rows_as_dicts) for xlsx/csv/tsv.

    Handles files where row 0 is a metadata title and real headers are in row 1
    (e.g. DATEV Kontoblatt exports, Xero exports).
    """
    import pandas as pd
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path, dtype=str, header=0).fillna("")
    else:
        df = pd.read_csv(path, dtype=str, sep=None, engine="python").fillna("")

    # Detect metadata header: if first column looks like a title string
    # and second row contains recognisable column names
    if len(df) > 0:
        first_col = str(df.columns[0])
        # Check if real headers are in first data row
        first_row = df.iloc[0].tolist()
        known_headers = {"Buchungstext", "Date", "Datum", "Description",
                         "Transaction Description", "Omschrijving", "BL", "HK"}
        if any(str(v).strip() in known_headers for v in first_row):
            # Promote first row to header
            df.columns = [str(v).strip() for v in first_row]
            df = df.iloc[1:].reset_index(drop=True).fillna("")

    return list(df.columns), df.to_dict("records")


def _read_pdf(path):
    """Extract table from text PDF. Raises RuntimeError('SCANNED') if image-only."""
    try:
        import pdfplumber
    except ImportError:
        sys.exit("pdfplumber required: pip install pdfplumber --break-system-packages")

    all_rows, total_chars = [], 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            total_chars += len((page.extract_text() or "").strip())
            for table in page.extract_tables():
                for row in table:
                    all_rows.append([str(c or "").strip() for c in row])

    if total_chars < 50 and not all_rows:
        raise RuntimeError("SCANNED")
    if not all_rows:
        raise RuntimeError("SCANNED")

    columns = all_rows[0]
    rows = [dict(zip(columns, r)) for r in all_rows[1:]]
    return columns, rows


SCANNED_NOTICE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SKILL LIMITATION - Scanned PDF detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  This skill reads text-based PDFs only. The file you
  uploaded appears to be a scanned image.

  Please export as a text PDF or CSV from your bank
  portal and re-upload.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

UNSUPPORTED_NOTICE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SKILL LIMITATION - Unsupported file format
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Supported: XLSX, XLS, CSV, TSV, text-based PDF.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def normalize(path):
    """Load file, detect format, return list of raw transaction dicts.

    Each dict: {description, amount_raw, year, month, guid, gegen, is_datev}
    """
    ext = os.path.splitext(path)[1].lower()

    if ext not in (".xlsx", ".xlsm", ".xls", ".csv", ".tsv", ".pdf"):
        print(UNSUPPORTED_NOTICE)
        sys.exit(1)

    if ext == ".pdf":
        try:
            columns, rows = _read_pdf(path)
        except RuntimeError:
            print(SCANNED_NOTICE)
            sys.exit(2)
    else:
        columns, rows = _read_file(path)

    col_set = set(columns)

    # ── Xero bank statement detection ─────────────────────────────────────
    # Xero exports have N metadata rows before real headers (Date/Type/Description/Spent).
    # Scan the first 10 rows to find the real header line.
    xero_hdr_idx = None
    for _ri, _row in enumerate(rows[:10]):
        _vals = {str(v).strip() for v in _row.values()}
        if {"Date", "Type", "Description", "Spent"}.issubset(_vals):
            xero_hdr_idx = _ri
            break
    if xero_hdr_idx is not None:
        real_cols = [str(rows[xero_hdr_idx].get(c, "")).strip() for c in columns]
        rows = [{real_cols[i]: str(row.get(c, "")).strip()
                 for i, c in enumerate(columns)}
                for row in rows[xero_hdr_idx + 1:]]
        columns = real_cols
        col_set  = set(columns)
        print("Format detected: Xero bank statement")

    is_datev = DATEV_DESCRIPTION_COL in columns
    # Kontoblatt = single-account DATEV ledger (has HK + BSNr cols, no Buchungs GUID)
    is_kontoblatt = (is_datev
                     and "HK" in col_set
                     and "BSNr." in col_set
                     and DATEV_GUID_COL not in col_set)

    txns = []
    if is_kontoblatt:
        print("Format detected: DATEV Kontoblatt (single-account ledger)")
        # Kontoblatt uses "Datum", full DATEV uses "Belegdatum"
        date_col_kbl = "Datum" if "Datum" in col_set else DATEV_DATE_COL
        for row in rows:
            desc = str(row.get(DATEV_DESCRIPTION_COL, "")).strip()
            if not desc:
                continue
            soll  = _to_float(row.get(DATEV_SOLL_COL))
            if not soll or soll <= 0:
                continue
            year, month = _parse_date(row.get(date_col_kbl))
            txns.append({
                "description": desc,
                "amount_raw":  soll,
                "year":        year,
                "month":       month,
                "guid":        "",        # no GUID in Kontoblatt
                "gegen":       str(row.get(DATEV_GEGEN_COL, "")).strip(),
                "is_datev":    False,     # treat as bank format (no dedup)
                "is_kontoblatt": True,
            })
    elif is_datev:
        print("Format detected: DATEV")
        for row in rows:
            desc = str(row.get(DATEV_DESCRIPTION_COL, "")).strip()
            if not desc:
                continue
            soll  = _to_float(row.get(DATEV_SOLL_COL))
            haben = _to_float(row.get(DATEV_HABEN_COL))
            # Signed amount: soll = debit (cost), haben = credit (income/refund)
            if soll and soll > 0:
                amount_raw = soll
            elif haben and haben > 0:
                amount_raw = -haben  # credit = negative spend
            else:
                amount_raw = None
            year, month = _parse_date(row.get(DATEV_DATE_COL))
            txns.append({
                "description": desc,
                "amount_raw":  amount_raw,
                "year":        year,
                "month":       month,
                "guid":        str(row.get(DATEV_GUID_COL, "")).strip(),
                "gegen":       str(row.get(DATEV_GEGEN_COL, "")).strip(),
                "is_datev":    True,
            })
    else:
        desc_col   = _best_col(columns, DESC_SYNONYMS)
        amount_col = _best_col(columns, AMOUNT_SYNONYMS)
        date_col   = _best_col(columns, DATE_SYNONYMS)

        if not desc_col:
            # Interactive fallback - support column number or partial name
            print("\nCould not auto-detect description column.")
            print("Available columns:\n")
            for _ci, _cn in enumerate(columns, 1):
                print(f"  {_ci:>3}. {_cn}")
            print()
            while True:
                _ans = input("Which column contains the vendor/description? (name or number): ").strip()
                if _ans.isdigit():
                    _idx = int(_ans) - 1
                    if 0 <= _idx < len(columns):
                        desc_col = columns[_idx]
                        break
                    print(f"  Number out of range. Enter 1–{len(columns)}.")
                    continue
                _exact = next((c for c in columns if c.lower() == _ans.lower()), None)
                if _exact:
                    desc_col = _exact
                    break
                _partials = [c for c in columns if _ans.lower() in c.lower()]
                if len(_partials) == 1:
                    desc_col = _partials[0]
                    print(f"  Matched: '{desc_col}'")
                    break
                if len(_partials) > 1:
                    print(f"  Ambiguous - matches: {_partials}. Be more specific.")
                    continue
                print(f"  Column '{_ans}' not found. Try again.")

        print(f"Format detected: generic  |  description='{desc_col}'  "
              f"amount='{amount_col}'  date='{date_col}'")

        # Xero: Type column DD = Direct Debit (expense), CR = credit - keep only DD
        xero_type_col = "Type" if "Type" in col_set else None

        for row in rows:
            desc = str(row.get(desc_col, "")).strip()
            if not desc:
                continue
            # Skip Xero credit rows
            if xero_type_col and str(row.get(xero_type_col, "")).strip() == "CR":
                continue
            amount_raw = _to_float(row.get(amount_col)) if amount_col else None
            # Xero Spent column is positive; normalise to positive (pipeline expects > 0)
            if amount_col and amount_col.lower() == "spent" and amount_raw is not None:
                amount_raw = abs(amount_raw)
            year, month = _parse_date(row.get(date_col)) if date_col else (None, None)
            txns.append({
                "description": desc,
                "amount_raw":  amount_raw,
                "year":        year,
                "month":       month,
                "guid":        "",
                "gegen":       "",
                "is_datev":    False,
            })

    print(f"  → {len(txns)} rows loaded")
    return txns


# ---------------------------------------------------------------------------
# 2. DEDUPLICATE - one economic event per row
# ---------------------------------------------------------------------------

def deduplicate(txns):
    """For DATEV: deduplicate by GUID using cash-basis logic.
    For bank formats: keep all rows, filter to expenses only.

    Returns list of dicts: {description, amount, year, month}
    amount is always positive = spend; refunds/credits are excluded.
    """
    if not txns:
        return []

    is_datev = txns[0]["is_datev"]

    if is_datev:
        # Group by GUID
        guid_groups = defaultdict(list)
        no_guid = []
        for t in txns:
            if t["guid"]:
                guid_groups[t["guid"]].append(t)
            else:
                no_guid.append(t)

        result = []
        for guid, group in guid_groups.items():
            # Prefer rows where counterpart is a real payment account
            pay_rows = [r for r in group if r["gegen"] in DATEV_PAYMENT_GEGEN]
            candidates = pay_rows if pay_rows else group
            # Take the row with the largest positive amount (expense debit)
            best = max(candidates, key=lambda r: (r["amount_raw"] or 0))
            amt = best["amount_raw"] or 0
            if amt <= 0:
                continue
            result.append({
                "description": best["description"],
                "amount":      amt,
                "year":        best["year"],
                "month":       best["month"],
            })

        # No-GUID rows: take as-is if positive
        for t in no_guid:
            amt = t["amount_raw"] or 0
            if amt > 0:
                result.append({"description": t["description"],
                               "amount": amt, "year": t["year"], "month": t["month"]})
        before = len(result)
        result = [t for t in result if t["amount"] <= MAX_TRANSACTION_EUR]
        if before - len(result):
            print(f"  → Filtered {before - len(result)} transactions above "
                  f"{MAX_TRANSACTION_EUR:,} EUR cap")
        print(f"  → DATEV dedup: {len(guid_groups)} GUIDs + {len(no_guid)} ungrouped "
              f"→ {len(result)} transactions")
        return result

    else:
        # Bank format or Kontoblatt
        result = []
        for t in txns:
            amt = t["amount_raw"]
            if amt is None:
                continue
            # Kontoblatt / Xero: amounts are already positive = expenses
            if t.get("is_kontoblatt") or amt > 0:
                result.append({"description": t["description"],
                               "amount": abs(amt),
                               "year": t["year"], "month": t["month"]})
            # Generic bank format: negative = expense (money leaving account)
            elif amt < 0:
                result.append({"description": t["description"],
                               "amount": abs(amt),
                               "year": t["year"], "month": t["month"]})
            # Zero amount - skip
        before = len(result)
        result = [t for t in result if t["amount"] <= MAX_TRANSACTION_EUR]
        if before - len(result):
            print(f"  → Filtered {before - len(result)} transactions above "
                  f"{MAX_TRANSACTION_EUR:,} EUR cap")
        print(f"  → Bank dedup: {len(result)} expense transactions "
              f"(skipped {len(txns)-len(result)} credits/income)")
        return result


# ---------------------------------------------------------------------------
# 3. EXTRACT CANDIDATES - clean & deduplicate descriptions
# ---------------------------------------------------------------------------

# Reused from extract_candidates.py
PAYMENT_PREFIXES = re.compile(
    r"^(paypal\s*\*?|pp\*|stripe\s*\*?|sumup\s*\*?|sq\s*\*|gpay\s+|apple\.com/bill\s*|"
    r"amzn\s+mktp\s*|checkout\.com\s*|mollie\s*\*?|adyen\s*\*?)",
    re.IGNORECASE,
)
NOISE_TOKENS = re.compile(
    r"\b(inv(oice)?[\s#:.\-]*\d+|re(chnung)?[\s#:.\-]*\d+|ref[\s#:.\-]*\w+|"
    r"\d{2}[./-]\d{2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}|[a-z]{2}\d{2}[a-z0-9]{10,30}|\d{5,})\b",
    re.IGNORECASE,
)
TRAILING_LEGAL = re.compile(
    r"[\s,]+(gmbh|ag|inc\.?|llc|ltd\.?|limited|corp\.?|co\.?|b\.?v\.?|s\.?a\.?|"
    r"ug|kg|ohg|se|plc|pte|oy|ab|aps)\.?$",
    re.IGNORECASE,
)
MULTISPACES = re.compile(r"\s+")
PUNCT_EDGES = re.compile(r"^[\s\-_*.,;:/\\|]+|[\s\-_*.,;:/\\|]+$")
STOPWORDS = {
    "accrual","accruals","release","prepaid","exp","expense","expenses",
    "gehalt","lohn","umbuchung","sammelbuchung","rückstellung","abgrenzung","storno",
    "vorsteuer","umsatzsteuer","ust","steuer","sozialversicherung",
    "opening","balance","zinsen","bankgebühr","kontoführung",
    "invoice","rechnung","payment","pmt","zahlung","gutschrift","erstattung",
    "subscription","license","licences","licence","lizenz","lizenzen",
    "monthly","annual","fee","fees",
}
PERSON_NAME = re.compile(r"^[A-ZÄÖÜ]\.\s?[A-ZÄÖÜ][a-zäöüßA-Za-z\-]+$")


def _cleanse(raw):
    s = raw.strip()
    # Take first segment before semicolons (DATEV multi-part descriptions)
    parts = [p.strip() for p in s.split(";") if p.strip()]
    # Filter out person names
    parts = [p for p in parts if not PERSON_NAME.match(p)]
    s = parts[0] if parts else s
    s = PAYMENT_PREFIXES.sub("", s)
    s = NOISE_TOKENS.sub(" ", s)
    tokens = [t for t in s.split() if t.lower() not in STOPWORDS]
    s = " ".join(tokens)
    s = TRAILING_LEGAL.sub("", s)
    s = PUNCT_EDGES.sub("", s)
    s = MULTISPACES.sub(" ", s).strip()
    return s or raw.strip()


def extract_candidates(transactions):
    """Returns dict: {candidate_str: {amount_total, tx_count, months, sample_original}}"""
    candidates = defaultdict(lambda: {"amount": 0.0, "tx_count": 0,
                                       "months": set(), "sample": ""})
    for t in transactions:
        raw  = t["description"]
        cand = _cleanse(raw)
        if len(cand) < 3:
            continue
        key = cand.lower()
        candidates[key]["amount"]   += t["amount"]
        candidates[key]["tx_count"] += 1
        if t["year"] and t["month"]:
            candidates[key]["months"].add((t["year"], t["month"]))
        if not candidates[key]["sample"]:
            candidates[key]["sample"] = raw

    print(f"  → {len(candidates)} unique candidates after cleansing")
    return candidates


# ---------------------------------------------------------------------------
# 4. MATCH TAXONOMY - deterministic Pass 1
# ---------------------------------------------------------------------------

def load_taxonomy(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _taxonomy_match(text_lower, taxonomy):
    for row in taxonomy:
        p = row["pattern"]
        if row["match_type"] == "exact":
            if text_lower == p:
                return row
        else:
            if p in text_lower:
                return row
    return None


def match_taxonomy(candidates, taxonomy):
    """Returns (matched, unmatched, excluded).

    matched:  {candidate_key: {canonical, category, is_ai, ...candidate_data}}
    unmatched: {candidate_key: candidate_data}
    excluded: set of candidate_keys
    """
    matched, unmatched, excluded = {}, {}, set()

    for key, data in candidates.items():
        hit = _taxonomy_match(key, taxonomy)
        if hit is None:
            hit = _taxonomy_match(data["sample"].lower(), taxonomy)

        if hit:
            if hit["is_excluded"] == "1":
                excluded.add(key)
            else:
                matched[key] = {**data, "canonical": hit["canonical"],
                                "category": hit["category"], "is_ai": hit["is_ai"]}
        else:
            unmatched[key] = data

    n_canon = len({v["canonical"] for v in matched.values()})
    print(f"  → Taxonomy: {n_canon} vendors matched, "
          f"{len(excluded)} excluded, {len(unmatched)} → LLM pass")
    return matched, unmatched, excluded


# ---------------------------------------------------------------------------
# 5. LLM CLASSIFY - Pass 2 for unmatched candidates
# ---------------------------------------------------------------------------

def _print_unmatched_for_claude(items):
    """Print unmatched candidates so Claude can classify them in-context."""
    top = items[:30]  # top 30 by tx_count
    print("  --- UNMATCHED CANDIDATES (top by frequency) ---")
    for key, data in top:
        print(f"  {key!r}  (tx_count={data['tx_count']}, amount={data['amount']:.0f})")
    print("  --- END UNMATCHED CANDIDATES ---")


LLM_SYSTEM = """You are a software spend classifier. Given a list of transaction
descriptions, decide for each whether it represents a software, SaaS, cloud, or
digital tool purchase. Return ONLY a JSON array - no prose, no markdown.

Each element: {"candidate": "<exact input string>", "is_software": true/false,
               "canonical": "<clean vendor name or empty string if not software>",
               "category": "<one of: AI Tools, Cloud Infrastructure, Productivity,
                             Security, Finance Tools, HR Tools, Sales & Marketing,
                             Dev Tools, Design Tools, Analytics, Communication,
                             Other Software>"}

Rules:
- is_software=true only for software, SaaS, cloud services, digital subscriptions
- is_software=false for physical goods, human services, rent, utilities, payroll,
  bank fees, intercompany transfers, or anything unclear
- canonical: use the well-known product/company name; empty string if is_software=false
- Be conservative: when in doubt, is_software=false"""

LLM_BATCH_SIZE = 80


def llm_classify(unmatched: dict) -> dict:
    """Classify unmatched candidates via Anthropic API.

    Returns {candidate_key: {canonical, category, is_ai}} for software ones.
    """
    if not unmatched:
        return {}

    # Sort by tx_count descending - prioritise high-frequency candidates
    items = sorted(unmatched.items(), key=lambda x: -x[1]["tx_count"])

    try:
        import anthropic
        client = anthropic.Anthropic()
    except ImportError:
        _print_unmatched_for_claude(items)
        return {}
    except Exception as e:
        _print_unmatched_for_claude(items)
        return {}

    results = {}
    batches = [items[i:i+LLM_BATCH_SIZE] for i in range(0, len(items), LLM_BATCH_SIZE)]
    print(f"  → LLM pass: {len(items)} candidates in {len(batches)} batch(es)")

    for b_idx, batch in enumerate(batches):
        candidates_list = [key for key, _ in batch]
        prompt = json.dumps(candidates_list, ensure_ascii=False)

        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=LLM_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
            parsed = json.loads(raw)

            for item in parsed:
                if item.get("is_software") and item.get("canonical"):
                    key = item["candidate"].lower()
                    results[key] = {
                        "canonical": item["canonical"],
                        "category":  item.get("category", "Other Software"),
                        "is_ai":     "1" if "ai" in item.get("category", "").lower() else "0",
                    }
        except Exception as e:
            print(f"  WARNING: LLM batch {b_idx+1} failed ({e})")
            continue

        print(f"  → Batch {b_idx+1}/{len(batches)}: "
              f"{sum(1 for k,_ in batch if k in results)} software found")

    return results


# ---------------------------------------------------------------------------
# 6. AGGREGATE - sum spend per canonical vendor per month
# ---------------------------------------------------------------------------

def aggregate(transactions, matched, llm_results):
    """Map each transaction to a canonical vendor and sum spend.

    Returns:
        merged: {canonical: {desc, category, total, tx_count, months: {(y,m): float}}}
        classified_txns: list of {description, canonical, category, amount, year, month}
            - only software transactions with a resolved canonical vendor
    """
    # Build lookup: candidate_key → canonical info
    lookup = {}
    for key, data in matched.items():
        lookup[key] = {"canonical": data["canonical"], "category": data["category"]}
    for key, data in llm_results.items():
        if key not in lookup:
            lookup[key] = {"canonical": data["canonical"], "category": data["category"]}

    result = defaultdict(lambda: {"desc": "", "category": "", "total": 0.0,
                                   "tx_count": 0, "months": defaultdict(float)})
    raw_classified = []  # pre-merge classified transactions

    for t in transactions:
        raw  = t["description"]
        cand = _cleanse(raw).lower()

        # Try exact candidate match first, then substring scan
        info = lookup.get(cand)
        if info is None:
            for key, val in lookup.items():
                if key in cand or cand in key:
                    info = val
                    break

        if info is None:
            continue

        canon = info["canonical"]
        ym    = (t["year"], t["month"]) if t["year"] else (None, None)
        result[canon]["total"]    += t["amount"]
        result[canon]["tx_count"] += 1
        result[canon]["months"][ym] += t["amount"]
        if not result[canon]["category"]:
            result[canon]["category"] = info["category"]
        raw_classified.append({
            "description": raw,
            "canonical":   canon,
            "category":    info["category"],
            "amount":      t["amount"],
            "year":        t["year"],
            "month":       t["month"],
        })

    # Merge canonical variants: same name in different cases or with suffix
    # e.g. "Figma" + "FIGMA" + "FigmaSubscription" → all map to single entry
    merge_map = {}  # old canonical → merged canonical
    merged = {}
    for vendor, data in result.items():
        # Normalise: lowercase, strip common suffixes
        key = vendor.lower()
        key = re.sub(r'\s*(inc\.?|llc|ltd\.?|gmbh|ag|b\.?v\.?|sas|corp\.?)$', '', key).strip()
        key = re.sub(r'[*\s]+', ' ', key).strip()
        # Find if a "better" (title-case, shorter) version already exists
        existing = None
        for k in merged:
            nk = k.lower()
            nk = re.sub(r'\s*(inc\.?|llc|ltd\.?|gmbh|ag|b\.?v\.?|sas|corp\.?)$', '', nk).strip()
            if nk == key or key.startswith(nk) or nk.startswith(key):
                existing = k
                break
        if existing:
            merged[existing]["total"]    += data["total"]
            merged[existing]["tx_count"] += data["tx_count"]
            for ym, amt in data["months"].items():
                merged[existing]["months"][ym] = merged[existing]["months"].get(ym, 0) + amt
            merge_map[vendor] = existing
        else:
            merged[vendor] = dict(data)
            merged[vendor]["months"] = dict(data["months"])
            merge_map[vendor] = vendor

    # Apply merge map so each transaction carries the final canonical vendor name
    classified_txns = []
    for t in raw_classified:
        final_canon = merge_map.get(t["canonical"], t["canonical"])
        classified_txns.append({**t, "canonical": final_canon})

    n_before = len(result)
    n_after  = len(merged)
    if n_before != n_after:
        print(f"  → Canonical merge: {n_before} → {n_after} vendors "
              f"({n_before - n_after} duplicates merged)")
    print(f"  → {n_after} vendors with spend data")
    return merged, classified_txns



# ---------------------------------------------------------------------------
# INSIGHTS - automatic anomaly detection
# ---------------------------------------------------------------------------

def generate_insights(agg, all_months):
    """Analyse aggregated spend and return a list of insight strings.

    Checks for:
    - Vendors with abnormally high single-month spend vs their own average
    - Vendors with sudden drop to zero (potential churn / cancellation)
    - Months with large MoM swings at portfolio level
    - Partial last month (data cut-off warning)
    - Category concentration (top category >40% of total)
    """
    insights = []
    if not agg or not all_months:
        return insights

    total_spend = sum(d["total"] for d in agg.values())
    month_totals = {}
    for ym in all_months:
        month_totals[ym] = sum(v["months"].get(ym, 0) for v in agg.values())

    # ── Partial last month ──────────────────────────────────────────────────
    if len(all_months) >= 2:
        last_ym  = all_months[-1]
        prev_ym  = all_months[-2]
        last_tot = month_totals[last_ym]
        prev_tot = month_totals[prev_ym]
        if prev_tot > 0 and last_tot < prev_tot * 0.3:
            y, m = last_ym
            insights.append(
                f"⚠️  Data appears cut off mid-{y}-{m:02d} - only "
                f"{last_tot:,.0f} EUR recorded vs {prev_tot:,.0f} EUR in prior month. "
                f"Last month figures are incomplete."
            )

    # ── Portfolio MoM swings ────────────────────────────────────────────────
    sorted_months = all_months[:]
    for i in range(1, len(sorted_months) - 1):  # skip last (partial)
        ym   = sorted_months[i]
        prev = sorted_months[i - 1]
        cur  = month_totals[ym]
        prv  = month_totals[prev]
        if prv > 0:
            delta = (cur - prv) / prv
            y, m = ym
            if delta > 0.30:
                insights.append(
                    f"📈  {y}-{m:02d}: total software spend up {delta*100:.0f}% MoM "
                    f"({prv:,.0f} → {cur:,.0f} EUR). "
                    f"Likely an annual subscription payment landing this month."
                )
            elif delta < -0.30:
                insights.append(
                    f"📉  {y}-{m:02d}: total software spend down {abs(delta)*100:.0f}% MoM "
                    f"({prv:,.0f} → {cur:,.0f} EUR). "
                    f"May reflect a large annual payment in the prior month."
                )

    # ── Category concentration ──────────────────────────────────────────────
    cat_totals = {}
    for d in agg.values():
        cat = d.get("category", "Other")
        cat_totals[cat] = cat_totals.get(cat, 0) + d["total"]
    if total_spend > 0:
        top_cat, top_val = max(cat_totals.items(), key=lambda x: x[1])
        pct = top_val / total_spend * 100
        if pct > 35:
            insights.append(
                f"📊  Category concentration: {top_cat} accounts for "
                f"{pct:.0f}% of total software spend ({top_val:,.0f} EUR). "
                f"Consider whether this reflects strategic priorities."
            )

    return insights


def detect_billing_pattern(months_data, all_months):
    """Classify vendor billing pattern from monthly spend history.

    Returns one of: Monthly / Annual / Usage-Based / Irregular / Single Payment
    """
    active = {ym: amt for ym, amt in months_data.items()
              if ym[0] is not None and amt > 0}
    n_active = len(active)
    n_total  = len(all_months)

    if n_active == 0:
        return "No Data"
    if n_active == 1:
        return "Annual"   # single payment → likely annual / one-time

    amounts = list(active.values())
    mean = sum(amounts) / len(amounts)
    if mean == 0:
        return "Irregular"
    variance = sum((a - mean) ** 2 for a in amounts) / len(amounts)
    cov = (variance ** 0.5) / mean   # coefficient of variation

    coverage = n_active / n_total if n_total else 0

    if n_active <= 2 and n_total >= 4:
        return "Annual"          # paid at most twice across 4+ months
    if coverage >= 0.7:
        return "Monthly" if cov <= 0.35 else "Usage-Based"
    return "Irregular"


def generate_anomalies(agg, all_months):
    """Return list of vendor-level anomaly dicts for the Anomalies sheet.

    Each dict: {flag, vendor, period, amount, avg, detail, action}
    """
    anomalies = []
    if not agg or len(all_months) < 2:
        return anomalies

    # Skip the last month if it looks partial (< 30% of prior month total)
    month_totals = {ym: sum(v["months"].get(ym, 0) for v in agg.values())
                    for ym in all_months}
    analysis_months = all_months[:-1]
    if len(all_months) >= 2:
        last  = month_totals[all_months[-1]]
        prior = month_totals[all_months[-2]]
        if prior > 0 and last >= prior * 0.3:
            analysis_months = all_months   # last month looks complete

    for vendor, d in sorted(agg.items(), key=lambda x: -x[1]["total"]):
        month_vals = [(ym, d["months"].get(ym, 0)) for ym in analysis_months]
        active_months = [v for _, v in month_vals if v > 0]
        if len(active_months) < 2:
            continue
        avg = sum(active_months) / len(active_months)
        if avg <= 0:
            continue

        # ── Spike: one month >3× average and >10k ─────────────────────────
        for ym, val in month_vals:
            if val > avg * 3 and val > 10_000:
                y, m = ym
                anomalies.append({
                    "flag":   "Spike",
                    "vendor": vendor,
                    "period": f"{y}-{m:02d}",
                    "amount": val,
                    "avg":    avg,
                    "detail": (f"{val / avg:.1f}× monthly average "
                               f"({avg:,.0f} avg). Likely annual prepayment or overage."),
                    "action": "Verify invoice - confirm prepayment, true-up, or billing error.",
                })

        # ── Stopped: active 3+ months then zero for 2+ months ─────────────
        for i in range(3, len(month_vals)):
            prev_three = [month_vals[i-3][1], month_vals[i-2][1], month_vals[i-1][1]]
            cur_val = month_vals[i][1]
            if all(v > 0 for v in prev_three) and cur_val == 0:
                if i + 1 < len(month_vals) and month_vals[i+1][1] == 0:
                    last_ym  = month_vals[i-1][0]
                    ly, lm   = last_ym
                    n_prior  = len([v for _, v in month_vals[:i] if v > 0])
                    anomalies.append({
                        "flag":   "Stopped",
                        "vendor": vendor,
                        "period": f"{ly}-{lm:02d}",
                        "amount": month_vals[i-1][1],
                        "avg":    avg,
                        "detail": (f"Payments stopped after {ly}-{lm:02d}. "
                                   f"Was active for {n_prior} months."),
                        "action": "Confirm cancellation or investigate billing change.",
                    })
                    break  # one flag per vendor

    return anomalies


# ---------------------------------------------------------------------------
# 7. WRITE REPORT - Excel with 3 sheets
# ---------------------------------------------------------------------------

def write_report(agg, classified_txns, output_path, currency="EUR", include_charts=True):
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.table import Table, TableStyleInfo
        from openpyxl.chart import BarChart, PieChart, DoughnutChart, Reference as ChartRef
        from openpyxl.chart.series import DataPoint
        from openpyxl.chart.label import DataLabelList
        from openpyxl.formatting.rule import CellIsRule
    except ImportError:
        sys.exit("openpyxl required: pip install openpyxl --break-system-packages")

    wb = openpyxl.Workbook()

    all_months = sorted(
        {ym for v in agg.values() for ym in v["months"] if ym[0] is not None}
    )

    # ── Moss brand palette ─────────────────────────────────────────────────
    MOSS_900   = "002414"   # near-black green - main headers
    MOSS_700   = "264939"   # dark green - secondary headers
    MOSS_550   = "2B765F"   # primary green - chart bars, accents
    MOSS_LIGHT = "D6F1E5"   # light green - alternating rows
    MOSS_NEON  = "B9FF3F"   # neon accent - TOTAL row amount
    MOSS_TEXT  = "131212"   # near-black - body text
    MOSS_GRAY  = "3D3C3C"   # gray - secondary text

    DARK   = MOSS_900
    ALT    = MOSS_LIGHT
    hfont  = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    hfill  = PatternFill("solid", fgColor=DARK)
    afill  = PatternFill("solid", fgColor=ALT)
    tfill  = PatternFill("solid", fgColor=MOSS_900)   # TOTAL row: dark green
    num_fmt = f'#,##0.00 "{currency}"'
    compact = "#,##0"

    # Chart bar/series color palette (greens from dark to light)
    CHART_PALETTE = [
        "2B765F", "264939", "3D8A6E", "5AA882", "002414",
        "7DBFA6", "9DCFC2", "B9E0D8", "265F4F", "4A9E84",
    ]

    def hdr(ws, col, row, val):
        c = ws.cell(row, col, val)
        c.font = hfont; c.fill = hfill
        c.alignment = Alignment(horizontal="center")
        return c

    def body_font(bold=False, size=10, color=None):
        return Font(bold=bold, size=size,
                    color=color or MOSS_TEXT, name="Calibri")

    sorted_vendors = sorted(agg.items(), key=lambda x: -x[1]["total"])

    # Pre-compute: unique vendors per month (static value for By Month sheet)
    vendors_per_month = {
        ym: len({v for v, d in agg.items() if d["months"].get(ym, 0) > 0})
        for ym in all_months
    }

    # Pre-compute billing patterns per vendor
    billing_patterns = {
        v: detect_billing_pattern(d["months"], all_months)
        for v, d in agg.items()
    }

    def no_grid(ws):
        """Hide sheet gridlines so white and green rows look consistent."""
        ws.sheet_view.showGridLines = False

    # ── Sheet 1: By Vendor (formulas referencing Transactions table) ───────
    ROW_H = 22   # data row height (pts) - matches design reference

    ws1 = wb.active
    ws1.title = "By Vendor"
    no_grid(ws1)
    for col, h in enumerate(["Vendor", "Category", f"Total {currency}",
                              "Line Items", "Months Active",
                              f"Avg Monthly {currency}", f"Annual Run Rate {currency}",
                              "Billing Pattern"], 1):
        hdr(ws1, col, 1, h)
    ws1.row_dimensions[1].height = ROW_H
    ws1.freeze_panes = "A2"   # keep header visible when scrolling
    ws1.column_dimensions["A"].width = 30
    ws1.column_dimensions["B"].width = 22
    ws1.column_dimensions["C"].width = 18
    ws1.column_dimensions["D"].width = 14
    ws1.column_dimensions["E"].width = 14
    ws1.column_dimensions["F"].width = 20
    ws1.column_dimensions["G"].width = 22
    ws1.column_dimensions["H"].width = 16

    for i, (vendor, d) in enumerate(sorted_vendors, 2):
        fill = afill if i % 2 == 0 else None
        ref  = f"A{i}"

        ws1.cell(i, 1, vendor)
        ws1.cell(i, 2, d["category"])

        # Total: sum all Amount rows where Vendor matches
        c_total = ws1.cell(i, 3,
            f"=IFERROR(SUMIF(Transactions[Vendor],{ref},Transactions[Amount]),0)")
        c_total.number_format = num_fmt
        c_total.alignment = Alignment(horizontal="right")

        # Transaction count
        c_count = ws1.cell(i, 4,
            f"=IFERROR(COUNTIF(Transactions[Vendor],{ref}),0)")
        c_count.alignment = Alignment(horizontal="center")

        # Unique active months
        c_months = ws1.cell(i, 5,
            f"=IFERROR(SUMPRODUCT(IF(Transactions[Vendor]={ref},"
            f"1/COUNTIFS(Transactions[Vendor],{ref},"
            f"Transactions[YM],Transactions[YM]),0)),0)")
        c_months.alignment = Alignment(horizontal="center")

        # Avg monthly spend = Total / Months Active
        c_avg = ws1.cell(i, 6, f"=IFERROR(C{i}/E{i},0)")
        c_avg.number_format = num_fmt
        c_avg.alignment = Alignment(horizontal="right")

        # Annual run rate = Avg Monthly × 12
        c_arr = ws1.cell(i, 7, f"=IFERROR(F{i}*12,0)")
        c_arr.number_format = num_fmt
        c_arr.alignment = Alignment(horizontal="right")

        # Billing pattern (static, computed from transaction history)
        bp = billing_patterns.get(vendor, "Irregular")
        c_bp = ws1.cell(i, 8, bp)
        c_bp.alignment = Alignment(horizontal="center")

        ws1.row_dimensions[i].height = ROW_H
        if fill:
            for col in range(1, 9):
                ws1.cell(i, col).fill = fill

    tr = len(sorted_vendors) + 2
    for col in range(1, 9):
        c = ws1.cell(tr, col)
        c.fill = tfill
    ws1.cell(tr, 1, "TOTAL").font = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    # SUBTOTAL(9,...) sums only visible rows - updates when filters are applied
    tc = ws1.cell(tr, 3, f"=SUBTOTAL(9,C2:C{tr-1})")
    tc.number_format = num_fmt
    tc.font = Font(bold=True, color=MOSS_NEON, size=10, name="Calibri")  # neon accent
    tc.alignment = Alignment(horizontal="right")
    td = ws1.cell(tr, 4, f"=SUBTOTAL(9,D2:D{tr-1})")
    td.font = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    td.alignment = Alignment(horizontal="center")
    for col in (5, 6, 7, 8):
        ws1.cell(tr, col).font = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    # Run rate TOTAL = sum of individual run rates (for filtered view)
    tarr = ws1.cell(tr, 7, f"=SUBTOTAL(9,G2:G{tr-1})")
    tarr.number_format = num_fmt
    tarr.font = Font(bold=True, color=MOSS_NEON, size=10, name="Calibri")
    tarr.alignment = Alignment(horizontal="right")

    # AutoFilter on header row (excludes TOTAL row)
    ws1.auto_filter.ref = f"A1:H{tr - 1}"

    # ── Category dropdown validation ───────────────────────────────────────
    # Source: Category Summary col A (all known categories).
    # Changing a category here updates Transactions and Monthly Detail via VLOOKUP.
    from openpyxl.worksheet.datavalidation import DataValidation as _DV
    cat_dv = _DV(
        type="list",
        formula1="'Category Summary'!$A$2:$A$60",
        allow_blank=True,
        showDropDown=False,   # False = show the dropdown arrow in Excel
        showErrorMessage=True,
        errorTitle="Invalid category",
        error="Choose a category from the list, or type a new one to add it.",
        errorStyle="warning",   # warning (not stop) so users can still type new values
    )
    ws1.add_data_validation(cat_dv)
    cat_dv.sqref = f"B2:B{tr - 1}"

    # ── Column guide - right of data table (I=spacer, J=label, K=desc) ─────
    # Table occupies A–H (8 cols); guide starts at col J (I = narrow spacer)
    ws1.column_dimensions["I"].width = 2
    ws1.column_dimensions["J"].width = 18
    ws1.column_dimensions["K"].width = 44

    guide_hdr = ws1.cell(1, 10, "How to read this sheet")
    guide_hdr.font = Font(bold=True, size=10, color="FFFFFF", name="Calibri")
    guide_hdr.fill = hfill
    guide_hdr.alignment = Alignment(horizontal="left")
    ws1.cell(1, 11, "").fill = hfill  # extend header fill to col K

    guide_rows = [
        ("Vendor",              "Canonical vendor name. Edit any cell to rename a vendor - all totals update automatically."),
        ("Category",            "Dropdown - select to reclassify. "
                                "Changing a category here automatically updates Transactions and Monthly Detail."),
        (f"Total {currency}",   "Live SUMIF - sums all matching rows in Transactions. Updates when you edit Vendor or Amount."),
        ("Line Items",          "Raw accounting/bank rows in the source file attributed to this vendor. "
                                "One invoice can generate many lines (e.g. per-seat billing in DATEV). "
                                "Does not equal number of payments."),
        ("Months Active",       "Number of distinct calendar months with at least one charge."),
        (f"Avg Monthly {currency}", "Total ÷ Months Active. Normalised monthly cost for benchmarking."),
        (f"Annual Run Rate {currency}", "Avg Monthly × 12. Use this for annual budget planning."),
        ("Billing Pattern",     "Monthly: regular charge, similar amount each month. "
                                "Annual: 1–2 payments/year. "
                                "Usage-Based: charged monthly but amount varies significantly. "
                                "Irregular: no clear pattern."),
        ("", ""),
        ("Tip:",                "To correct a mis-classified vendor, edit the Vendor column in the Transactions sheet. All totals update live."),
    ]
    tip_font = Font(size=9, color="555555", italic=True)

    _GUIDE_COL_CHARS = 44   # col K width in characters
    _LINE_H_PT       = 14   # height per wrapped line (points)
    _ROW_PAD_PT      = 6    # top/bottom padding

    for offset, (label, desc) in enumerate(guide_rows, 2):
        cl = ws1.cell(offset, 10, label)
        cd = ws1.cell(offset, 11, desc)
        cl.font = Font(bold=True, size=9, color=MOSS_900, name="Calibri") if label and label != "Tip:" else tip_font
        cd.font = Font(size=9, color="555555", italic=True, name="Calibri")
        cd.alignment = Alignment(wrap_text=True)
        # Calculate row height from actual text length so nothing gets clipped
        if desc:
            import math
            n_lines = math.ceil(len(desc) / _GUIDE_COL_CHARS)
            ws1.row_dimensions[offset].height = n_lines * _LINE_H_PT + _ROW_PAD_PT
        else:
            ws1.row_dimensions[offset].height = ROW_H   # spacer row
        if offset % 2 == 0:
            for col in (10, 11):
                ws1.cell(offset, col).fill = afill

    # ── Sheet 2: By Month (formulas) ──────────────────────────────────────
    ws2 = wb.create_sheet("By Month")
    no_grid(ws2)
    for col, h in enumerate(["Month", f"Total {currency}", "Vendors Active",
                              "vs Prior Month", f"YTD Cumulative {currency}"], 1):
        hdr(ws2, col, 1, h)
    ws2.row_dimensions[1].height = ROW_H
    ws2.freeze_panes = "A2"
    ws2.column_dimensions["A"].width = 12
    ws2.column_dimensions["B"].width = 20
    ws2.column_dimensions["C"].width = 16
    ws2.column_dimensions["D"].width = 16
    ws2.column_dimensions["E"].width = 22
    ws2.column_dimensions["F"].width = 2   # narrow spacer before chart

    for i, ym in enumerate(all_months, 2):
        y, m = ym
        label = f"{y}-{m:02d}"
        fill = afill if i % 2 == 0 else None

        ws2.cell(i, 1, label)

        # Total spend for this month
        c_total = ws2.cell(i, 2,
            f'=IFERROR(SUMIF(Transactions[YM],A{i},Transactions[Amount]),0)')
        c_total.number_format = num_fmt
        c_total.alignment = Alignment(horizontal="right")

        # Unique vendors active this month (static - SUMPRODUCT unique-count
        # formulas are unreliable when some YM values don't match any row)
        c_active = ws2.cell(i, 3, vendors_per_month.get(ym, 0))
        c_active.alignment = Alignment(horizontal="center")

        # MoM delta
        if i > 2:
            dc = ws2.cell(i, 4, f'=IFERROR((B{i}-B{i-1})/B{i-1},"")')
            dc.number_format = "+0.0%;-0.0%;0.0%"
            dc.alignment = Alignment(horizontal="center")

        # YTD cumulative: sum of all months up to and including this row
        ce = ws2.cell(i, 5, f"=IFERROR(SUM(B$2:B{i}),0)")
        ce.number_format = num_fmt
        ce.alignment = Alignment(horizontal="right")

        ws2.row_dimensions[i].height = ROW_H
        if fill:
            for col in range(1, 5):
                ws2.cell(i, col).fill = fill

    ws2.auto_filter.ref = f"A1:E{len(all_months) + 1}"

    # Conditional formatting: green for positive MoM, red for negative
    n_m_rows = len(all_months) + 1
    ws2.conditional_formatting.add(f"D2:D{n_m_rows}",
        CellIsRule(operator="greaterThanOrEqual", formula=["0"],
                   font=Font(color="265F4F", bold=False, name="Calibri")))
    ws2.conditional_formatting.add(f"D2:D{n_m_rows}",
        CellIsRule(operator="lessThan", formula=["0"],
                   font=Font(color="B8211C", bold=False, name="Calibri")))

    # Monthly spend bar chart
    n_m = len(all_months)
    if include_charts and n_m >= 2:
        ch_month = BarChart()
        ch_month.type    = "col"
        ch_month.title   = f"Monthly Software Spend ({currency})"
        ch_month.width   = 24
        ch_month.height  = 14
        ch_month.legend  = None
        ch_month.y_axis.numFmt = "#,##0"
        ch_month.y_axis.title  = None
        ch_month.add_data(ChartRef(ws2, min_col=2, min_row=1, max_row=n_m + 1),
                          titles_from_data=True)
        ch_month.set_categories(ChartRef(ws2, min_col=1, min_row=2, max_row=n_m + 1))
        if ch_month.series:
            s = ch_month.series[0]
            s.graphicalProperties.solidFill = MOSS_550
            s.graphicalProperties.line.solidFill = MOSS_550
            s.dLbls = DataLabelList()
            s.dLbls.showVal = True
            s.dLbls.showLegendKey = False
            s.dLbls.showCatName   = False
            s.dLbls.showSerName   = False
            s.dLbls.numFmt        = f'#,##0 "{currency}"'
        ws2.add_chart(ch_month, "G2")

    # ── Sheet 3: Monthly Detail (pivot, formulas) ─────────────────────────
    ws3 = wb.create_sheet("Monthly Detail")
    no_grid(ws3)
    ws3.freeze_panes = "C2"   # freeze vendor+category columns and header row
    month_labels = [f"{ym[0]}-{ym[1]:02d}" for ym in all_months]
    total_col = len(all_months) + 3   # column index of row-total (1-based)
    pivot_hdrs = ["Vendor", "Category"] + month_labels + [f"Total {currency}"]
    for col, h in enumerate(pivot_hdrs, 1):
        hdr(ws3, col, 1, h)
    ws3.row_dimensions[1].height = ROW_H
    ws3.column_dimensions["A"].width = 30
    ws3.column_dimensions["B"].width = 20
    for col in range(3, len(pivot_hdrs) + 1):
        ws3.column_dimensions[get_column_letter(col)].width = 12
    # Total EUR column needs extra width for "#,##0.00 EUR" format
    ws3.column_dimensions[get_column_letter(total_col)].width = 20

    for i, (vendor, d) in enumerate(sorted_vendors, 2):
        fill = afill if i % 2 == 0 else None
        ws3.cell(i, 1, vendor)
        # Category pulled from By Vendor - changes there propagate here automatically
        c_cat3 = ws3.cell(i, 2,
            f"=IFERROR(VLOOKUP(A{i},'By Vendor'!$A:$B,2,FALSE),\"\")")
        c_cat3.alignment = Alignment(horizontal="left")
        if fill:
            ws3.cell(i, 1).fill = fill
            ws3.cell(i, 2).fill = fill

        first_month_col = get_column_letter(3)
        last_month_col  = get_column_letter(2 + len(all_months))

        for j, ym in enumerate(all_months, 3):
            ym_label = f"{ym[0]}-{ym[1]:02d}"
            col_letter = get_column_letter(j)
            # SUMIFS: vendor row A{i} AND month header {col_letter}$1
            c = ws3.cell(i, j,
                f'=IFERROR(SUMIFS(Transactions[Amount],'
                f'Transactions[Vendor],A{i},'
                f'Transactions[YM],{col_letter}$1),0)')
            c.number_format = compact
            c.alignment = Alignment(horizontal="right")
            if fill:
                c.fill = fill

        ws3.row_dimensions[i].height = ROW_H
        # Row total = SUM of month columns
        tc = ws3.cell(i, total_col,
            f'=IFERROR(SUM({first_month_col}{i}:{last_month_col}{i}),0)')
        tc.number_format = num_fmt
        tc.font = Font(bold=True)
        tc.alignment = Alignment(horizontal="right")
        if fill:
            tc.fill = fill

    # Column totals row
    tr3 = len(sorted_vendors) + 2
    _total_font = Font(bold=True, color="FFFFFF", name="Calibri")
    for col in range(1, len(pivot_hdrs) + 1):
        ws3.cell(tr3, col).fill = tfill
        ws3.cell(tr3, col).font = _total_font
    ws3.cell(tr3, 1, "TOTAL")
    # SUBTOTAL(9,...) respects filters - shows totals for visible vendors only
    for j in range(3, 3 + len(all_months)):
        col_letter = get_column_letter(j)
        c = ws3.cell(tr3, j,
            f'=SUBTOTAL(9,{col_letter}2:{col_letter}{tr3-1})')
        c.number_format = compact
        c.alignment = Alignment(horizontal="right")
    grand = ws3.cell(tr3, total_col,
        f'=SUBTOTAL(9,{get_column_letter(total_col)}2'
        f':{get_column_letter(total_col)}{tr3-1})')
    grand.number_format = num_fmt
    grand.alignment = Alignment(horizontal="right")

    # AutoFilter on Monthly Detail (vendor + category columns)
    ws3.auto_filter.ref = f"A1:{get_column_letter(total_col)}{tr3 - 1}"

    # ── Column guide for Monthly Detail ───────────────────────────────────
    guide_col_start = total_col + 2   # two columns after the Total EUR column
    guide_col_label = guide_col_start
    guide_col_desc  = guide_col_start + 1
    ws3.column_dimensions[get_column_letter(guide_col_label)].width = 18
    ws3.column_dimensions[get_column_letter(guide_col_desc)].width  = 44

    md_guide_hdr = ws3.cell(1, guide_col_label, "How to read this sheet")
    md_guide_hdr.font = Font(bold=True, size=10, color="FFFFFF", name="Calibri")
    md_guide_hdr.fill = hfill
    ws3.cell(1, guide_col_desc, "").fill = hfill

    md_guide_rows = [
        ("Vendor",          "Canonical vendor name - same as in By Vendor."),
        ("Category",        "Pulled from By Vendor via formula - change the category there to update this sheet automatically."),
        ("[month columns]", "Each column is one calendar month. Value = SUMIFS formula: "
                            "spend for that vendor in that month. Updates when you edit Transactions."),
        (f"Total {currency}", "Row total = SUM of all month columns for this vendor."),
        ("TOTAL row",       "Column totals = SUM of all vendor rows for that month."),
        ("",                ""),
        ("Tip:",            "Cells show 0 when a vendor had no spend in that month - "
                            "not a blank, so you can filter and sort freely."),
    ]
    for offset, (label, desc) in enumerate(md_guide_rows, 2):
        cl = ws3.cell(offset, guide_col_label, label)
        cd = ws3.cell(offset, guide_col_desc,  desc)
        cl.font = Font(bold=True, size=9, color=MOSS_900, name="Calibri")
        cd.font = Font(size=9, color="555555", italic=True, name="Calibri")
        cd.alignment = Alignment(wrap_text=True)
        ws3.row_dimensions[offset].height = 30 if desc and len(desc) > 80 else ROW_H
        if offset % 2 == 0:   # alternating green background
            for col in (guide_col_label, guide_col_desc):
                ws3.cell(offset, col).fill = afill

    # ── Sheet: Category Summary ───────────────────────────────────────────
    from collections import defaultdict as _ddict2
    cat_spend = _ddict2(lambda: {"total": 0.0, "vendors": set()})
    for vendor, d in agg.items():
        cat = d.get("category", "Other")
        cat_spend[cat]["total"] += d["total"]
        cat_spend[cat]["vendors"].add(vendor)
    sorted_cats_summary = sorted(cat_spend.items(), key=lambda x: -x[1]["total"])
    grand_total = sum(d["total"] for d in agg.values()) or 1

    ws_cat = wb.create_sheet("Category Summary")
    no_grid(ws_cat)
    ws_cat.freeze_panes = "A2"
    cat_hdrs = ["Category", f"Total {currency}", "% of Spend",
                "Vendor Count", f"Avg per Vendor {currency}", f"Annual Run Rate {currency}"]
    for col, h in enumerate(cat_hdrs, 1):
        hdr(ws_cat, col, 1, h)
    ws_cat.row_dimensions[1].height = ROW_H
    ws_cat.column_dimensions["A"].width = 26
    ws_cat.column_dimensions["B"].width = 20
    ws_cat.column_dimensions["C"].width = 14
    ws_cat.column_dimensions["D"].width = 14
    ws_cat.column_dimensions["E"].width = 22
    ws_cat.column_dimensions["F"].width = 24

    n_months = len(all_months) or 1
    for i, (cat, data) in enumerate(sorted_cats_summary, 2):
        fill = afill if i % 2 == 0 else None
        n_vendors = len(data["vendors"])
        total = data["total"]
        avg = total / n_vendors if n_vendors else 0
        arr = (total / n_months) * 12

        ws_cat.cell(i, 1, cat)
        c_tot = ws_cat.cell(i, 2, f"=IFERROR(SUMIF('By Vendor'!$B:$B,A{i},'By Vendor'!$C:$C),0)")
        c_tot.number_format = num_fmt
        c_tot.alignment = Alignment(horizontal="right")
        c_pct = ws_cat.cell(i, 3, f"=IFERROR(B{i}/SUM('By Vendor'!$C$2:$C${tr-1}),0)")
        c_pct.number_format = "0.0%"
        c_pct.alignment = Alignment(horizontal="center")
        ws_cat.cell(i, 4, n_vendors).alignment = Alignment(horizontal="center")
        c_avg = ws_cat.cell(i, 5, f"=IFERROR(B{i}/D{i},0)")
        c_avg.number_format = num_fmt
        c_avg.alignment = Alignment(horizontal="right")
        c_arr = ws_cat.cell(i, 6, arr)
        c_arr.number_format = num_fmt
        c_arr.alignment = Alignment(horizontal="right")
        ws_cat.row_dimensions[i].height = ROW_H

        if fill:
            for col in range(1, 7):
                ws_cat.cell(i, col).fill = fill

    tr_cat = len(sorted_cats_summary) + 2
    for col in range(1, 7):
        ws_cat.cell(tr_cat, col).fill = tfill
    ws_cat.cell(tr_cat, 1, "TOTAL").font = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    tc_cat = ws_cat.cell(tr_cat, 2, f"=SUBTOTAL(9,B2:B{tr_cat-1})")
    tc_cat.number_format = num_fmt
    tc_cat.font = Font(bold=True, color=MOSS_NEON, size=10, name="Calibri")
    tc_cat.alignment = Alignment(horizontal="right")
    tp_cat = ws_cat.cell(tr_cat, 3, "100%")
    tp_cat.number_format = "0.0%"
    tp_cat.font = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    tp_cat.alignment = Alignment(horizontal="center")
    ws_cat.auto_filter.ref = f"A1:F{tr_cat - 1}"

    # ── Sheet: Budget vs Actual ───────────────────────────────────────────
    ws_bva = wb.create_sheet("Budget vs Actual")
    no_grid(ws_bva)
    ws_bva.freeze_panes = "A2"
    bva_hdrs = ["Category", f"Budget {currency}", f"Actual {currency}",
                f"Variance {currency}", "Variance %", "Status"]
    for col, h in enumerate(bva_hdrs, 1):
        hdr(ws_bva, col, 1, h)
    ws_bva.row_dimensions[1].height = ROW_H
    ws_bva.column_dimensions["A"].width = 26
    ws_bva.column_dimensions["B"].width = 20
    ws_bva.column_dimensions["C"].width = 20
    ws_bva.column_dimensions["D"].width = 20
    ws_bva.column_dimensions["E"].width = 14
    ws_bva.column_dimensions["F"].width = 14

    # Instructions row
    instr = ws_bva.cell(2, 1,
        "← Enter your budget per category in column B. Actual and variance update automatically.")
    instr.font = Font(size=9, color="888888", italic=True, name="Calibri")
    ws_bva.merge_cells("A2:F2")
    ws_bva.row_dimensions[2].height = 18

    for i, (cat, _) in enumerate(sorted_cats_summary, 3):
        fill = afill if i % 2 == 0 else None
        ws_bva.cell(i, 1, cat)
        # Budget: left blank for finance team to fill in
        ws_bva.cell(i, 2, "").number_format = num_fmt
        # Actual: live SUMIF from By Vendor
        c_act = ws_bva.cell(i, 3,
            f"=IFERROR(SUMIF('By Vendor'!$B:$B,A{i},'By Vendor'!$C:$C),0)")
        c_act.number_format = num_fmt
        c_act.alignment = Alignment(horizontal="right")
        # Variance = Actual - Budget
        c_var = ws_bva.cell(i, 4, f'=IFERROR(C{i}-B{i},"")')
        c_var.number_format = num_fmt
        c_var.alignment = Alignment(horizontal="right")
        # Variance %
        c_vpct = ws_bva.cell(i, 5, f'=IFERROR((C{i}-B{i})/B{i},"")')
        c_vpct.number_format = "+0.0%;-0.0%;0.0%"
        c_vpct.alignment = Alignment(horizontal="center")
        # Status: Over / Under / On track
        c_st = ws_bva.cell(i, 6,
            f'=IFERROR(IF(D{i}>B{i}*0.05,"⚠ Over",IF(D{i}<-B{i}*0.05,"✓ Under","● On track")),"")')
        c_st.alignment = Alignment(horizontal="center")
        ws_bva.row_dimensions[i].height = ROW_H
        if fill:
            for col in range(1, 7):
                ws_bva.cell(i, col).fill = fill

    tr_bva = len(sorted_cats_summary) + 3
    for col in range(1, 7):
        ws_bva.cell(tr_bva, col).fill = tfill
    ws_bva.cell(tr_bva, 1, "TOTAL").font = Font(bold=True, color="FFFFFF", size=10, name="Calibri")
    for col_idx, rng_col in [(2, "B"), (3, "C"), (4, "D")]:
        tc_bva = ws_bva.cell(tr_bva, col_idx,
            f"=IFERROR(SUM({rng_col}3:{rng_col}{tr_bva-1}),0)")
        tc_bva.number_format = num_fmt
        tc_bva.font = Font(bold=True, color=MOSS_NEON, size=10, name="Calibri")
        tc_bva.alignment = Alignment(horizontal="right")

    # Conditional formatting: red for over-budget, green for under
    from openpyxl.formatting.rule import CellIsRule as _CIR
    ws_bva.conditional_formatting.add(f"D3:D{tr_bva-1}",
        _CIR(operator="greaterThan", formula=["0"],
             font=Font(color="B8211C", bold=True, name="Calibri")))
    ws_bva.conditional_formatting.add(f"D3:D{tr_bva-1}",
        _CIR(operator="lessThan", formula=["0"],
             font=Font(color="265F4F", bold=True, name="Calibri")))

    # ── Sheet 4: Insights ─────────────────────────────────────────────────
    insights = generate_insights(agg, all_months)
    if insights:
        ws4 = wb.create_sheet("Insights", 0)  # insert as first sheet
        no_grid(ws4)
        ws4.column_dimensions["A"].width = 48   # text column - compact
        ws4.column_dimensions["B"].width = 2    # narrow spacer before charts

        title_cell = ws4.cell(1, 1, "Moss - Automatic Insights")
        title_cell.font = Font(bold=True, size=14, color=MOSS_900, name="Calibri")
        subtitle = ws4.cell(2, 1,
            f"Generated from {len(agg)} vendors · "
            f"Total spend: {sum(d['total'] for d in agg.values()):,.0f} {currency} · "
            f"{len(all_months)} months analysed")
        subtitle.font = Font(size=9, color=MOSS_GRAY, name="Calibri")

        ws4.cell(3, 1, "")  # spacer

        _ins_col_w = 48   # col A width in chars - used to estimate text wrap
        for i, insight in enumerate(insights, 4):
            c = ws4.cell(i, 1, insight)
            c.font = Font(size=10, color=MOSS_TEXT, name="Calibri")
            c.alignment = Alignment(wrap_text=True)
            if i % 2 == 0:
                c.fill = PatternFill("solid", fgColor=MOSS_LIGHT)
            n_lines = max(1, -(-len(insight) // _ins_col_w))  # ceiling division
            ws4.row_dimensions[i].height = n_lines * 15 + 8

        note_row = len(insights) + 5
        ws4.cell(note_row, 1,
                 "⚠ This report is AI-generated (Claude). "
                 "Figures are derived from raw transaction data - verify against source systems "
                 "before using for financial reporting or auditing.")
        ws4.cell(note_row, 1).font = Font(size=8, color=MOSS_GRAY, italic=True, name="Calibri")

        # ── Moss promo block ───────────────────────────────────────────────
        promo_row = note_row + 3
        divider = ws4.cell(promo_row, 1, "─" * 60)
        divider.font = Font(size=8, color="CCCCCC")

        promo_lines = [
            ("Share this report with whoever owns software spend, accounting cleanup, "
             'or the next \u201cwait, what are we actually paying for?\u201d meeting.', 9, "444444", False),
            ("", 6, "FFFFFF", False),  # spacer
            ("Built by the team at Moss - a spend management platform trusted by 7,000+ "
             "companies to automate invoice processing, control card and employee spend, "
             "and sync with 40+ accounting and ERP systems in real time.", 9, "444444", False),
            ("If hunting down software costs manually sounds familiar, Moss is built to fix exactly that.", 9, "444444", False),
            ("", 6, "FFFFFF", False),  # spacer
            ("getmoss.com  ·  Moss team", 9, "1F3864", True),
        ]
        # Column A is 65 chars wide - estimate lines needed for row height
        _col_width = 65
        for offset, (text, size, color, bold) in enumerate(promo_lines, promo_row + 1):
            c = ws4.cell(offset, 1, text)
            c.font = Font(size=size, color=color, bold=bold, name="Calibri")
            c.alignment = Alignment(wrap_text=True)
            if text:
                n_lines = max(1, -(-len(text) // _col_width))  # ceiling division
                ws4.row_dimensions[offset].height = n_lines * 16 + 8
            else:
                ws4.row_dimensions[offset].height = 8

        # ── Charts (skipped when include_charts=False) ────────────────────
        if include_charts:
            n_top = min(15, len(sorted_vendors))
            VENDORS_CHART_CM = 16
            VENDORS_START_COL = 5
            CM_PER_COL = 1.78
            COL_GAP    = 2

            ws4.column_dimensions["C"].width = 2
            ws4.column_dimensions["D"].width = 2

            ch_vendors = BarChart()
            ch_vendors.type   = "bar"
            ch_vendors.title  = f"Top {n_top} vendors by spend"
            ch_vendors.width  = VENDORS_CHART_CM
            ch_vendors.height = 14
            ch_vendors.legend = None
            ch_vendors.x_axis.numFmt = "#,##0"
            ch_vendors.x_axis.title  = None
            ch_vendors.y_axis.scaling.orientation = "maxMin"  # DoiT at top
            ch_vendors.add_data(ChartRef(ws1, min_col=3, min_row=1, max_row=n_top + 1),
                                titles_from_data=True)
            ch_vendors.set_categories(ChartRef(ws1, min_col=1, min_row=2, max_row=n_top + 1))
            if ch_vendors.series:
                s = ch_vendors.series[0]
                s.graphicalProperties.solidFill = MOSS_550
                s.graphicalProperties.line.solidFill = MOSS_550
                s.dLbls = DataLabelList()
                s.dLbls.showVal = True
                s.dLbls.showLegendKey = False
                s.dLbls.showCatName   = False
                s.dLbls.showSerName   = False
                s.dLbls.numFmt        = f'#,##0 "{currency}"'
            ws4.add_chart(ch_vendors, "E1")

            # Category charts - shared colour palette (cycles if > len)
            PIE_PALETTE = [
                "2B765F", "4E79A7", "F28E2B", "E15759", "76B7B2",
                "59A14F", "EDC948", "B07AA1", "FF9DA7", "9C755F",
                "BAB0AC", "D4A6C8", "86BCB6", "FABFD2", "A0CBE8", "FFBE7D",
                "8CD17D", "499894", "F1CE63", "D7B5A6",
            ]
            from collections import defaultdict as _ddict
            cat_agg = _ddict(float)
            for d in agg.values():
                cat_agg[d.get("category", "Other")] += d["total"]
            sorted_cats = sorted(cat_agg.items(), key=lambda x: -x[1])
            n_cats = len(sorted_cats)

            # ── Donut chart helper table at row 50+ ───────────────────────
            cat_hdr_row = 50
            _lbl = ws4.cell(cat_hdr_row, 1, "Category Totals (chart data - do not delete)")
            _lbl.font = Font(size=8, color="BBBBBB", italic=True)
            ws4.cell(cat_hdr_row, 2, f"Total {currency}").font = Font(size=8, color="BBBBBB", italic=True)
            for ci, (cat, _) in enumerate(sorted_cats, cat_hdr_row + 1):
                ws4.cell(ci, 1, cat)
                ws4.cell(ci, 2,
                    f"=IFERROR(SUMIF('By Vendor'!$B:$B,A{ci},'By Vendor'!$C:$C),0)")
                ws4.cell(ci, 2).number_format = compact

            ch_donut = DoughnutChart()
            ch_donut.title    = "Spend by category"
            ch_donut.width    = 16
            ch_donut.height   = 14
            ch_donut.holeSize = 45
            ch_donut.add_data(ChartRef(ws4, min_col=2, min_row=cat_hdr_row,
                                       max_row=cat_hdr_row + n_cats),
                              titles_from_data=True)
            ch_donut.set_categories(ChartRef(ws4, min_col=1, min_row=cat_hdr_row + 1,
                                             max_row=cat_hdr_row + n_cats))
            for idx in range(n_cats):
                pt = DataPoint(idx=idx)
                pt.graphicalProperties.solidFill = PIE_PALETTE[idx % len(PIE_PALETTE)]
                ch_donut.series[0].dPt.append(pt)
            pie_col_offset = round(VENDORS_CHART_CM / CM_PER_COL) + COL_GAP
            pie_anchor     = get_column_letter(VENDORS_START_COL + pie_col_offset) + "1"
            ws4.add_chart(ch_donut, pie_anchor)

            # ── Category × Month stacked bar chart ────────────────────────
            from collections import defaultdict as _ddict_cm
            cat_month_totals = _ddict_cm(lambda: _ddict_cm(float))
            for _v, _d in agg.items():
                _cat = _d.get("category", "Other")
                for _ym, _amt in _d["months"].items():
                    if _ym[0] is not None:
                        cat_month_totals[_cat][_ym] += _amt

            n_months_cm = len(all_months)
            if n_months_cm >= 2 and n_cats >= 2:
                cm_row_start = cat_hdr_row + n_cats + 4
                _lbl2 = ws4.cell(cm_row_start, 1,
                    "Category×Month (chart data - do not delete)")
                _lbl2.font = Font(size=8, color="BBBBBB", italic=True)
                for ci, (cat, _) in enumerate(sorted_cats, 2):
                    ws4.cell(cm_row_start, ci, cat).font = Font(size=8, color="BBBBBB", italic=True)
                for ri, ym in enumerate(all_months, cm_row_start + 1):
                    y, m = ym
                    ws4.cell(ri, 1, f"{y}-{m:02d}").font = Font(size=8, color="BBBBBB", italic=True)
                    for ci, (cat, _) in enumerate(sorted_cats, 2):
                        ws4.cell(ri, ci, cat_month_totals[cat].get(ym, 0))
                        ws4.cell(ri, ci).number_format = compact

                ch_stacked = BarChart()
                ch_stacked.type     = "col"
                ch_stacked.grouping = "stacked"
                ch_stacked.title    = f"Category spend by month ({currency})"
                ch_stacked.width    = 22
                ch_stacked.height   = 18
                ch_stacked.y_axis.numFmt = "#,##0"
                ch_stacked.y_axis.title  = None

                for ci, (cat_name, _) in enumerate(sorted_cats):
                    col_idx = ci + 2
                    s_data = ChartRef(ws4,
                        min_col=col_idx, min_row=cm_row_start,
                        max_col=col_idx, max_row=cm_row_start + n_months_cm)
                    ch_stacked.add_data(s_data, titles_from_data=True)
                    if ch_stacked.series:
                        s = ch_stacked.series[-1]
                        s.graphicalProperties.solidFill = PIE_PALETTE[ci % len(PIE_PALETTE)]
                        s.graphicalProperties.line.solidFill = PIE_PALETTE[ci % len(PIE_PALETTE)]

                cat_ref_cm = ChartRef(ws4,
                    min_col=1, min_row=cm_row_start + 1,
                    max_row=cm_row_start + n_months_cm)
                ch_stacked.set_categories(cat_ref_cm)

                stacked_anchor = get_column_letter(VENDORS_START_COL) + "21"
                ws4.add_chart(ch_stacked, stacked_anchor)

    # ── Sheet: Anomalies ─────────────────────────────────────────────────────
    anomalies = generate_anomalies(agg, all_months)
    # Insert at position 1 so it appears right after Insights (position 0)
    ws_anom = wb.create_sheet("Anomalies", 1)
    no_grid(ws_anom)

    anom_title = ws_anom.cell(1, 1, "Anomalies & Flags")
    anom_title.font = Font(bold=True, size=13, color=MOSS_900, name="Calibri")
    flag_count = len(anomalies)
    anom_sub = ws_anom.cell(2, 1,
        f"{flag_count} flag{'s' if flag_count != 1 else ''} detected  ·  "
        f"For details, filter the Transactions sheet by the vendor name shown below.")
    anom_sub.font = Font(size=9, color=MOSS_GRAY, italic=True, name="Calibri")

    anom_hdrs = ["Flag", "Vendor", "Period", f"Amount ({currency})",
                 "Monthly Avg", "Detail", "Recommended Action"]
    anom_widths = [14, 30, 10, 18, 18, 46, 42]
    for col, (h, w) in enumerate(zip(anom_hdrs, anom_widths), 1):
        hdr(ws_anom, col, 3, h)
        ws_anom.column_dimensions[get_column_letter(col)].width = w
    ws_anom.row_dimensions[3].height = ROW_H
    ws_anom.freeze_panes = "A4"

    if anomalies:
        for i, anom in enumerate(anomalies, 4):
            fill = afill if i % 2 == 0 else None
            flag_icon = "🔍" if anom["flag"] == "Spike" else "❓"
            ws_anom.cell(i, 1, f"{flag_icon} {anom['flag']}")
            ws_anom.cell(i, 2, anom["vendor"])
            ws_anom.cell(i, 3, anom["period"])
            c_amt = ws_anom.cell(i, 4, anom["amount"])
            c_amt.number_format = num_fmt
            c_amt.alignment = Alignment(horizontal="right")
            c_avg = ws_anom.cell(i, 5, anom["avg"])
            c_avg.number_format = num_fmt
            c_avg.alignment = Alignment(horizontal="right")
            c_det = ws_anom.cell(i, 6, anom["detail"])
            c_det.alignment = Alignment(wrap_text=True)
            c_act = ws_anom.cell(i, 7, anom["action"])
            c_act.alignment = Alignment(wrap_text=True)
            ws_anom.row_dimensions[i].height = ROW_H + 8
            if fill:
                for col in range(1, 8):
                    ws_anom.cell(i, col).fill = fill

        # TOTAL row
        tr_anom = len(anomalies) + 4
        for col in range(1, 8):
            ws_anom.cell(tr_anom, col).fill = tfill
        ws_anom.cell(tr_anom, 1, f"{flag_count} flags").font = Font(
            bold=True, color="FFFFFF", size=10, name="Calibri")
        ws_anom.auto_filter.ref = f"A3:G{tr_anom - 1}"
    else:
        ok_cell = ws_anom.cell(4, 1, "✓  No anomalies detected in this dataset.")
        ok_cell.font = Font(size=10, color="265F4F", name="Calibri")

    print(f"  → Anomalies sheet: {flag_count} flag(s)")

    # ── Sheet: Transactions (raw classified data - source for formulas) ────
    # Appended last so it doesn't shift other sheet indices; formulas use table name.
    ws_txn = wb.create_sheet("Transactions")
    no_grid(ws_txn)
    txn_headers = ["Date", "Description", "Vendor", "Category", "Amount", "YM"]
    for col, h in enumerate(txn_headers, 1):
        hdr(ws_txn, col, 1, h)
    ws_txn.column_dimensions["A"].width = 12
    ws_txn.column_dimensions["B"].width = 50
    ws_txn.column_dimensions["C"].width = 28
    ws_txn.column_dimensions["D"].width = 22
    ws_txn.column_dimensions["E"].width = 16
    ws_txn.column_dimensions["F"].width = 10

    for i, t in enumerate(classified_txns, 2):
        fill = afill if i % 2 == 0 else None
        if t["year"] and t["month"]:
            from datetime import date as _date
            date_val = _date(t["year"], t["month"], 1)
            ym_val   = f"{t['year']}-{t['month']:02d}"
        else:
            date_val = None
            ym_val   = ""

        c_date = ws_txn.cell(i, 1, date_val)
        if date_val:
            c_date.number_format = "YYYY-MM-DD"
        ws_txn.cell(i, 2, t["description"])
        ws_txn.cell(i, 3, t["canonical"])
        # Category: live formula - change category in By Vendor to update all transactions
        ws_txn.cell(i, 4,
            f"=IFERROR(VLOOKUP(C{i},'By Vendor'!$A:$B,2,FALSE),\"\")")
        c_amt = ws_txn.cell(i, 5, t["amount"])
        c_amt.number_format = compact
        c_amt.alignment = Alignment(horizontal="right")
        ws_txn.cell(i, 6, ym_val)

        if fill:
            for col in range(1, 7):
                ws_txn.cell(i, col).fill = fill

    # Register as Excel Table so formulas can use Transactions[Vendor] syntax
    if classified_txns:
        n_txn_rows = len(classified_txns)
        tbl = Table(displayName="Transactions",
                    ref=f"A1:F{n_txn_rows + 1}")
        tbl.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2", showRowStripes=True)
        ws_txn.add_table(tbl)

    print(f"  → Transactions sheet: {len(classified_txns)} rows")

    wb.save(output_path)
    print(f"\nReport saved → {output_path}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Moss - Software Spend Intelligence pipeline"
    )
    ap.add_argument("--input",    required=True, help="Transaction file (xlsx/csv/pdf)")
    ap.add_argument("--output",   default="spend_report.xlsx")
    ap.add_argument("--taxonomy", default=None,
                    help="Path to vendor_taxonomy.csv (default: auto-detect)")
    ap.add_argument("--currency", default="EUR")
    ap.add_argument("--no-charts", action="store_true",
                    help="Skip chart generation (for compatibility with Numbers/claude.ai preview)")
    args = ap.parse_args()

    # Auto-locate taxonomy relative to this script
    if args.taxonomy is None:
        here = os.path.dirname(os.path.abspath(__file__))
        args.taxonomy = os.path.join(here, "..", "references", "vendor_taxonomy.csv")
    if not os.path.exists(args.taxonomy):
        sys.exit(f"Taxonomy not found: {args.taxonomy}\nPass --taxonomy PATH")

    print(f"\n{'='*55}")
    print(f"  Moss - Software Spend Intelligence")
    print(f"{'='*55}")

    print("\n[1/6] Loading file...")
    txns = normalize(args.input)

    print("\n[2/6] Deduplicating transactions...")
    txns = deduplicate(txns)
    if not txns:
        sys.exit("No expense transactions found after deduplication.")

    print("\n[3/6] Extracting candidates...")
    candidates = extract_candidates(txns)

    print("\n[4/6] Taxonomy matching (Pass 1)...")
    taxonomy = load_taxonomy(args.taxonomy)
    matched, unmatched, excluded = match_taxonomy(candidates, taxonomy)

    print("\n[5/6] LLM classification (Pass 2)...")
    llm_results = llm_classify(unmatched)
    total_vendors = len({v["canonical"] for v in matched.values()}) + len(
        {v["canonical"] for v in llm_results.values()}
    )
    print(f"  → {total_vendors} total software vendors identified")

    print("\n[6/6] Aggregating spend and writing report...")
    agg, classified_txns = aggregate(txns, matched, llm_results)
    include_charts = not args.no_charts
    if not include_charts:
        print("  → Charts disabled (--no-charts flag)")
    write_report(agg, classified_txns, args.output, args.currency,
                 include_charts=include_charts)

    # Console summary
    print(f"\n{'─'*55}")
    print(f"  {'Vendor':<28} {'Total':>12}  Mo")
    print(f"{'─'*55}")
    for vendor, d in sorted(agg.items(), key=lambda x: -x[1]["total"])[:15]:
        active = sum(1 for ym in d["months"] if ym[0])
        print(f"  {vendor:<28} {d['total']:>12,.0f}  {active}")
    if len(agg) > 15:
        print(f"  ... and {len(agg)-15} more")
    print(f"{'─'*55}")
    print(f"  {'TOTAL':<28} {sum(d['total'] for d in agg.values()):>12,.0f}")
    print(f"{'─'*55}\n")


if __name__ == "__main__":
    main()
