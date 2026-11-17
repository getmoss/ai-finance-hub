---
name: moss-approver-workload
description: "Shows which approvers hold the most waiting value and for how long, and drafts a message to each. Needs the Moss MCP connected to your AI assistant."
---

# Approver Workload

Shows which approvers hold the most waiting value and for how long, and drafts a message to each.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Top or minimum: [number of approvers, or amount]
• Item types: [invoices, reimbursements, or both]
• Tone: [friendly or formal]
• Delivery: [overview in chat & messages, or Excel overview only]

RULES
• Find all items of the chosen types in Moss that are not yet ready for review because they are still stuck in the approval flow. Exclude drafts and rejected items.
• Take the approver from the approval details of each item. If several people can approve, count the item for each of them and say so.

OUTPUT
• Approvers ranked by waiting value: number of items, total value, oldest wait in days and share of the total.
• The items behind each approver, largest first, with transaction ID.
• A short draft message per approver in the chosen tone, with their items listed.
