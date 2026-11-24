---
name: moss-budget-structure-map
description: "Maps all budgets with owner, type, period, limit and assignment rules, so you see what each one covers. Needs the Moss MCP connected to your AI assistant."
---

# Budget Structure Map

Maps all budgets with owner, type, period, limit and assignment rules, so you see what each one covers.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [running now, or a period from start date to end date]
• Delivery: [overview in chat, or Excel overview]

RULES
• Look only at budgets in Moss. Include the budgets running in the time frame. Show one line per budget, with all its periods in one line.

OUTPUT
• One line per budget: name, owner, type, status, period start and end, limit, visibility, description and auto assigned rules.
