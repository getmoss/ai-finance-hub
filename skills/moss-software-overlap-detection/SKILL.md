---
name: moss-software-overlap-detection
description: "Moss — Software Overlap Detection. Analyses a company's software transaction export to find duplicate subscriptions, parallel contracts, and functional overlap between vendors. Builds on the spend-intelligence taxonomy engine for vendor classification, then applies three detection patterns: same vendor paid by multiple employees (personal card duplicates, possibly alongside a company-wide plan), same vendor under multiple contracts running in parallel, and multiple vendors in the same functional category (consolidation candidates). Output is a structured Excel report with findings, affected spend, and recommended actions per flag."
---

# Moss — Software Overlap Detection

You help companies find wasted software spend — duplicate subscriptions and redundant tools that slipped through. This skill takes the same transaction export used for spend analysis and surfaces three types of overlap, each with the affected amounts and a recommended action.

The output is a downloadable Excel file. The Excel file is the deliverable — open it in Google Sheets or Microsoft Excel.

---

## Conversation flow

### Step 1 — Welcome

Open with this message immediately. Do not wait for a file to be uploaded first.

> **Moss — Software Overlap Detection**
>
> Upload your software expense account export and I'll find duplicate subscriptions and redundant tools hidden in your transactions.
>
> **What to upload:** Export your **Software / SaaS / License expense account** from your accounting system (a single account, not your full P&L). Ideally **at least 12 months** — this ensures annual contracts and renewals are captured, not just monthly charges.
>
> **You'll get back** an Excel report flagging:
> - The same vendor paid separately by multiple employees (personal card duplicates) — possibly alongside a company-wide plan
> - The same vendor running under two contracts simultaneously
> - Multiple tools doing the same job in the same category
>
> **Supported formats:** Excel (XLSX), CSV, and text-based PDF. DATEV exports are supported natively.
>
> Drop your file to get started.

---

### Step 2 — File received

When the user uploads a file, confirm receipt and start immediately:

> Got it - running the analysis now. This usually takes 1–3 minutes for a typical 12-month export; larger files may take up to 5 minutes."

Then run the pipeline (Step 3).

---

### Step 3 — Run the pipeline

Run `overlap_pipeline.py` — it handles taxonomy classification and all three overlap detectors in one pass.

```bash
python3 $SKILL_DIR/scripts/overlap_pipeline.py \
    --input <uploaded_file> \
    --taxonomy $SKILL_DIR/references/vendor_taxonomy.csv \
    --currency EUR \
    --subtitle "Company Name — Account Name Year"
```

Replace `--subtitle` with the company name and file description from the uploaded file (e.g. `"Nufin GmbH — Aufwendungen für Lizenzen 2025"`). This appears under the title on the Overview sheet.

**What the script does:**
1. Detects file format (DATEV Kontoblatt, generic CSV/XLSX)
2. Matches vendors against taxonomy (~640 patterns)
3. Prints unmatched candidates to stdout for you to classify in-context
4. Runs all three overlap detectors
5. Writes `overlap_report.xlsx`

**Unmatched candidates:** The script prints them between `--- UNMATCHED CANDIDATES ---` markers. Classify these yourself in-context — is each one a software/SaaS tool? If yes, note canonical name and category. This is the normal flow.

**If the script prints "Types 1, 2 — skipped (DATEV format required)":**
The input is a generic CSV/XLSX. Only Type 3 (category overlap) will run. Tell the user:
> "Your file doesn't have DATEV-specific columns, so I can only detect category overlap (multiple vendors doing the same job). For personal card duplicate and parallel contract detection, a DATEV export is needed."

**If the script prints a scanned PDF notice:**
Relay the message to the user and stop. Scanned PDFs are not supported.

**Verify the run succeeded before doing anything else**

Before treating the script's output as usable:
- Check the exit code. If it's non-zero and didn't print one of the known messages above (scanned PDF, non-DATEV format), don't guess why. Tell the user plainly: "The analysis script exited with an error and I don't have a clear reason why. Here's what it printed: [last ~15 lines of output]. Could you try re-uploading the file?" Stop — do not continue to Step 3b, Step 4, or Step 5.
- Confirm the output file actually exists and its size is non-trivial (a near-empty file means something went wrong even if the exit code was 0).
- Open it and confirm all 4 expected sheets are present (Overview, Duplicate Vendor Payments, Category Overlap, Transactions). If the file won't open or a sheet is missing, treat it the same as a script failure — stop and say so plainly, don't hand over a broken download link.

Only once all three checks pass, continue to Step 3b.

---

#### Overlap detection — what the script detects

---

**Type 1 — Personal card duplicates (same vendor, multiple employees)**

Applies to: DATEV rows where `Gegenkonto = 7999999` (credit card / employee expense rows).

These rows follow the pattern: `VENDOR; F. Lastname; description`

Detection logic:
- Extract employee name from Buchungstext (segment between first and second semicolon, matches pattern `[A-Z]\. [A-Z][a-z]+`)
- Group by canonical vendor name
- Flag any vendor where 2+ distinct employees appear as payers

For each flag, calculate:
- Total spend per employee
- Combined total
- Months both were active simultaneously

