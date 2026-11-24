---
name: moss-close-blocker-dashboard
description: "Shows what still blocks the close this month: open items per stage, missing receipts and stuck approvals. Needs the Moss MCP connected to your AI assistant."
---

# Close Blocker Dashboard

Shows what still blocks the close this month: open items per stage, missing receipts and stuck approvals.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]

RULES
• Filter every query to expense dates from the 1st of the current month to today, never all time. Include card transactions, invoices and reimbursements. Exclude rejected items. Exported items are done.
• The "of" total is a separate count of all items of that type in that date range, whatever their status except rejected. Never use all-time totals.
• Count each expense once, never a split expense and its parts together.
• Stages: draft is Collect, submitted is Approve, approved is Review, completed but not exported is Export.
• Missing receipt: receipt status not created or pending on cards and reimbursements, no file attached on invoices. Missing coding: no GL account (check the lines of split items). Missing approval: reimbursements and invoices not yet approved, cards have none. Items not yet submitted wait for their creator.
• An item with several blockers counts once per blocker and once in the unique total. Owner is the creator or cardholder.
• If I choose all entities, show each entity.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
Start with one line: the date range used, then unique open items out of all items of the month, with amount. Then, in chat and in this order:
• Table of open items per stage, by type and entity: type, Collect, Approve, Review, Export, total (open out of all items of that type dated this month), entity (count and amount in each cell).
• Table of the blockers, each named once: blocker, card, reimbursement, invoice, total, entity (count and amount).
• Detail table, missing coding, 5 biggest: transaction ID, date, type, merchant, amount, owner, entity.
• Detail table, missing approval, 5 biggest: transaction ID, date, type, merchant, amount, step, waiting for, days open, entity.
• Detail table, missing receipt, 5 biggest: transaction ID, date, type, merchant, amount, owner, days open, entity.
• Table of the 5 biggest open items and where each is stuck: transaction ID, date, type, merchant, amount, owner, stuck at, entity.
