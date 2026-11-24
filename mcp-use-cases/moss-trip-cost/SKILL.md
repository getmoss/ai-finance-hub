---
name: moss-trip-cost
description: "Adds up trip costs per employee on the travel accounts you name, and flags foreign VAT. Needs the Moss MCP connected to your AI assistant."
---

# Trip Cost

Adds up trip costs per employee on the travel accounts you name, and flags foreign VAT.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Travel accounts: [hotel, flight, rail and transport accounts, or leave empty]
• Time frame: [quarter, year or trip period]
• Policy: [paste or name the travel policy, or leave empty]
• Budget: [a Moss budget, or leave empty]

RULES
• Include card transactions, invoices and reimbursements. Include drafts, exclude rejected items.
• Count each expense once, never a split expense and its parts together.
• If I name no accounts, use the closest ones by name and past bookings, and tell me which.
• Show every item, not only flagged ones. Flag column first, "-" if none, flagged items on top.
• Flag: foreign VAT (supplier in another EU country and a VAT amount shown, EU entities only), breaks policy (name the rule).
• If I name a budget, say what is left or by how much it is overdrawn.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• Total, number of items and the budget status if named.
• Table per employee and expense account: employee, expense account, items, amount, foreign VAT, cost centre, entity.
• Table of all items: flag, transaction ID, date, employee, supplier, country, expense account, amount, VAT amount, cost centre, entity.