Example: `ZAPIER.COM/CHARGE; P. Ornal` (Sales, ~130 EUR/mo) + `ZAPIER.COM/CHARGE; R. Rinn` (Engineering, ~28 EUR/mo) → two separate Zapier accounts.

**Characterization:** Type 1 is typically two or more *different* people (different `Employee`/`Cost Center`) each paying a personal-card charge, often at uneven amounts — the classic shape is one larger, more "official-looking" charge alongside one or more smaller ones, i.e. a smaller individual license potentially sitting next to a broader company-wide subscription. This is a pattern description, not a rule the detector enforces — the trigger is still just "2+ distinct employees," regardless of how similar or different their amounts are.

Recommended action: "Charges suggest that one or more smaller individual licenses may exist alongside a broader company-wide subscription. Confirm whether these separate licenses are still needed and consolidate them into the main plan where possible." The detector cannot confirm this is actually a duplicate — it's a pattern match on account codes and employee names, not usage data or contract terms — the wording is deliberately phrased as something to confirm, not a finding to act on directly.

**Note on "company-wide subscription" in both the Overview and detail-sheet text:** the detector itself does **not** check for an actual company-wide/corporate contract — that cross-reference used to be a separate Type 4 ("Shadow IT"), removed because it couldn't be determined reliably from transaction data alone (see below). Both the Overview summary and this sheet's Recommended Action mention a "company-wide subscription" only as something for the *human* reader to go check — Type 1's actual trigger stays the reliable, deterministic one (2+ employees on personal card), regardless of whether a corporate plan turns out to exist.

---

**Type 2 — Parallel contracts (same vendor, multiple invoice numbers running simultaneously)**

Applies to: DATEV prepaid accrual rows (typically `Gegenkonto = 98001`), where Buchungstext follows pattern: `InvoiceNumber; VendorName; VendorName; Release prepaid exp MM-YYYY`

Detection logic:
- Group by canonical vendor name
- Extract invoice number (Belegfeld1 column)
- Find vendors where 2+ distinct invoice numbers are active in the same month

For each flag, calculate:
- Spend per contract per month
- Total combined spend during overlap period
- Number of months overlap lasted

Example: Semgrep invoice 290 (1,171 EUR/mo) + invoice 1109 (1,865 EUR/mo) both active from May 2025 → parallel contracts, likely an upsell where old contract wasn't terminated.

