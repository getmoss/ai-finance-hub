---
name: moss-highest-amount-receipt-chase
description: "Ranks transactions without a receipt by amount, so the biggest gaps get chased first. Needs the Moss MCP connected to your AI assistant."
---

# Highest-Amount Receipt Chase

Ranks transactions without a receipt by amount, so the biggest gaps get chased first.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [month, quarter or date range]
• Top: [number]
• Minimum amount: [amount, optional]
• Reply by: [date]
• Delivery: [overview in chat only or messages]

RULES
• Look only at the card transactions tab in Moss.
• Count drafts and receipts that are still pending as missing for the named time frame and entity.
• Rank by amount, highest first, and only above the minimum amount if given.

OUTPUT
• The top [number] open card transactions, highest amount first, with transaction ID, cardholder, merchant, date, amount and running total.
• A short message per cardholder that names their highest amount first, includes the transaction ID and asks for the receipts by the reply date.
• How much of the total missing amount the top items cover.
