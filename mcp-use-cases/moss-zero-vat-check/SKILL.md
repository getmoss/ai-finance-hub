---
name: moss-zero-vat-check
description: "Lists transactions booked on zero VAT and flags unusual ones and home or EU suppliers first. Needs the Moss MCP connected to your AI assistant."
---

# Zero VAT Check

Lists transactions booked on zero VAT and flags unusual ones and home or EU suppliers first.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real EU entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an EU entity or All EU entities]
• Zero VAT codes: [type the VAT codes that mean 0% or exempt, or leave empty]
• Time frame: [month, quarter, or a period from start date to end date]

RULES
• Only EU entities. Skip entities outside the EU, for example UK entities.
• If I do not name the codes, use the VAT codes that look closest, based on their names and past bookings, and tell me which.
• Check card transactions, invoices and reimbursements. Only the VAT codes I name count as zero VAT.
• Flag a transaction as unusual if the supplier was normally booked on another VAT code in the 12 months before the time frame.
• Flag a transaction as home supplier if the supplier is in the entity's country, and as EU supplier if it is in another EU country. VAT may be missing, reverse charge may apply or foreign VAT may be reclaimable.
• Do not flag suppliers outside the EU unless they are unusual.
• Sort the flagged ones: unusual first, then home supplier, then EU supplier.
• Exclude drafts and rejected items.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• How many transactions and what total amount were booked on zero VAT in the time frame, per transaction type.
• A table of all of them, flagged ones first: flag, transaction ID, type, date, supplier, country, amount, VAT code, the usual VAT code of the supplier and entity.
