---
name: moss-pull-supplier-master-data
description: "Looks up the full record of a supplier: accounting defaults, payment details and address. Needs the Moss MCP connected to your AI assistant."
---

# Pull Supplier Master Data

Looks up the full record of a supplier: accounting defaults, payment details and address.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Ask me to type the supplier name in chat first.

INPUTS
• Supplier: [name or part of the name]

RULES
• Look at all entities and all statuses, active and inactive. Show the status.
• Find suppliers by part of the name. If several match, list them and show the closest first.

OUTPUT
• Supplier: name, number, status and VAT ID.
• Default accounting: expense account, VAT rate, cost centre, cost carrier and team.
• Payment details: currency, IBAN, bank code, default payment method and payment terms.
• Address: country, street, address line 2, post code and city.
• A list of the fields that are not set.
