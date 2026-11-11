# Approval chains in Sentire Ledger: structural analysis and plan (M5.3)

Written 12 Nov 2026. Asked by the owner after decision 2 of the BIR forms plan: a filed return changes only with a manager's approval, and the same is wanted for financial documents (Sales Invoice, Purchase Order, Journal Entry and the rest).

## 1. What exists today

- No approval chain. The Ledger has a single gate, the manager role: Accounting Period and Stock Reconciliation can only be created or changed by an Accounts Manager (`ph_cas.controls.dates.require_manager`). Everything else is posted by whoever has the submit permission on the doctype.
- Frappe ships a workflow engine that is exactly the base an approval chain needs and that is already used by ERPNext customers: a `Workflow` per doctype with states (each state maps to a docstatus 0, 1 or 2 and says which role may edit in that state), transitions (from state, action name, to state, allowed role, an optional condition such as `doc.grand_total > 100000`), `Workflow Action` records (one per pending approval, with e-mail to the approver and an approve link), and the "Actions" button on the form. Permissions for a state are evaluated by the engine on every save.
- The Annex B controls stay the frame: posting is the submit event, nothing posted is edited or deleted, the event log records every transition. An approval chain sits entirely before submit (the document is a draft until approved), so nothing in the locks changes.

## 2. Design (revised 12 Nov after the owner's decisions)

The owner's reference is Form Approvals for Google Forms (youtube.com/watch?v=eXdbUwzqI6s): a chain of any number of steps, each step with its recipients (a named person, a group, a role, or a person looked up from the document), its receiving order (one after the other, or all at once with "any one" or "everyone" deciding), its role type (approver, or notify-only such as a record keeper), and business logic that routes by amount (up to PHP 1,000 to the department manager, over it to the head of department), with a decline sending the document back to the requestor from any step. That is the shape to build. Frappe's built-in Workflow cannot express it (its transitions are by role only, no named people, no lookups, no "any one of" versus "everyone", no notify-only step, no per-step private note), so the Ledger gets its own small chain engine and uses Frappe only for what it is good at: the submit gate, permissions, e-mail and the event log.

### 2.1 The three doctypes
**PH Approval Chain** (one per doctype and company, or all companies): `document_type`, `company`, `enabled`, `applies_when` (always, or a condition in Frappe's expression syntax such as `doc.grand_total > 50000`), and the table **PH Approval Step**, one row per step in order:

| Column | Meaning |
|---|---|
| step | 1, 2, 3 ... no limit |
| title | "Supervisor", "Department manager", "Purchasing" |
| condition | optional; the step is skipped when false. Two steps with complementary conditions make a branch (up to 1,000 / over 1,000) |
| recipient type | Role (every user with the role, in the document's company), User (named), Group (a PH Approval Group of named users), Dynamic (a field of the document that names a user, such as `owner`'s reporting manager from the Employee record, the cost center's owner, or a lookup table PH Approval Lookup: field value -> approver) |
| receiving order | Sequential (each recipient in turn), Any one (the first decision counts), Everyone (all must approve) |
| role type | Approver (decides), Notify (gets the e-mail and the document link, cannot block; the "record keeper") |
| allow self-approval | the requestor may decide this step when they are a recipient |
| private note | a message shown only to this step's recipients |

**PH Approval Request** (one per document, created at "Request approval"): the document link, chain snapshot (the steps as they were, so a later edit of the chain does not change a running request), current step, status (Pending, Approved, Rejected, Withdrawn), requested by and at, decided at, reason. Child table **PH Approval Decision**: step, recipient, decision (Approved, Rejected, Pending, Skipped), decided at, comment. The request is the audit record; its lines are copied into the PH Event Log.

**PH Approval Group** (a named set of users), **PH Approval Lookup** (a small table: doctype, field, value, approver) for dynamic routing.

### 2.2 How a document moves
1. The maker saves. If an enabled chain applies, Submit is hidden and "Request approval" shows; the request is created, step 1's recipients are resolved and e-mailed (Postal), each gets a Workflow-Action-style entry in "Awaiting your approval" on the home page.
2. A recipient opens the document and sees the approval panel: the chain with each step's state, a comment box, Approve and Reject. Reject needs a reason, closes the request as Rejected and returns the document to the maker (it stays a draft; the maker edits and requests again, from step 1). Approve records the decision; when the step's receiving order is satisfied the next applicable step starts; a Notify step sends its mail and passes at once.
3. After the last step the request is Approved and the engine submits the document: this is the posting event, the BIR Series number is taken now, the event log records maker and every approver, and the Annex B locks apply from here. If submit fails (a validation on the document), the request stays Approved and the maker sees the error; a second Submit by the maker then goes through without a new chain (the approved request is attached to the saved document and consumed once; any edit after approval voids it, through the posted-fields diff already used for the locks).
4. The maker may withdraw a pending request. An approver who is also the maker is skipped unless the step allows self-approval.
5. No chain applies (none enabled, or the condition is false) and the site has more than one user: Submit works as today. A site with exactly one active system user, or a form with no chain: the maker submits, which is the owner's "self-approval when there is no chain or only one user".

### 2.3 Filed BIR returns (decision 2 of the BIR forms plan)
The same engine runs the change request on a filed PH Tax Return: chain on document type PH Tax Return with one step, role Accounts Manager, applies always. The request is raised on a submitted document, so for this doctype the approved outcome is not a submit but a server action: create the amendment with `amends` set. The original stays read-only throughout.

### 2.4 What the chain does not do
- It never edits a submitted financial document; a change after posting is still amend or a reversing entry.
- It does not replace permissions: a user who cannot submit a Journal Entry still cannot, and the engine submits on their behalf only when the chain is approved by people who could.

### 2.5 Shipped state
Nothing on by default. The owner onboards every client and switches chains on per doctype as the client wants (decision 4). Chain templates are offered in the settings page to save typing: "Manager approves above an amount", "Supervisor then manager by amount band", "Everyone in a group". The demo site has Journal Entry and Purchase Order chains on above PHP 50,000.

### 2.6 Module toggle (M5.2)
Approval chains are a module: off hides the pages and suspends every chain (documents submit as today); on restores them. One more switch in LDG-83.

## 3. Build plan

| Step | What lands |
|---|---|
| A1 | PH Approval Chain, Step, Group, Lookup doctypes; the resolver (recipients for a step on a given document, condition evaluation, self-approval skip); chain templates; tests on resolution and branching |
| A2 | PH Approval Request and Decision; request, approve, reject, withdraw; sequential, any one, everyone; notify steps; auto-submit on approval and the consumed-once rule; posted-fields diff voids an approved request; Submit hidden and the approval panel on the form (client script for every chained doctype); event log lines |
| A3 | "Awaiting your approval" card on the home page and a list page of requests; approver and maker e-mails through the product's Email Account |
| A4 | PH Tax Return change chain (approved outcome creates the amendment), built with LDG-82 |
| A5 | Nothing on by default, demo chains, user guide section, module toggle wiring |

A1 to A3 are about three days now that the engine is our own; A4 belongs to the BIR forms common layer; A5 half a day.

## 4. Decisions (owner, 12 Nov 2026)
1. Default approver role: Accounts Manager.
2. Levels: any number of steps, each configurable (recipients, order, role type, condition), as in Form Approvals.
3. Self-approval: allowed when no chain applies to the form, or the site has only one user; otherwise per step.
4. Nothing on by default; the owner switches chains on during each client's onboarding.
