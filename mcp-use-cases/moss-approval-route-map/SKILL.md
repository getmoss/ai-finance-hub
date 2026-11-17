---
name: moss-approval-route-map
description: "Maps all approval routes by rule and shows who and which team, cost centre or cost carrier carries the most approvals. Needs the Moss MCP connected to your AI assistant."
---

# Approval Route Map

Maps all approval routes by rule and shows who and which team, cost centre or cost carrier carries the most approvals.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: last [number] months
• Item types: [invoices, reimbursements, card transactions or all]
• Delivery: [overview in chat, or Excel overview]

RULES
• Map all approval routes in Moss for the chosen items: for each approval rule, who approves at each step.
• Learn the routes from the approval details of the items in the time frame, 100 items at a time. Don’t invent rules. Items approved automatically or without a route can be excluded.

OUTPUT
• The route map: one line per approval rule with item types, the steps in order with their approvers, and the teams, cost centres and cost carriers it applied to.
• Who carries the most approvals: approvers ranked by number and value of items.
• Which teams, cost centres and cost carriers carry the most: number and value of items, with share of the total.
