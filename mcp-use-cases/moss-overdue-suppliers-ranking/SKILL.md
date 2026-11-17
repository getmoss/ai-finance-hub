---
name: moss-overdue-suppliers-ranking
description: "Lists suppliers with overdue invoices, ranked by days overdue and by amount. Needs the Moss MCP connected to your AI assistant."
---

# Overdue Suppliers Ranking

Lists suppliers with overdue invoices, ranked by days overdue and by amount.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Ranking: [days overdue or amount]
• Top: [number]
• Delivery: [overview in chat, or Excel overview]

RULES
• Find all overdue invoices in Moss (unpaid, due date before today) and rank the suppliers you owe the most. Exclude drafts and rejected invoices.
• Rank in the entity currency and show each original currency next to it. List credit notes (negative amounts) apart.

OUTPUT
• The top suppliers: number of overdue invoices, oldest due date, days overdue and total overdue amount.
• Under each supplier, its overdue invoices with transaction ID, number, due date and gross amount.
• Total overdue per currency, and the credit notes listed apart.
