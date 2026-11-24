#!/usr/bin/env python3
"""Builds the final vendor table by merging Pass 1 matches + Pass 2 additions.

Usage:
    python3 scripts/build_table.py \
        --matched matched.csv \
        --pass2 pass2_includes.csv \
        --output final_table.csv \
        [--taxonomy references/vendor_taxonomy.csv] \
        [--priority pass2_priority.csv]

Key guarantee: every P2 vendor name is normalized against taxonomy.
If a model writes "CP Wave GmbH" but taxonomy has pattern "cp wave" → "CP Wave",
the output uses the canonical name. This makes naming deterministic regardless
of how the model phrased the vendor name in pass2_includes.csv.
"""
import argparse
import csv
import re
import sys


# Legal suffixes to strip as last-resort fallback normalizer
_LEGAL_SUFFIXES = re.compile(
    r'\s+(gmbh|ltd\.?|llc\.?|inc\.?|b\.v\.?|ag|ab|s\.a\.s?|ug|bv|as|oy|'
    r'gmbh\s*&\s*co\.?\s*kg|limited|corporation|corp\.?|plc\.?|s\.l\.?)\s*$',
    re.IGNORECASE
)
_URL_PREFIXES = re.compile(r'^(https?://)?(www\.)?', re.IGNORECASE)
_STAR_NOISE = re.compile(r'\*.*$')  # "GUMROAD* JORDI BRUIN" → "GUMROAD"


def load_taxonomy(path):
    """Load taxonomy patterns for P2 name normalization."""
    try:
        with open(path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        return [(r['pattern'].lower(), r['canonical'], r['match_type'])
                for r in rows if r['is_excluded'] == '0']
    except FileNotFoundError:
        return []


def normalize_vendor_name(raw_name, taxonomy_patterns):
    """Normalize a P2 vendor name to its taxonomy canonical, or clean it up.

    Priority:
    1. Exact taxonomy match on raw name → use canonical
    2. Substring taxonomy match on raw name → use canonical
    3. Strip legal suffixes, try taxonomy again → use canonical
    4. Return stripped name as-is
    """
    raw = raw_name.strip()
    raw_lower = raw.lower()

    # Pass 1: try matching raw name directly against taxonomy
    for pattern, canonical, match_type in taxonomy_patterns:
        if match_type == 'exact':
            if raw_lower == pattern:
                return canonical
        else:
            if pattern in raw_lower:
                return canonical

    # Pass 2: strip noise, try again
    cleaned = _STAR_NOISE.sub('', raw).strip()
    cleaned = _LEGAL_SUFFIXES.sub('', cleaned).strip()
    cleaned = _URL_PREFIXES.sub('', cleaned).strip()
    cleaned_lower = cleaned.lower()

    if cleaned_lower != raw_lower:
        for pattern, canonical, match_type in taxonomy_patterns:
            if match_type == 'exact':
                if cleaned_lower == pattern:
                    return canonical
            else:
                if pattern in cleaned_lower:
                    return canonical

    # Strip any trailing punctuation left after suffix removal
    cleaned = re.sub(r'[,\s]+$', '', cleaned).strip()

    # No taxonomy match — return cleaned name (strip legal suffix at minimum)
    return cleaned if cleaned else raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matched", required=True)
    ap.add_argument("--pass2", required=True)
    ap.add_argument("--output", default="final_table.csv")
    ap.add_argument("--unmatched", default="unmatched.csv")
    ap.add_argument("--priority", default="pass2_priority.csv")
    ap.add_argument("--taxonomy", default=None,
                    help="vendor_taxonomy.csv for P2 name normalization")
    args = ap.parse_args()

    # Auto-detect taxonomy path if not provided
    taxonomy_path = args.taxonomy
    if not taxonomy_path:
        import os
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(skill_dir, '..', 'references', 'vendor_taxonomy.csv'),
            'references/vendor_taxonomy.csv',
        ]
        for c in candidates:
            if os.path.exists(c):
                taxonomy_path = c
                break

    taxonomy_patterns = load_taxonomy(taxonomy_path) if taxonomy_path else []
    if taxonomy_patterns:
        print(f"Taxonomy loaded: {len(taxonomy_patterns)} patterns for P2 normalization")
    else:
        print("WARNING: no taxonomy loaded — P2 names won't be normalized", file=sys.stderr)

    # --- Pass 1: all canonical vendors ---
    matched_rows = list(csv.DictReader(open(args.matched)))
    canon_map = {}
    for r in matched_rows:
        c = r["canonical"]
        if c not in canon_map:
            canon_map[c] = {"vendor": c, "description": "", "unverified": "0"}

    canon_lower = {c.lower(): c for c in canon_map}

    # --- Pass 2 additions ---
    pass2_rows = []
    try:
        pass2_rows = list(csv.DictReader(open(args.pass2)))
    except FileNotFoundError:
        print("WARNING: pass2_includes.csv not found — using Pass 1 only", file=sys.stderr)

    p2_map = {}
    p2_sources = set()
    normalized_count = 0

    for r in pass2_rows:
        raw_vendor = r["vendor"].strip()
        desc = r.get("description", "").strip()
        unverified = r.get("unverified", "0")

        # Normalize vendor name against taxonomy
        vendor = normalize_vendor_name(raw_vendor, taxonomy_patterns)
        if vendor != raw_vendor:
            normalized_count += 1

        # Skip if already in P1
        if vendor.lower() in canon_lower:
            continue
        # Also skip if raw name was already covered by P1 under a different form
        if raw_vendor.lower() in canon_lower:
            continue

        if unverified == "1":
            desc = f"⚠ unverified — {desc}"

        # Use normalized name as key; if two P2 rows normalize to same vendor, keep first
        key = vendor.lower()
        if key not in p2_map:
            p2_map[key] = {"vendor": vendor, "description": desc, "unverified": unverified}

        src = r.get("source_candidate", "").strip().lower()
        if src:
            p2_sources.add(src)

    if normalized_count:
        print(f"P2 normalization: {normalized_count} vendor names corrected via taxonomy")

    # --- Merge ---
    final = {}
    for canon, row in canon_map.items():
        key = canon.lower()
        if key in p2_map:
            # P2 had a description for this P1 vendor — use it
            final[key] = p2_map[key]
            del p2_map[key]
        else:
            final[key] = {"vendor": canon, "description": row["description"], "unverified": "0"}

    for key, row in p2_map.items():
        final[key] = row

    rows = sorted(final.values(), key=lambda r: r["vendor"].lower())

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["vendor", "description", "unverified"])
        w.writeheader()
        w.writerows(rows)

    p1_count = len(canon_map)
    p2_new = len([r for r in rows if r["vendor"].lower() not in canon_lower])
    unverified = sum(1 for r in rows if r["unverified"] == "1")
    print(f"✓ final_table.csv: {len(rows)} vendors "
          f"({p1_count} from taxonomy + {p2_new} from Pass 2, {unverified} marked ⚠)")

    _run_exhaustion_check(args, p2_sources, p2_new)


