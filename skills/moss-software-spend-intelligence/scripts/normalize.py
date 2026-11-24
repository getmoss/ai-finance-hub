#!/usr/bin/env python3
"""Input normalizer for the Software Spend Snapshot skill.

Accepts any transaction file (DATEV xlsx, generic xlsx/csv, text PDF) and
produces a standardised CSV with columns [description, amount, date] that
the rest of the pipeline can consume without knowing the source format.

Detected formats
----------------
1. DATEV xlsx/csv  — column "Buchungstext" present → pass-through, no questions asked.
2. Generic xlsx/csv — known column sets detected automatically; interactive fallback
                      if detection fails.
3. Text PDF        — pdfplumber extracts tables; same detection logic as xlsx/csv.
4. Scanned PDF     — detected when pdfplumber finds no meaningful text; prints a
                      limitation notice and exits with code 2.
5. Unknown format  — unsupported extension; prints a limitation notice and exits.

Output
------
normalised.csv with columns: description, amount, date
  - description : str  (mandatory — the merchant / booking text)
  - amount      : str  (optional — empty string if not mappable)
  - date        : str  (optional — empty string if not mappable)

The downstream extract_candidates.py reads the "description" column; amount and
date are carried through for context but are not used by the taxonomy pipeline.

Usage
-----
    python3 normalize.py --input FILE [--output normalised.csv]

Interactive mode is triggered automatically when the format cannot be detected.
Pass --non-interactive to skip prompts and exit with code 3 instead.
"""

import argparse
import csv
import os
import sys
import re


# ---------------------------------------------------------------------------
# Format detection helpers
# ---------------------------------------------------------------------------

DATEV_COLUMN = "Buchungstext"

# Kontoblatt detection: single-account DATEV ledger report
# Identified by: has Buchungstext + HK + BSNr columns, but NO "Buchungs GUID"
# In this format every Soll row = one expense posting, no GUID dedup needed
KONTOBLATT_MARKER_COLS = {"HK", "BSNr.", "KOST1"}

# Known column-name synonyms for description / amount / date across common
# accounting exports (lowercase for matching).
DESCRIPTION_SYNONYMS = [
    "buchungstext", "description", "memo", "narrative", "details",
    "transaction description", "omschrijving", "libellé", "riferimento",
    "concepto", "text", "booking text", "transaction details", "particulars",
    "merchant", "vendor", "payee", "beneficiary", "remittance info",
    "zahlungsreferenz", "verwendungszweck", "referenz",
]
AMOUNT_SYNONYMS = [
    "amount", "betrag", "umsatz", "soll", "haben", "debit", "credit",
    "value", "sum", "total", "montant", "bedrag", "importe",
]
DATE_SYNONYMS = [
    "date", "datum", "buchungsdatum", "valuta", "wertstellung",
    "transaction date", "posting date", "booking date", "value date",
    "fecha", "data", "datum", "datum der buchung",
]


def _best_match(columns: list[str], synonyms: list[str]) -> str | None:
    """Return the first column whose lowercase name appears in synonyms."""
    lower_cols = {c.lower(): c for c in columns}
    for s in synonyms:
        if s in lower_cols:
            return lower_cols[s]
    return None


def _is_datev(columns: list[str]) -> bool:
    return any(c.strip() == DATEV_COLUMN for c in columns)


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------

def _read_xlsx_csv(path: str) -> tuple[list[str], list[list[str]]]:
    """Return (header_row, data_rows) for xlsx or csv."""
    import pandas as pd
    low = path.lower()
    if low.endswith((".xlsx", ".xlsm", ".xls")):
        df = pd.read_excel(path, sheet_name=0, dtype=str, header=0)
    else:
        df = pd.read_csv(path, dtype=str, sep=None, engine="python")
    df = df.fillna("")
    return list(df.columns), df.values.tolist()


