---
name: moss-supplier-coding-qa-check
description: "Shows where card transactions, invoices and reimbursements were booked differently from the usual booking of that supplier. Needs the Moss MCP connected to your AI assistant."
---

# Supplier Coding QA Check

Shows where card transactions, invoices and reimbursements were booked differently from the usual booking of that supplier.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Time frame: [period to check, for example last month]
• Only check: [optional, type a supplier name or choose card transactions, invoices or reimbursements]
• Delivery: [overview in chat or Excel overview]

RULES
• Check card transactions, invoices and reimbursements for all suppliers and merchants. Cards use the merchant name, invoices and reimbursements the supplier name.
• Only look at completed items, which are ready to export or already exported. Exclude drafts and rejected items, also in the 12-month history.
• The usual booking is the value most used for that supplier in the 12 months before the time frame. Compare expense account, VAT rate, cost centre, cost carrier and team.
• A supplier with fewer than 3 past transactions has no history.
• Always show the current booking of each difference in full, with the transaction ID and all key details.
• For each difference name the field, the usual value and how many past transactions used it. Mention any other field that also differs, such as team or cardholder, and add 1 or 2 past transaction IDs with the usual booking to compare.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• One table, one row per difference: transaction ID, type, date, supplier, amount, cardholder or employee, expense account, VAT rate, cost centre, cost carrier, team, what differs from the usual booking, the past transaction IDs to compare and entity.
• How many transactions were checked, per type.
• Suppliers with no history.
