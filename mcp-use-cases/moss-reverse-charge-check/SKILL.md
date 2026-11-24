---
name: moss-reverse-charge-check
description: "Flags transactions booked on reverse charge where it usually does not apply. Needs the Moss MCP connected to your AI assistant."
---

# Reverse Charge Check

Flags transactions booked on reverse charge where it usually does not apply.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real EU entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an EU entity or All EU entities]
• Reverse charge VAT codes: [type all your reverse charge VAT codes, or leave empty]
• Time frame: [month, quarter, or a period from start date to end date]

RULES
• Only EU entities. Skip entities outside the EU, for example UK entities.
• If I do not name the codes, use the VAT codes that look closest, based on their names and past bookings, and tell me which.
• Check card transactions, invoices and reimbursements booked on the reverse charge codes I name.
• Flag as domestic supplier if the supplier is in the entity's country. Reverse charge only applies there for a few categories, for example construction.
• Flag as no VAT ID if the supplier is in an EU country and has no VAT ID.
• Flag as local service if the supplier or expense account is a hotel, restaurant, event, passenger transport, short-term vehicle rental or property. These are taxed where they take place, not by reverse charge.
• Flag as goods if the supplier is outside the EU and the expense account looks like goods, for example hardware, equipment or office supplies. Goods from outside the EU are import VAT, not reverse charge.
• Do not flag other suppliers outside the EU, with or without a VAT ID. Reverse charge is correct for their services.
• Exclude drafts and rejected items.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• How many transactions were booked on reverse charge in the time frame, and how many are flagged, with the flagged amount.
• A table of the flagged transactions: reason, transaction ID, type, date, supplier, country, VAT ID, amount, VAT code and entity.
