---
name: moss-invoice-cover-check
description: "Checks if the available balance covers the invoices due in the next days and shows any shortfall. Needs the Moss MCP connected to your AI assistant."
---

# Invoice Cover Check

Checks if the available balance covers the invoices due in the next days and shows any shortfall.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Days ahead: [number]
• Include overdue: [yes or no]
• Delivery: [overview in chat, or Excel list of invoices]

RULES
• Look only at supplier invoices and Moss accounts.
• Unpaid means payment status not paid, even if the invoice is approved or completed. Exclude drafts and rejected invoices.
• Compare per currency. If there is no account in an invoice currency, say so.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• Per currency: total due, available balance and the shortfall or surplus.
• The invoices due, soonest first: supplier, invoice number, due date, amount, currency and status.
• Overdue invoices, listed apart.
