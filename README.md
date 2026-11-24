# Moss AI Finance Hub

**Purpose.** Moss AI Finance Hub is an open library of AI skills, agents and workflows for finance teams, maintained by Moss. It is meant to give finance teams ideas and a starting point for their own AI workflows.
See the [disclaimer](#disclaimer).

The skills are also listed, with a demo for each, in the [Moss AI Hub](https://www.getmoss.com/en-gb/ai-in-finance).

## What is in here

| Folder | Content |
| --- | --- |
| [`mcp-use-cases/`](mcp-use-cases) | Skills that answer one finance task each from your live Moss data through the Moss MCP. One folder per skill, each with a `SKILL.md` with the instructions for the AI assistant. |
| [`skills/`](skills) | General skills that do not need the Moss MCP. Today they analyse an export of software and SaaS transactions, from a first list of vendors to an overlap report. They work on a file you give them and run bundled Python scripts. One folder per skill, each with a `SKILL.md`, a `scripts/` folder and a `references/` folder. |

### MCP use cases

These skills are examples that answer one finance task each, from your live Moss data through the Moss MCP.

| Skill | What it does | Categories |
| --- | --- | --- |
| [Account Balances by Entity](mcp-use-cases/moss-account-balances-by-entity) | Shows the balance of every Moss account with reserved and available amounts. | Cash management |
| [Approval Route Lookup](mcp-use-cases/moss-approval-route-lookup) | Shows who must approve one specific item, in which order, and which rule routes it. | Approvals |
| [Approval Route Map](mcp-use-cases/moss-approval-route-map) | Maps all approval routes by rule and shows who and which team, cost centre or cost carrier carries the most approvals. | Approvals |
| [Approver Workload](mcp-use-cases/moss-approver-workload) | Shows which approvers hold the most waiting value and for how long, and drafts a message to each. | Approvals |
| [Booking Suggestion](mcp-use-cases/moss-booking-suggestion) | Shows the last 3 bookings of a supplier and recommends how to book a new invoice or transaction. | Reviewing before export, Suppliers, Accounts payable |
| [Budget Balance Lookup](mcp-use-cases/moss-budget-balance-lookup) | Finds a budget from a rough name, shows what is left, warns if the current spending pace is not sustainable, and lists its expenses. | Budgets |
| [Budget Overview Today](mcp-use-cases/moss-budget-overview-today) | Lists all active budgets as of today with owner, limit, spent, committed and what is left, and flags the ones close to the limit in money or in time. | Budgets, Spend analysis and reporting |
| [Budget Reallocation Identifier](mcp-use-cases/moss-budget-reallocation-identifier) | Compares budgets that run out fast with budgets that are barely used and suggests where money could move. | Budgets |
| [Budget Spend Drill-Down](mcp-use-cases/moss-budget-spend-drill-down) | Flags active budgets that are almost used up or spending too fast, and shows the biggest expenses behind them. | Budgets, Spend analysis and reporting |
| [Budget Structure Map](mcp-use-cases/moss-budget-structure-map) | Maps all budgets with owner, type, period, limit and assignment rules, so you see what each one covers. | Budgets |
| [Bulk Invoice Download](mcp-use-cases/moss-bulk-invoice-download) | Downloads all documents of any supplier for any date range in one go. | Receipts and documents |
| [Card Spend Trend](mcp-use-cases/moss-card-spend-trend) | Compares card spend over time by the dimension you choose, such as supplier, team, cardholder or cost centre. | Spend analysis and reporting, Month-end close, Cards and employee expenses |
| [Close Blocker Dashboard](mcp-use-cases/moss-close-blocker-dashboard) | Shows what still blocks the close this month: open items per stage, missing receipts and stuck approvals. | Month-end close, Approvals, Reviewing before export |
| [Duplicate Supplier Finder](mcp-use-cases/moss-duplicate-supplier-finder) | Finds supplier records that look like the same supplier by name, VAT ID, IBAN or address, with the spend on each. | Suppliers, Accounts payable |
| [Entity Spend Month over Month](mcp-use-cases/moss-entity-spend-month-over-month) | Compares spend per entity between two months, split by cards, invoices and reimbursements. | Spend analysis and reporting, Month-end close, Cards and employee expenses |
| [Event Cost](mcp-use-cases/moss-event-cost) | Adds up what an event cost on the expense accounts you name, with cost per attendee, and flags foreign VAT. | Cards and employee expenses, Spend analysis and reporting |
| [Expense Finder](mcp-use-cases/moss-expense-finder) | Finds one expense from a few details like merchant, month and amount. | Reviewing before export, Cards and employee expenses, Accounts payable |
| [Export / Transaction Status Check](mcp-use-cases/moss-export-transaction-status-check) | Shows how many items sit in Collect, Approve, Review and Export, and how many are exported. | Reviewing before export, Month-end close, Approvals |
| [External Food Spend](mcp-use-cases/moss-external-food-spend) | Lists external food spend and flags missing purpose, unusual VAT coding and policy breaks. | Cards and employee expenses, Spend analysis and reporting |
| [Highest-Amount Receipt Chase](mcp-use-cases/moss-highest-amount-receipt-chase) | Ranks transactions without a receipt by amount, so the biggest gaps get chased first. | Receipts and documents, Month-end close, Cards and employee expenses |
| [Home Country VAT Check](mcp-use-cases/moss-home-country-vat-check) | Flags transactions on home country VAT codes where the VAT does not fit the supplier or the rate. | Reviewing before export, Suppliers |
| [Internal Meal and Food Check](mcp-use-cases/moss-internal-meal-and-food-check) | Checks internal meals and team food against a limit or policy and flags unusual VAT coding. | Cards and employee expenses, Spend analysis and reporting |
| [Invoice Cover Check](mcp-use-cases/moss-invoice-cover-check) | Checks if the available balance covers the invoices due in the next days and shows any shortfall. | Cash management, Accounts payable |
| [Invoice Spend Trend](mcp-use-cases/moss-invoice-spend-trend) | Compares supplier invoice spend over time by the dimension you choose, such as supplier, team, category or cost centre. | Spend analysis and reporting, Month-end close, Accounts payable |
| [Invoice Status Lookup](mcp-use-cases/moss-invoice-status-lookup) | Finds one invoice from any detail and shows whether it is already in Moss and where it stands. | Accounts payable, Suppliers, Approvals |
| [Invoices Due and Overdue](mcp-use-cases/moss-invoices-due-and-overdue) | Lists unpaid invoices due soon, shows overdue ones separately and compares the total with your balance. | Accounts payable, Cash management |
| [Invoices Without Attachment](mcp-use-cases/moss-invoices-without-attachment) | Finds supplier invoices with no attachment and who to ask for the document. | Receipts and documents, Month-end close |
| [Largest Expenses](mcp-use-cases/moss-largest-expenses) | Lists the largest expenses in a time frame with type, vendor, cost centre and status. | Spend analysis and reporting, Month-end close |
| [Latest Account Transactions](mcp-use-cases/moss-latest-account-transactions) | Shows the latest bank transactions of one Moss account with date, counterparty and amount. | Cash management, Reviewing before export |
| [Latest Card Spend](mcp-use-cases/moss-latest-card-spend) | Shows the latest card payments with receipt and coding status. | Cards and employee expenses |
| [Missing Coding Quick Check](mcp-use-cases/moss-missing-coding-quick-check) | Shows card transactions, invoices and reimbursements that still miss coding and suggests the booking from past bookings. | Reviewing before export, Month-end close |
| [Missing Receipt Chaser](mcp-use-cases/moss-missing-receipt-chaser) | Lists card transactions with no receipt and drafts a reminder for each cardholder. | Receipts and documents, Month-end close, Cards and employee expenses |
| [Overdue Suppliers Ranking](mcp-use-cases/moss-overdue-suppliers-ranking) | Lists suppliers with overdue invoices, ranked by days overdue and by amount. | Accounts payable, Suppliers |
| [Paid and Failed Payments](mcp-use-cases/moss-paid-and-failed-payments) | Lists paid and failed payments in a period and any later payment to the same payee. | Accounts payable, Month-end close |
| [Payment Status Lookup](mcp-use-cases/moss-payment-status-lookup) | Looks up whether and when an invoice was paid, from a supplier, number or amount. | Accounts payable, Suppliers |
| [Pull Supplier Master Data](mcp-use-cases/moss-pull-supplier-master-data) | Looks up the full record of a supplier: accounting defaults, payment details and address. | Suppliers, Reviewing before export |
| [Quick Past Coding Lookup](mcp-use-cases/moss-quick-past-coding-lookup) | Shows how a supplier or invoice was coded in the past, over all time or a period you choose. | Accounts payable, Suppliers, Month-end close |
| [Best Match Receipt Finder](mcp-use-cases/moss-receipt-finder) | Finds a transaction and its receipt from rough details like merchant, month and amount. | Receipts and documents, Cards and employee expenses |
| [Reimbursement Spend Trend](mcp-use-cases/moss-reimbursement-spend-trend) | Compares reimbursement spend over time by the dimension you choose, such as team, employee, expense account or cost centre. | Spend analysis and reporting, Cards and employee expenses, Month-end close |
| [Reverse Charge Check](mcp-use-cases/moss-reverse-charge-check) | Flags transactions booked on reverse charge where it usually does not apply. | Reviewing before export, Suppliers |
| [Software and Subscription Tracker](mcp-use-cases/moss-software-and-subscription-tracker) | Lists every recurring software vendor with monthly cost, growth and the entities that pay. | Spend analysis and reporting, Suppliers |
| [Spend Spike Finder](mcp-use-cases/moss-spend-spike-finder) | Shows which suppliers were paid far more than usual in a month, plus the highest payments. | Spend analysis and reporting |
| [Stuck Approval Chaser](mcp-use-cases/moss-stuck-approval-chaser) | Lists items waiting too long for approval and drafts a message per approver. | Approvals, Month-end close |
| [Supplier Coding QA Check](mcp-use-cases/moss-supplier-coding-qa-check) | Shows where card transactions, invoices and reimbursements were booked differently from the usual booking of that supplier. | Reviewing before export, Suppliers, Accounts payable |
| [Supplier Exists Check](mcp-use-cases/moss-supplier-exists-check) | Checks whether a supplier already exists in any entity and shows the closest matches with their master data. | Suppliers |
| [Supplier Invoice List](mcp-use-cases/moss-supplier-invoice-list) | Lists every invoice of one supplier across all entities for the time frame you choose. | Suppliers, Accounts payable |
| [Supplier “X” Spend by Month](mcp-use-cases/moss-supplier-x-spend-by-month) | Shows what one supplier costs per month and per entity, with the monthly average. | Suppliers, Spend analysis and reporting, Cards and employee expenses |
| [Top Card Spenders](mcp-use-cases/moss-top-card-spenders) | Ranks cardholders by card spend in a period, with every card transaction listed underneath. | Cards and employee expenses, Spend analysis and reporting |
| [Trip Cost](mcp-use-cases/moss-trip-cost) | Adds up trip costs per employee on the travel accounts you name, and flags foreign VAT. | Cards and employee expenses, Spend analysis and reporting |
| [Vendors by Spend](mcp-use-cases/moss-vendors-by-spend) | Ranks your biggest vendors by spend across cards, invoices and reimbursements, with every transaction listed underneath. | Spend analysis and reporting, Suppliers |
| [Zero VAT Check](mcp-use-cases/moss-zero-vat-check) | Lists transactions booked on zero VAT and flags unusual ones and home or EU suppliers first. | Reviewing before export, Suppliers |

### Software spend skills

These skills work on a transaction export that you give them, so they do not need the Moss MCP. They run Python scripts that come with the skill, so use an assistant that can run code. Each one goes a step further than the one before.

| Skill | What it does | Categories |
| --- | --- | --- |
| [Software Spend Surface](skills/moss-software-spend-surface) | Finds which transactions are software or SaaS spend, merges the name variants of each vendor and describes each tool in one line. | Spend analysis |
| [Software Spend Intelligence](skills/moss-software-spend-intelligence) | Builds an Excel workbook from the export: spend per vendor and month, billing patterns, anomaly flags and a budget versus actual template, all with live formulas. | Spend analysis |
| [Software Overlap Detection](skills/moss-software-overlap-detection) | Finds duplicate subscriptions, parallel contracts and tools with overlapping features, and recommends what to do about each. | Spend analysis |

## Before you start

The MCP use cases read your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first. The software spend skills need no connection, they work on the file you upload. The steps for Claude and ChatGPT are on the page of each skill in the [Moss AI Hub](https://www.getmoss.com/en-gb/ai-in-finance).

## Install a skill

### With the command line

Install every skill in this repository:

```bash
npx skills add getmoss/ai-finance-hub
```

Install one skill:

```bash
npx skills add getmoss/ai-finance-hub --skill moss-missing-receipt-chaser
```

### In Claude Code, by hand

Copy the skill folder into your skills folder, for all projects or for one project:

```bash
cp -r mcp-use-cases/moss-missing-receipt-chaser ~/.claude/skills/
cp -r mcp-use-cases/moss-missing-receipt-chaser .claude/skills/
```

Then start Claude Code and ask for the task, for example "Chase missing receipts".

### In Claude on the web or desktop

Claude takes a skill as a zip file with the skill folder inside. Zip the folder, then open Settings, Capabilities, Skills and upload the file:

```bash
cd mcp-use-cases
zip -r moss-missing-receipt-chaser.zip moss-missing-receipt-chaser
```

On team plans an admin may need to allow skill uploads first.

### In any other assistant

Open the `SKILL.md` of the skill, copy the text below the heading and paste it into a chat that has the Moss MCP switched on. Replace the text in [square brackets] with your own details.

## How a skill is built

```
mcp-use-cases/<skill-name>/
  SKILL.md    # name and description at the top, then the instructions

skills/<skill-name>/
  SKILL.md    # name and description at the top, then the instructions
  scripts/    # Python scripts the skill runs
  references/ # lookup tables the scripts read
```

- The folder name and the `name` in the file are the same, and start with `moss-`.
- The `description` says in one sentence what the skill does. The assistant uses it to decide when to run the skill.
- Text in [square brackets] is a detail the assistant asks you for before it starts.

## Contributing

Open a pull request with a new skill folder. A skill that answers one task from Moss data through the Moss MCP goes under `mcp-use-cases/`. Keep one task per skill, write plainly and check every statement about Moss against the real product before you open the pull request.

## Disclaimer

**Disclaimer.** The prompts, skills and any other materials in this repository (the “Content”) are provided solely as examples and ideas for illustration and inspiration. The Content is provided “as is” and “as available”, without warranty of any kind, express or implied (see [LICENSE](LICENSE)). In particular, Moss gives no warranty that the Content is accurate, complete, up to date, secure, error-free, suitable or fit for any particular purpose or task, or capable of producing any particular result, or that it does not infringe third-party rights. Outputs generated using the Content, including AI-generated outputs, may be inaccurate, incomplete or misleading and must be independently verified before use. The Content does not constitute financial, tax, accounting or legal advice. The Content is not a Moss product or service, is not covered by any Moss agreement, support or service level, and is not intended for regulated activities or for decisions about individuals. Users are solely responsible for their use and adaptation of the Content, including testing, their own data and credentials, third-party API and model terms, and compliance with applicable law, including data protection. To the extent permitted by law, Moss excludes liability arising from the use of the Content. “Moss” and the Moss logo are trademarks of Moss and are not licensed under the MIT licence. Third-party names are used for identification only and imply no affiliation.