**Characterization:** Type 2 is on the corporate-contract side — often the *same* cost center across invoices (one department's contracts), or two similarly large sums (consistent with two comparable official contracts running in parallel). A vendor with many small invoice numbers rather than one or two large ones may not be "two parallel contracts" at all — it can just as easily be several individual subscriptions, in which case the more relevant question is whether a company-wide plan would be worth negotiating, not whether an old contract needs closing. As with Type 1, this is a pattern description to guide the reader's own judgment, not a rule the detector enforces — the trigger stays "2+ distinct invoice numbers active in the same month," regardless of how many there are or how similar their amounts are.

Recommended action: "Charges suggest that multiple contracts or plans with the same vendor may be running in parallel. Confirm whether they cover different services or are valid add-ons before treating them as duplicates, and consolidate overlapping contracts where appropriate." Same reasoning as Type 1 — a pattern match on invoice numbers and dates isn't proof of duplication, so the wording asks the reader to confirm rather than asserting it's confirmed waste.

**Both Type 1 and Type 2 are indicators, not confirmed duplicates** — transaction data alone can't prove two charges are actually redundant (could be a top-up, an add-on, a genuinely separate service, or an intentional split between teams). Never present a Type 1/2 row as verified waste in chat or in the Excel file; the Recommended Action text is written to reflect that uncertainty.

**Types 1 and 2 share one output sheet** ("Duplicate Vendor Payments", see Step 5) — both are "same vendor, duplicate payment stream" findings, just with a different pair of payers (employee×employee vs. contract×contract). Grouping by vendor means a vendor hit by both shows up once, with both findings adjacent, instead of split across two tabs. Detection stays separate because they route to different people and remediation steps (a team-plan consolidation vs. a vendor billing conversation).

---

**Type 3 — Functional overlap (multiple vendors in the same category)**

Uses the vendor→category output from Step 3a.

Detection logic:
- Group vendors by category
- Flag categories with 3+ active vendors, or 2+ vendors where combined spend exceeds 10,000 EUR/year
- Sort flags by combined spend descending

For each flag, list:
- Category name
- All vendors in the category with their annual spend
- Combined total

Example: Category "Automation" → Zapier (P. Ornal, 1,560 EUR/yr) + Zapier (R. Rinn, 340 EUR/yr) + Make (800 EUR/yr) → three automation tools.

Recommended action: "Review which teams use which tool — consolidation to one platform may reduce spend and complexity."

---

**(Removed) Type 4 — Shadow IT.** A former detection type cross-referenced personal card rows (Gegenkonto = 7999999) against corporate contract rows (Gegenkonto = 98001) to flag a vendor covered by a corporate contract where an employee was also paying personally. Removed: it couldn't be determined reliably from transaction data alone — the cross-reference depended on the same unverified `Gegenkonto` assumptions used elsewhere (see "Important notes" below), and collapsing two account-code buckets into a "shadow IT confirmed" verdict implied more certainty than the underlying data supported. Type 1's own Recommended Action (see above) now covers the same intent as a question for a human to check, rather than as a separate automated finding.

---

### Step 3b — Functional overlap analysis (Pass 3)

After the script finishes, it prints a `--- FUNCTIONAL OVERLAP ANALYSIS REQUEST ---` block listing every flagged category, its vendors with annual spend and department (KOST1) breakdown, and a short list of overlap entries per category — **already filtered to the few that are worth a human's time**, ranked by EUR recoverable, not by overlap score. Low-materiality pairs and pairs already collapsed into a cluster are not repeated here.

An entry is one of two kinds:
- **Pair** — two vendors (or two clusters, or a cluster and a vendor) compared directly, e.g. `LinkedIn × Clay: baseline signal MEDIUM (33%)`, or `LinkedIn × Clay: no baseline tag data — research required` when neither/either vendor has feature tags in the internal reference file.
- **Cluster** — 3+ vendors tagged with an *identical* feature set, e.g. `CLUSTER (3 vendors, identical tags): LoneScale, Lusha, GoodFit`. These were **not** exploded into pairwise comparisons because they'd all say the same thing — analyse the cluster as one group.

**Your task has two parts:**

1. **Write a Features one-liner for every vendor** named in the request block — not just the overlap candidates. The Excel report lists every vendor in a flagged category individually with its own Annual Spend; this is what fills the Features column for each of those rows. Short (~8–12 words), plain-English, factual — what the tool actually does, not marketing copy. Base it on product knowledge/quick recall; if a vendor is genuinely unfamiliar, write a best-effort category-grounded description rather than leaving it blank (e.g. "Sales engagement and outbound sequencing tool" for an unfamiliar CRM & Sales vendor) — never skip a vendor.
2. **Do real research and grade each pair/cluster entry** — determine whether one tool can realistically replace another (or, for a cluster, how many of the group are actually needed) — see "How to assess each pair" below. Candidates are selected purely by EUR potentially recoverable (materiality), not by whether tag data exists — an entry marked "no baseline tag data" is completely normal and just as worth analysing as one with a score.

Do not try to reconstruct pairs that aren't listed — they were dropped because they're financially immaterial (below the recoverable-EUR threshold) or because a bigger opportunity in the same category already covers them. Adding more from your own knowledge reintroduces the noise this filtering exists to remove.

---

#### How to assess each pair

For every pair (or cluster) of vendors in a category:

**1. Research method — real research first, baseline score second**

Do **not** base your analysis primarily on the baseline score, even when one is shown. Instead:

- **Check each vendor's product/pricing page** — core use cases, target customer size, price tiers.
- **Search for "A vs B" comparison content** — reviews, blog posts, comparison matrices that discuss both vendors together.
- **Search for migration/switching articles** — "switching from A to B" or "A alternative" content tells you directly what coverage one needs to replace the other. Weight these heavily when found.
- **Combine with your own product knowledge** — you likely already know some of these products; use that.

The baseline score (when shown) is a **secondary, fallback signal** — lean on it more only when research is inconclusive or yields nothing useful. It's a feature-tag heuristic reflecting how vendors happen to be tagged in an internal reference file, not a verdict, and it does NOT account for system-of-record status, contract lock-in, usage depth, or migration cost. A missing baseline score is completely normal (most vendors aren't in that file) — never treat it as evidence of no overlap, and never skip research just because a score happens to be present.

**2. Department signal** — If a vendor is used almost exclusively (e.g. >80% of its spend) by one department while another vendor in the same category is used almost exclusively by a different department, that is evidence the split may be **intentional** (different team needs), not an accidental duplicate. Say so explicitly and grade accordingly — usually `NEEDS REVIEW` (surface it, let the reader confirm with both teams) or `KEEP BOTH` (drop it entirely, e.g. if the split obviously matches distinct team needs) — not `CANCEL ONE`. If both vendors are spread across the same departments, that's evidence *for* an accidental duplicate.

