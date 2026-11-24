#!/usr/bin/env python3
"""Deterministic Pass 1 for the Software Spend Snapshot skill.

Matches cleansed candidates against references/vendor_taxonomy.csv using
first-match-wins in taxonomy row order (specific patterns come before broad
ones, mirroring the source CASE statement).

Outputs:
    matched.csv   [candidate, sample_original, tx_count, canonical, category,
                   is_ai, taxonomy_excluded]
    unmatched.csv [candidate, sample_original, tx_count]  -> Pass 2 (LLM)

Semantics: is_excluded=1 patterns mark merchants that are definitively NOT
software spend (physical goods, human services, ledger noise). They go to
excluded.csv — not to the table and not to Pass 2.

Usage:
    python3 match_taxonomy.py --candidates candidates.csv \
        --taxonomy ../references/vendor_taxonomy.csv
"""
import argparse
import csv


def load_taxonomy(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def match(candidate_lower, taxonomy):
    for row in taxonomy:  # order matters: first match wins
        p = row["pattern"]
        if row["match_type"] == "exact":
            if candidate_lower == p:
                return row
        else:  # like -> substring
            if p in candidate_lower:
                return row
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--matched", default="matched.csv")
    ap.add_argument("--unmatched", default="unmatched.csv")
    args = ap.parse_args()

    taxonomy = load_taxonomy(args.taxonomy)
    matched, unmatched, excluded = [], [], []
    with open(args.candidates, newline="", encoding="utf-8") as f:
        for c in csv.DictReader(f):
            # Try candidate first, then sample_original as fallback
            hit = match(c["candidate"].lower(), taxonomy)
            if hit is None and c.get("sample_original"):
                hit = match(c["sample_original"].lower(), taxonomy)
            if hit and hit["is_excluded"] == "1":
                excluded.append(c)
            elif hit:
                matched.append({
                    **c,
                    "canonical": hit["canonical"],
                    "category": hit["category"],
                    "is_ai": hit["is_ai"],
                })
            else:
                unmatched.append(c)

    matched.sort(key=lambda r: (r["canonical"].lower(), r["candidate"].lower()))
    unmatched.sort(key=lambda r: r["candidate"].lower())

    with open(args.matched, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["candidate", "sample_original", "tx_count",
                                          "canonical", "category", "is_ai"])
        w.writeheader(); w.writerows(matched)
    with open(args.unmatched, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["candidate", "sample_original", "tx_count"])
        w.writeheader(); w.writerows(unmatched)

    with open("excluded.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["candidate", "sample_original", "tx_count"])
        w.writeheader(); w.writerows(sorted(excluded, key=lambda r: r["candidate"].lower()))

    canon = sorted({r["canonical"] for r in matched})
    print(f"matched: {len(matched)} candidates -> {len(canon)} canonical vendors; "
          f"excluded: {len(excluded)}; unmatched: {len(unmatched)} -> Pass 2")


if __name__ == "__main__":
    main()
