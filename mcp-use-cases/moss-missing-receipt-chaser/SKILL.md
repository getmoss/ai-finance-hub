---
name: moss-missing-receipt-chaser
description: "Lists card transactions with no receipt and drafts a reminder for each cardholder. Needs the Moss MCP connected to your AI assistant."
---

# Missing Receipt Chaser

Lists card transactions with no receipt and drafts a reminder for each cardholder.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [start date] to [end date]
• Reply by: [date]
• Tone: [friendly or formal]
• Delivery: [overview in chat & message, or Excel overview only]

RULES
• Look only at the card transactions tab in Moss.
• Count drafts and receipts that are still pending as missing for the named time frame and entity.

OUTPUT
• Per cardholder: number of open transactions, total, and each transaction with transaction ID, date, merchant and amount, oldest first.
• A short message per cardholder asking for the receipts by the reply date.
• Total open count and amount.
