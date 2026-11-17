---
name: moss-quick-past-coding-lookup
description: "Shows how a supplier or invoice was coded in the past, over all time or a period you choose. Needs the Moss MCP connected to your AI assistant."
---

# Quick Past Coding Lookup

Shows how a supplier or invoice was coded in the past, over all time or a period you choose.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Supplier or invoice: [type supplier name or invoice number, or attach an invoice]
• Time frame: [all time or last X months]
• Fields: [GL account, VAT code, cost centre, cost carrier or all]

RULES
• Show how this supplier was booked in the past. Find the supplier by part of the name, name variants included. Exclude rejected invoices.
• For split invoices, read the coding on the lines.

OUTPUT
• Each booking combination: the chosen fields, number of bookings, share and latest date.
• The usual booking, and the bookings that differ from it, with transaction ID.
• The latest invoice with its coding and transaction ID.
