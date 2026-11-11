# Approval chains in Sentire Ledger: structural analysis and plan (M5.3)

Written 12 Nov 2026. Asked by the owner after decision 2 of the BIR forms plan: a filed return changes only with a manager's approval, and the same is wanted for financial documents (Sales Invoice, Purchase Order, Journal Entry and the rest).

## 1. What exists today

- No approval chain. The Ledger has a single gate, the manager role: Accounting Period and Stock Reconciliation can only be created or changed by an Accounts Manager (`ph_cas.controls.dates.require_manager`). Everything else is posted by whoever has the submit permission on the doctype.
- Frappe ships a workflow engine that is exactly the base an approval chain needs and that is already used by ERPNext customers: a `Workflow` per doctype with states (each state maps to a docstatus 0, 1 or 2 and says which role may edit in that state), transitions (from state, action name, to state, allowed role, an optional condition such as `doc.grand_total > 100000`), `Workflow Action` records (one per pending approval, with e-mail to the approver and an approve link), and the "Actions" button on the form. Permissions for a state are evaluated by the engine on every save.
- The Annex B controls stay the frame: posting is the submit event, nothing posted is edited or deleted, the event log records every transition. An approval chain sits entirely before submit (the document is a draft until approved), so nothing in the locks changes.

## 2. Design

### 2.1 One settings page, not hand-made workflows
`PH Approval Settings` (single doctype, in Settings): a table of rules, one row per doctype and company:

| Field | Meaning |
|---|---|
| doctype | Sales Invoice, Purchase Invoice, Purchase Order, Sales Order, Journal Entry, Payment Entry, Expense Claim, Stock Entry, Delivery Note, Purchase Receipt, PH Tax Return (the ones that carry money or stock) |
| company | a company, or blank for all |
| applies when | always, or amount above a threshold (grand total, or debit total for a journal), or a condition in Frappe's expression syntax for the unusual case |
| levels | 1 or 2: level 1 approver role (default Accounts Manager), optional level 2 role (for instance Director above a second, higher threshold) |
| self-approval | whether the person who made the document may approve it (default no) |
| who may reject back to draft | the approver; the maker may cancel their own request |
| notify | e-mail the approvers on request, the maker on approve or reject (uses the existing Postal mail) |

Saving the settings generates or updates the Frappe `Workflow` for each doctype listed, with states Draft, Pending approval (level 1), Pending approval (level 2) when used, Approved (docstatus 1, i.e. submitted), Rejected (back to Draft with the reason in a comment). The rule rows are the only thing the user touches; the generated workflows are marked as owned by the settings so a hand edit is overwritten on the next save, and removing a row removes its workflow. A doctype with no row behaves as today.

### 2.2 How a document moves
1. The maker saves the Sales Invoice; the Actions button shows "Request approval" (and "Submit" is hidden by the workflow).
2. The approver gets an e-mail with a link, and the home dashboard shows a card "Awaiting your approval: 3" (one query on Workflow Action, open, for the user's roles).
3. Approve posts the document: the workflow transition sets docstatus 1, so the BIR Series number is taken at that moment, the event log records who made it and who approved it, and from here the Annex B locks apply.
4. Reject returns it to Draft; a reason is required and becomes a comment; the maker edits and requests again. The chain restarts from level 1.
5. A threshold rule below the threshold skips the chain: Submit stays available as today. The threshold is read at request time and written on the document (`ph_approval_rule`) so a later change in settings does not reopen history.

### 2.3 Filed BIR returns (decision 2)
The same engine on PH Tax Return, with states after submit: Filed (docstatus 1) -> Change requested -> Change approved; the approved transition runs a server action that creates the amendment. This is the one workflow with transitions after docstatus 1, and it is read-only on the original throughout.

### 2.4 What the chain does not do
- It never edits a submitted financial document; approval of a change after posting is not a thing in the Ledger. The user cancels through amend (where the Annex B rule allows) or posts a reversing entry, as today.
- It does not replace permissions: a user who cannot submit a Journal Entry still cannot, approval or not.

### 2.5 Doctypes and defaults shipped
Default rows on install, all off until the owner turns them on: Sales Invoice, Purchase Invoice, Purchase Order, Journal Entry, Payment Entry, Stock Entry (Material Issue and Receipt), PH Tax Return (change after filing, always on when the forms module is on). The demo site gets Journal Entry and Purchase Order on, above PHP 50,000, so the chain is visible in the tutorial.

### 2.6 Module toggle (M5.2)
Approval chains are a module: toggle off hides the settings page and disables every generated workflow; toggle on restores them. Fits LDG-83 as one more switch.

## 3. Build plan

| Step | What lands |
|---|---|
| A1 | PH Approval Settings doctype and the workflow generator (states, transitions, conditions, roles, e-mail), idempotent; tests that a row produces the expected Workflow and that removing it removes the workflow |
| A2 | Document behaviour: Submit hidden under a rule, request, approve, reject with reason comment, self-approval rule, `ph_approval_rule` stamped on the document, event log lines for request, approve, reject |
| A3 | Home dashboard card "Awaiting your approval" and a list view filter; approver e-mails through the product's Email Account |
| A4 | PH Tax Return workflow (Filed, Change requested, Change approved -> amendment), built with LDG-82 |
| A5 | Defaults on install, demo rows, user guide section, module toggle wiring |

A1 to A3 are about two days; A4 belongs to the BIR forms common layer; A5 half a day.

## 4. Decisions for the owner
1. Default approver role: Accounts Manager (recommended), or a new role "Approver" that can be given to anyone without the manager's other powers.
2. Levels: ship one level with an optional second (recommended), or one level only for now.
3. Self-approval: refused by default (recommended); a Solo-tier site with one user needs it on, so the setting is per company and the Solo site gets it on at install.
4. Which doctypes are on by default for a new site: none (recommended, the owner switches on what the client wants during onboarding), or Journal Entry and Purchase Order on.
