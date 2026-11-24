---
name: moss-latest-account-transactions
description: "Shows the latest bank transactions of one Moss account with date, counterparty and amount. Needs the Moss MCP connected to your AI assistant."
---

# Latest Account Transactions

Shows the latest bank transactions of one Moss account with date, counterparty and amount.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity]
• Number of transactions: [number, default 10]

RULES
• Look only at bank transactions in Moss. Show money out as negative.

OUTPUT
• One row per transaction, newest first: booking date, counterparty, purpose, amount, currency and export status.
• Money in, money out and net for the list.
