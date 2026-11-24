---
name: moss-budget-reallocation-identifier
description: "Compares budgets that run out fast with budgets that are barely used and suggests where money could move. Needs the Moss MCP connected to your AI assistant."
---

# Budget Reallocation Identifier

Compares budgets that run out fast with budgets that are barely used and suggests where money could move.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [budgets active this quarter, or a period you choose]
• Maxed out from: [percent, default 95]
• Low usage below: [percent, default 20]
• Delivery: [overview in chat, or Excel overview]

RULES
• Look only at budgets in Moss. Include the budgets active in the time frame.
• Used means spent plus committed. Count a budget as low usage only once half of its period has passed.
• For recurring monthly and quarterly budgets, also check their spending in earlier periods. Say whether the same overspend or unused amount happened before, to support the move.
• Keep 10% of the unused limit in place and pair only budgets of the same type, for example both quarterly. Suggest only, change nothing.

OUTPUT
• Maxed-out budgets: limit, used, percent used and amount over.
• Low-usage budgets: limit, used, percent used and unused amount.
• Past periods: for recurring monthly and quarterly budgets, whether the same overspend or unused amount happened before.
• Suggested moves: from which budget to which, and how much.
• The total that could move.
