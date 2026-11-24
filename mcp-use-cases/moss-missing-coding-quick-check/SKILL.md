---
name: moss-missing-coding-quick-check
description: "Shows card transactions, invoices and reimbursements that still miss coding and suggests the booking from past bookings. Needs the Moss MCP connected to your AI assistant."
---

# Missing Coding Quick Check

Shows card transactions, invoices and reimbursements that still miss coding and suggests the booking from past bookings.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [month, quarter, or a period from start date to end date]
• Delivery: [overview in chat or Excel overview]

RULES
• Check card transactions, invoices and reimbursements that are not exported yet. Include drafts, exclude rejected items.
• Missing means the expense account, VAT rate or cost centre is empty. For split items check each line.
• Suggest only the missing fields, from the completed bookings of the same supplier or merchant in the same entity in the last 12 months.
• Rate the confidence: high if one value was used in at least 80% of at least 3 past bookings, medium for 50% to 79%, otherwise low. With no past bookings, say no suggestion.
• If the confidence is not high, also show the second likeliest value.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• A summary: how many items miss coding, per transaction type and per missing field.
• One small table each for card transactions, invoices and reimbursements: transaction ID, date, supplier or merchant, amount, cardholder or employee, team, what is missing, suggested booking, past bookings behind it, confidence and entity.
• A separate table for split items, with one row per line.
