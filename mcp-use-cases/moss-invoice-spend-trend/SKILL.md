---
name: moss-invoice-spend-trend
description: "Compares supplier invoice spend over time by the dimension you choose, such as supplier, team, category or cost centre. Needs the Moss MCP connected to your AI assistant."
---

# Invoice Spend Trend

Compares supplier invoice spend over time by the dimension you choose, such as supplier, team, category or cost centre.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Compare by: [supplier, team, expense account category, VAT code, cost carrier or cost centre]
• Frequency: [weekly, monthly, quarterly or yearly]
• Time frame: [start date] to [end date]
• Delivery: [overview in chat or Excel overview]

RULES
• Use supplier invoices by invoice date. Include drafts. Exclude rejected invoices.
• Show items without a value as none.
• Count each expense once, never a split expense and its parts together.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• One table with one row per value of the chosen dimension, with spend for each period and a total row.
• One table with the change in amount and percent from each period to the previous one.
• The biggest increase and decrease over the time frame.
• Deliver as chosen. If you cannot create an Excel file, give the tables in chat.
