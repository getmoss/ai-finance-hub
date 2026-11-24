---
name: moss-spend-spike-finder
description: "Shows which suppliers were paid far more than usual in a month, plus the highest payments. Needs the Moss MCP connected to your AI assistant."
---

# Spend Spike Finder

Shows which suppliers were paid far more than usual in a month, plus the highest payments.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Month: [month]
• Spike limit: [percent above usual, or leave empty for 50%]

RULES
• Look at card transactions, invoices and reimbursements by supplier. Merge name variants and ignore upper and lower case. Use gross amounts by expense date, in the entity currency. Include drafts, exclude rejected items and refunds.
• Count each expense once, never a split expense and its parts together.
• A supplier's usual is its average total per month, in the months it was paid in the 12 months before. A spike is a month total above usual by more than my limit. No payment in those 12 months is New.
• Check the usual only for the 15 biggest suppliers of the month, and say so.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.
• If I choose all entities, check each one on its own.

OUTPUT
• Table of supplier spikes, biggest amount above usual first: supplier, types, this month, usual, above usual, entity.
• Table of the 5 highest payments of the month: transaction ID, date, supplier, type, amount, expense account, entity.
• A one-line note: how many suppliers were checked and whether any result was partial.
