---
name: moss-supplier-invoice-list
description: "Lists every invoice of one supplier across all entities for the time frame you choose. Needs the Moss MCP connected to your AI assistant."
---

# Supplier Invoice List

Lists every invoice of one supplier across all entities for the time frame you choose.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Supplier: [type a name or part of a name]
• Date range: [start date] to [end date]

RULES
• Look at invoices across all entities.
• Find the supplier by part of the name.
• Sort by invoice date, newest first.
• Include drafts. Exclude rejected invoices.
• Overdue means the due date has passed and the payment status is not paid.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• One row per invoice: transaction ID, invoice number, date, due date, gross amount, currency, status, payment status, employee, team and entity.
• Count, total and unpaid amount, per currency.
• Overdue invoices marked with the days overdue.
