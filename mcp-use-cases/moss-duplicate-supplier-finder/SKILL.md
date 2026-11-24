---
name: moss-duplicate-supplier-finder
description: "Finds supplier records that look like the same supplier by name, VAT ID, IBAN or address, with the spend on each. Needs the Moss MCP connected to your AI assistant."
---

# Duplicate Supplier Finder

Finds supplier records that look like the same supplier by name, VAT ID, IBAN or address, with the spend on each.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]

RULES
• Look at all suppliers of the entity, or of all entities. Ignore inactive suppliers.
• Group records that share a similar name (ignore upper and lower case and legal forms such as Ltd, GmbH or B.V.), the same VAT ID, the same IBAN or the same address (street, post code and city).
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• One table, one row per record, records of the same group together. First column: the attributes that overlap in the group.
• Per record: supplier name, number, VAT ID, IBAN, address, total spend, date of the last transaction and entity.
