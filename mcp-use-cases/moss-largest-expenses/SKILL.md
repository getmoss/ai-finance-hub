---
name: moss-largest-expenses
description: "Lists the largest expenses in a time frame with type, vendor, cost centre and status. Needs the Moss MCP connected to your AI assistant."
---

# Largest Expenses

Lists the largest expenses in a time frame with type, vendor, cost centre and status.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [month, quarter or date range]
• Top: [number]
• Minimum amount: [type an amount, optional]
• Delivery: [overview in chat or Excel overview]

RULES
• Count card transactions, invoices and each reimbursement line on its own, by amount in the entity currency.
• Show the vendor for cards and invoices, and the creator for reimbursement lines. Take the status of a reimbursement line from the reimbursement.
• Exclude rejected items, refunds and credit notes. Include drafts.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• The top [number] expenses, largest first: transaction ID, type, vendor or creator, date, amount, currency, cost centre and status.
• The share of total spend these expenses cover.
