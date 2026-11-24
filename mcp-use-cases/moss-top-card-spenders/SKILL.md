---
name: moss-top-card-spenders
description: "Ranks cardholders by card spend in a period, with every card transaction listed underneath. Needs the Moss MCP connected to your AI assistant."
---

# Top Card Spenders

Ranks cardholders by card spend in a period, with every card transaction listed underneath.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Period: [this month, this quarter, this year, or a period from start date to end date]
• Top: [number of cardholders]

RULES
• Look only at the card transactions in Moss.
• Spend is the amount including VAT, in EUR. Leave out refunds and cashback. Include drafts, exclude rejected items.
• Count each expense once, never a split expense and its parts together.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• A ranked list of cardholders: rank, name, team, number of transactions and total spend in the period.
• The overall total of the listed cardholders.
• Underneath, every card transaction of each listed cardholder: transaction ID, date, merchant, amount, receipt status, expense account, cost centre and cost carrier.
