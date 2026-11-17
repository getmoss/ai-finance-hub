---
name: moss-approval-route-lookup
description: "Shows who must approve one specific item, in which order, and which rule routes it. Needs the Moss MCP connected to your AI assistant."
---

# Approval Route Lookup

Shows who must approve one specific item, in which order, and which rule routes it.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Item: [type an invoice number, or a supplier and amount]
• Compare with earlier items: [same supplier, last number months, optional]

RULES
• Find the item by invoice number first, then by supplier and amount. If several items fit, list them and ask me which one.
• Show the approval route of that item in Moss, from submission to the last step. Do not guess amount limits or how many approvers are needed, because Moss does not return them.

OUTPUT
• The item: supplier, amount, currency, date, transaction ID and status.
• The route: each step in order with the approver, the decision and the date, who still has to decide, and the name of the rule that routes it. Say if the item has no approval route.
• If asked, whether earlier items of the same supplier took the same route.
