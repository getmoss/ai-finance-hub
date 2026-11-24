---
name: moss-budget-spend-drill-down
description: "Flags active budgets that are almost used up or spending too fast, and shows the biggest expenses behind them. Needs the Moss MCP connected to your AI assistant."
---

# Budget Spend Drill-Down

Flags active budgets that are almost used up or spending too fast, and shows the biggest expenses behind them.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Flag above: [percent, default 80]
• Top: [number, default 3]
• Delivery: [overview in chat, or Excel overview]

RULES
• Look only at budgets and the expenses assigned to them in Moss. Include all active budgets, always as of today.
• Used means spent plus committed. Pace is the amount used so far divided by the days passed.
• Flag a budget, with the reason, if the share used is above the flag level, or if its pace is not sustainable, meaning it would be used up before the period ends. List only flagged budgets.
• Rank expenses by the amount counted against the budget. Show the merchant for card payments and the supplier for invoices. Purchase requests count as committed.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• How many of the active budgets are flagged.
• Per flagged budget: name, owner, period, limit, spent, committed, left, percent used, spend per day and the reason for the flag.
• The top [number] expenses behind each flagged budget: date, type, merchant or supplier, amount counted and status.