def _read_pdf(path: str) -> tuple[list[str], list[list[str]]]:
    """Extract the largest table from a text PDF via pdfplumber.

    Returns (header, rows).
    Raises RuntimeError('SCANNED') if the PDF appears to be image-only.
    """
    try:
        import pdfplumber
    except ImportError:
        sys.exit(
            "pdfplumber is not installed. Run: pip install pdfplumber --break-system-packages"
        )

    all_rows: list[list[str]] = []
    total_text_chars = 0

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            total_text_chars += len(text.strip())
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    all_rows.append([str(c or "").strip() for c in row])

    # Heuristic: if we extracted very little text and no tables, it's likely scanned
    if total_text_chars < 50 and not all_rows:
        raise RuntimeError("SCANNED")

    if not all_rows:
        # Fall back: try to parse text as whitespace-delimited rows
        with pdfplumber.open(path) as pdf:
            lines = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines.extend(text.splitlines())
        if not lines:
            raise RuntimeError("SCANNED")
        # Use the first non-empty line as header
        non_empty = [l for l in lines if l.strip()]
        if not non_empty:
            raise RuntimeError("SCANNED")
        header_line = non_empty[0]
        # Split by 2+ spaces as column separator
        header = re.split(r"\s{2,}", header_line.strip())
        rows = []
        for line in non_empty[1:]:
            cols = re.split(r"\s{2,}", line.strip())
            rows.append(cols)
        return header, rows

    # Use first row as header
    header = all_rows[0]
    rows = all_rows[1:]
    return header, rows


# ---------------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------------

def _autodetect_columns(
    columns: list[str],
) -> tuple[str | None, str | None, str | None]:
    """Return (description_col, amount_col, date_col) using synonym matching."""
    return (
        _best_match(columns, DESCRIPTION_SYNONYMS),
        _best_match(columns, AMOUNT_SYNONYMS),
        _best_match(columns, DATE_SYNONYMS),
    )


def _interactive_column_mapping(
    columns: list[str], non_interactive: bool
) -> tuple[str, str | None, str | None]:
    """Ask the user to identify columns when autodetect fails.

    Returns (description_col, amount_col, date_col).
    amount_col and date_col may be None if the user skips them.
    """
    if non_interactive:
        sys.exit(
            "ERROR: Could not auto-detect columns and --non-interactive flag is set.\n"
            "Re-run without --non-interactive to answer column questions interactively."
        )

    print("\n" + "=" * 60)
    print("File not recognised as a standard format.")
    print("=" * 60)
    print("\nColumns found in the file:\n")
    for i, col in enumerate(columns, 1):
        print(f"  {i:>3}. {col}")
    print()

    def _ask(prompt: str, required: bool) -> str | None:
        while True:
            answer = input(prompt).strip()
            if not answer:
                if required:
                    print("  This field is required. Please enter a column name or number.")
                    continue
                return None
            # Accept number
            if answer.isdigit():
                idx = int(answer) - 1
                if 0 <= idx < len(columns):
                    return columns[idx]
                print(f"  Number out of range. Enter 1–{len(columns)}.")
                continue
            # Accept name (case-insensitive)
            match = next((c for c in columns if c.lower() == answer.lower()), None)
            if match:
                return match
            # Partial match
            partials = [c for c in columns if answer.lower() in c.lower()]
            if len(partials) == 1:
                print(f"  Matched: '{partials[0]}'")
                return partials[0]
            if len(partials) > 1:
                print(f"  Ambiguous — matches: {partials}. Be more specific.")
                continue
            print(f"  Column '{answer}' not found. Try again.")

    desc_col = _ask(
        "Which column contains the vendor name / transaction description? (required): ",
        required=True,
    )
    amount_col = _ask(
        "Which column contains the transaction amount? (press Enter to skip): ",
        required=False,
    )
    date_col = _ask(
        "Which column contains the transaction date? (press Enter to skip): ",
        required=False,
    )

    print()
    print(f"  Description column : {desc_col}")
    print(f"  Amount column      : {amount_col or '(skipped)'}")
    print(f"  Date column        : {date_col or '(skipped)'}")
    print()

    return desc_col, amount_col, date_col


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def _write_normalised(
    rows: list[list[str]],
    columns: list[str],
    desc_col: str,
    amount_col: str | None,
    date_col: str | None,
    output_path: str,
) -> int:
    """Write normalised.csv and return the number of rows written."""
    col_idx = {c: i for i, c in enumerate(columns)}
    desc_i = col_idx[desc_col]
    amount_i = col_idx[amount_col] if amount_col and amount_col in col_idx else None
    date_i = col_idx[date_col] if date_col and date_col in col_idx else None

    written = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["description", "amount", "date"])
        for row in rows:
            def _get(i):
                if i is None or i >= len(row):
                    return ""
                return str(row[i]).strip()
            desc = _get(desc_i)
            if not desc:
                continue
            writer.writerow([desc, _get(amount_i), _get(date_i)])
            written += 1

    return written


