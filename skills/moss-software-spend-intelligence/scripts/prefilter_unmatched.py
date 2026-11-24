#!/usr/bin/env python3
"""Deterministic pre-filter for Pass 2: splits unmatched.csv into two files.

  pass2_priority.csv   — likely software candidates, sorted by software-signal
                         strength, then tx_count desc. LLM reads this first.
  pass2_residual.csv   — everything else after noise removal, sorted tx_count desc.
                         LLM reads this second if time/tokens allow.

Goal: shrink the haystack before the LLM sees it. The signal/noise ratio in raw
unmatched.csv is ~1% software; after pre-filter it should be 5–15%. This lets
the LLM find real vendors instead of drowning in restaurant receipts.

IMPORTANT: this script never drops candidates permanently. Whatever it can't
confidently classify goes to pass2_residual.csv, not to /dev/null. The LLM is
still the final judge.

Usage:
    python3 scripts/prefilter_unmatched.py \
        --unmatched unmatched.csv \
        [--priority pass2_priority.csv] \
        [--residual pass2_residual.csv]
"""
import argparse
import csv
import re

# ---------------------------------------------------------------------------
# Noise patterns — candidates matching ANY of these go to the discard pile.
# Built from empirical analysis of Nufin 2025 DATEV export.
# ---------------------------------------------------------------------------

# Applied to combined candidate + sample_original (lowercased)
NOISE_PATTERNS = [
    # Travel — TravelPerk / FlexiPerk booking fragments
    r"\bflight\b", r"\btrain\b", r"\bflight for trip\b", r"\btrain for trip\b",
    r"premium service for trip", r"flexiperk service", r"flexitravel service",
    r"seat booking fee", r"seat booking for trip",
    r"priority boarding", r"\bcabin bag\b", r"\bluggage charge\b",
    r"\brefund for trip\b",

    # Hotels & accommodation (generic)
    r"\bhotel\b", r"\bcity tax\b", r"\bnh city centre\b",

    # Restaurants, cafes, food delivery
    r"\blunch\b", r"\bdinner\b", r"\bbreakfast\b",
    r"\brestaurant\b", r"\bbistro\b", r"\bcafe\b", r"\bcaffe\b",
    r"\bkantine\b", r"\bpizz\b", r"\bburger\b", r"\bsushi\b",
    r"\bkebab\b", r"\bpoke\b", r"\bramen\b", r"\bwolt\b",
    r"\blieferando\b", r"\bdeliveroo\b", r"\bpret a manger\b",
    r"\bglobo\b",

    # Grocery / drugstore / retail
    r"\brewe\b", r"\baldi\b", r"\blidl\b", r"\btesco\b", r"\bsainsbury\b",
    r"\bdm drogerie\b", r"\bdm-drogerie\b", r"\bknuspr\b", r"\bfrisco\b",
    r"\bknuspr\.de\b",

    # Payroll / HR / intercompany
    r"\blohnabrechnung\b", r"\bgehalt\b", r"\blohn\b", r"\bpayroll\b",
    r"\bsozialversicherung\b", r"\bkrankenkasse\b", r"\bbav\b",
    r"cross charges? nufin", r"cross charges? moss",
    r"salary pmts", r"abzuf.hrende sv", r"abzug sachb",

    # Accounting noise / ledger entries
    r"\bbonus accrual\b", r"unwind bonus", r"vacation accrual",
    r"\beb-wert\b", r"\bsaldenvortrag\b", r"normalabschreibung",
    r"sofortabschreibung", r"\binterest iban\b", r"\bbank charge\b",
    r"nebenkosten des geldverkehrs", r"habenzinsen",

    # Customer pre-billing (Nufin SaaS revenue rows — not Moss's own spend)
    r"^pre billing\s*[-–]", r"pre billing 2025\.",
    r"writeoff.saasrevenue", r"writeoff-saas",

    # Card scheme / payment processing noise
    r"chargeback frauds", r"card frauds", r"mastercom",
    r"transact mc scheme", r"transact mc issuer", r"transact issuer assessment",
    r"tpl.*apple pay", r"tpl.*scheme costs", r"tpl.*transaction",
    r"cardholder fee", r"reverse service fee", r"reverse cardholder",

    # Tax / government
    r"\bsteuer\b", r"\bversicherung\b", r"\bfinanzamt\b",
    r"\bihk beitrag\b", r"\brundfunk\b", r"\bbolagsverket\b",
    r"\bkamer van koophandel\b",

    # Cleaning / physical office services
    r"office cleaning", r"city clean", r"3b dienstleistung",
    r"reinigung", r"fruit.?work", r"office fruit",

    # Physical goods / hardware (described explicitly)
    # Note: only filter when it's clearly a hardware purchase description,
    # NOT when "apple.com/de" appears as the vendor itself in sample_original
    r"^\d+\s*x\s*(apple|jabra|logitech|dell|lenovo|samsung)\b",
    r"^\d+x\s+(macbook|thinkpad|iphone|ipad|airpod)",
    r"^(macbook air m\d|mbp\s*\d+|mba\s*\d+)\s*$",

    # Receipt / expense noise
    r"receipt lost", r"receipt missing", r"private spend",
    r"office expenses?$", r"\bvat \d+%\b",

    # Person names as candidates (First.Last or "K. Szczepa" patterns)
    r"^[a-z]\.\s?[a-z][a-z\s-]{3,20}$",  # initials pattern
]

