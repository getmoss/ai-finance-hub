---
name: moss-vendors-by-spend
description: "Ranks your biggest vendors by spend across cards, invoices and reimbursements, with every transaction listed underneath. Needs the Moss MCP connected to your AI assistant."
---

# Vendors by Spend

Ranks your biggest vendors by spend across cards, invoices and reimbursements, with every transaction listed underneath.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Period: [this month, this quarter, this year, or a period from start date to end date]
• Top: [number of vendors]

RULES
• Look at card transactions, invoices and reimbursements.
• Card transactions use the merchant name, invoices and reimbursements use the supplier name. Merge names that differ only by case.
• Spend is the amount including VAT, in EUR. Exclude rejected items. Include drafts.
• Count each expense once, never a split expense and its parts together.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• A ranked list of vendors: rank, vendor, number of transactions and total spend in the period.
• The overall total of the listed vendors.
• Underneath, every transaction of each listed vendor: date, type, amount, status, expense account, cost centre and employee.
