---
name: moss-supplier-exists-check
description: "Checks whether a supplier already exists in any entity and shows the closest matches with their master data. Needs the Moss MCP connected to your AI assistant."
---

# Supplier Exists Check

Checks whether a supplier already exists in any entity and shows the closest matches with their master data.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Ask me to type the names in chat first.

INPUTS
• Names: [type one or several names, or part of a name]

RULES
• Look at all entities and all statuses, active and inactive. Show the status.
• Match by part of the name and ignore upper and lower case and legal forms such as Ltd, GmbH or B.V.
• Show up to 3 closest matches per name. Show only one if it is clearly the best fit.

OUTPUT
• Per name: the closest matches, as described in the rules.
• For each match, the master data that is set: name, number, status, VAT ID, default expense account, VAT rate, cost centre, cost carrier, team, currency, IBAN, bank code, default payment method, payment terms and address.
• A name without a match shown as not found.