_NOISE_RE = re.compile(
    "|".join(f"(?:{p})" for p in NOISE_PATTERNS),
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Software-signal patterns — positive indicators that a candidate is likely
# software. Scored: more matches → higher priority batch position.
# ---------------------------------------------------------------------------

SOFTWARE_SIGNALS = [
    # Strong: explicit subscription/license language in context
    (3, r"\bsubscription\b"),
    (3, r"\bprepaid exp\b"),
    (3, r"\brelease prepaid\b"),
    (3, r"\bmerchant card\b"),
    (3, r"\babokarte\b"),
    (3, r"\bannual (fee|plan|license)\b"),
    (3, r"\bmonthly plan\b"),
    (3, r"\bplatform fee\b"),
    (3, r"\blicense fee\b"),
    (3, r"\bsaas\b"),
    (3, r"\bl&d\b"),          # learning & development budget signal
    (3, r"\bl&d budget\b"),
    (3, r"\bide\b"),           # integrated development environment
    (3, r"\bdevice management\b"),

    # Medium: domain-style names or known tech suffixes
    (2, r"\.io\b"),
    (2, r"\.ai\b"),
    (2, r"\.dev\b"),
    (2, r"\.app\b"),
    (2, r"\.com\b"),
    (2, r"\bcloud\b"),
    (2, r"\bapi\b"),

    # Weak: general tech language
    (1, r"\bsoftware\b"),
    (1, r"\bplatform\b"),
    (1, r"\bdigital\b"),
    (1, r"\btech\b"),
    (1, r"\bai\b"),
    (1, r"\bdata\b"),
    (1, r"\banalytics\b"),
    (1, r"\bsecurity\b"),
    (1, r"\binfra\b"),
    (1, r"\bhosting\b"),
    (1, r"\bcrm\b"),
    (1, r"\berp\b"),
    (1, r"\blearn\b"),
    (1, r"\bcourse\b"),
    (1, r"\btraining\b"),
    (1, r"\bworkflow\b"),
    (1, r"\bautom\b"),
    (1, r"\brecruit\b"),
    (1, r"\bpayment\b"),
    (1, r"\bfintech\b"),
    (1, r"\bmonitor\b"),
    (1, r"\btrack\b"),
]

_SIGNAL_RES = [(score, re.compile(pat, re.IGNORECASE)) for score, pat in SOFTWARE_SIGNALS]


def software_score(text: str) -> int:
    return sum(score for score, rx in _SIGNAL_RES if rx.search(text))


def is_noise(candidate: str, sample: str) -> bool:
    combined = (candidate + " " + sample).lower()
    return bool(_NOISE_RE.search(combined))


def load_p1_canonicals(matched_path: str) -> set:
    """Load canonical vendor names already found in Pass 1."""
    try:
        with open(matched_path, newline="", encoding="utf-8") as f:
            return {r["canonical"].lower() for r in csv.DictReader(f)}
    except FileNotFoundError:
        return set()


def is_p1_duplicate(sample: str, p1_canonicals: set) -> bool:
    """Return True if sample_original clearly references a P1 vendor.

    Many invoice-reference fragments appear in unmatched because the cleansed
    candidate is the invoice number (e.g. 'INVCZ9972288'), not the vendor name.
    The sample_original often contains the real vendor: '...JetBrains; Release
    prepaid exp...'. If the vendor is already in Pass 1, skip this row — the
    model would just re-discover a known vendor under a confusing alias.
    """
    sample_lower = sample.lower()
    for canon in p1_canonicals:
        # Only match if canon is at least 4 chars (avoid false positives on short names)
        if len(canon) >= 4 and canon in sample_lower:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unmatched", required=True)
    ap.add_argument("--priority", default="pass2_priority.csv")
    ap.add_argument("--residual", default="pass2_residual.csv")
    ap.add_argument("--matched", default="matched.csv",
                    help="matched.csv to skip P1-duplicate rows in priority")
    args = ap.parse_args()

    p1_canonicals = load_p1_canonicals(args.matched)

    with open(args.unmatched, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    priority, residual, discarded, p1_dupes = [], [], [], []

    for r in rows:
        cand = r["candidate"]
        samp = r.get("sample_original", "")
        tc = int(r["tx_count"])
        combined = cand + " " + samp

        if is_noise(cand, samp):
            discarded.append(r)
            continue

        score = software_score(combined)
        r["_score"] = score
        r["_tc"] = tc

        if score > 0:
            # Check if this is just an invoice fragment for a P1 vendor
            if p1_canonicals and is_p1_duplicate(samp, p1_canonicals):
                p1_dupes.append(r)
            else:
                priority.append(r)
        else:
            residual.append(r)

    # Sort priority by tx_count desc first (high-value first), then score as tiebreaker
    # Rationale: tc=26 AIM-X is more important than tc=2 Cursor L&D even if score is lower
    priority.sort(key=lambda r: (-r["_tc"], -r["_score"]))
    # Sort residual by tx_count desc
    residual.sort(key=lambda r: -r["_tc"])

    fieldnames = ["candidate", "sample_original", "tx_count"]

    def write(path, data):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)

    write(args.priority, priority)
    write(args.residual, residual)

    total = len(rows)
    print(f"Pre-filter results ({total} unmatched candidates):")
    print(f"  → pass2_priority.csv : {len(priority):>5} rows  (software signals, sorted by tx_count desc)")
    print(f"  → pass2_residual.csv : {len(residual):>5} rows  (no strong signal, review if time allows)")
    print(f"  → P1 duplicate skip  : {len(p1_dupes):>5} rows  (invoice refs for known P1 vendors)")
    print(f"  → discarded (noise)  : {len(discarded):>5} rows  (definite non-software)")
    print(f"  Noise reduction: {(len(discarded)+len(p1_dupes))/total*100:.0f}% removed, "
          f"{(len(priority)+len(residual))/total*100:.0f}% passed to LLM")


if __name__ == "__main__":
    main()
