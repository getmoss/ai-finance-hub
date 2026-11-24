---
name: moss-expense-finder
description: "Finds one expense from a few details like merchant, month and amount. Needs the Moss MCP connected to your AI assistant."
---

# Expense Finder

Finds one expense from a few details like merchant, month and amount.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Ask me to type the details in chat first.

INPUTS
• Details: [type anything you know, such as merchant, supplier, invoice number, cardholder, amount or time frame]

RULES
• Search across all entities and all transaction types: card transactions, invoices and reimbursements.
• Match names by part and ignore upper and lower case. Match a type such as hotel on merchant name and category. Allow about 10% around an amount.
• If many transactions match, for example for a common supplier, show the 5 most recent ones.
• If nothing fits, widen the details step by step and tell me how.
• Give the output as a table in chat.

OUTPUT
• If one transaction is clearly the match, show only that one. Otherwise show up to 5 closest candidates, closest first.
• For each: transaction ID, type, date, merchant or supplier, amount, status, cardholder or employee, team, expense account, cost centre, cost carrier, receipt status and export status. For invoices also the invoice number and payment status.
• Which of my details matched.
