---
name: moss-export-transaction-status-check
description: "Shows how many items sit in Collect, Approve, Review and Export, and how many are exported. Needs the Moss MCP connected to your AI assistant."
---

# Export / Transaction Status Check

Shows how many items sit in Collect, Approve, Review and Export, and how many are exported.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [month, quarter or date range]
• Item types: [card transactions, invoices, reimbursements or all]

RULES
• Steps by status: draft is Collect, submitted is Approve, approved or approval skipped is Review, completed is Export.
• No export state means not exported.
• An item is late after 7 days in its step.
• Include drafts. Exclude rejected items.
• Count each expense once, never a split expense and its parts together.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• A table with one row per item type and one column per step, each with count and amount.
• Under Export: how many are not exported, export pending and exported.
• Items that are late in their step, oldest first.
