---
name: moss-entity-spend-month-over-month
description: "Compares spend per entity between two months, split by cards, invoices and reimbursements. Needs the Moss MCP connected to your AI assistant."
---

# Entity Spend Month over Month

Compares spend per entity between two months, split by cards, invoices and reimbursements.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose entities or All entities]
• Month: [month and year]
• Compare with: [previous month or same month last year]
• Delivery: [overview in chat or Excel overview]

RULES
• Spend means card transactions, invoices and reimbursement lines, by expense date, in the reporting currency.
• Exclude rejected items. Include drafts.
• Count each expense once, never a split expense and its parts together.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• One row per entity: spend in both months split by cards, invoices and reimbursements, with change in amount and percent.
• Group total, group change and the type that drove the change most.
• Entities with no spend in either month.
