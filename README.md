# Moss AI Finance Hub

**Purpose.** Moss AI Finance Hub is an open library of AI skills, agents and workflows for finance teams, maintained by Moss. It is meant to give finance teams ideas and a starting point for their own AI workflows.
See the [disclaimer](#disclaimer).

The skills are also listed, with a demo for each, in the [Moss AI Hub](https://www.getmoss.com/en-gb/ai-in-finance).

## What is in here

| Folder | Content |
| --- | --- |
| [`mcp-use-cases/`](mcp-use-cases) | Skills that answer one finance task each from your live Moss data through the Moss MCP. One folder per skill, each with a `SKILL.md` with the instructions for the AI assistant. |

### MCP use cases

These skills are examples that answer one finance task each, from your live Moss data through the Moss MCP.

| Skill | What it does | Categories |
| --- | --- | --- |
| [Approval Route Lookup](mcp-use-cases/moss-approval-route-lookup) | Shows who must approve one specific item, in which order, and which rule routes it. | Approvals |
| [Approval Route Map](mcp-use-cases/moss-approval-route-map) | Maps all approval routes by rule and shows who and which team, cost centre or cost carrier carries the most approvals. | Approvals |
| [Approver Workload](mcp-use-cases/moss-approver-workload) | Shows which approvers hold the most waiting value and for how long, and drafts a message to each. | Approvals |
| [Bulk Invoice Download](mcp-use-cases/moss-bulk-invoice-download) | Downloads all documents of any supplier for any date range in one go. | Receipts and documents |
| [Highest-Amount Receipt Chase](mcp-use-cases/moss-highest-amount-receipt-chase) | Ranks transactions without a receipt by amount, so the biggest gaps get chased first. | Receipts and documents, Month-end close, Cards and employee expenses |
| [Invoice Status Lookup](mcp-use-cases/moss-invoice-status-lookup) | Finds one invoice from any detail and shows whether it is already in Moss and where it stands. | Accounts payable, Suppliers, Approvals |
| [Invoices Due and Overdue](mcp-use-cases/moss-invoices-due-and-overdue) | Lists unpaid invoices due soon, shows overdue ones separately and compares the total with your balance. | Accounts payable, Cash management |
| [Invoices Without Attachment](mcp-use-cases/moss-invoices-without-attachment) | Finds supplier invoices with no attachment and who to ask for the document. | Receipts and documents, Month-end close |
| [Missing Receipt Chaser](mcp-use-cases/moss-missing-receipt-chaser) | Lists card transactions with no receipt and drafts a reminder for each cardholder. | Receipts and documents, Month-end close, Cards and employee expenses |
| [Overdue Suppliers Ranking](mcp-use-cases/moss-overdue-suppliers-ranking) | Lists suppliers with overdue invoices, ranked by days overdue and by amount. | Accounts payable, Suppliers |
| [Paid and Failed Payments](mcp-use-cases/moss-paid-and-failed-payments) | Lists paid and failed payments in a period and any later payment to the same payee. | Accounts payable, Month-end close |
| [Payment Status Lookup](mcp-use-cases/moss-payment-status-lookup) | Looks up whether and when an invoice was paid, from a supplier, number or amount. | Accounts payable, Suppliers |
| [Quick Past Coding Lookup](mcp-use-cases/moss-quick-past-coding-lookup) | Shows how a supplier or invoice was coded in the past, over all time or a period you choose. | Accounts payable, Suppliers, Month-end close |
| [Best Match Receipt Finder](mcp-use-cases/moss-receipt-finder) | Finds a transaction and its receipt from rough details like merchant, month and amount. | Receipts and documents, Cards and employee expenses |
| [Stuck Approval Chaser](mcp-use-cases/moss-stuck-approval-chaser) | Lists items waiting too long for approval and drafts a message per approver. | Approvals, Month-end close |

## Before you start

The skills read your data through the Moss MCP, so the Moss MCP has to be connected to your AI assistant first. The steps for Claude and ChatGPT are on the page of each skill in the [Moss AI Hub](https://www.getmoss.com/en-gb/ai-in-finance).

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
```

- The folder name and the `name` in the file are the same, and start with `moss-`.
- The `description` says in one sentence what the skill does. The assistant uses it to decide when to run the skill.
- Text in [square brackets] is a detail the assistant asks you for before it starts.

## Contributing

Open a pull request with a new skill folder. A skill that answers one task from Moss data through the Moss MCP goes under `mcp-use-cases/`. Keep one task per skill, write plainly and check every statement about Moss against the real product before you open the pull request.

## Disclaimer

**Disclaimer.** The prompts, skills and any other materials in this repository (the “Content”) are provided solely as examples and ideas for illustration and inspiration. The Content is provided “as is” and “as available”, without warranty of any kind, express or implied (see [LICENSE](LICENSE)). In particular, Moss gives no warranty that the Content is accurate, complete, up to date, secure, error-free, suitable or fit for any particular purpose or task, or capable of producing any particular result, or that it does not infringe third-party rights. Outputs generated using the Content, including AI-generated outputs, may be inaccurate, incomplete or misleading and must be independently verified before use. The Content does not constitute financial, tax, accounting or legal advice. The Content is not a Moss product or service, is not covered by any Moss agreement, support or service level, and is not intended for regulated activities or for decisions about individuals. Users are solely responsible for their use and adaptation of the Content, including testing, their own data and credentials, third-party API and model terms, and compliance with applicable law, including data protection. To the extent permitted by law, Moss excludes liability arising from the use of the Content. “Moss” and the Moss logo are trademarks of Moss and are not licensed under the MIT licence. Third-party names are used for identification only and imply no affiliation.
