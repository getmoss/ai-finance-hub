---
name: moss-account-balances-by-entity
description: "Shows the balance of every Moss account with reserved and available amounts. Needs the Moss MCP connected to your AI assistant."
---

# Account Balances by Entity

Shows the balance of every Moss account with reserved and available amounts.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Currency: [one currency or all]

RULES
• Look only at Moss accounts.
• Include active accounts only. Total per currency and never add different currencies together.

OUTPUT
• One row per account: entity, account, currency, balance, reserved or pending and available.
• Total available per currency.
