---
name: moss-stuck-approval-chaser
description: "Lists items waiting too long for approval and drafts a message per approver. Needs the Moss MCP connected to your AI assistant."
---

# Stuck Approval Chaser

Lists items waiting too long for approval and drafts a message per approver.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Waiting longer than: [number] days
• Item types: [invoices, reimbursements, or both]
• Tone: [friendly or formal]
• Delivery: [overview in chat & messages, or Excel overview only]

RULES
• Find all items of the chosen types in Moss that are not yet ready for review because they are still stuck in the approval flow. Exclude drafts and rejected items.
• Take the approver and the days waiting from the approval details of each item. If any one of several people can approve, address them in one message.

OUTPUT
• Per approver: number of waiting items and total value, then each item with transaction ID, type, creator, amount, currency and days waiting, oldest first.
• A short draft message per approver in the chosen tone, with their items listed.
