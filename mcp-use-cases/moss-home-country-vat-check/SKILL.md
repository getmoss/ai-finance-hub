---
name: moss-home-country-vat-check
description: "Flags transactions on home country VAT codes where the VAT does not fit the supplier or the rate. Needs the Moss MCP connected to your AI assistant."
---

# Home Country VAT Check

Flags transactions on home country VAT codes where the VAT does not fit the supplier or the rate.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real EU entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an EU entity or All EU entities]
• Home country VAT codes: [type all VAT codes with a home country rate, or leave empty]
• Time frame: [month, quarter, or a period from start date to end date]

RULES
• Only EU entities. Skip entities outside the EU, for example UK entities.
• If I do not name the codes, use the VAT codes that look closest, based on their names and past bookings, and tell me which.
• Check card transactions, invoices and reimbursements booked on the home country VAT codes I name.
• Flag as foreign supplier on home VAT if the supplier is in another country and has no VAT ID from the entity's country. That VAT is foreign VAT and does not belong on the home VAT return.
• Flag as VAT does not match code if the VAT amount differs from the VAT included in the gross amount at the rate of the code by more than EUR 0.10. Skip this test where no VAT amount is booked.
• Flag as rate differs from usual if the code is not the supplier's usual code in the 12 months before the time frame.
• Zero VAT and reverse charge are not covered here.
• Exclude drafts and rejected items.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• How many transactions were booked on home country VAT codes in the time frame, and how many are flagged, with the flagged amount.
• A table of the flagged transactions: reason, transaction ID, type, date, supplier, country, amount, VAT amount, VAT code, usual VAT code and entity.
