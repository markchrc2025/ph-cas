# Sentire Ledger role sets and permission matrix (B79, B82)

Every client user gets exactly one role set (User > Role Profiles). The sets are kept by `ph_cas/setup/roles.py` and re-applied on every migrate. Bookkeeper was renamed Accountant and Cashier was renamed Staff in B79; users who held the old names moved with them.

| Role set | Who | In one line |
| --- | --- | --- |
| Owner | The business owner or the firm partner | Everything, including users, modules and system settings |
| Accounting Manager | The head of accounting | Everything in the books except users, modules and system settings |
| Accountant | The person who records the business | Records invoices, bills, payments, journals, masters, stock and BIR return drafts; reads the books |
| Staff | Counter or front-desk staff | Sales invoices, collections and stock issues at the counter |

The UAT accounts on staging, one per set: Owner A, Accounting Manager A, Accountant A, Staff A (Company A), and Accountant B (Company B, the other tenant). See `tools/uat/cases/_common.py`.

## The matrix

Y = allowed, N = refused, R = read only. "Enforced by" names where the rule lives, so a failure can be traced.

| # | Capability | Owner | Acctg Mgr | Accountant | Staff | Enforced by | UAT case |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Add users, give role sets | Y | N | N | N | System Manager (User) | LDG-RP-001..004 |
| 2 | Switch modules on and off (Settings > Modules) | Y | R | N | N | PH Modules perms | LDG-RP-005, 006 |
| 3 | Sentire Ledger Settings | Y | R | N | N | PH CAS Settings perms | LDG-RP-007 |
| 4 | Company details (TIN, COR, go-live date) | Y | Y | R | R | Company perms | LDG-RP-008, 009 |
| 5 | Chart of accounts and cost centers | Y | Y | R | R | roles.chart_limit | LDG-RP-010..012 |
| 6 | Account mapping (tax accounts) | Y | Y | N | N | PH Account Mapping perms | LDG-RP-013 |
| 7 | Sales invoice: create and submit | Y | Y | Y | Y | Accounts User | LDG-RP-014, 015 |
| 8 | Sales invoice or collection receipt: cancel an issued one | Y | Y | Y | Y | Accounts User cancel right; a Cancel approval chain gates it where set (B84) | LDG-RP-016, SL-008, AP-011 |
| 9 | Collection (Payment Entry, Receive) | Y | Y | Y | Y | Accounts User | LDG-RP-017 |
| 10 | Payment out (Payment Entry, Pay) | Y | Y | Y | N | roles.cashier_limit | LDG-RP-018, 020 |
| 11 | Bill (Purchase Invoice), Record an expense | Y | Y | Y | N | roles.cashier_limit | LDG-RP-019, 021 |
| 12 | Journal Entry dated today | Y | Y | Y | N | roles.cashier_limit | LDG-RP-022, 023 |
| 13 | Journal Entry or bill with an earlier date (with a reason) | Y | Y | N | N | controls.dates (Accounting Manager role) | LDG-RP-024, 025 |
| 14 | Accounting Period (close a month) | Y | Y | N | N | controls.dates.manager_only_permission | LDG-RP-026, 027 |
| 15 | Customers | Y | Y | Y | Y | Sales User | LDG-RP-028 |
| 16 | Suppliers | Y | Y | Y | N | Purchase Master Manager; cashier_limit | LDG-RP-029 |
| 17 | Items and item prices | Y | Y | Y | R | Item Manager, Master Managers | LDG-RP-030 |
| 18 | Stock entries (issue, receipt, transfer) | Y | Y | Y | Y | Stock User | LDG-RP-031 |
| 19 | Stock count (Stock Reconciliation) | Y | Y | N | N | Stock Manager + manager_only_permission | LDG-RP-032, 033 |
| 20 | BIR return: prepare (create, refresh from books, preview) | Y | Y | Y | R | Accounts User; roles.cashier_limit | LDG-RP-034 |
| 21 | BIR return: mark filed (submit) | Y | Y | N | N | PH Tax Return before_submit (B79) | LDG-RP-035, 036 |
| 22 | BIR return: open an amendment | Y | Y | N | N | PH Tax Return MANAGER_ROLES | LDG-BR cases |
| 23 | Books of accounts (journals, ledgers, cash books) | Y | Y | Y | N | Report roles; roles.check_report | LDG-RE-004..006 |
| 24 | Financial statements, AR/AP reports | Y | Y | Y | AR only | Report roles; roles.check_report | LDG-RE-004..007 |
| 25 | Audit trail, chain check | Y | Y | N | N | Report roles | LDG-RE-005 |
| 26 | Approve requests in an approval chain | per chain | per chain | per chain | N | approvals | LDG-AP cases |
| 27 | Approval chains: set up | Y | Y | N | N | approvals.api.from_template | LDG-AP cases |
| 28 | Paper-check print pack | Y | Y | N | N | paper_check.download | LDG-PC-006 |
| 29 | Import from a template | Y | Y | Y | customers only | imports (each row needs the right to save it) | LDG-IM cases |
| 30 | Another company's records (cross-tenant) | N | N | N | N | User Permissions on Company | LDG-RP-037..040 |

Notes:

- Row 8 (owner, 21 Nov 2026): an issued invoice or collection receipt may be cancelled; it keeps its BIR serial and a replacement takes the next. Where the business sets a Cancel approval chain, the form shows Request cancellation instead of Cancel. A draft can be deleted by whoever made it; a posted document is never deleted.
- B82: Staff's lists of bills, journals, suppliers and BIR returns are empty and their menus are hidden; collections stay. A new form a role cannot save shows a note and no Save button. Every role set has Prepared Report User.
- Row 13: Sales invoices, collections and stock documents always carry today's date, for every role.
- Row 24: Staff opens only the counter's reports (`STAFF_REPORTS` in `roles.py`): PH Cash Position, Sales Register, Sales by item, Accounts Receivable and its summary, Stock Balance, Projected quantity. Any other report, by menu or by URL, is refused.
- A switched-off module hides its menus and reports for every role, Owner and Administrator included. Nothing is deleted, and turning the module on restores everything. A System Manager sees which modules are off on the Home page and the Reports page.
