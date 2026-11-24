---
name: moss-budget-overview-today
description: "Lists all active budgets as of today with owner, limit, spent, committed and what is left, and flags the ones close to the limit in money or in time. Needs the Moss MCP connected to your AI assistant."
---

# Budget Overview Today

Lists all active budgets as of today with owner, limit, spent, committed and what is left, and flags the ones close to the limit in money or in time.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Scope: [type a team, cost centre or cost carrier, optional]
• Delivery: [overview in chat, or Excel overview]

RULES
• Look only at budgets in Moss. Include all active budgets, always as of today.
• Used means spent plus committed, shown as a percentage of the limit.
• Take team, cost centre and cost carrier from the budget's rules. Days left run from today to the end of the period.
• Flag a budget, with the reason, if 80% or more of the limit is used, or if fewer than 7 days are left and the budget is not recurring.

OUTPUT
• List all active budgets, highest percent used first: name, owner, team, budget type, scope, period, days left, limit, spent, committed, left and percent used.
• Add a flag with the reason to those budgets.
• Total limit and total left.
