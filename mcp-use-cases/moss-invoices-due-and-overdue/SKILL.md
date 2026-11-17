---
name: moss-invoices-due-and-overdue
description: "Lists unpaid invoices due soon, shows overdue ones separately and compares the total with your balance. Needs the Moss MCP connected to your AI assistant."
---

# Invoices Due and Overdue

Lists unpaid invoices due soon, shows overdue ones separately and compares the total with your balance.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Days ahead: [number]
• Delivery: [overview in chat, or Excel overview]

RULES
• Find all unpaid invoices in Moss that are due in the chosen number of days or already overdue. Exclude drafts and rejected invoices.
• Compare each currency with the account balance in that currency. Credit notes reduce the total.

OUTPUT
• Invoices due, soonest first: transaction ID, supplier, invoice number, due date, gross amount, currency and the approver still needed.
• Overdue invoices listed apart, oldest first, with days overdue.
• Total due and total overdue per currency, and whether the account balance covers them.
