#!/usr/bin/env python3
"""Deterministic spend aggregation for the Software Spend Snapshot skill.

Reads normalised.csv (output of normalize.py) + vendor_list.csv (output of the
LLM/taxonomy pass) and produces a spend report per vendor, per month, and a
monthly breakdown.

Input files
-----------
normalised.csv
    Columns: description, amount, date
    - description : str   (merchant / booking text)
    - amount      : str   (signed float, negative = expense; OR may be blank for DATEV)
    - date        : str   (any parseable date format)

vendor_list.csv
    Columns: vendor, description_text, pattern
    - vendor           : str  (canonical vendor name)
    - description_text : str  (one-line description of the vendor)
    - pattern          : str  (the substring that matched this vendor)

OR: if vendor_list.csv is not available, uses matched.csv from match_taxonomy.py
    Columns: candidate, canonical, description (taxonomy output format)

--datev flag
    Activates DATEV double-entry deduplication mode.
    normalised.csv in DATEV mode contains the raw Buchungstext + a special
    _guid column carried through by normalize.py.
    Without --datev: each row = one transaction (bank statement mode).

Output
------
spend_report.xlsx   with three sheets:
    1. By Vendor     — vendor, description, total_eur, txn_count, months_active
    2. By Month      — month (YYYY-MM), total_eur, vendor_count
    3. Monthly Detail — vendor × month pivot table

Usage
-----
    python3 aggregate_spend.py \\
        --normalised normalised.csv \\
        --vendors matched.csv \\
        [--datev] \\
        [--output spend_report.xlsx] \\
        [--currency EUR]
"""

import argparse
import csv
import re
import sys
import os
from collections import defaultdict

# ---------------------------------------------------------------------------
# Amount parsing
# ---------------------------------------------------------------------------

def parse_amount(raw: str) -> float | None:
    """Parse a monetary amount string into a float.

    Handles:
    - German format: 1.234,56  →  1234.56
    - English format: 1,234.56 →  1234.56
    - Signed: -89.00, +4200.00
    - Empty / non-numeric → None
    """
    if not raw or str(raw).strip() in ("", "nan", "NaN", "-", "0.0", "0"):
        return None
    s = str(raw).strip()
    # Detect German format: ends with ,XX (2 decimal digits after comma)
    if re.search(r",\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    # Remove currency symbols
    s = re.sub(r"[€£$\s]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(raw: str):
    """Return (year, month) tuple or (None, None) if unparseable."""
    if not raw or str(raw).strip() in ("", "nan", "NaN"):
        return None, None
    s = str(raw).strip()
    # Try common formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y",
                "%Y-%m-%d %H:%M:%S", "%d %b %Y", "%d-%m-%Y"):
        try:
            from datetime import datetime
            dt = datetime.strptime(s[:10], fmt[:len(fmt)])
            return dt.year, dt.month
        except ValueError:
            continue
    # Try pandas as fallback
    try:
        import pandas as pd
        dt = pd.to_datetime(s, dayfirst=True)
        return dt.year, dt.month
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Vendor matching
# ---------------------------------------------------------------------------

def load_vendors(path: str) -> list[dict]:
    """Load vendor list from either matched.csv or vendor_list.csv.

    Returns list of dicts with keys: vendor, pattern, description_text
    Patterns are lowercased substrings to match against description.
    """
    vendors = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for row in reader:
            # Support both formats
            if "canonical" in cols:
                # match_taxonomy.py output: candidate, canonical, description
                vendor = str(row.get("canonical", "")).strip()
                pattern = str(row.get("candidate", "")).strip().lower()
                desc = str(row.get("description", "")).strip()
            elif "vendor" in cols:
                # vendor_list.csv: vendor, description_text, pattern
                vendor = str(row.get("vendor", "")).strip()
                pattern = str(row.get("pattern", row.get("vendor", ""))).strip().lower()
                desc = str(row.get("description_text", "")).strip()
            else:
                continue
            if vendor and pattern:
                vendors.append({"vendor": vendor, "pattern": pattern, "desc": desc})
    return vendors


def match_vendor(description: str, vendors: list[dict]) -> str | None:
    """Return canonical vendor name if description matches any pattern."""
    dl = description.lower()
    for v in vendors:
        if v["pattern"] in dl:
            return v["vendor"]
    return None


# ---------------------------------------------------------------------------
# DATEV deduplication
# ---------------------------------------------------------------------------

def load_normalised_datev(path: str) -> list[dict]:
    """Load normalised.csv in DATEV mode.

    DATEV normalised.csv has an extra _guid column (Buchungs GUID carried through
    by normalize.py). We deduplicate per GUID using cash-basis logic:

    Cash-basis: only count rows where the counterpart account (_gegen column)
    is a bank, card, or creditor account. These represent actual money movements.

    Returns list of dicts: description, amount (float, always positive = spend),
    date, guid.
    """
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))

    has_guid = "_guid" in (rows[0] if rows else {})
    has_gegen = "_gegen" in (rows[0] if rows else {})

    if not has_guid:
        # Fallback: no GUID column — treat each row as one transaction
        return _load_bank_rows(rows)

    # Cash-basis counterpart accounts (Gegenkonto values that signal real payment)
    PAYMENT_COUNTERPARTS = {
        "160000",   # bank account
        "7999999",  # Moss card clearing
        "150011",   # creditors
        "150013",   # creditors
        "121003",   # bank transit
        "121706",   # bank transit
    }

    # Group by GUID
    guid_groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        guid = str(row.get("_guid", "")).strip()
        if guid:
            guid_groups[guid].append(row)
        else:
            # No GUID → treat as standalone
            guid_groups[id(row)].append(row)

    result = []
    for guid, group in guid_groups.items():
        # Prefer rows where counterpart is a payment account
        if has_gegen:
            payment_rows = [r for r in group
                            if str(r.get("_gegen", "")).strip() in PAYMENT_COUNTERPARTS]
        else:
            payment_rows = []

        candidate_rows = payment_rows if payment_rows else group

        # From candidates, take the row with the largest positive soll amount
        # (the expense debit posting)
        best_row = None
        best_amount = 0.0
        for r in candidate_rows:
            amt_raw = str(r.get("amount", "")).strip()
            amt = parse_amount(amt_raw)
            if amt is None:
                continue
            # In DATEV normalised.csv, amount is the raw Umsatz Soll value (always >= 0)
            # We want the expense debit: positive soll on a non-balance-sheet account
            if amt > best_amount:
                best_amount = amt
                best_row = r

        if best_row is None or best_amount == 0:
            continue

        year, month = parse_date(str(best_row.get("date", "")))
        result.append({
            "description": str(best_row.get("description", "")).strip(),
            "amount": best_amount,
            "year": year,
            "month": month,
            "guid": str(guid),
        })

    return result


