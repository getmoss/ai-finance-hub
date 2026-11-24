#!/usr/bin/env python3
"""Deterministic candidate extraction for the Software Spend Snapshot skill.

Input : a CSV/TSV/XLSX file and the name of the column holding merchant /
        booking text (Claude identifies the column; everything after that
        is deterministic).
Output: candidates.csv with columns [candidate, sample_original, tx_count],
        sorted alphabetically (case-insensitive). Same input file + same
        column always yields byte-identical output.

Usage:
    python3 extract_candidates.py --input FILE --column COLNAME \
        [--sheet SHEETNAME] [--output candidates.csv]
"""
import argparse
import csv
import re
import sys
import unicodedata

def _fix_encoding(s: str) -> str:
    """Repair common mojibake from latin-1/cp1252 bytes misread as UTF-8.

    Two patterns seen in DATEV exports:
    - 黨 (U+9EE8): ü (0xFC) or üh (0xFC 0x68) decoded as 3-byte UTF-8 sequence.
      Followed by 'h' → replace with 'ü' (h stays). Otherwise → replace with 'üh'.
    - '?' literal: ü replaced by question mark when encoding was simply dropped.
      Restore common German patterns: ?h → üh, ?r → är, ?s → äs, ?n → än.
    """
    # 黨 followed by h: only ü was swallowed, h is already present
    s = re.sub(r'黨(?=h)', 'ü', s)
    # 黨 not followed by h: both ü and h were swallowed
    s = s.replace('黨', 'üh')
    # Other known mojibake characters
    for bad, good in (('鰏', 'öh'), ('盲', 'ä'), ('脺', 'Ü'), ('脰', 'Ö'), ('脛', 'Ä'), ('脽', 'ß')):
        s = s.replace(bad, good)
    # ? replacing umlauts — restore common German patterns
    s = re.sub(r'([a-zA-Z])\?h', r'\1üh', s)
    s = re.sub(r'([a-zA-Z])\?r', r'\1är', s)
    s = re.sub(r'([a-zA-Z])\?s', r'\1äs', s)
    s = re.sub(r'([a-zA-Z])\?n', r'\1än', s)
    # Remove any remaining isolated ? between word chars
    s = re.sub(r'(?<=[a-zA-Z])\?(?=[a-zA-Z])', '', s)
    return s


PAYMENT_PREFIXES = re.compile(
    r"^(paypal\s*\*?|pp\*|stripe\s*\*?|sumup\s*\*?|sq\s*\*|gpay\s+|apple\.com/bill\s*|"
    r"amzn\s+mktp\s*|checkout\.com\s*|mollie\s*\*?|adyen\s*\*?)",
    re.IGNORECASE,
)
# invoice/ref numbers, dates, long digit runs, IBAN-ish tokens
NOISE_TOKENS = re.compile(
    r"\b(inv(oice)?[\s#:.-]*\d+|re(chnung)?[\s#:.-]*\d+|ref[\s#:.-]*\w+|"
    r"\d{2}[./-]\d{2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}|[a-z]{2}\d{2}[a-z0-9]{10,30}|\d{5,})\b",
    re.IGNORECASE,
)
TRAILING_LEGAL = re.compile(
    r"[\s,]+(gmbh|ag|inc\.?|llc|ltd\.?|limited|corp\.?|co\.?|b\.?v\.?|s\.?a\.?|"
    r"ug|kg|ohg|se|plc|pte|oy|ab|aps)\.?$",
    re.IGNORECASE,
)
MULTISPACE = re.compile(r"\s+")
PUNCT_EDGES = re.compile(r"^[\s\-_*.,;:/\\|]+|[\s\-_*.,;:/\\|]+$")
# whole-word ledger/accounting noise (German DATEV + English), removed token-wise
STOPWORDS = {
    "accrual", "accruals", "release", "prepaid", "exp", "expense", "expenses",
    "eb-wert", "gehalt", "gehälter", "lohn", "löhne", "umbuchung", "sammelbuchung",
    "rückstellung", "rueckstellung", "abgrenzung", "storno", "miete", "kaution",
    "vorsteuer", "umsatzsteuer", "ust", "steuer", "sozialversicherung", "krankenkasse",
    "opening", "balance", "zinsen", "bankgebühr", "bankgebuehren", "kontoführung",
    "invoice", "rechnung", "payment", "pmt", "zahlung", "gutschrift", "erstattung",
    "subscription", "license", "licenses", "licence", "lizenz", "lizenzen",
    "monthly", "annual", "jährlich", "monatlich", "fee", "fees", "from",
}
PERSON_NAME = re.compile(r"^[A-ZÄÖÜ]\.\s?[A-ZÄÖÜ][a-zäöüßA-Za-z-]+$")
MONTHS = re.compile(
    r"\b(jan(uar|uary)?|feb(ruar|ruary)?|mär(z)?|mar(ch)?|apr(il)?|mai|may|jun[ei]?|"
    r"jul[yi]?|aug(ust)?|sep(tember)?|okt(ober)?|oct(ober)?|nov(ember)?|"
    r"dez(ember)?|dec(ember)?)\b\.?",
    re.IGNORECASE,
)


def strip_stopwords(s: str) -> str:
    kept = [t for t in s.split(" ") if t and t.lower().strip(".,;:") not in STOPWORDS]
    return " ".join(kept)


def cleanse_segment(seg: str) -> str:
    s = unicodedata.normalize("NFKC", seg).strip()
    s = _fix_encoding(s)
    s = PAYMENT_PREFIXES.sub("", s)
    s = NOISE_TOKENS.sub(" ", s)
    s = MONTHS.sub(" ", s)
    s = MULTISPACE.sub(" ", s).strip()
    s = TRAILING_LEGAL.sub("", s)
    s = strip_stopwords(s)
    s = MULTISPACE.sub(" ", s)
    s = PUNCT_EDGES.sub("", s).strip()
    if PERSON_NAME.match(s):
        return ""
    if not re.search(r"[a-zA-Zäöüß]{2}", s):
        return ""
    return s


def cleanse(raw: str) -> list[str]:
    """Split booking text into segments (';' is the dominant separator in
    ledger exports) and cleanse each independently. One raw value can yield
    several candidates; segments reduced to noise yield none."""
    out = []
    for seg in str(raw).split(";"):
        c = cleanse_segment(seg)
        if len(c) >= 2:
            out.append(c)
    return out


def load_column(path: str, column: str, sheet: str | None):
    import pandas as pd

    low = path.lower()
    if low.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(path, sheet_name=sheet or 0, dtype=str)
    elif low.endswith(".tsv"):
        df = pd.read_csv(path, sep="\t", dtype=str)
    else:
        df = pd.read_csv(path, dtype=str, sep=None, engine="python")
    if column not in df.columns:
        sys.exit(f"ERROR: column '{column}' not found. Available: {list(df.columns)}")
    return df[column].dropna().astype(str).tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--column", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--output", default="candidates.csv")
    args = ap.parse_args()

    values = load_column(args.input, args.column, args.sheet)
    buckets: dict[str, dict] = {}
    for raw in values:
        for c in cleanse(raw):
            key = c.lower()
            if key not in buckets:
                buckets[key] = {"candidate": c, "sample_original": str(raw).strip()[:200], "tx_count": 0}
            buckets[key]["tx_count"] += 1

    rows = sorted(buckets.values(), key=lambda r: r["candidate"].lower())
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["candidate", "sample_original", "tx_count"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(values)} rows -> {len(rows)} unique candidates -> {args.output}")


if __name__ == "__main__":
    main()
