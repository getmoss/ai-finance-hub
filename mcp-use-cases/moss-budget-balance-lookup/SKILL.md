---
name: moss-budget-balance-lookup
description: "Finds a budget from a rough name, shows what is left, warns if the current spending pace is not sustainable, and lists its expenses. Needs the Moss MCP connected to your AI assistant."
---

# Budget Balance Lookup

Finds a budget from a rough name, shows what is left, warns if the current spending pace is not sustainable, and lists its expenses.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Budget: [type the name or part of the name]
• Period: [current period or a named one]

RULES
• Look only at budgets in Moss, across all entities. Match the name by part, ignoring upper and lower case, and find the closest match.
• Used means spent plus committed. Pace is the amount used so far divided by the days passed. Say whether that pace is sustainable until the period ends, and warn if the budget would be used up before then.
• List every expense counted in the budget, committed ones included with their status.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• The closest budget: owner, period, limit, spent, committed, left and percent used.
• Pace warning: spend per day so far and whether that pace is sustainable until the period ends.
• All expenses in the budget, newest first: transaction ID, type, vendor, date, amount, cost centre and status.
