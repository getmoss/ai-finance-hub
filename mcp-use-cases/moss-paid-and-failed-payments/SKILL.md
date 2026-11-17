---
name: moss-paid-and-failed-payments
description: "Lists paid and failed payments in a period and any later payment to the same payee. Needs the Moss MCP connected to your AI assistant."
---

# Paid and Failed Payments

Lists paid and failed payments in a period and any later payment to the same payee.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [last X days or start date to end date]
• Outcomes: [paid, failed or both]
• Payment types: [invoices, reimbursements or both]
• Delivery: [overview in chat, or Excel overview]

RULES
• List all payments in the time frame by outcome, paid or failed.
• Take the outcome from the payment status: PAID (invoices) or COMPLETED (reimbursements) is paid, FAILED is failed. A later payment is any payment to the same payee after the failed one.

OUTPUT
• One row per payment: transaction ID, date, payee, gross amount, currency, outcome and invoice number.
• For failed payments: the later payment to the same payee, or that there is none.
• Count and total per outcome and currency.
