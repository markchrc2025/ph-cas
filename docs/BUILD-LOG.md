# Build log

One entry per bundle, newest first. Counts are the test totals on main after the merge.

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
