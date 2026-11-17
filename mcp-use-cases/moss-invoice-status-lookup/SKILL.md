---
name: moss-invoice-status-lookup
description: "Finds one invoice from any detail and shows whether it is already in Moss and where it stands. Needs the Moss MCP connected to your AI assistant."
---

# Invoice Status Lookup

Finds one invoice from any detail and shows whether it is already in Moss and where it stands.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Invoice number: [type an exact or partial number]
• Supplier: [type the name or part of the name]
• Amount: [type an exact or approximate amount]
• Time frame: [month or rough period]
• Upload: [invoice file to find the match in Moss, optional]

RULES
• Find out if the invoice is already in Moss and where it stands. Use the invoice number first, then supplier and amount, or read these details from the uploaded invoice.
• Search all statuses, drafts and rejected included, and say which status it has. If several invoices fit, show the best match first and up to 3 others.

OUTPUT
• The invoice in Moss: transaction ID, supplier, invoice number, date, due date, gross amount and status. If it is not in Moss, say what you searched.
• Where it stands: who approved it and when, or who still has to approve it, the payment status and the export state.
• Up to 3 other candidates, closest first.
