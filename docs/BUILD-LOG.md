# Build log

One entry per bundle, newest first. Counts are the test totals on main after the merge.

## B09 Philippine master data (9 Nov 2026)
- PR: #8
- Built: ph_cas.setup.master_data. Company: registered name, business style, 5-digit branch code, RDO (Link), VAT status (VAT, Non-VAT, VAT-exempt), taxpayer classification per RR 8-2024, taxpayer type, top withholding agent flag, ACCN and date issued; the TIN (tax_id) is validated as 9 digits and normalised to 000-000-000, and a TIN typed with its branch code is refused. Customer and Supplier: TIN and branch, registered name, payee type with last, first and middle names for individuals (required), VAT status, government, top withholding agent, RBE, non-resident digital service provider (suppliers only) and online platform flags, registered address lines and ZIP. Item: VAT class (VATable, VAT-exempt, Zero-rated, Government) and capital-good flag. Sales, Purchase and POS Invoice lines: VAT class fetched from the item when empty. DocType PH RDO seeded with the 138 RDO codes of the eBIRForms package, 121 with names as recalled and flagged unconfirmed. payee_name_parts gives the alphalist name split; dat_branch gives the 4-digit DAT branch code (RDO question 8b default: drop the leading zero, refuse otherwise). The BIR serial's branch code now comes from the Company.
- Tests: 84 on main (+9).
- Assumed: RDO names are not an official list: the eBIRForms package carries codes only. Every row is flagged name_confirmed = 0 until the owner checks it against the BIR directory; 084 and 088 are left unnamed.
- Known limit: The alphalist-style address of Customer and Supplier is kept in the ph_address fields, separate from ERPNext's Address records, because the DAT files want two plain lines.

## B08 Audit trail report and the Annex B print header (9 Nov 2026)
- PR: #7
- Built: ph_cas.audit.header: ph_header(doc) and ph_header_lines(company) give the Annex B header (registered name, address, VAT or NON-VAT REG TIN with 5-digit branch, software name from PH CAS Settings and version with the ERPNext and Frappe versions, printed by, printed on). Registered as Jinja globals; a Letter Head "BIR Header" with content {{ ph_header(doc) }} is created and made the default, so every document print and every query-report print (Frappe v16 renders the letter head server side with the report filters as doc) carries it. ph_cas.audit.export: csv_with_header and xlsx_with_header put the same lines first in exports, and the whitelisted download_report exports any script report that way and logs the export in the event log. Script reports: BIR Audit Trail (PH Event Log merged with Version, Deleted Document, Access Log and Activity Log, time-ordered, filtered by period, user, document type and document) and PH Chain Check.
- Tests: 75 on main (+7).
- Assumed: The header reads ph_registered_name, ph_vat_status and ph_branch_code from Company when B09 adds them, and falls back to company_name and tax_id meanwhile. The Annex B item on the product name ticks only when the owner sets D9 in PH CAS Settings.
- Known limit: The report view's generic Export button (any report) still produces a bare file; ph_cas's own reports (B23 onward) use download_report. Frappe's test environment writes no Version rows, so the merge test inserts one directly.

## B07 Hash-chained event log (9 Nov 2026)
- PR: #6
- Built: DocType PH Event Log (sequence, timestamp, user, event, document type and name, docstatus after, details JSON, previous hash, SHA-256 hash), insert-only through ph_cas.audit.events.record, which appends under a row lock on the latest row. Writers: create, submit, amend, cancel, edits after submit (with the diff), delete attempts, print (before_print), exports and PDFs (Access Log), sign-in and sign-out (on_login, on_logout), failed sign-ins (Activity Log), user deactivation and reactivation, role changes, permission records, settings changes with diffs (System, Accounts, Stock, Selling, Buying, PH CAS Settings, BIR Series, Accounting Period, Document Naming Settings, Print Settings), master-data changes (Customer, Supplier, Item, Account, Company, Cost Center, Warehouse). verify_chain recomputes every hash and reports the first bad row; a daily scheduler job records the result on PH CAS Settings and emails System Managers on a break.
- Tests: 68 on main (+11).
- Assumed: Masters are logged at field level; vouchers at event level with totals and serial, since their field history is in Version. Comments and attachments are not logged.
- Known limit: Rows are written in the caller's transaction, so an event of a request that later fails is rolled back with it (correct: the thing it describes did not happen). The daily check needs the scheduler enabled, which B31 does.

