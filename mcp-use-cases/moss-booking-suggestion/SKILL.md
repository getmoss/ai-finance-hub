---
name: moss-booking-suggestion
description: "Shows the last 3 bookings of a supplier and recommends how to book a new invoice or transaction. Needs the Moss MCP connected to your AI assistant."
---

# Booking Suggestion

Shows the last 3 bookings of a supplier and recommends how to book a new invoice or transaction.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Ask me in chat to type the supplier name, invoice number or transaction ID first.

INPUTS
• Supplier: [type a name, part of the name, invoice number or transaction ID]

RULES
• Search across all entities and use the full booking history.
• Match the supplier by part of the name, name variants included. For an invoice number or transaction ID, take the supplier from that invoice.
• Recommend the combination of GL account, VAT code, cost centre and cost carrier used most often across all bookings. Say how many bookings used it and the percentage.
• Show the last 3 bookings only. If an older booking differs from the recommendation, show it too and say when it was.
• Only suggest. Never change an invoice or transaction.
• If a query hits the result limit, keep fetching page by page. If you cannot, say the numbers are partial.

OUTPUT
• The last 3 bookings, newest first: date, invoice number, amount, cardholder or creator, team, GL account, VAT code, cost centre, cost carrier.
• One recommendation with how often it was used (count and percentage).
• Older bookings that differ from the recommendation.
• A note if there is no history.
