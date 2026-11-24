---
name: moss-latest-card-spend
description: "Shows the latest card payments with receipt and coding status. Needs the Moss MCP connected to your AI assistant."
---

# Latest Card Spend

Shows the latest card payments with receipt and coding status.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Look-back: [last X transactions or last X days]
• Cards: [all cards, or type one card or cardholder]

RULES
• Count card transactions only, newest first by transaction time. Include drafts, exclude rejected.
• Coding is missing when the GL account, VAT code, cost centre or carrier is empty. Name the empty fields.

OUTPUT
• One row per transaction: date, merchant, amount, card name, cardholder, receipt status and missing coding fields.
• Count and total of the transactions shown.
• Flags: no receipt, first-time merchant, much larger than usual for that merchant.
