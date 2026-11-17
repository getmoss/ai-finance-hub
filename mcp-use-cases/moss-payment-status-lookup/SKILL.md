---
name: moss-payment-status-lookup
description: "Looks up whether and when an invoice was paid, from a supplier, number or amount. Needs the Moss MCP connected to your AI assistant."
---

# Payment Status Lookup

Looks up whether and when an invoice was paid, from a supplier, number or amount.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Supplier, invoice number or amount: [type any one or more]
• Time frame: [month or rough period]

RULES
• Find the invoice in Moss and show if it was paid, and when.
• Then look for the matching payment in the bank transactions. If there is none, say so and go by the payment status of the invoice.

OUTPUT
• The invoice: transaction ID, supplier, invoice number, gross amount, due date and payment status.
• The payment date and source, and the matching bank transaction with payee, date and amount.
• If it is not paid: days overdue and whether a payment is scheduled or failed.