def _run_exhaustion_check(args, p2_sources: set, p2_new_count: int):
    """Warn if Pass 2 looks like it stopped early."""
    source_file = args.priority
    try:
        with open(source_file, newline="", encoding="utf-8") as f:
            candidates = list(csv.DictReader(f))
        source_label = "pass2_priority.csv"
    except FileNotFoundError:
        try:
            with open(args.unmatched, newline="", encoding="utf-8") as f:
                candidates = list(csv.DictReader(f))
            source_label = "unmatched.csv"
        except FileNotFoundError:
            return

    if not candidates:
        return

    high_freq = [r for r in candidates if int(r.get("tx_count", 0)) >= 4]
    high_freq_covered = sum(
        1 for r in high_freq if r["candidate"].lower() in p2_sources
    )
    coverage_pct = high_freq_covered / len(high_freq) * 100 if high_freq else 100

    print(f"\n── Pass 2 exhaustion check ({source_label}) ──")
    print(f"   Candidates reviewed (tx≥4): {high_freq_covered}/{len(high_freq)} "
          f"({coverage_pct:.0f}% coverage)")
    print(f"   Total candidates in file  : {len(candidates)}")
    print(f"   New vendors added         : {p2_new_count}")

    if coverage_pct < 50:
        print(
            f"\n⚠  WARNING: Pass 2 coverage is LOW ({coverage_pct:.0f}%). "
            f"The LLM likely stopped early.\n"
            f"   → Continue Pass 2 from where it stopped. Do NOT present the table yet."
        )
    elif coverage_pct < 80:
        print(
            f"\n⚠  NOTE: Pass 2 coverage is partial ({coverage_pct:.0f}%). "
            f"Consider reviewing remaining {len(high_freq) - high_freq_covered} candidates."
        )
    else:
        print(f"   ✓ Pass 2 appears complete.")


if __name__ == "__main__":
    main()
