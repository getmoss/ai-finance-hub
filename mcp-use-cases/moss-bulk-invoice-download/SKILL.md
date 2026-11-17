---
name: moss-bulk-invoice-download
description: "Downloads all documents of any supplier for any date range in one go. Needs the Moss MCP connected to your AI assistant."
---

# Bulk Invoice Download

Downloads all documents of any supplier for any date range in one go.

This skill reads your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first.

Use AskUserQuestion (clickable multiple choice) to collect [inputs] first. Offer my real entities from Moss as options. Ask me to type names, dates and numbers in chat. If I pick Other, ask again for the exact value.

INPUTS
• Entity: [choose an entity or All entities]
• Supplier: [type one or several supplier names, or choose All]
• Date range: [start date] to [end date]
• Delivery: [overview in chat & files, Excel overview & files, or files only]

RULES
• Look at invoices, card transactions and reimbursements in Moss.
• Match card transactions by merchant name and reimbursements by description.
• If you cannot save files, give download links instead.

OUTPUT
• Every item of the supplier in the date range except rejected ones, with the files in one folder, named date_supplier_documentnumber.
• An overview per item, oldest first: source (card transaction, invoice or reimbursement), document number, date, gross amount, currency, status (Draft, In review, Approved or Paid), transaction ID, file name and file link.
• How many items were found per source, how many rejected were left out, how many files were delivered, and which items have no file or several files.