# ---------------------------------------------------------------------------
# Limitation messages
# ---------------------------------------------------------------------------

SCANNED_PDF_NOTICE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SKILL LIMITATION — Scanned PDF detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  This skill can read text-based PDFs (where the text is
  selectable / copy-pasteable), but the file you uploaded
  appears to be a scanned image PDF.

  At the moment, OCR (optical character recognition) is
  not supported. To process this file, please:

    1. Export the statement as a text PDF from your bank's
       online portal if available, or
    2. Convert the file to XLSX or CSV and re-upload.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

UNSUPPORTED_FORMAT_NOTICE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SKILL LIMITATION — Unsupported file format
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  The file '{filename}' has an extension that is not yet
  supported by this skill.

  Supported formats:
    • XLSX / XLS / XLSM  (Excel)
    • CSV / TSV          (comma- or tab-separated)
    • PDF                (text-based, not scanned)

  Please export your transactions in one of those formats
  and re-upload.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Normalise any transaction file to a standard CSV for the spend-snapshot pipeline."
    )
    ap.add_argument("--input", required=True, help="Path to input file")
    ap.add_argument("--output", default="normalised.csv", help="Output CSV path")
    ap.add_argument(
        "--non-interactive",
        action="store_true",
        help="Exit with error instead of prompting when format is unknown",
    )
    args = ap.parse_args()

    path = args.input
    ext = os.path.splitext(path)[1].lower()
    supported_tabular = {".xlsx", ".xlsm", ".xls", ".csv", ".tsv"}
    supported_pdf = {".pdf"}

    # ── Unsupported extension ────────────────────────────────────────────────
    if ext not in supported_tabular and ext not in supported_pdf:
        print(UNSUPPORTED_FORMAT_NOTICE.format(filename=os.path.basename(path)))
        sys.exit(1)

    # ── PDF branch ───────────────────────────────────────────────────────────
    if ext in supported_pdf:
        try:
            columns, rows = _read_pdf(path)
        except RuntimeError as e:
            if "SCANNED" in str(e):
                print(SCANNED_PDF_NOTICE)
                sys.exit(2)
            raise
        print(f"PDF: extracted {len(rows)} rows, {len(columns)} columns.")

    # ── Tabular branch ───────────────────────────────────────────────────────
    else:
        columns, rows = _read_xlsx_csv(path)
        print(f"File: {len(rows)} rows, {len(columns)} columns.")

    # ── DATEV fast-path ──────────────────────────────────────────────────────
    if _is_datev(columns):
        print(f"Format detected: DATEV (column '{DATEV_COLUMN}' found).")
        desc_col = DATEV_COLUMN
        # Try to autodetect amount / date for completeness
        _, amount_col, date_col = _autodetect_columns(columns)
    else:
        # ── Generic autodetect ───────────────────────────────────────────────
        desc_col, amount_col, date_col = _autodetect_columns(columns)
        if desc_col:
            print(
                f"Format detected: generic tabular.\n"
                f"  Description → '{desc_col}'\n"
                f"  Amount      → '{amount_col or '(not found)'}'\n"
                f"  Date        → '{date_col or '(not found)'}'"
            )
        else:
            # ── Interactive fallback ─────────────────────────────────────────
            print("Could not auto-detect the description column.")
            desc_col, amount_col, date_col = _interactive_column_mapping(
                columns, args.non_interactive
            )

    written = _write_normalised(rows, columns, desc_col, amount_col, date_col, args.output)
    print(f"\nNormalised: {written} rows → {args.output}")
    print("Next step: python3 extract_candidates.py --input", args.output, "--column description")


if __name__ == "__main__":
    main()