def _load_bank_rows(rows: list[dict]) -> list[dict]:
    """Load bank-format rows: each row = one transaction.

    Amount convention: negative = expense (debit), positive = income (credit).
    We keep only expenses (negative amounts) and return absolute values.
    """
    result = []
    for row in rows:
        amt_raw = str(row.get("amount", "")).strip()
        amt = parse_amount(amt_raw)
        if amt is None:
            continue
        # Negative = outgoing payment (expense)
        # Some bank formats (NatWest) have separate Debit/Credit columns —
        # normalize.py should have merged them into a signed amount already.
        # Keep both debits (negative) and credits (positive refunds):
        # For spend analysis, we want net = abs(debits) - abs(credits)
        # Here we store the signed amount and let aggregation handle netting.
        if amt == 0:
            continue
        year, month = parse_date(str(row.get("date", "")))
        result.append({
            "description": str(row.get("description", "")).strip(),
            "amount": amt,        # signed: negative = expense
            "year": year,
            "month": month,
            "guid": None,
        })
    return result


def load_normalised(path: str, datev_mode: bool) -> list[dict]:
    """Load normalised.csv in the appropriate mode."""
    if datev_mode:
        return load_normalised_datev(path)

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return _load_bank_rows(rows)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(transactions: list[dict], vendors: list[dict]) -> dict:
    """Match each transaction to a vendor and aggregate spend.

    Returns:
        {
          vendor_name: {
            "desc": str,
            "total": float,
            "txn_count": int,
            "months": {(year, month): float},
          }
        }
    """
    result: dict[str, dict] = {}

    for txn in transactions:
        desc = txn["description"]
        vendor = match_vendor(desc, vendors)
        if vendor is None:
            continue

        amt = txn["amount"]
        # For bank format: negative = expense; for DATEV mode: always positive
        # Normalise to positive spend amount
        spend = abs(amt) if amt < 0 else amt
        if spend == 0:
            continue

        year, month = txn["year"], txn["month"]
        ym = (year, month) if year and month else (None, None)

        if vendor not in result:
            # Find description for this vendor
            desc_text = next((v["desc"] for v in vendors if v["vendor"] == vendor), "")
            result[vendor] = {"desc": desc_text, "total": 0.0, "txn_count": 0, "months": {}}

        result[vendor]["total"] += spend
        result[vendor]["txn_count"] += 1
        if ym not in result[vendor]["months"]:
            result[vendor]["months"][ym] = 0.0
        result[vendor]["months"][ym] += spend

    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_report(agg: dict, output_path: str, currency: str):
    """Write spend_report.xlsx with three sheets."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, numbers
        from openpyxl.utils import get_column_letter
    except ImportError:
        sys.exit("openpyxl is required. Run: pip install openpyxl --break-system-packages")

    wb = openpyxl.Workbook()

    # ── Collect all months ──────────────────────────────────────────────────
    all_months = sorted(set(
        ym for v in agg.values() for ym in v["months"]
        if ym[0] is not None
    ))

    # ── Sheet 1: By Vendor ──────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "By Vendor"

    hdr_fill = PatternFill("solid", fgColor="1F3864")
    hdr_font = Font(bold=True, color="FFFFFF", size=10)
    num_fmt  = f'#,##0.00 "{currency}"'

    headers1 = ["Vendor", "Description", f"Total ({currency})", "Transactions", "Months Active"]
    for col, h in enumerate(headers1, 1):
        c = ws1.cell(1, col, h)
        c.fill = hdr_fill; c.font = hdr_font
        c.alignment = Alignment(horizontal="center")

    ws1.column_dimensions["A"].width = 28
    ws1.column_dimensions["B"].width = 52
    ws1.column_dimensions["C"].width = 16
    ws1.column_dimensions["D"].width = 14
    ws1.column_dimensions["E"].width = 14

    sorted_vendors = sorted(agg.items(), key=lambda x: -x[1]["total"])
    alt_fill = PatternFill("solid", fgColor="EEF2F7")

    for i, (vendor, data) in enumerate(sorted_vendors, 2):
        months_active = sum(1 for ym in data["months"] if ym[0] is not None)
        fill = alt_fill if i % 2 == 0 else None
        row_data = [vendor, data["desc"], data["total"], data["txn_count"], months_active]
        for col, val in enumerate(row_data, 1):
            c = ws1.cell(i, col, val)
            if fill: c.fill = fill
            if col == 3:
                c.number_format = num_fmt
                c.alignment = Alignment(horizontal="right")
            elif col in (4, 5):
                c.alignment = Alignment(horizontal="center")

    # Totals row
    total_row = len(sorted_vendors) + 2
    ws1.cell(total_row, 1, "TOTAL").font = Font(bold=True)
    total_cell = ws1.cell(total_row, 3, sum(d["total"] for d in agg.values()))
    total_cell.number_format = num_fmt
    total_cell.font = Font(bold=True)
    total_cell.alignment = Alignment(horizontal="right")
    ws1.cell(total_row, 4, sum(d["txn_count"] for d in agg.values())).font = Font(bold=True)

    # ── Sheet 2: By Month ───────────────────────────────────────────────────
    ws2 = wb.create_sheet("By Month")
    headers2 = ["Month", f"Total Spend ({currency})", "Vendors Active"]
    for col, h in enumerate(headers2, 1):
        c = ws2.cell(1, col, h)
        c.fill = hdr_fill; c.font = hdr_font
        c.alignment = Alignment(horizontal="center")
    ws2.column_dimensions["A"].width = 14
    ws2.column_dimensions["B"].width = 22
    ws2.column_dimensions["C"].width = 16

    for i, ym in enumerate(all_months, 2):
        year, month = ym
        month_label = f"{year}-{month:02d}" if year else "Unknown"
        month_total = sum(
            v["months"].get(ym, 0) for v in agg.values()
        )
        vendors_active = sum(1 for v in agg.values() if ym in v["months"])
        fill = alt_fill if i % 2 == 0 else None
        for col, val in enumerate([month_label, month_total, vendors_active], 1):
            c = ws2.cell(i, col, val)
            if fill: c.fill = fill
            if col == 2:
                c.number_format = num_fmt
                c.alignment = Alignment(horizontal="right")
            elif col == 3:
                c.alignment = Alignment(horizontal="center")

    # ── Sheet 3: Monthly Detail (pivot) ────────────────────────────────────
    ws3 = wb.create_sheet("Monthly Detail")

    month_labels = [f"{ym[0]}-{ym[1]:02d}" if ym[0] else "Unknown" for ym in all_months]
    pivot_headers = ["Vendor"] + month_labels + [f"Total ({currency})"]
    for col, h in enumerate(pivot_headers, 1):
        c = ws3.cell(1, col, h)
        c.fill = hdr_fill; c.font = hdr_font
        c.alignment = Alignment(horizontal="center" if col > 1 else "left")

    ws3.column_dimensions["A"].width = 28
    for col in range(2, len(pivot_headers) + 1):
        ws3.column_dimensions[get_column_letter(col)].width = 13

    for i, (vendor, data) in enumerate(sorted_vendors, 2):
        fill = alt_fill if i % 2 == 0 else None
        ws3.cell(i, 1, vendor)
        if fill: ws3.cell(i, 1).fill = fill
        row_total = 0.0
        for j, ym in enumerate(all_months, 2):
            val = data["months"].get(ym, 0)
            row_total += val
            c = ws3.cell(i, j, val if val > 0 else None)
            if fill: c.fill = fill
            if val > 0:
                c.number_format = "#,##0"
                c.alignment = Alignment(horizontal="right")
        total_c = ws3.cell(i, len(all_months) + 2, row_total)
        total_c.number_format = num_fmt
        total_c.font = Font(bold=True)
        total_c.alignment = Alignment(horizontal="right")
        if fill: total_c.fill = fill

    # Column totals row
    total_row3 = len(sorted_vendors) + 2
    ws3.cell(total_row3, 1, "TOTAL").font = Font(bold=True)
    for j, ym in enumerate(all_months, 2):
        col_total = sum(v["months"].get(ym, 0) for v in agg.values())
        c = ws3.cell(total_row3, j, col_total if col_total > 0 else None)
        c.font = Font(bold=True)
        if col_total > 0:
            c.number_format = "#,##0"
            c.alignment = Alignment(horizontal="right")
    grand = sum(d["total"] for d in agg.values())
    gc = ws3.cell(total_row3, len(all_months) + 2, grand)
    gc.number_format = num_fmt; gc.font = Font(bold=True)
    gc.alignment = Alignment(horizontal="right")

    wb.save(output_path)
    print(f"Report saved: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Aggregate software spend per vendor from normalised transaction data."
    )
    ap.add_argument("--normalised", required=True,
                    help="normalised.csv from normalize.py")
    ap.add_argument("--vendors", required=True,
                    help="matched.csv from match_taxonomy.py, or vendor_list.csv")
    ap.add_argument("--datev", action="store_true",
                    help="Enable DATEV double-entry deduplication mode")
    ap.add_argument("--output", default="spend_report.xlsx",
                    help="Output Excel file path")
    ap.add_argument("--currency", default="EUR",
                    help="Currency label for display (default: EUR)")
    args = ap.parse_args()

    # Load
    print(f"Loading transactions from {args.normalised}...")
    transactions = load_normalised(args.normalised, datev_mode=args.datev)
    print(f"  → {len(transactions)} transactions loaded")

    print(f"Loading vendors from {args.vendors}...")
    vendors = load_vendors(args.vendors)
    print(f"  → {len(vendors)} vendor patterns loaded")

    # Aggregate
    print("Aggregating spend per vendor...")
    agg = aggregate(transactions, vendors)
    print(f"  → {len(agg)} vendors matched with spend data")

    if not agg:
        print("WARNING: No vendors matched. Check that vendor patterns match transaction descriptions.")
        sys.exit(1)

    # Summary to console
    print(f"\n{'Vendor':<30} {'Total':>14}  {'Txns':>5}")
    print("-" * 55)
    for vendor, data in sorted(agg.items(), key=lambda x: -x[1]["total"])[:20]:
        print(f"{vendor:<30} {data['total']:>12,.2f}  {data['txn_count']:>5}")
    if len(agg) > 20:
        print(f"  ... and {len(agg) - 20} more vendors")
    print("-" * 55)
    print(f"{'TOTAL':<30} {sum(d['total'] for d in agg.values()):>12,.2f}")

    # Write Excel
    write_report(agg, args.output, args.currency)


if __name__ == "__main__":
    main()
