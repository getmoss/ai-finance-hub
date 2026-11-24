---
name: moss-supplier-x-spend-by-month
description: "Shows what one supplier costs per month and per entity, with the monthly average. Needs the Moss MCP connected to your AI assistant."
---

# Supplier “X” Spend by Month

Shows what one supplier costs per month and per entity, with the monthly average.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Supplier: [type one name or part of a name]
• Time frame: [this year, a period from start date to end date, or the whole time]

RULES
• Search all entities and all transaction types: invoices, card transactions and reimbursements.
• Find the supplier by part of the name, including spelling variants. Match card transactions by merchant name.
• Use gross amounts in the entity currency. Include drafts, exclude rejected items. Count each expense once, never a split expense and its parts together.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• A table in chat, one row per month and entity: invoices, card transactions, reimbursements, total and entity.
• Then the total for the time frame, the average per month over all months, the total per transaction type and the months without spend.
