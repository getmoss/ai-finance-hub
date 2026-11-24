---
name: moss-internal-meal-and-food-check
description: "Checks internal meals and team food against a limit or policy and flags unusual VAT coding. Needs the Moss MCP connected to your AI assistant."
---

# Internal Meal and Food Check

Checks internal meals and team food against a limit or policy and flags unusual VAT coding.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Food accounts: [internal meal and team food accounts, or leave empty]
• Time frame: [month or quarter]
• Limit or policy: [a limit per person, your hospitality policy, or leave empty]
• Budget: [a Moss budget, or leave empty]

RULES
• Include card transactions, invoices and reimbursements. Include drafts, exclude rejected items.
• Count each expense once, never a split expense and its parts together.
• If I name no accounts, use the closest ones by name and past bookings, and tell me which.
• Show every meal, not only flagged ones. Flag column first, "-" if none, flagged meals on top.
• The number of people is not in the data. Ask me once for all meals. Without it, show no cost per person.
• Flag: over limit or breaks policy (name the rule), no purpose (hospitality purpose empty), unusual VAT code (differs from the merchant's usual code in the last 12 months).
• If I name a budget, say what is left or by how much it is overdrawn.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• Table: flag, transaction ID, date, merchant, person, amount, people, cost per person, VAT code, cost centre, entity.
• Total per cost centre, and the budget status if named.
