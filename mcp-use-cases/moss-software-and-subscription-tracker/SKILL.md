---
name: moss-software-and-subscription-tracker
description: "Lists every recurring software vendor with monthly cost, growth and the entities that pay. Needs the Moss MCP connected to your AI assistant."
---

# Software and Subscription Tracker

Lists every recurring software vendor with monthly cost, growth and the entities that pay.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Software accounts: [software, licence and AI tool accounts, or leave empty]
• Time frame: [6 or more] months
• Growth limit: [percent, or leave empty for 20%]

RULES
• Include card transactions, invoices and reimbursements. Include drafts, exclude rejected items.
• Count each expense once, never a split expense and its parts together.
• If I name no accounts, use the closest ones by name and past bookings, and tell me which.
• Use gross amounts (with VAT) by expense date. Merge name variants of one vendor and ignore upper and lower case.
• A vendor counts as recurring only if charged in more than 2 months in a row.
• Change: average monthly spend in the second half of the time frame against the first half. Flag Growing if above my limit, New if first charged in the second half, Stopped if not charged in the last month.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• Table, biggest first: vendor, average per month charged, total, months in a row, change, flag ("-" if none), entity (all that pay).
• Total software spend, and the vendors that make up 80% of it.
• How many vendors were left out.
