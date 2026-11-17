---
name: moss-receipt-finder
description: "Finds a transaction and its receipt from rough details like merchant, month and amount. Needs the Moss MCP connected to your AI assistant."
---

# Best Match Receipt Finder

Finds a transaction and its receipt from rough details like merchant, month and amount.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Merchant or supplier: [type the name or part of the name]
• Time frame: [month or rough period]
• Amount: [type an exact or approximate amount]
• Other clues: [type a person, team or purpose, optional]
• Delivery: [answer in chat, file link and/or file]

RULES
• Look at card transactions, invoices and reimbursements in Moss.
• Match names by part, ignoring upper and lower case, and allow about 10% on the amount.
• If nothing fits, widen the time frame and amount range.

OUTPUT
• The best match with transaction ID, date, merchant or supplier, amount, person, status and receipt status, and which of my details matched.
• Up to 4 other candidates.
• The receipt file of the best match as a file link or a file, if chosen, or a note if there is none, and how sure you are.