## B06 BIR serial number (9 Nov 2026)
- PR: #5
- Built: DocType BIR Series (company, 5-digit branch code, document type Sales Invoice / Credit Note / Debit Note / Collection Receipt, optional prefix, 8 digits, registered range, ACCN, date issued, next number, warning threshold). Custom fields on Sales Invoice and Payment Entry: ph_branch_code (default 00000), bir_serial (read-only, listed, filterable) and a hidden unique bir_serial_key (series plus number), so the same number may legitimately appear on an invoice and a credit note. ph_cas.controls.serial.allocate takes the number with SELECT FOR UPDATE inside the submit transaction; a failed submit rolls the counter back; cancellation keeps the number; copies and amendments never inherit one; the range end is enforced; a warning shows and PH Accounting Managers are emailed as the range runs down. ensure_series creates the four series of a branch (used by the Philippine setup action in B10).
- Tests: 57 on main (+9), including a 50-thread concurrency test on the counter.
- Assumed: D4 as recommended. Credit notes are Sales Invoices with is_return, debit notes with is_debit_note; a Payment Entry of type Receive is the Collection Receipt.
- Known limit: The series' branch code comes from the document's ph_branch_code field until B09 fetches it from the Company and branch master.

## B05 Security baseline (9 Nov 2026)
- PR: #4
- Built: ph_cas.controls.security. System Settings forced and refused weaker: one session per user, password change every 30 days at most, strong password policy (score 3 or more), Frappe's lock after 5 consecutive failures for 300 seconds or more, two-factor sign-in with an OTP app. Deactivation after N failed sign-ins since the last successful one (N from the new single DocType PH CAS Settings, default 5, minimum 3), done from the Activity Log after_insert event, with an Info comment on the User and an email to System Managers; reactivation is a User edit by a System Manager, recorded in Version history. PH CAS Settings also carries the product name (D9) and refuses the ERPNext trademark in it.
- Tests: 48 on main (+7).
- Assumed: Two-factor sign-in is turned on for every user at once; on a new site the first sign-in shows the OTP setup. Stricter values than the baseline are allowed and are not loosened by migrate.
- Known limit: Infrastructure items of Annex B 11 (firewall, encryption at rest, server room) belong to B31.

## B04 Lock-down 3: dates, drafts, periods, inventory (8 Nov 2026)
- PR: #3
- Built: ph_cas.controls.dates. Sales Invoice, POS Invoice, Payment Entry and the stock documents carry today's date (Asia/Manila; the System Settings time zone is forced) and Edit Posting Date and Time is refused; an amendment is a new document and takes today's date. Journal Entry and Purchase Invoice may be back-dated only by the role PH Accounting Manager (created here) with a written reason in the new field "Reason for earlier posting date"; future dates are refused for every posted voucher type. Drafts of posted voucher types cannot be printed or turned into PDFs (before_print refuses). Accounting Period: creating or changing one needs the manager role; every posted voucher type is closed; no exempted role. Company: perpetual inventory off for new companies and refused on (D7). Stock Reconciliation needs the manager role.
- Tests: 41 on main (+16).
- Assumed: Purchase Invoice back-dating allowed under the same manager-plus-reason rule as Journal Entry (supplier bills arrive late); the bundle text named only Journal Entry. Drafts are refused outright instead of watermarked (stricter and simpler; B20 may add a watermark if the owner wants draft previews).
- Known limit: ERPNext v16.54.0 crashes on inserting an Accounting Period through the API with an empty closed-documents table (dict attribute access in bootstrap_doctypes_for_closing); the form never does that. Tests supply one row. The period_closing_doctypes hook lists every posted voucher type for the form.
- Left out: nothing in scope.

