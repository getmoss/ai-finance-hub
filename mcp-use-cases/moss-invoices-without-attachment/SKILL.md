---
name: moss-invoices-without-attachment
description: "Finds supplier invoices with no attachment and who to ask for the document. Needs the Moss MCP connected to your AI assistant."
---

# Invoices Without Attachment

Finds supplier invoices with no attachment and who to ask for the document.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Date range: [start date] to [end date], or all history
• Stage in Moss: [Review, Export, Exported or all]
• Delivery: [overview in chat & message, or Excel overview only]

RULES
• Look only at the supplier invoices tab in Moss.
• Count an invoice with no PDF as missing its document, drafts included, for the named date range and entity.
• Read the stage from status and export state: Review until completed, Export when completed and not yet exported, Exported when exported.

OUTPUT
• Supplier invoices in the date range without a PDF, rejected ones left out, oldest first: supplier, invoice number, date, gross amount, currency, stage in Moss, transaction ID, owner and either approval completed or the current approval step with who has to approve.
• How many invoices and how much money are missing a document, and who has the most to chase.
• A short message per owner listing their invoices. If every invoice has a file, how many were checked.