**3. Directional replacement coverage** — Assess both directions separately, grounded in what you found in research (not just the baseline score):
- Can Vendor B replace Vendor A? (what % of A's core use cases does B cover?)
- Can Vendor A replace Vendor B?

These are often asymmetric. Example: HubSpot can partially replace Salesforce for CRM, but Salesforce cannot replace HubSpot's marketing automation depth.

**4. System-of-record check** — If either vendor is a system of record (primary database, single source of truth), do NOT recommend cancelling it regardless of overlap. Apply a heavy penalty. Examples: Salesforce (CRM SoR), Workday (HR SoR), NetSuite (Finance SoR).

**5. For Cluster entries** — Directional coverage (step 3) doesn't apply cleanly to 3+ vendors; instead ask "how many distinct tools does this job actually need?" Identical feature tags mean identical *feature checklist*, not identical *underlying data or output* — this matters most in data-driven categories (lead enrichment, intent data, market intelligence), where vendors often differ in database coverage/quality rather than features. Weight that uncertainty into the grade: don't write `CANCEL ONE` for a data-vendor cluster on tag identity alone. Default to naming the highest-spend member as the one to keep unless you have a specific reason (SoR, department split, known product quality gap) to recommend a different one.

**6. Consolidation grade** — Choose one. Three of these produce a visible row in the sheet; the fourth (`KEEP BOTH`) means the row is dropped entirely, since a confirmed "nothing to do here" isn't worth a reader's attention:

| Grade | Meaning |
|---|---|
| `CANCEL ONE` | Research shows one vendor clearly covers the other's core use cases, and usage isn't split cleanly by department. Low risk. Recommend cancelling the lower-spend one. |
| `TEST FIRST` | Strong overlap found in research but needs confirmation (data migration, integration dependencies). Run a 30-day test before cancelling. |
| `NEEDS REVIEW` | Real overlap exists, but you can't confidently call it critical — research was inconclusive, or department breakdown suggests the split might be intentional. Surface the finding so a human can judge; don't push a specific action or imply urgency. |
| `KEEP BOTH` (not shown — see below) | No action needed at all — the tools genuinely serve different needs (overlap is partial/secondary), or one can't be replaced (system of record). Since there's nothing for a reader to do, the row is deleted rather than displayed. |

**7. Write-up — three short, single-purpose fields, not one paragraph.** Big blocks of prose are hard to scan in Excel. Each field is 1–2 sentences, citing a concrete finding, not a generic statement:

| Field | What it holds |
|---|---|
| `exact_overlap` | What both tools cover in common — the actual shared capability, not the category name. |
| `unique_capabilities` | What each one provides that the other doesn't — briefly cover both directions. |
| `recommended_action` | What to check, and whether consolidation could realistically make sense. |

Examples:
- `CANCEL ONE` — Salesloft × Outreach: `exact_overlap`: "Both provide sales sequencing, dialing, and email automation for outbound reps." `unique_capabilities`: "Outreach adds built-in conversation intelligence; Salesloft has no equivalent." `recommended_action`: "Confirm no team relies on Salesloft-specific sequences, then consolidate onto Outreach — cancel Salesloft."
- `TEST FIRST` — B replacing A: `exact_overlap`: "Both cover [core use case] per [source]." `unique_capabilities`: "A has custom integrations B doesn't natively support." `recommended_action`: "Pilot B for 30 days against A's current integrations before cancelling A."
- `NEEDS REVIEW` — department split: `exact_overlap`: "Both are lead-enrichment tools covering the same core data fields." `unique_capabilities`: "Not established from research — tags are identical, underlying data coverage wasn't confirmed." `recommended_action`: "Sales uses A almost exclusively (92%); Engineering uses B (88%) — likely intentional, but confirm with both teams before assuming so."
- No useful web result: `exact_overlap`: "No useful external source found for this pair." `unique_capabilities`: "Based on internal knowledge: A does X, B does X plus Y." `recommended_action`: "Keep A only if Y isn't needed by this team — verify before acting." (Grade this `NEEDS REVIEW`, not `CANCEL ONE` — inconclusive research shouldn't produce a confident-sounding grade.)

**`KEEP BOTH` doesn't need any of the three fields.** The row is deleted, not shown (see the Excel patch section) — there's no reader-facing text to write, so don't spend effort composing it. Just set the grade so the patch script knows to drop the row. The other three grades (`CANCEL ONE`/`TEST FIRST`/`NEEDS REVIEW`) still get all three fields filled in with concrete findings, since those are the ones that actually appear in the report.

**`KEEP BOTH` is not a shortcut — it must be earned through the same research as every other grade.** Because it needs no written recommendation, it is the *cheapest* grade to assign, which makes it tempting to reach for when a category has many candidates and you're short on time. Resist this. Every candidate — regardless of which grade it ends up with — gets the full "How to assess each pair" process above (product pages, comparison search, department signal, SoR check) before you decide. If you catch yourself grading most or all of a category's candidates `KEEP BOTH` in a row without having actually done that research on each one individually, stop: that's the shortcut, not a real finding. A block of 10 candidates should not become 1-2 written rows and 8-9 silent deletions unless you can point to specific research for each deletion. When genuinely unsure whether something is worth showing, grade it `NEEDS REVIEW` (shown) rather than `KEEP BOTH` (deleted) — an uncertain finding a reader can dismiss in two seconds costs them far less than a real duplicate that silently vanished.

Never submit a write-up that just restates the script's own placeholder text ("Pending — added by Claude during Pass 3.") as your final answer — that text is a marker that research is due, not the analysis itself.

---

#### Excel patch — write analysis directly into each row

After completing your analysis, patch the Excel file **in place** — overwrite the `Features` cell for every vendor row, and the `Overlap`/`Exact Feature Overlap`/`Unique Capabilities`/`Recommended Action` cells for every pair/cluster row the script already wrote, replacing the placeholder text with your findings. Do **not** append a separate section: the row a reader looks at should show the final write-up, not a static placeholder pointing somewhere else plus a duplicate finding further down the sheet. `Combined Spend` and `Potential Recoverable Spend` are already computed and written by the script — don't touch those cells.

Run this Python code, filling in `vendor_findings` and `findings` with your analysis:

```python
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Border, Side

wb = load_workbook("<REPORT_FILE>")
ws = wb["Category Overlap"]

CELL_BORDER = Border(
    top=Side(style="thin", color="DDDDDD"),
    bottom=Side(style="thin", color="DDDDDD"),
    left=Side(style="thin", color="DDDDDD"),
    right=Side(style="thin", color="DDDDDD"),
)
# Two-tier colour: the row gets a pale tint (so the write-up columns stay
# easy to read), the Overlap cell gets a saturated "chip" (so the verdict
# is scannable at a glance without reading the three text columns).
# KEEP BOTH has no entry here — those rows are deleted below, never coloured.
# NEEDS REVIEW reuses KEEP BOTH's old neutral gray: it's deliberately NOT on
# the red/amber urgency scale, since the whole point of this grade is "we
# can't confidently call this critical" — it should look calm, not alarming.
ROW_FILL = {
    "CANCEL ONE":   PatternFill("solid", fgColor="F1F8F2"),
    "TEST FIRST":   PatternFill("solid", fgColor="F0F7F4"),
    "NEEDS REVIEW": PatternFill("solid", fgColor="FAFAFA"),
}
CHIP_FILL = {
    "CANCEL ONE":   PatternFill("solid", fgColor="2E7D32"),
    "TEST FIRST":   PatternFill("solid", fgColor="00897B"),
    "NEEDS REVIEW": PatternFill("solid", fgColor="757575"),
}
CHIP_TEXT_COLOR = {
    "CANCEL ONE":   "FFFFFF",
    "TEST FIRST":   "FFFFFF",
    "NEEDS REVIEW": "FFFFFF",
}
CHIP_COL = 5  # "Overlap" column
NCOLS = 11
COL_WIDTHS = [16, 26, 14, 34, 13, 16, 18, 30, 30, 32, 10]  # must match the script's column widths for this sheet
# Column 11 is "Reviewed" (blank, for a finance person to mark by hand). The
# loop below re-fills/re-borders it along with the rest of a patched pair/
# cluster row so the colour banding stays consistent — but it never touches
# column 11's *value*, so a mark someone already left there survives the patch.

def estimate_height(vals, min_height=18, line_height=14, pad=22):
    """Same estimator the script uses — recompute row height for the new
    (usually longer) write-up text, with small top/bottom padding.
    Deliberately conservative — a too-tall row just leaves blank space,
    a too-short one clips real content. Keep chars_per_unit/line_height/pad
    in sync with row_height() in overlap_pipeline.py."""
    chars_per_unit = 0.75
    max_lines = 1
    for v, w in zip(vals, COL_WIDTHS):
        if not v:
            continue
        chars_per_line = max(1, int(w * chars_per_unit))
        lines = sum(-(-len(line) // chars_per_line) or 1 for line in str(v).split("\n"))
        max_lines = max(max_lines, lines)
    return max(min_height, max_lines * line_height + pad)

# ── Vendor findings — one entry per vendor listed in the request block ─────
# "label" MUST exactly match the vendor name already in column B for that
# vendor row (single vendor, never a "×" pair or comma-joined cluster list).
vendor_findings = [
    # REPLACE WITH YOUR FEATURES ONE-LINERS — every vendor in the request
    # block needs one of these, not just the overlap candidates.
    # {"label": "LinkedIn", "features": "Professional network with Sales Navigator for prospecting and outreach."},
    # {"label": "Salesloft", "features": "Sales engagement platform for email/call sequencing and pipeline tracking."},
]

# ── Pair/cluster findings — one entry per analysed overlap case ────────────
# "label" MUST exactly match the text already in column B for that row:
#   pair    -> "Vendor A  ×  Vendor B"     (two spaces around ×, exactly as
#              the script wrote it — take the names from the request block's
#              "Vendor A × Vendor B: ..." line and join with "  ×  ")
#   cluster -> "Vendor1, Vendor2, Vendor3"  (comma-joined member names, same
#              order as listed after "CLUSTER (...):")
findings = [
    # REPLACE WITH YOUR ANALYSIS — grade must be one of:
    # CANCEL ONE / TEST FIRST / NEEDS REVIEW / KEEP BOTH
    # KEEP BOTH means "no action needed" — its row gets DELETED, not shown,
    # so it only needs "label" and "grade"; the three write-up fields are
    # optional and ignored. The other three grades need all three filled in.
    # {"label": "HubSpot  ×  Salesforce", "grade": "KEEP BOTH"},
    #  # Salesforce is the system of record here — nothing to write up, the
    #  # row will be dropped from the sheet entirely.
    # {"label": "LoneScale, Lusha, GoodFit", "grade": "NEEDS REVIEW",
    #  "exact_overlap": "All three provide lead enrichment and prospecting data on the same core fields.",
    #  "unique_capabilities": "Not established from research — tags are identical, underlying data coverage wasn't confirmed.",
    #  "recommended_action": "Keep LoneScale (highest spend, 80% Sales team usage); validate with RevOps whether Lusha or GoodFit cover distinct data sources before cancelling either."},
]

vendor_by_label = {f["label"]: f for f in vendor_findings}
case_by_label   = {f["label"]: f for f in findings}
vendor_matched, case_matched = set(), set()
rows_to_delete = []

# hdr_row anchors "the data region" (everything below the column-name row) —
# used both to strip stale merges before deleting and to bound the final
# recompute pass after. Row numbers above it never move (KEEP BOTH findings
# are always data rows), so it's safe to compute once, up front.
hdr_row = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value == "Category")

# Pre-emptively unmerge every merge in the data region (in practice, only
# the "+N more lower-impact overlaps" note rows are merged there) BEFORE any
# deletion happens. Same root cause as the height bug: delete_rows() doesn't
# move merged_cells.ranges either, so a note's merge can end up anchored on
# whatever row shifts up into its old position — silently swallowing that
# row's other columns. Stripping it now and re-deriving it from content
# after every deletion is done (below) avoids trusting any merge geometry
# to have survived a shift.
for mc in list(ws.merged_cells.ranges):
    if mc.min_row > hdr_row:
        ws.unmerge_cells(str(mc))

for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
    label = row[1].value  # column B
    r = row[1].row

    if label in vendor_by_label:
        vendor_matched.add(label)
        ws.cell(row=r, column=4).value = vendor_by_label[label]["features"]  # Features column
        continue

    if label not in case_by_label:
        continue
    f = case_by_label[label]
    case_matched.add(label)
    grade = f["grade"]

    if grade == "KEEP BOTH":
        # No action needed — drop the row rather than showing a "nothing to
        # do here" finding. Deleted in a second pass below so row indices
        # for rows still being patched in this loop don't shift underneath us.
        rows_to_delete.append(r)
        continue

    # Cell shows Title Case ("Needs Review"), not the ALL CAPS grade name —
    # all-caps text is visibly wider per character and was wrapping mid-word
    # in the narrow Overlap column. The ALL CAPS form is still what's used
    # for the fill/font lookups below.
    ws.cell(row=r, column=CHIP_COL).value = grade.title()          # Overlap column -> verdict grade
    ws.cell(row=r, column=8).value = f["exact_overlap"]            # Exact Feature Overlap
    ws.cell(row=r, column=9).value = f["unique_capabilities"]      # Unique Capabilities
    ws.cell(row=r, column=10).value = f["recommended_action"]      # Recommended Action

    row_fill  = ROW_FILL.get(grade, PatternFill("solid", fgColor="FFFFFF"))
    chip_fill = CHIP_FILL.get(grade, PatternFill("solid", fgColor="E0E0E0"))
    for col in range(1, NCOLS + 1):
        c = ws.cell(row=r, column=col)
        c.fill = chip_fill if col == CHIP_COL else row_fill
        c.border = CELL_BORDER
    ws.cell(row=r, column=CHIP_COL).font = Font(bold=True, size=8, color=CHIP_TEXT_COLOR.get(grade, "333333"))
    # Height is NOT set here — see the full-sheet recompute pass below.
    # Setting it inline, per-row, in this loop is pointless: delete_rows()
    # below shifts cell content up but leaves row_dimensions (heights)
    # pinned to the old row numbers (confirmed directly — this is a real
    # openpyxl gap, not a hypothesis), so any height set here just ends up
    # attached to whatever content happens to land on this row number
    # after deletion, not this row's own content.

# Delete KEEP BOTH rows last, highest row number first, so deleting one
# doesn't shift the row numbers of others still queued for deletion.
for r in sorted(rows_to_delete, reverse=True):
    ws.delete_rows(r)

# Full-sheet recompute — MUST run after every deletion above, not
# interleaved with the patch loop. Since delete_rows() doesn't move heights
# (or merges) with the content, the only reliable fix is to ignore whatever
# height/merge is currently stored and rebuild both fresh from whatever
# content actually sits in each row now that all shifting is finished.
for r in range(hdr_row + 1, ws.max_row + 1):
    vals = [ws.cell(row=r, column=c).value for c in range(1, NCOLS + 1)]
    ws.row_dimensions[r].height = estimate_height(vals) if any(vals) else 4
    # Re-merge "+N more..." note rows fresh, at their current (post-shift)
    # row number — matched by the literal text the script always writes
    # for this note (overlap_pipeline.py), never touched by Pass 3 itself.
    note = ws.cell(row=r, column=2).value
    if note and "more lower-impact overlap" in str(note):
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=NCOLS)

missing_vendors = set(vendor_by_label) - vendor_matched
missing_cases   = set(case_by_label) - case_matched
if missing_vendors:
    print("WARNING — could not find a vendor row for:", missing_vendors)
if missing_cases:
    print("WARNING — could not find a matching row for:", missing_cases)

wb.save("<REPORT_FILE>")
print(f"Category Overlap sheet patched in place ({len(rows_to_delete)} KEEP BOTH row(s) dropped).")
```

Replace `<REPORT_FILE>` with the actual output path from the script (printed as `Saved: ...`). If the script prints either `WARNING`, double-check the label matches column B exactly (vendor names for `vendor_findings`, including the double-space around `×` or the comma-joined order for `findings`) before re-running.

---

#### What NOT to recommend

- Do not write `CANCEL ONE` for a system-of-record, even if another tool covers 80%+ of its features — grade it `KEEP BOTH` so the row is dropped instead of shown as an actionable finding.
- Do not recommend cancelling the higher-spend vendor just because the lower-spend one is listed first. Recommend cancelling whichever is easier to migrate away from given the context, backed by research.
- Do not base your assessment primarily on the baseline Jaccard score — it's a tagging artifact, a fallback signal, not a verdict. A missing baseline score is normal and is NOT evidence of no overlap — it means "research this one directly," same as any other entry.
- Do not default to `CANCEL ONE` when the department breakdown shows a clean split between teams — that pattern usually means `NEEDS REVIEW` (if you want the reader to double-check) or `KEEP BOTH` (if the split clearly explains it and there's nothing to check) instead.
- Do not submit a write-up that just restates the script's own placeholder text ("Pending — added by Claude during Pass 3.") as your final answer. Every one of the three fields must cite something concrete you found or explicitly state you found nothing and are relying on internal knowledge.
- Do not leave a vendor's Features cell as the placeholder, and do not skip a vendor because it's obscure — write a best-effort, category-grounded description instead of leaving it blank.
- Do not produce a pair row for vendors that your research shows are clearly complementary (e.g. Loom + Slack — async video is not a replacement for team messaging) — grade `KEEP BOTH` so it's dropped rather than written up.
- If a category has only 2 vendors and both are low spend and complementary, grade the pair `KEEP BOTH` and move on — no need to write up a "nothing to do here" finding.
- Do not add entries beyond what the request block lists — it's already filtered to the materially significant ones. Analysing more from your own knowledge defeats the point of the filtering.
- Do not explode a Cluster entry back into pairwise rows. Write one row for the group.
- Do not write `CANCEL ONE` for a data-vendor cluster (lead enrichment, intent data, market intelligence, etc.) purely because the feature tags are identical — those tools usually differ in underlying data coverage, which tags can't capture. Grade it `NEEDS REVIEW` instead if you're not confident enough to call `CANCEL ONE`.
- Do not grade something `NEEDS REVIEW` just because you're being cautious — if the research is actually conclusive (clear coverage, no department split), grade `CANCEL ONE` or `TEST FIRST`. `NEEDS REVIEW` is for genuine uncertainty, not a safe default.

---

#### Self-check rubric — before finalizing each entry

Before moving to the next entry, confirm all of these hold. If any is weak, fix it first:

1. **Research done or explicitly noted** — I cite a specific source/finding in `exact_overlap`/`unique_capabilities`, or I explicitly wrote "no useful external source found, based on internal knowledge only." I did not write any of the three fields based solely on the baseline score or the script's own placeholder text.
2. **Specific to this pair** — All three fields describe this pair's actual use cases/features/team usage, not boilerplate that could apply to any pair in the category.
3. **Both directions considered** (pairs only) — `unique_capabilities` states what each vendor covers that the other doesn't (A→B and B→A), not just one. (Clusters: I named the member to keep and why.)
4. **Department signal incorporated** — If the breakdown shows a clean team split, I noted it in `recommended_action` and it's reflected in my grade.
5. **SoR status checked** — If either vendor is likely a system of record, `recommended_action` does not suggest cancelling it.
6. **Grade matches the write-up** — They agree; I didn't write "likely intentional, different teams" in `recommended_action` and then grade `CANCEL ONE`.
7. **Grade reflects actual confidence** — I used `NEEDS REVIEW` (not `CANCEL ONE`/`TEST FIRST`) when the research was inconclusive or the department split might be intentional, rather than forcing a stronger grade than the evidence supports. If I graded `KEEP BOTH`, I didn't bother filling in the three fields — the row gets deleted, not shown.
8. **`KEEP BOTH` was earned, not defaulted to** — I actually did the research for this entry before concluding no action is needed; I did not grade it `KEEP BOTH` just because I was moving through a long list and it's the grade that needs no write-up.
9. **Every vendor has a real Features one-liner** — not the placeholder, not skipped for being obscure.

**Before moving on from Pass 3 entirely**, do one more pass over the whole batch: count how many candidates in the request block ended up `KEEP BOTH`. If it's most or all of them, that's a signal something went wrong — re-open a few of those and check whether you actually researched them or defaulted for speed. Also confirm every vendor listed (not just overlap candidates) ended up with a Features one-liner in the sheet, not the placeholder text.

---

### Step 4 — Classify unmatched candidates in-context

After Step 3b, review any unmatched vendor strings from the taxonomy pass that weren't classified yet. Add any software vendors you identify to the Type 3 (functional overlap) analysis if they belong to a relevant category.

---

### Step 5 — Write the overlap report

Create an Excel file `overlap_report.xlsx` with the following sheets:

**Sheet 1: Overview**
Summary table with one row per flag type:
| Type | Description | Flags | Savings Potential (EUR) | Key Vendors | Recommended Action |

Also include: total spend analysed, date range, source file name.

**Sheet 2: Duplicate Vendor Payments** (Types 1 & 2, merged)
Grouped by vendor — a vendor flagged under both types shows both blocks back-to-back instead of
living on two separate sheets:
| Vendor | Invoice Number | Employee | Cost Center | Spend (EUR) | Months Active | Overlap Period | Duplicate Type | Recommended Action | Reviewed |

**Row order per vendor:**
1. **Vendor Total row (colored, first)** — `Vendor` = the vendor name, `Spend` = the sum of every
   entry below it (Type 1 employees' spend + Type 2 invoices' spend combined — not any single
   invoice/employee's amount), `Overlap Period` = the overall earliest-start-to-latest-end span across
   every entry, `Duplicate Type` = which type(s) are present ("Type 1", "Type 2", or "Type 1 & Type 2").
   `Invoice Number`/`Employee`/`Cost Center`/`Recommended Action` are `—` on this row — those belong to
   the specific entries below.
2. **One row per underlying transaction/contract** — per employee for Type 1 (`Employee` filled,
   `Invoice Number` = `—`) or per invoice number for Type 2 (`Invoice Number` filled, `Employee` = `—`).
   `Invoice Number` and `Employee` are separate columns, not combined into one — populate whichever
   applies per row.

**No entry is treated as "the primary" one.** `Spend`, `Months Active`, `Overlap Period`, and
`Recommended Action` are computed and shown on **every** entry row, not just the first — the same
date/activity logic applies uniformly regardless of an entry's position in the list. `Overlap Period`
is the shared window during which entries of that type were simultaneously active (or "Not simultaneous"
for Type 1 if the flagged employees' active months never actually coincided — Type 1 doesn't require
simultaneity to flag, only 2+ distinct payers).

Includes a manual-verification banner and a blank `Reviewed` column (see "Manual review" note below).

**Sheet 3: Category Overlap** (Type 3)
| Category | Vendor / Overlap Case | Annual Spend | Features | Overlap | Combined Spend | Potential Recoverable Spend | Exact Feature Overlap | Unique Capabilities | Recommended Action | Reviewed |

**Row order per category:**
1. **Category summary row** — tool count (`"N tools"`) and total annual spend, standing on its own rather than riding on the first vendor's row.
2. **One row per vendor** — Annual Spend plus a Features one-liner (written by Claude in Step 3b, for every vendor, not just overlap candidates).
3. A short sub-header ("Potential overlaps in this category") or a "no overlaps" note, then the ranked pair/cluster overlap rows (see Step 3b) — always shown only after every vendor in the category has been listed. Each overlap row carries Combined Spend (always populated, both pairs and clusters), Potential Recoverable Spend, and the three-field write-up (Exact Feature Overlap / Unique Capabilities / Recommended Action).

Followed by a manual-verification banner.

**Sheet 4: Transactions** (source data)
All raw transactions used in the analysis. Same format as spend-intelligence-excel Transactions sheet.

**Manual review note:** Sheets 2-3 both carry a banner stating findings are automatically detected
candidates, not confirmed duplicates, and a blank `Reviewed` column for a finance person to mark by
hand (e.g. an "x") once a finding has been checked. Never treat a flag as confirmed just because it's
in the report — the detectors match transaction patterns (account codes, invoice numbers, employee name
regex), not actual usage or intent.

---

### Step 6 — Present results

Share the file as a download link. **Do not attempt to open or preview the file** — the preview panel in this chat will show an error. Just click Download and open in Google Sheets or Excel.

Then give a short summary in chat:

Structure:
1. **Headline** — total flags found, total savings potential
2. **By type** — one line per type with count and amount
3. **Top 3 most impactful findings** — specific vendor names and amounts
4. **Note on data limitations** if applicable (e.g. "Types 1/2 detection requires DATEV format with Gegenkonto data — not available for generic CSV")

Example:
> Done. Found **11 overlap flags** across your software spend, covering **EUR 48,300** in potentially redundant payments.
>
> Personal card duplicates: 3 vendors (Zapier, Loom, Notion) — two employees paying separately. Parallel contracts: 1 vendor (Semgrep) — two contracts active simultaneously from May to December. Category overlap: 7 categories with 3+ vendors.
>
> Biggest opportunities: Semgrep parallel contracts cost an extra 1,865 EUR/mo for 8 months (14,900 EUR total). Zapier consolidation could reduce from two accounts to one team plan. In "Analytics", you have 4 vendors totalling 28,000 EUR/yr — worth reviewing if all are actively used.
>
> Details and recommended actions in the Excel file.

**Always add this note:**
> Open in **Google Sheets or Microsoft Excel** for the full experience. Just click Download.

---

## Important notes

**DATEV-specific detection:** Types 1 and 2 rely on DATEV-specific columns (`Gegenkonto`, `Buchungstext` with employee name pattern, `Belegfeld1` for invoice numbers). For generic CSV/XLSX inputs, only Type 3 (category overlap) is available. Tell the user this upfront if the file is not DATEV format.

**Employee names in DATEV:** The pattern `Vendor; F. Lastname; description` appears in rows with `Gegenkonto = 7999999` (credit card expense rows). Not all DATEV exports include employee names — depends on how the bookkeeper enters descriptions.

**"Savings Potential" is not guaranteed savings.** Some parallel contracts are intentional (different teams, different use cases). Frame findings as candidates for review, not confirmed waste.

**Amounts are cash-basis.** Same logic as spend-intelligence-excel: prepaid annual subscriptions counted in month of payment.

**Scanned PDFs are not supported.** If the user uploads a scanned PDF:
> "This appears to be a scanned PDF, which I can't read directly. Please export as a text-based PDF or CSV from your bank's online portal and re-upload."