## B03 Lock-down 2: nothing posted can be changed or renumbered (8 Nov 2026)
- PR: #2
- Built: ph_cas.controls.posted_fields. Property setters turn allow_on_submit off on every accounting field of the posted voucher types and their child tables (ERPNext ships 21 such fields on Sales Invoice alone, including cost centre, write-off and unrealised profit accounts; 10 on its lines including income and expense account; account_head on both tax tables; party_name on Payment Entry). An explicit allowlist keeps presentation and reference fields editable: letter head, print heading, title, page break, PO number and date, dispatch address, sales team, auto repeat, the read-only stock displays. The before_update_after_submit hook diffs header and child rows against the database and refuses any change outside the allowlist, even if a field were allow-on-submit. With no accounting field editable after submit, ERPNext's automatic Repost Accounting Ledger path is unreachable, and B02 refuses the insert regardless. ph_cas.controls.naming overrides Document Naming Settings so that update_series_start is refused for any accounting document type or prefix.
- Tests: 25 on main (+9).
- Assumed: nothing new.
- Known limit: deleting a draft that was the latest in its series hands its number back (Frappe behaviour). Drafts are not accounting documents and the BIR serial of B06 is taken at submit, so this is accepted; Deleted Document keeps the record.
- Left out: nothing in scope.

## B02 Lock-down 1: nothing posted can be deleted or reposted (8 Nov 2026)
- PR: #1
- Built: ph_cas.controls.locks. on_trash on every DocType refuses deletion of GL Entry, Stock Ledger Entry and Payment Ledger Entry rows, of any posted voucher type (docstatus 1 or 2), and of any other submitted or cancelled document that has ledger rows. before_insert refuses Transaction Deletion Record, Repost Accounting Ledger and Repost Item Valuation (this also stops ERPNext's automatic repost on edits of posted fields, since it inserts a Repost Accounting Ledger; B03 tests that path). Accounts Settings: Immutable Ledger forced on and "Delete Accounting and Stock Ledger Entries on deletion of Transaction" forced off by setup_all on install and migrate, and the validate hook refuses turning them back. The Company form's Delete Transactions button is removed by a client script; the server refuses the request regardless. Escape hatch for tests: ph_cas_unlocked: 1 in site_config, ignored when ph_cas_production: 1.
- Tests: 16 on main (+13). Fixtures in ph_cas.tests.fixtures (customer, supplier, service item, Sales Invoice, Journal Entry on the setup-wizard company).
- Assumed: D6 (corrections by cancel and reissue) as recommended.
- Known limit: when the ledger-deletion setting is on, ERPNext's own on_trash removes GL rows by raw SQL before doc_events run; the ph_cas refusal then aborts the request and the rollback restores them. The setting is forced off and refused on, so this path should never be reachable; the test exercises it with a savepoint.
- Left out: nothing in scope.

## B01 Repository, bench, CI, bootstrap, reference docs (7 Nov 2026)
- PR: (filled in at merge)
- Built: scripts/bootstrap.sh (uv Python 3.14, Node 24 from the npm registry, bench init at the pinned tags, ERPNext, ph_cas, test site); the ph_cas app skeleton (hooks, after_install and after_migrate through ph_cas.setup.install.setup_all, patches.txt, tests); VERSIONS.md; docs/DECISIONS.md; docs/CONFORMANCE.md with every Annex B item pending; docs/reference with the six reference documents; CI on GitHub Actions.
- Tests: 3 (ph_cas.tests.test_install), run on a real bench; a before_tests hook completes the ERPNext setup wizard for "_Test PH Company" (Philippines, PHP, Asia/Manila) because Frappe runs before_tests only for the app under test.
- Assumed: D1 and D2 as recommended. Node binaries come from the npm registry because nodejs.org was not reachable from the build workspace. The bootstrap points bench at the system Redis on 6379 instead of the 11000 and 13000 instances bench start would run; bench refuses to run as root, so the script exits early with that message.
- Left out: nothing in scope. The em-dash check covers docs/ only; reference documents copied in were cleaned of em and en dashes on the way in.
