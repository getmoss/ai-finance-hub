---
name: moss-external-food-spend
description: "Lists external food spend and flags missing purpose, unusual VAT coding and policy breaks. Needs the Moss MCP connected to your AI assistant."
---

# External Food Spend

Lists external food spend and flags missing purpose, unusual VAT coding and policy breaks.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Food accounts: [external food and client entertainment accounts, or leave empty]
• Time frame: [quarter or year]
• Policy: [paste or name the policy, or leave empty]
• Budget: [a Moss budget, or leave empty]

RULES
• Include card transactions, invoices and reimbursements. Include drafts, exclude rejected items.
• Count each expense once, never a split expense and its parts together.
• If I name no accounts, use the closest ones by name and past bookings, and tell me which.
• Show every item, not only flagged ones. Flag column first, "-" if none, flagged items on top.
• Flag: no hospitality purpose (field empty), unusual VAT code (differs from the merchant's usual code in the last 12 months), breaks policy (name the rule).
• If I name a budget, say what is left or by how much it is overdrawn.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• Count and total per transaction type.
• Table: flag, transaction ID, date, merchant, person, amount, expense account, VAT code, purpose, entity.
• Budget status, if named.
