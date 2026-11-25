# Build log

One entry per bundle, newest first. Counts are the test totals on main after the merge.

## B81 Ledger runs on Sentire Framework (21 Nov 2026)
- Asked by the owner (20 Nov 2026): build Sentire Framework, Sentire's own framework, and run Ledger on it. Issue LDG-184.
- Pins: framework from plain Frappe v16.60.2 to Sentire Framework v16.60.2-sentire.1 (github.com/markchrc2025/sentire-framework, release branch release/v16.60.2-sentire.1, commit 0e53f54d; the build checks the exact commit, based on Frappe v16.60.2). ERPNext stays upstream v16.60.0. bench CLI pinned to 5.31.1 (it renames the cloned sentire-framework folder to apps/frappe). Dockerfile, scripts/bootstrap.sh, VERSIONS.md.
- The framework keeps the `frappe` package and upstream's `__version__`, so ERPNext and ph_cas install unchanged. Its changes (name, logos, no update calls, no product ads, the event format and the TypeScript kit) are listed in the framework's CHANGES-SENTIRE.md.
- Users still see Sentire Ledger only (B38). The licences line in About, the registration pack and the sworn statement now name "Sentire Framework v16.60.2-sentire.1 (based on Frappe Framework 16.60.2)" (audit.header.framework_label).
- System Settings "Disable Product Suggestion" is now forced on (no Frappe CRM or Helpdesk ads for System Managers).
- Docs: docs/LEGAL-FRAMEWORK.md, docs/runbooks/framework-upstream-sync.md. D1 updated.
- Tests: +10 (test_b81_framework). UAT: tools/uat/cases/framework_branding.py (6 cases), to hand off after the current UAT run.
## B91 The Home checklist ticks from the work done (26 Nov 2026)
- Owner's test (25 Nov 2026): Print your first BIR invoice stayed unticked after the invoice was printed. The steps ticked only when clicked from the checklist itself (Frappe's onboarding flags), and step 1 only because setup marked it.
- Each step now ticks from the company's records, read every time Home opens, for the company chosen on Home (ph_cas/home/progress.py; rules in D13, approved by the owner 26 Nov 2026). Saving the Modules page by a user records the Choose what you use step (not install or migrate).
- New UAT workbook get-to-know (LDG-GK-001 to LDG-GK-010), approved by the owner 26 Nov 2026; runs last.
- Tests: +7 (test_b91_onboarding_progress).

## B90 The 2307 prints clean, with Printed and Issued (25 Nov 2026)
- Owner (25 Nov 2026): a 2307 is issued to the supplier, not filed, so the "DRAFT, NOT FILED" watermark and the preview line came off. Printing locks the certificate (a draft is saved with the latest bills and submitted first, after a confirmation); the status goes Draft, Printed, Issued (Mark as issued asks the day it was handed over; not before the first print, not in the future), Cancelled. Reprints are counted on the certificate and in the Event Log. A correction is cancel and amend; the amendment records the certificate it replaces.
- Where the tax came from: each certificate lists every bill and payment that withheld tax in the quarter (document, date, supplier's invoice number, ATC, month, income, tax), linked to the document. Existing certificates get their status and their list by patch.
- The quarter's batch print from BIR Returns (form 2307) is unchanged.
- Decision D12. Tests: +3 (test_b90_2307_status).

## B89 PDFs on the server, and Print prints the PDF (25 Nov 2026)
- Owner's human test of SL-013 (25 Nov): Download PDF failed with a server error ("Chromium took too long to start": Frappe 16 makes PDFs with Chromium by default, and the image carries wkhtmltopdf, not Chromium). Print opened the browser's own print of the page, so Chrome added the date, title, web address and page numbers to the sheet.
- Every PDF is now made on the server with wkhtmltopdf (Print Settings and every print format, re-applied on migrate). "Print generated PDF" is on: Print fetches the server's PDF and sends that to the printer dialog, so the sheet carries only the invoice. Prints made this way are counted in PH Print Record as before.
- Tests: +1 (test_b89_pdf_printing).

## B88 Hold Submit until the approval status arrives (25 Nov 2026)
- Retest 4 noted that a bill showed a plain Submit for 1 to 5 seconds after opening or saving, before it turned into Request approval or Approve (a click got the server's refusal). The boot now lists the document types an enabled chain covers, with their actions; on those forms Submit (or Cancel, on a posted document under a Cancel chain) stays disabled, with "Checking approval...", until the status arrives.
- Tests: +1 (test_b88_approval_hold).

## B87 Fixes from retest 3 (25 Nov 2026)
- Retest 3 on 0.1.0+742f9d22845a: 20 cases, 16 passed, 1 failed, 3 blocked (AP-010 waits on AP-008; FW-004 and FW-005 wait on the Administrator password).
- Later-day posting (LDG-244): a draft saved on one day and approved (or submitted) on a later day failed with "Due Date cannot be before Supplier Invoice Date": ERPNext moves the posting date to today, but the due dates stayed. Sales and purchase invoices now carry today on such a submit, with their due dates (and payment schedule) moved by the same number of days; a date set on purpose (Edit Posting Date) is left alone. The dates are no longer part of an approval's fingerprint, so a maker's own submit after a failed post still matches the approval.
- Stale scripts (LDG-243): the app's scripts and style sheet are loaded with the build in their address (?v=<build>), so a browser fetches them again after every deploy instead of keeping the previous build's copies.
- Tests: +3 (test_b87_later_day).

## B86 Fixes from retest 2 (24 Nov 2026)
- Retest 2 on 0.1.0+b8680cc281fc: 34 cases, 22 passed, 9 failed, 3 blocked.
- Cancelling (LDG-235): ERPNext gives Accounts User (the Accountant's and Staff's role) submit but not cancel on Sales Invoice, so B84's rule could not be used. The role sets now get cancel on Sales Invoice and Payment Entry (Custom DocPerm, re-applied on migrate).
- Approval panel (LDG-236, LDG-237): the panel is drawn at the top of the form itself, not in the form dashboard (which the form can reset or hide after the panel's call returns); its actions (Request cancellation, Approve, Reject, Withdraw request) are buttons in the panel as well as in the toolbar. Reject asks its reason in a dialog that never marks it required, so the server's "Give the reason for the rejection." shows (LDG-233).
- Switched-off module (LDG-165): the browser goes to the product's workspace address, which the product turns into Home (a page's own address is not /desk/<page> in this desk).
- Framework branding: the sign-in card shows the Sentire Ledger wordmark and the tab title names the product (LDG-238); the product's About adds the Sentire Framework logo, "Sentire Framework, based on Frappe Framework (MIT)." and the Sentire Framework Version (LDG-239); the apps screen's avatar menu gets Get help and Your plan, and the framework's "Frappe Support" link is taken off it (LDG-240, LDG-242). In this desk Help sits in the menu under the product name at the top of the sidebar; FW-003's steps now say so.
- UAT pack: FW-004 and FW-005 name the Administrator password (STAGING_ADMIN_PASSWORD, given in the chat; LDG-241); AP-004 and AP-008 no longer ask a reason the bill's Request approval does not take.
- Tests: +2 (test_b86_retest2_fixes).

## B85 Tutorial uploads in 1 MB requests (24 Nov 2026)
- Owner's upload on live failed ("Error" on V01 and V02): each 8 MB piece took longer than 60 seconds to send from the owner's connection, and the proxy in front of the site cuts a request at 60 seconds, so every piece was cut and retried until the file failed (the site logs show part 1 of each video sent again about every 62 seconds and never answered).
- The browser now sends every file in 1 MB requests (five tries each). The site writes a part's chunks into a temporary file in the site's private folder and, at the part's last chunk, sends the 8 MB part to the bucket as before; the file is removed at once. A resent chunk overwrites its place; a resent last chunk after success returns the same part. Captions and thumbnails go the same way. A dropped connection or a server answer now shows its reason in the Status column instead of "Error".
- Tests: +1 in test_b51 (chunked upload with retries).

## B84 Cancelling issued invoices and receipts, with an optional approval chain (21 Nov 2026)
- Asked by the owner (21 Nov 2026, answering the retest question on SL-010): all principal and supplementary invoices can be cancelled; Staff can cancel invoices; cancellation can be set with an approval chain. Replaces D6's "never cancelled" (B21, B46, LDG-96).
- An issued Sales Invoice, credit note or debit note may now be cancelled by any role with the cancel right, Staff included (collection receipts already could). It keeps its BIR serial; Amend makes the replacement, which takes the next serial. The form says so under the title. The delete refusal is the general one again ("Cancel it, or correct it with a new document").
- Approval chains have an Action: Submit (as before, the default) or Cancel. With an enabled Cancel chain, a posted document's Cancel button gives way to Request cancellation (reason required); the last approval cancels it; a cancel sent any other way is refused ("... needs approval to be cancelled ..."). A filed BIR return keeps its own amendment chain.
- UAT: RP-016 (Staff cancels an issued invoice), SL-008 (cancel and reissue with the next serial) and the new AP-011 (cancellation chain) replace the never-cancelled cases; BA-013 back to the general message.
- Tests: +3 (test_b84_cancel); test_b06 and the QA full pass now cancel an issued invoice and check its serial.

## B83 Fixes from the B82 retest (21 Nov 2026)
- Asked by the owner (21 Nov 2026): fix every failure of the retest on 0.1.0+5195441c14c2 (78 cases: 63 passed, 9 failed, 3 blocked, 3 human), then retest.
- Chart of accounts: Frappe 16.60's row menu ran Add Child on the selected node, not on the row clicked, so a new account landed under Expenses; each row action now selects its own row first (tree_fix.js, LDG-230).
- General Journal: a journal entry's lines whose ledger remark is empty show the entry's User Remark (LDG-210).
- Modules: a switched-off module's address now sends the browser to the Sentire Ledger home and shows the notice there; Frappe's start-up routing had overruled the earlier redirect (LDG-165).
- Deleting: a posted voucher or a filed return deleted from the list or the form gets the app's message before Frappe's "Cancel it first". An issued BIR document says "... (BIR serial ...) has been issued and cannot be deleted. Correct it with a credit note or a debit note." (LDG-222). Managers (and the Owner) may delete BIR returns, so a draft can be removed and a filed one shows its sealed message (LDG-214).
- Customer and Supplier: the BIR details sit in a tab of their own, "BIR details", on the new form too. Frappe 16.60 had moved the section into the Items tab, which shows only after the first save (LDG-229, LDG-171).
- Approvals: an empty rejection reason gets "Give the reason for the rejection." instead of the generic Missing Values dialog (LDG-233).
- UAT cases corrected (owner approval asked): AP-003 (no Submit, Request approval instead; LDG-232), AP-010 (a step that posts a new bill over the amount), BR-011 (Open amendment no longer offered once an amendment exists; LDG-216), SL-010 (ERPNext's status Credit Note Issued; LDG-231), BA-013 (the new message).
- Tests: +4 (test_b83_retest_fixes).

## B82 Fixes from the first full UAT run (21 Nov 2026)
- Asked by the owner (21 Nov 2026): fix every finding of the UAT run on 0.1.0+1d56e40d2b40 (227 cases: 158 passed, 37 failed, 14 blocked, 18 not tested; 37 bugs, 25 gaps), then retest.
- Controls: saving an enabled approval chain switches approval chains on for the business, so the chain is never silently ignored (LDG-205). A journal entry whose debits and credits differ is refused on save, not only on submit (LDG-208). A credit note against an invoice with an outstanding balance reduces that balance by default (LDG-197).
- Staff: refused every right on the bill, journal, supplier and BIR doctypes (collections excepted); their lists come back empty and the menus, search bar and sidebar leave them out, with every report but the counter's (LDG-183, 196, 204, 209, 225). Every role set gets Prepared Report User, so the Accountant sees Stock Balance results (LDG-198).
- BIR returns: a filed return is called by name, so the Accountant opens it read only and no "modified after you opened it" conflict follows (LDG-214, 215). One amendment at a time; the original shows it at once, and a deleted draft amendment frees it (LDG-216). The Accountant's form says a manager files the return and shows no Open amendment (LDG-188, 213). Nested book figures no longer show as [object Object] (LDG-218). The generate and export buttons sit under one BIR files menu (LDG-191). Book to tax reconciliation gains a 2550Q output VAT view: Sales Journal, ledger and Item 37 of the period's 2550Q, with the differences (LDG-212).
- Books: the Purchase and Sales Journals show their tie-out row (LDG-181); every book refuses a company the user may not open with a message (LDG-189); the General Ledger book ends with a GRAND TOTAL row (LDG-219); the Inventory book shows opening, in, out, stock count adjustment and closing per item with a TOTAL (LDG-221); a cash book lists a voucher cancelled and reversed the same day, so its TOTAL equals its rows (LDG-223).
- Forms: a new form the role cannot save says so at once, without a Save button (LDG-168, 187, 193, 206). Journal Entry User Remark shows (LDG-190, 210); Accounting Period's Exempted role is hidden and its closed documents are listed once (LDG-211); Stock Reconciliation has Remarks (LDG-192); the Customer and Supplier lists show the TIN (LDG-178, 227); a customer or supplier with the business's own TIN gets a warning (LDG-226); BIR Series list shows the next number (LDG-177); withholding categories and internal doctype names read in words (LDG-182, 169).
- Users: the Owner's user form shows role sets, not the raw role list; the provider box and the Administrator and provider accounts are hidden from the client, and only the provider may change the box (LDG-166, 170). Go-live counts enabled users only (LDG-167). Your plan says "Branches besides the head office" (LDG-172). A switched-off module's URL lands on the Sentire Ledger home (LDG-165).
- UAT cases corrected for the retest (owner approval asked in LDG-153): EX-003, EX-004 (Grand Total is net of the tax withheld; a paid bill shows the Creditors pair), PU-001 and PU-002 (janitorial is a contractor, WC120), PU-010 (period), RP-016, BA-013, BR-009 (no Cancel or Delete button: the banner and the list's Delete), RP-026, RP-035, BR-006 (the form's note), RH-005, RH-006 (Currency and Price List shows after a customer), BA-005, BA-006, BA-001, BR-002, BR-014, JP-001, GL-007, GL-008, the paid-now customer's address (unblocks SL-011), and the refused-message wording (it also accepts the new form note).
- Tests: +6 (test_b82_uat_fixes).

## B80 Frappe v16.60.2 and ERPNext v16.60.0; no update popup for clients (20 Nov 2026)
- Asked by the owner (20 Nov 2026): live showed Administrator "New updates are available: Frappe Framework v16.60.2 (contains 1 security fix), ERPNext v16.60.0".
- Pins: Frappe v16.55.2 to v16.60.2, ERPNext v16.54.0 to v16.60.0 (Dockerfile, scripts/bootstrap.sh, VERSIONS.md). Same major version (v16); the full suite re-runs on the new pins in CI.
- System Settings "Disable System Update Notification" is now forced on (controls.security FORCED_SYSTEM_SETTINGS), so no client site shows the popup and a System Manager cannot turn it back on. Sentire updates every site through a pinned bundle instead.
- Found by the full suite on the new pins: ERPNext v16.60 refuses a group-type Supplier or Customer Group ("Cannot select a Group type Supplier Group"). The import templates fell back to "All Supplier Groups" and "All Customer Groups", so importing suppliers would have failed on live after the update. New master_data.leaf_group picks the settings' group if it is a leaf, else the first leaf group; imports, the QA seed and the full pass use it.
- Tests: +1 (test_b05_security.test_no_update_popup_for_clients).

## B79 Four role sets, the Reports page, the modules note and the full UAT checklist (20 Nov 2026)
- PR: (this one)
- Asked by the owner (20 Nov 2026): every role tested in every module; "where are the Reports?"; "why did the Administrator lose the modules?".
- Built, roles (LDG-150): the role sets are now Owner, Accounting Manager, Accountant and Staff (ph_cas.setup.roles). Bookkeeper is renamed Accountant and Cashier is renamed Staff, in place, so their users follow. Accounting Manager has the books without System Manager. Accountant loses Accounts Manager: it cannot change the chart of accounts or cost centers (new has_permission chart_limit, because ERPNext lets Accounts User add accounts), post with an earlier date, close a period, count stock, file a BIR return (new check in PH Tax Return before_submit) or open an amendment. Staff is kept away from the BIR return doctypes, and it runs only the counter's reports: frappe.desk.query_report.run and export_query are overridden to refuse any other report, and the loose-leaf and year-end book downloads refuse it too. The matrix is docs/uat/ROLE_MATRIX.md.
- Built, reports (LDG-151): a Reports page (/app/ph-reports) lists every report by area: books, statements, receivables and payables, cash, BIR, sales, purchases, stock, projects, assets, manufacturing and audit. It shows only the reports the user's modules and roles allow. The home Reports tile (which used to open only the BIR Audit Trail), the Staff home and the Sentire Ledger sidebar point to it.
- Built, modules (LDG-152): the live site has modules switched off (the open demo's set), which hides their menus for everyone, Administrator included; nothing was lost. A System Manager now sees on Home and on the Reports page which modules are off, with a link to turn them on.
- UAT (LDG-153): ten new workbooks (roles-permissions with 40 cases, reports-page, sales-collections, purchases-payables, journals-periods, bir-returns, books-audit, masters-stock, approvals, setup-company), the seven earlier ones re-issued with the new accounts (Owner A, Accounting Manager A, Accountant A, Staff A, Accountant B), docs/uat/UAT_MASTER_CHECKLIST.md (run order and per-role coverage) and docs/uat/UAT_RUNNER_GUIDE.md.
- Full pass: section roles now covers the four sets (Accountant cannot change the chart; Accounting Manager can; neither adds users); role_homes adds the Reports page per role.
- Tests: +1 (test_b79_roles_reports).

## B78 Print pack for the paper check at 100%, and PDFs at true size (19 Nov 2026)
- PR: #97
- Built: Company > Sentire Ledger > Print pack for the paper check (ph_cas.invoicing.paper_check): one PDF with a cover (print at Actual size, a 100 mm bar drawn by the page engine, the checklist of what to look at on paper) and the latest invoice, credit note, collection receipt and 2307 (on the BIR blank). Each document page is stamped SPECIMEN, PAPER CHECK with a 100 mm bar in its bottom margin; the pages are rendered like the screen preview, so no print is counted and an original stays unprinted. Accounting Managers and System Managers; recorded in the audit trail.
- Found by it: the Debian wkhtmltopdf (unpatched Qt) ignores --disable-smart-shrinking, so every PDF came out at about 77% of true size (the 100 mm bar measured 76.9 mm). The image now installs wkhtmltopdf 0.12.6.1-3 with patched Qt from the project's release, checked against its SHA-256; the build fails if the installed one is not the patched build.
- Full pass: section paper_check (3 steps; one measures the bar in the PDF's drawing commands and must read 100 mm).
- Tests: +1 (test_b78_paper_check).

## B76 Counter and cash: Paid in full now, the company credit card, the Payment Entry counter view (after ECOUNT) (19 Nov 2026)
- PR: #95
- Built: "Paid in full now" and "Paid by" on the Sales Invoice (ph_cas.invoicing.paid_now): the payment is taken on the invoice itself (Is POS with one payment row), so the sale is one document with its BIR invoice serial and no Collection Receipt serial is used; it still posts cash or bank, so it shows in the Cash Receipts Book under the invoice serial, the cash position, the Sales Journal and the 2550Q. Refused for a credit or debit note, a customer who withholds tax, and a mode of payment with no account. The Philippine setup adds the company's credit card: account Company Credit Card under Current Liabilities (no account type, so nothing takes it for a bank; ERPNext's Credit Card payment mode stays for customers paying by card); Record an expense offers it under Paid from and posts the expense to it; the cash books, the cash position and the home's cash card leave it out; the Go-live checklist shows it. The Payment Entry gets the counter view (ph_cas.counter_view, shared with the Sales Invoice), on by default for a Cashier.
- Full pass: section counter (5 steps).
- Tests: +1 (test_b76_counter).

## B77 UAT standard adopted, with the UAT workbooks for B71 to B75 (19 Nov 2026)
- PR: (filled in at merge)
- Built: the Sentire UAT Standard v1.0 (docs/uat/UAT_STANDARD.md, UAT_TEMPLATE.xlsx, the block in CLAUDE.md). What a separate UAT session needs on staging: a build stamp (ph_cas/buildstamp.py: version + a hash of the package's files, written into the image; shown under Help > Your plan and Help > Get help and at /api/method/ph_cas.qa.uat.build_info); UAT accounts seeded with the staging site (Owner, Bookkeeper and Cashier for Company A, Owner and Bookkeeper also for the fresh Companies C and D, a Bookkeeper for Company B), kept to their companies by User Permissions, password STAGING_UAT_PASSWORD; every staging mail goes to the test mailbox (mcrc.business.solutions@gmail.com). The PH Cash Position now refuses a company the user is kept from.
- Workbooks (tools/uat/make_workbooks.py from tools/uat/cases/): go-live (14 cases, LDG-143), record an expense (9, LDG-144), import templates (16, LDG-145), ledgers and cash position (10, LDG-146), role homes (9, LDG-147).
- Tests: +1 (test_b77_uat).

## B75 A home per role set, the counter view, Your plan and Get help (after ECOUNT) (19 Nov 2026)
- PR: #88
- Built: the home page reads the user's role set (ph_cas.setup.roles.role_set). Owner and Bookkeeper: the whole business, with Record an expense and Import from a template among the Create actions. Cashier: Sales, Collections, Cash today and Items; today's sales, cash and bank, receivable and their own unposted invoices; the payables, the VAT and withholding position, the chart and the tax calendar are not shown and not sent. The Sales Invoice counter view: the customer, the lines, VAT, totals, payment and the Philippine sections only; on by default for a Cashier, a Full form / Counter view button for everyone, remembered on the browser; a required field still empty stays in sight. Help > Your plan: the tier, what it allows, what the site uses (users, companies, branches, invoices this month), the dates, and a link to ask the provider for a change. Help > Get help: the tutorials, a message to the provider that starts with the page and the user, and the page details to copy.
- Full pass: section role_homes (4 steps). Checked in a browser as a Cashier and as the owner.
- Tests: +1 (test_b75_role_homes).

## B74 Subsidiary ledgers and the daily cash position (after ECOUNT) (19 Nov 2026)
- PR: #88
- Built: the Accounts Receivable and Accounts Payable subsidiary ledgers in the loose-leaf books (Company > Loose-leaf books, tick "Add the customers' and suppliers' subsidiary ledgers"): one block per customer or supplier with its TIN and the balance forwarded, each invoice, credit note, collection receipt, bill and payment with its BIR reference and a running balance, and the TOTAL, which ties to the receivable (payable) accounts. Same page layout and BIR header as the six books; PAGES.txt counts them. The PH Cash Position report (ph_cas.books.cash): per cash and bank account the day's beginning balance, received, paid out and ending balance, with the total tied to the ledger and an ending balance below zero shown in red.
- Full pass: section ledgers (5 steps).
- Tests: +1 (test_b74_ledgers).

## B73 Philippine import templates and batch edit (after ECOUNT's Excel upload and Change Selected) (19 Nov 2026)
- PR: #88
- Built: ph_cas.imports. Four CSV templates (they open in Excel; Excel files are read too): customers and suppliers with TIN, branch code, payee type and the individual's names, VAT status, government and top withholding agent flags and the supplier's withholding category; items with VAT class, stock, capital good, price, cost and the company's income and expense accounts; opening account balances; open invoices and bills from the old books. "Check the file" reports every line's problems without saving; Import saves only when every line passes, all lines or none. A file imported again updates the same records. Opening balances post one opening Journal Entry dated the cut-over day; receivable and payable totals wait on Temporary Opening until the open items import lists them by customer and supplier, which clears it (the Go-live checklist shows it). Batch edit BIR fields on the Customer, Supplier and Item lists changes many records at once, each through its own validation; the TIN is not batch editable.
- Where: Customer, Supplier and Item lists (Import from a template; Actions > Batch edit BIR fields); Company > Sentire Ledger > Import from a template.
- Full pass: section imports (12 steps).
- Tests: +1 (test_b73_imports).

## B72 Record an expense (after ECOUNT's payment journal) (19 Nov 2026)
- PR: #88
- Built: ph_cas.expense and a "Record an expense" button on the Purchase Invoice list. One dialog: paid to, what for, item or expense account, VAT class, the amount on the receipt, receipt number and date, paid from, mode of payment; Preview shows net of VAT, input VAT, EWT and cash paid without posting; Post makes one paid Purchase Invoice (Is Paid), so the tax engine, the 2307, the books and the returns treat it like any bill. VAT is worked back from the receipt for a VAT supplier on a VATable line; EWT is on the net. The expense account is chosen or comes from the item, never the company default (cost of goods sold). A Cashier may not record one.
- Full pass: section expense (6 steps): 11,200 receipt to net 10,000, VAT 1,200, EWT 500, cash 10,700 with the GL checked; a non-VAT fare; the Purchase Journal, Cash Disbursements Book and the quarter's 2307; the Cashier refused; no account refused.
- Tests: +1 (test_b72_expense).

## B71 Go-live and opening balances (after ECOUNT's starting balance) (19 Nov 2026)
- PR: #87
- Built: ph_cas.golive. Company "Go-live date". Opening entries dated the cut-over day (the day before go-live) need no back-date reason: the opening Journal Entry (Entry Type Opening Entry, Is Opening Yes) for account balances and, as party rows on Debtors and Creditors, what each customer owes and each supplier is owed; and the opening stock count (Stock Reconciliation, purpose Opening Stock). An opening entry on any other day, or before the go-live date is set, is refused. Opening invoices and bills (Is Opening on a Sales or Purchase Invoice, ERPNext's Opening Invoice Creation Tool) are refused with a pointer to the opening entry, because an old invoice must not take a BIR serial, carry VAT again or enter the sales journal and the returns. Company > Sentire Ledger > Go-live checklist: COR details, Philippine setup, tax rules confirmed, go-live date, inventory method, bank account, users with a role set, opening balances (posted, trial balance even, Temporary Opening cleared), old open items, opening stock (perpetual: the count; periodic: the count and the inventory account).
- Full pass: section go_live (11 steps): refusals, the opening entry, the opening stock count, AR and AP from the opening entry, collecting an old balance against it, the checklist complete, the trial balance on the cut-over day.
- Tests: +2 (test_b71_go_live).

## B70 Tutorials in learning order: 57 videos benchmarked on ECOUNT (19 Nov 2026)
- PR: #86
- Built: the owner-approved list from the project doc claude/ledger-tutorials-proposal-2026-11-19.md. tutorials.json now holds 57 videos (was 38) numbered V01 to V57 in learning order: Get started, Your records, Opening balances, Selling, Buying, Stock and operations, Checks, Period close, BIR returns, Administration. Every video is 90 s or less (the long ones split: COR details and the PH setup, invoice and correction, General Ledger and audit trail, collection and 2307 received, payment and 2307s issued, quarterly and annual income tax, approval setup and use, item you sell and item you buy). 17 new topics fill the gaps (role sets, inventory method, bank account, assets, opening balances, old invoices and bills, quotation, SC/PWD, credit and debit notes, 2307 received and issued, audit trail, AR/AP, month close, year-end count). Each video carries section, menu_path (shown on screen) and ends_on (the report or document it must end on); PH Tutorial Video shows them. seed() removes records whose code left the file unless a video was uploaded (none were). Every onboarding card and form Help link keeps a video.
- Tests: test_b51 updated (57 videos, learning-order codes, 90 s cap, every row has section, menu path and ends_on, one video per card, retired codes removed unless uploaded); test_b34 unchanged.
- Left out: recording the videos (LDG-45, parked); the ECOUNT features in the proposal doc wait for the owner's pick.

## B69 Inventory method and year-end count, role sets, walk-in SLSP row, report tie-outs (17 Nov 2026)
- PR: #81
- Built: the owner's answers to QA pass 4. (1) D7 revised: Company "Inventory method" (Periodic default, or Perpetual), chosen before the first stock movement and locked after; ph_cas.stock.periodic posts the year-end inventory adjustment of a periodic company from its count (counted stock value minus the inventory account, to cost of sales; a rerun posts only what remains), with a Company menu button that previews before posting. (2) Walk-in buyers (no TIN) go into the SLS as one row: 000111222, GENERIC CUSTOMER, the seller's city and ZIP. (3) Role Profiles Owner, Bookkeeper, Cashier (ph_cas.setup.roles), written directly so setup never leaves a queued lock; the Cashier marker role keeps a counter user off bills, journal entries, suppliers and purchasing (has_permission), collections allowed. (4) Full pass: sections inventory_tracking (periodic year with hand figures: bought 100 x 250, sold 30, counted 68, adjustment 17,000, cost of sales 8,000 = 1702-RT item 30; perpetual receipt, sale, count and the stock-to-ledger tie), roles (each profile does its work and is refused what it should not do), reports (the six books tie, journals and registers equal the documents, AR and AP equal open documents and the control accounts, trial balance, P&L profit equals the ledger, balance sheet balances, 2550Q, 1601-EQ and 1702-RT equal the books, book-to-tax explains everything, SC/PWD and 2307 reports equal the documents, calendar, module reports carry their documents, the SLSP generic row, the audit trail per document).
- Tests: +4 (test_b69); test_b04 D7 test rewritten for the inventory method.
- Assumed: Generic Customer address is the seller's city with ZIP; Owner includes Auditor; Bookkeeper has no Accounting Manager (back-dating approvals and stock counts stay with the Owner).

## B68 QA pass 4 on staging: return-first SLSP and calendar, asset from its bill (17 Nov 2026)
- PR: #79
- Built: the full pass ran on staging section by section (165 steps). Two more defects, both from the older PH Tax Return Figures record standing beside the 2550Q return: (1) the SLSP purchases file took the input tax attributable to exempt sales from that record (53B), which can be stale; it now reads item 53 of the 2550Q return (filed, else the draft) and falls back to the record; (2) the compliance calendar counted only that record, so a return in progress showed "nothing computed"; a draft return now counts as computed. Runner: the capital-good purchase now creates its Asset from the bill (auto-create, naming series, location), and the stock check reads the Stock Ledger (Stock Balance is a background prepared report).
- Tests: +1 (test_b67: the SLSP and the calendar read the 2550Q return).
- Left out: owner questions in the QA pass 4 report.

## B67 QA pass 4: every function on staging, and the fixes it found (17 Nov 2026)
- PR: #78
- Built: ph_cas.qa.fullpass, a staging-only runner (call_method ph_cas.qa.fullpass.run, section by section) that drives every function as the signed-in user with no ignore_permissions: four taxpayer companies set up from scratch (VAT and non-VAT sole proprietors, VAT and non-VAT corporations), purchasing (PO, receipt, bill, EWT on goods, professional fees and rent, payment, 2307s), sales (invoice, serial continuity, manual number, the Annex B refusals, credit and debit notes, collections, SC/PWD, government sale, 2307 received, the six books, audit trail), tasks and assignments, inventory (receipt, transfer, stock sale, delivery note, count, D7), projects (tasks, timesheet billing, progress billing, costing), assets (category, capital-good purchase, depreciation schedule, opening asset, register), quality (procedure, goal, inspection gate on a receipt, non-conformance, action, meeting, review), CRM (lead to invoice), support (issue lifecycle, warranty claim, maintenance visit), the seven industry presets and an industry transaction each, and every BIR form with its SLSP, SAWT, QAP and alphalist files.
- Fixed: (1) a non-VAT seller's invoice carried zero Output VAT and four Input VAT rows: ERPNext's "add taxes from item tax template" copied the accounts of the line-scope templates; the setting is now forced off with the other locked Accounts Settings (the engine books VAT itself). (2) A draft 2307 never caught up with bills posted after it was made, and generating the quarter again skipped it; a draft now rebuilds its lines on every save and generate_quarter refreshes drafts. (3) BIR Audit Trail: a date without a time now means the whole day. (4) The QA admin gains Sales Master Manager, Purchase Master Manager, Projects User, Manufacturing User and Maintenance User (suppliers and item prices were refused).
- Tests: +5 (test_b67_qa_pass4: the setting is forced, the audit trail day, the companies, purchasing and sales sections pass with no VAT rows on non-VAT invoices, a draft 2307 follows the bills); test_b26 reissue check updated for refreshed drafts.
- Left out: owner questions in the QA pass 4 report (walk-in buyers in the SLSP).

## B66 Owner's decisions D1 to D11, POS and payroll (LDG-46) (17 Nov 2026)
- PR: #77
- Built: docs/DECISIONS.md updated with the owner's answers of 17 Nov 2026. Confirmed: D1, D2, D4, D5, D6, D8, D9 (Sentire Ledger), D10 (Christian R. Canlubo, Owner), D11 (EIS after launch, LDG-58), payroll from Sentire Payroll (LDG-119); POS confirmed by answer 10 of 14 Nov. D3 (waits on LDG-54) and D7 stay recommended. D10 in the app: the branding pass on every start fills the PH CAS Settings signatory and position where blank, so every client's joint sworn statement names him; an edited value stays. D9 in the app: the Company form's action menu carries the product name instead of "PH CAS"; the user guide, runbooks and CONFORMANCE row 4 follow. Internal code names (ph_cas, the PH CAS module, PH CAS Settings) stay, since renaming them renames database tables.
- Tests: +3 (test_b66_decisions: signatory filled in and printed on the sworn statement, an edited signatory kept, no open decision left).
- Fixed on the way: the test runner's stand-in manual invoice number (T-serial) collided between branches, since every branch's series starts at 1 (test_b09 failed depending on order); it is now T-branch-serial.
- Assumed: position "Owner"; the signatory's TIN is left for the owner to fill in on the settings.
- Left out: nothing in scope.

## B65 Demo signups followed up within 24 hours (LDG-57) (16 Nov 2026)
- PR: #75
- Built: the owner's answer to LDG-57 is the Sentire Helpdesk with Mark following up; the Helpdesk is not built yet, so this is the stand-in. Each demo signup is mailed to DEMO_LEADS_OWNER (site config demo_leads_owner, else the Administrator's address) with Reply-To set to the lead, a subject that says to follow up within 24 hours, and a signed "mark as contacted" link (ph_cas.hosting.demo_access.mark_contacted, HMAC with the site's encryption key). The hourly job remind_uncontacted_leads sends one reminder for a signup not marked contacted after 20 hours. Follow-up state is private/files/demo-followup.csv, outside the database, so the nightly demo reset keeps it. DEMO_LEADS_WEBHOOK stays for the Helpdesk once it exists.
- Tests: +2 (test_b65_demo_leads: listed, reminded once, marked contacted by the signed link, a forged link refused; the owner address).
- Assumed: one reminder is enough; the CSV is the lead list until the Helpdesk.
- Left out: the Helpdesk integration (LDG-57 follow-up once the Helpdesk is built).

## B64 Income tax returns take the Company's options and the filed quarters' payments (LDG-120, LDG-121, LDG-122) (16 Nov 2026)
- PR: #74
- Built: found in QA pass 3 on staging (income_year and individual_year scenarios).
  - LDG-120: the PH Tax Return context (engine.TAXPAYER_FIELDS) left out the Company's income tax options, so in the app every 1701Q, 1701, 1701A, 1702Q and 1702-RT ran on the defaults: no MCIT, 25% even for a small corporation, itemized deductions even under OSD, graduated rates even under the 8% option. The six fields are now in the context (and the filed snapshot). On staging, Tala Trading's 1702Q Q1 showed MCIT 0 where 6,000 was due on the schedule.
  - LDG-121: 1702Q Schedule 4 Items 2 and 3, 1702-RT Items 45 and 46, 1701Q Item 56, 1701 Part VII Item 2 and 1701A Item 58 read the old PH Tax Return Figures, which the PH Tax Return flow never writes, so they were always 0 and overstated the tax payable. They now add the net payable (Item 20 of the 1702Q, Item 28/63 of the 1701Q) of every filed return of each earlier quarter, amendments included; a 1702Q quarter that took MCIT counts under MCIT. A quarter without a filed return gives a warning.
  - LDG-122: the 1701 forms take the ATC from the Company (individual type, 8% option, mixed income) instead of asking.
  - The individual_year scenario carries a contact number and email.
- Tests: +2 (test_b64_income_feeds: 1702Q, 1702-RT and 1701Q built through PH Tax Return from the QA scenarios, with Q1 filed and Q2 not).
- Assumed: payments are the net payable before penalties of each filed return; an overpayment counts as 0 paid.
- Left out: nothing in scope.

## B63 Staging scenarios for income tax QA (QA pass 3) (16 Nov 2026)
- PR: #73
- Built: two staging scenarios for the income tax returns. income_year: every month of the year before the current quarter on the QA company, with VATable sales of 250,000, cost of sales 150,000, office expenses 50,000 and representation 5,000 a month (journal entries; a Representation and Entertainment account with its EAR tax class), a 3,000 income tax 2307 from the customer each quarter, and MCIT in force (operations from 2020). individual_year: QA Sole Proprietor, an individual on graduated rates with OSD, sales of 100,000 a month over the same months. Both add nothing twice. The QA connector lists them.
- Tests: +1 (test_b63_qa_income: the 1702Q and 1701Q figures worked out by hand); B54 lists the new scenarios.
- Assumed: nothing new.
- Left out: nothing in scope.

## B62 Alphalist files verified against the BIR's own module 7.4 (LDG-48, LDG-51) (16 Nov 2026)
- PR: #72
- Built: installed the BIR Alphalist Data Entry and Validation module 7.4 under Wine, typed an invented withholding agent and payees into its Data Entry module, and kept the files it generated as golden files (ph_cas/tests/golden/alphalist/: QAP July and September 2026, 1604-E 2026, SAWT for the 2550Q, MAP for the 1600-VT); all pass its Validation module. The writers now match them byte for byte. What the module showed and the writers now do:
  - Branch code: 4 digits. The validator rejects the 5-digit code B48 wrote on every line ("Invalid Length in Branch of Withholding Agent", "Invalid length of Payees Branch Code"), so dat_branch drops the leading zero and refuses a code that does not start with 0. This supersedes owner answer 8b (DECISIONS.md).
  - QAP: one file per month of the quarter, each with that month's rows, as the module writes it; no file for a month without payees (the validator rejects a header with no detail). Schedule 2 lines only when there are exempt payees. The PH Tax Return's "Generate QAP" writes up to three PH Alphalist Files and links the last.
  - Blank names are empty unquoted fields, names with a value are quoted (QAP, 1604-E, MAP; the MAP no longer leaves names unquoted). MAP rows sort by name.
  - Rates are the ATC's (the invoice's EWT rate), not tax over income, which printed 2.01 for a 2% ATC on 33.33.
  - Schedule 2 ATCs: IC010 (non-individual) and II012 (individual), the payee's income tax ATC; DI900 and EI900 are gone.
  - Names: the validator rejects ' & , and Ñ; clean_name turns & into AND, Ñ into N, drops apostrophes and turns commas into spaces. An individual withholding agent's SAWT header now carries the person's names.
  - SAWT: the 1702-RT (and 1702-EX, 1702-MX) files under 1702, the only annual corporate SAWT the module lists (it wrote H1702RT before). No SAWT, MAP or 1604-E file when there are no rows: the SAWT button says so, filing leaves no file.
  - Files built through the real code path (QAP for October and November 2026, 1604-E, SAWT 2550Q and 1702Q, with names containing &, a comma, Ñ and an apostrophe) pass the validator. The MAP passes except its WV080 line ("ATC is invalid"): the unpatched 7.4 lacks the digital-services codes; the BIR's ATC patch adds them and was not run here.
- Tests: +10 (test_b62_alphalist_golden: five byte-for-byte golden files, monthly QAP from the books with the ATC rate and no empty month, no empty files, name cleaning); B09, B27, B28, B55 and G2 follow the verified format.
- Assumed: the MAP's name order, seen on two rows; the 1604-E with exempt payees but no withheld payee (not generated by the module).
- Left out: the BIR's ATC patch for 7.4 (downloaded from bir.gov.ph, not run); the validator's eSubmission copy (its encryption step does not run under Wine, and the CAS never writes it).

## B61 No Item 5 question on the 1702Q and 1702-RT (16 Nov 2026)
- PR: #71
- Built: found on staging after B60. The 1702Q and 1702-RT still asked "Which ATC applies (Item 5: IC055)?", a question B60 made meaningless, since Item 5 now follows the higher of MCIT and the regular tax. The question and the old "5 ATC" input are gone from both forms; "ATC chosen" (to take the regular rate) and "Other ATC" stay.
- Tests: 350 on main (test_g3 checks the question is gone).
- Assumed: nothing new.
- Left out: nothing in scope.

## B60 Item 5 takes one ATC, the higher tax by default (16 Nov 2026)
- PR: #70
- Built: the owner's rule for Item 5 of the 1702Q and 1702-RT. One ATC is marked: IC055 when MCIT is higher than the regular tax, else the regular ATC. The taxpayer may still choose the regular rate (new input atcChoice), and the tax due (1702Q Schedule 2 Item 13 and Item 14; 1702-RT Item 43) follows the ATC chosen. Both computations stay on the return whichever ATC is marked: Schedule 2 (regular) and Schedule 3 (MCIT) on the 1702Q, Items 41 and 42 on the 1702-RT. The excess MCIT credit (1702Q Item 15) applies only when the regular rate is chosen. The 1702-RT names the regular ATC (new input regularAtc, default IC010) when the regular rate is chosen. B59 had marked both boxes, as eBIRForms' 1702Qv2018C needs both to compute Schedule 3.
- Tests: 350 on main (+1, test_g3: the higher tax by default, the regular rate by choice, both computations kept).
- Assumed: nothing new.
- Left out: nothing in scope.

## B59 Every return computed the way eBIRForms computes it (16 Nov 2026)
- PR: #68
- Built: LDG-49. eBIRForms v7.9.6.2 itself was run. BIRForms.exe unpacked its forms under wine, and each form ran in Chromium with a shim for what mshta and JScript provide: FileSystemObject reads of the package's xml folder, alerts, Date#getYear, and Number#toLocaleString. The test inputs were typed in, and every computed field was read back and compared with Ledger. The harness is in tools/ebirforms-parity (README there); the figures it recorded are in ph_cas/tests/data/ebirforms_parity.
- What the run found and what changed, form by form:
  - 2550Q and 2551Q: centavos, not whole pesos. The papers have centavo boxes and eBIRForms keeps centavos.
  - 2550Q:
    - 44B, 45B and 46B are 12% of A, with a feed warning when the books' input tax differs.
    - Items 39 and 52 come from Schedule 1 only. Col G is E / remaining life x 3 and Col H is E - G; purchases are up to 31 Dec 2021.
    - Item 53 comes from Schedule 2 (exempt / total sales x the input tax not directly attributable). Items 16 and 17 come from Schedules 3 and 4 only.
    - Item 15 carries Item 61. Item 26 is the penalties alone when there are excess credits.
  - 2551Q:
    - The ATC dropdown index followed a short list (PT120 and PT130 landed on PT101 and PT102). It now follows eBIRForms' 23 lines, including PT010 at 1%, and the rate must be the one eBIRForms lists.
    - Item 16 only on an amended return.
    - An individual on 8% files a zero return.
  - 0619-E, 1601-EQ and 1600-VT:
    - The previously remitted amount counts only on an amended return.
    - Tax withheld is base x the rate eBIRForms lists for the ATC (ph_cas/forms/data/ebirforms_atc.json, private and government lists).
    - 1601-EQ: a need when Item 24 (other payments) is used, since eBIRForms has no such line.
    - 1600-VT: Item 27 is the penalties alone on an over-remittance.
  - 1702Q:
    - The export wrote eBIRForms' pre-2018 1702Q layout. It now writes the 1702Qv2018C file: field for field, in the order the form saves them, with file name TIN-1702Qv2018C-YYYYQn.xml.
    - Item 5 is IC055 plus the regular ATC at its rate (new input regularAtc).
    - Schedule 3 is open only with MCIT, one line per quarter to date, at 1% from July 2020 to June 2023.
    - No regular tax on a loss to date. Item 15 only when the regular tax exceeds MCIT. Schedule 4 Item 6 only on an amended return. Item 25 is the penalties alone on an overpayment.
    - The print map follows the new keys and now prints Schedule 2 Items 1 to 9 and 11 and Schedule 1 Items 8, 11 and 12, which the old map left blank.
  - 1701Q, 1701A and 1701:
    - The ATC sets the rate (II015, II017 and II016 are 8%), and only that rate's schedule is filled.
    - Under OSD, cost of sales closes at 0 (40% of gross sales).
    - No 250,000 reduction for II016 or for a compensation earner.
    - 1701Q Item 59 only on an amended return.
    - 1701 Part VII Items 3 and 4 split creditable tax withheld into the first three quarters and the fourth (feed split).
    - 1701 marks the compensation earner box when there is compensation.
    - 1701 Schedule 2 Item 7 always carries the tax on compensation.
    - 1701 Item 31 is the penalties alone on an overpayment; on the 1701A, Item 29 is Item 24 on an overpayment, as eBIRForms does.
  - 1702-RT:
    - Item 38 only under OSD. MCIT is 1% from July 2020 to June 2023.
    - Schedule 3 is filled only on a net operating loss.
    - Item 21 is the penalties alone on an overpayment, and the overpayment boxes are marked only then.
- Result: 3,425 figures in 23 scenarios match eBIRForms field for field. One eBIRForms defect is recorded, not copied: the 1702-RT form recurses without end on Schedule 3 and stops half way, so Ledger keeps the form's own rule (Schedule 3 zero when there is no loss).
- Tests: test_b59_ebirforms_parity (every fixture, every figure). Updated test_g1, test_f1, test_g3 and test_f0 for the rules above. test_b18 no longer depends on the sales already on the test site.
- Assumed: an annual return is tested for a year that has ended; eBIRForms clears a year still running.
- Left out: the Portal's own 1702Q map and export still follow the pre-2018 layout. The Portal is another product, so this is reported, not changed here.

## B58 The owner accepted the tax rules (16 Nov 2026)
- PR: #67
- Built: LDG-47. The owner, MCRC Tax and Accounting Services, accepted all 74 rules in the tax rules catalogue without a signed document. ph_cas/setup/data/rules_acceptance.json lists every rule_id with who accepted them and when; ph_cas.tax.rules.apply_acceptance() runs on install and migrate after seed() and moves each listed rule still in draft to confirmed, with "Accepted by ... on ..." as its sign-off reference and one audit event. A new rule added to tax_rules.json later stays draft until the owner adds it to the acceptance list, so production keeps refusing unaccepted rules.
- Tests: 344 on main (+1; the draft-rule tests in test_b11 and test_b31 now use rules of their own).
- Assumed: nothing new.
- Left out: nothing in scope.

## B57 Cash books net each account within a voucher (16 Nov 2026)
- PR: #72
- Built: found on staging with a POS cash sale: the Cash Receipts Book showed the receivable raised and settled inside the same invoice as both an other debit and a credit (Debtors 1,620.00 each way). The cash books now net each account within the voucher (books.common.net_by_account), so a cash sale reads cash 1,620.00 against sales 1,500.00 and output VAT 120.00, and a collection reads cash and withheld tax against the receivable.
- Tests: +1 (test_b55_qa_fixes).
- Assumed: nothing new.
- Left out: nothing in scope.

## B56 Fixes from the second staging QA pass (16 Nov 2026)
- PR: #88
- Built: LDG-112: output VAT and input VAT sit only on the lines they belong to. ERPNext rebuilds each line's tax map from its Item Tax Template on every save, so ph_cas.tax.line_scope gives each company its own templates ("PH No VAT", "PH Input VAT goods", "services", "capital") marking the VAT accounts a line does not carry as not applicable, and the tax engine puts one on each line by its VAT class and kind; a template a person chose is left alone. LDG-115: recording an event asks for the commit, so downloads and exports (GET requests) keep their audit row. LDG-116: a PH Approval Chain left blank for every company is no longer filled with the saving user's default company. LDG-117: the 1604-E takes item 8A from Company > Top withholding agent; BIR Returns gains Generate SAWT (.dat) on the 2550Q, 2551Q, 1701Q, 1702Q, 1701 and 1702-RT, and the SAWT accepts the 1702-RT name; the demo company has a contact number and email. The QA scenarios add nothing twice when run again. Tests no longer depend on the bench's product name, user state or the QA scenario's commits.
- Tests: +5 (test_b55_qa_fixes).
- Assumed: nothing new.
- Left out: nothing in scope.

## B55 Fixes from the first staging QA pass (16 Nov 2026)
- PR: #72
- Built: the first QA pass on Ledger Staging through the QA connector (sales, credit note, collection with CWT, bills with EWT, 2550Q, 2551Q, 0619-E, 1601-EQ, books, locks, approvals, modules, tutorials). Fixed what it found. LDG-107: the print page and the PDF download are GET requests and Frappe commits only POST, so print records and print events were rolled back, while the desk's on-screen preview (a POST) counted as the first print; a print now asks for the commit, and the screen preview records nothing and is marked PREVIEW ON SCREEN with what the next print will carry. LDG-108: the seller address on invoices and the BIR header comes from Company > Registered address (per COR) with the ZIP code, then a linked Address. LDG-109: 1601-EQ items 20 and 21 are item 14 of the filed 0619-E of each month, with a warning when none was filed or it differs from the books (both the BIR Returns engine and the dashboard figures). LDG-110: a customer payment allocated in full but received net of the tax withheld books the withheld tax. LDG-111: the cash books show the other account debited or credited with the cash, so each receipt and disbursement balances on its face; the General Journal and General Ledger name the document (Sales Invoice, Credit Note, Debit Note, Collection Receipt). LDG-114: a computed return past its due date and not filed is "OVERDUE, computed, not filed" and stays on the Home due list; the compliance calendar starts at the first posting in the system, so earlier periods are not listed as overdue; the due list and the BIR links on Home open BIR Returns. LDG-113: "ACCN (not yet issued)" in place of a blank line; the posted-field refusal on an issued invoice points to credit and debit notes; staging shows "(staging)" after the product name; an upload on staging says plainly that staging only plays videos. The QA connector's get_print now goes through the print page, like the Print button, with preview: true for the on-screen preview.
- Tests: +8 (test_b55_qa_fixes).
- Assumed: the on-screen preview is not a print; only a render that can reach paper or leave the system is.
- Left out: LDG-112 (the per-line tax breakup on the form spreads output VAT over exempt lines; totals, ledger and print are right).

## B54 Staging QA site and its connector (16 Nov 2026)
- PR: #88
- Built: the owner's request, after the Payroll pattern. PH_STAGING=1 makes the container a staging site (docs/STAGING.md): on first start the site is seeded by ph_cas.qa.api.seed (demo VAT company, every module on, the QA admin qa.admin@sentire.solutions with STAGING_ADMIN_PASSWORD) and kept as the QA snapshot; every later start restores it (`ledger-site reset-staging`). The entrypoint refuses PH_STAGING with PH_PRODUCTION or PH_DEMO. ph_cas/qa/mcp_server.py is an MCP server (streamable HTTP, JSON responses, standard library plus requests) on QA_MCP_PORT, reached at /mcp/<QA_MCP_SECRET>; it signs in as the QA admin and calls the site's own API (12 tools: staging_status, list, get, create, update, submit, cancel, call_method, run_report, get_print, seed_scenario, api_request), refuses sign-in and password endpoints, allows 120 calls a minute and logs one JSON line per call. It refuses to start unless PH_STAGING=1, the secret has 32 characters or more and the site config says ph_staging_site. Scenarios: vat_quarter and non_vat_company.
- Tests: +6 (test_b54_staging). The connector was also run against the bench: every tool answered, an invoice got its BIR serial on submit, the cancel was refused by the Annex B lock, and both scenarios posted.
- Assumed: staging keeps no volumes, so a redeploy rebuilds it from nothing.
- Left out: nothing in scope.

## B53 Notice of third-party custody; the first-return step opens BIR Returns (16 Nov 2026)
- PR: #72
- Built: LDG-98: the registration pack gains 03a_Notice_of_Third_Party_Custody.txt, the client's notice to its RDO that the provider keeps its books and records in electronic form (RR 9-2009 Sec. 6.3.1; RDO answer 3): taxpayer and RDO from the Company, custodian, address and signatory from PH CAS Settings, and a new PH CAS Settings field "Where the records and backups are kept" for the data centre and backup site in the Philippines (left as a visible blank until it is set). Ten-year retention, production to the BIR on request, and the hand-back when the service ends. The Sentire Ledger guide's step "Run the 2550Q figures" becomes "Compute your first BIR return" and opens a new BIR Return (PH Tax Return) instead of Tax Return Figures, as tutorial V04 shows; Home's "Compute a return" opens BIR Returns too.
- Tests: +2 (test_b30_pack custody notice, test_b34 first-return step).
- Assumed: the place of custody is filled in once the Philippine hosting is decided (LDG-54).
- Left out: nothing in scope.

## B52 Module switches, industry presets, module-aware demo (16 Nov 2026)
- PR: #88
- Built: M5.2 (LDG-83, LDG-84, LDG-85). PH Modules (Settings > Modules): one switch per optional module (Selling, Buying, Stock, Manufacturing, Projects, Assets, Quality, CRM, Support); Accounts, BIR and the Home page are always on. A module that is off is hidden, not removed: ph_cas.modules prunes the boot (dock, sidebars and links to its doctypes and reports in the sidebars that stay, workspaces, the search bar's can_read, can_search and can_create, allowed reports) and public/js/modules.js leaves its steps out of the onboarding guides and stops a route to it before it renders, with a notice. Records, roles and permissions are not touched, so switching a module back on restores everything. Which doctypes and reports belong to a module is data (modules/data/modules.json: the Frappe modules' doctypes and reports, plus extra, minus keep); shared masters stay whatever is off (Customer, Supplier, Item, Item Price, Price List, Warehouse, the settings pages). Industry presets in modules/data/presets.json (Services, Retail and trading, Restaurant and food, Manufacturing, Construction and projects, Professional practice, Other); picking an industry on the Modules page offers its set, and a new onboarding step "Choose what you use" opens the page. `ledger-site new --industry "<industry>"` applies a preset at creation; the open demo starts with Selling and Buying (demo seed, once); the usage report carries modules_on and the PH Subscription record shows it. A site that never saved PH Modules has everything on, so existing sites look the same until someone chooses.
- Tests: +8 (test_b52_modules).
- Assumed: hiding is a convenience, not a security boundary: a user who knows a record's name can still open it through the API, as the roles allow.
- Left out: the full-text search page (Search for "x" in every document type) still lists records of hidden doctypes.

## B51 Tutorial videos play inside Sentire Ledger, from our own server (15 Nov 2026)
- PR: #72
- Built: the owner's ruling: the tutorials are not uploaded to YouTube; they are kept on our own server and played in the system. ph_cas.tutorials: PH Tutorial Video (V01 to V38, seeded from tutorials/data/tutorials.json on install and migrate: title, length, the onboarding steps whose card plays it, the forms that offer it) with its child PH Tutorial Video Step. The files live once, in a private bucket (tutorials/<code>/video.mp4, captions.vtt, poster.jpg), configured by the PH_VIDEOS_S3_* environment variables; a small signature-version-4 client (no boto3) signs playback links for six hours and the upload requests. Upload: System Manager, Upload videos on the list or Upload files on a record; the browser sends each video in 8 MB pieces through the site to an S3 multipart upload, captions are converted from SRT to WebVTT, thumbnails to a JPEG at most 1280 wide; nothing is kept on the site. The captions are served by the site so the player stays same-origin. Player: the onboarding widget's step shows our thumbnail and a native video player (patched from public/js/tutorials.js); Home's checklist has a Watch button; forms get "Watch: <title>" menu items; the record shows the player. Every ERPNext intro_video_url is cleared on migrate, so no card loads YouTube. Daily job and Check the server keep each site's records in step with the bucket.
- Tests: +8 (test_b51_tutorials: the AWS signature test vectors, path-style and internal endpoints, the catalogue, file names and captions, upload in pieces then signed playback, a missing piece, upload permission); test_b34 checks that no card keeps a YouTube link.
- Assumed: one shared bucket for every client site (owner's choice); uploads through the site (owner's choice).
- Left out: transcoding. The exports are H.264 with the index at the front, so they stream as they are.

## Role renamed: Accounting Manager (15 Nov 2026)
- PR: #88
- Built: the owner's ruling: the role "PH Accounting Manager" is now "Accounting Manager" (not "Approver"; only "PH" is dropped). A pre-model-sync patch (ph_cas.patches.v0.rename_accounting_manager_role) renames the role in place on existing sites, so every user who holds it and every permission row that names it follow; setup runs the same step if the old name is still there. Code, DocType and report permissions, the home page and the docs use the new name.
- Tests: +2 (test_role_rename).
- Assumed: nothing new.
- Left out: the build log keeps the old name in entries written before the rename.

## 2307 prints only on the BIR form (15 Nov 2026)
- PR: #52
- Built: the owner found tutorial V14 showing the B26 HTML look-alike of the 2307 instead of the BIR's own form. The look-alike (print format PH BIR 2307) is now disabled and no longer the default print format of PH 2307 Issued; migrate disables it on sites that have it. The certificate prints only on the BIR's January 2018 ENCS blank, filled the way every BIR form is filled (ph_cas.forms.f2307 on the F0 engine, the method of the MCRC Accounting Portal): from the Print on BIR form button, the toolbar Print and Ctrl+P alike. The registration pack's specimen is now 08_Sample_2307.pdf on the BIR blank.
- Tests: test_b26_2307 checks that the certificate prints on the BIR blank and that the look-alike is disabled (replaces the look-alike's face test).
- Assumed: nothing new.
- Left out: the look-alike stays in the repository, disabled, so older prints can be traced; it can be deleted later.

## Accountant, not CPA; date of incorporation required (15 Nov 2026)
- PR: #88
- Built: the owner's tutorial notes 1 and 2. A non-individual company with a TIN must have its date of incorporation or organization (the 1702-RT and 1702Q print it): Company validation refuses a save without it, and the field is marked required on the form once the TIN is entered; before the TIN (the setup wizard's first save) and for individuals it stays optional. The demo-access company is created with a date. The user's reviewer is "your accountant", not "the CPA" (not every accountant is a CPA): the unconfirmed-rule refusal, the Tax Rules onboarding step, a tax rule note and code comments. Supplier names that are themselves CPAs are unchanged.
- Tests: +1 (TestIncorporationDate in test_b48_rdo_answers); the test bootstrap gives the test company a date.
- Assumed: an existing company without the date is asked for it at its next save.
- Left out: nothing.

## B50 Loose-leaf books in the registered format (15 Nov 2026)
- PR: #51
- Built: ph_cas.books.looseleaf, the six books a client prints and binds when it keeps loose-leaf books instead of registering the CAS: Sales Journal, Purchase Journal, Cash Receipt Journal, Disbursement Journal, General Journal and General Ledger, laid out like the JuanTax exports the owner supplied (the format BIR has accepted on Form 1900 permits). Every page repeats the title and the header block: owner's name and address, VAT Reg. TIN (or Non-VAT Reg. TIN, or TIN) with the 5-digit branch, period, name of user, run date, page x of y, application software, permit to use number (and validity date on the General Ledger). Columns and their names follow the JuanTax books, with a TOTAL row; the General Ledger runs account by account with Opening Balance, entries, Total and Net Movement, and a grand TOTAL. The Cash Receipt and Disbursement Journals split each payment into the VAT columns of the invoices it settles, in proportion to the amount applied; anything unapplied goes in the first column (AMOUNT); tax withheld (on the receipt, or on the supplier invoice) goes in DISCOUNT, so GROSS less DISCOUNT is the cash. Both formats: Excel (numbers and dates are real numbers and dates, references stay text with their leading zeroes, legal landscape, one sheet with a page break and repeated header per page, rows at most two lines high) and PDF (legal landscape, header and footer on every page). The two have the same page count; PAGES.txt in the download gives each book's pages for the sworn statement on the bound volumes. Company > PH CAS > Loose-leaf books (Excel / PDF); new Company fields: loose-leaf permit to use number and date (the ACCN is printed when there is no permit).
- Tests: +4 (test_b50_looseleaf).
- Assumed: the JuanTax layout is the registered sample format (owner, 15 Nov 2026). Not copied from it: amounts and dates stored as text, invoice numbers that lose their leading zeroes, gross purchases net of withholding, "CUSTOMER" headings on the supplier books, the reversed balance sign in the ledger, and a General Journal without the header block. Cancelled invoices stay out of the journals; the General Ledger shows a cancelled voucher and its reversal, as the ledger holds both.
- Left out: binding, the sworn statement and the ORUS submission are the client's (the page counts are given for them).

## B49 Release method: major versions and the quarterly notice (15 Nov 2026)
- PR: #88
- Built: the owner's release method (LDG-99) in docs/DECISIONS.md and docs/runbooks/upgrades.md; the release log ph_cas/setup/data/releases.json with its rules, left empty (the owner: no versioning until the product is done; the first entry will be 1.0.0, and ph_cas.__version__ stays 0.1.0 until then); ph_cas.ops.releases: the log check (classes, increasing versions and dates, a major release starts the next major number, a minor one stays within it) and the combined quarterly notice of minor enhancements per client (RMO 9-2021 V.9), from Company > PH CAS. One container per major version; the runbook says how a client moves after filing.
- Tests: +5 (test_b49_releases).
- Assumed: the notice goes out in the first two weeks after the quarter (firm policy; the RMO sets no deadline); a quarter without a minor release needs no notice.
- Left out: the second container appears only with version 2.

## B48 The owner's answers to the RDO questions (15 Nov 2026)
- PR: #72
- Built: every answer recorded in docs/DECISIONS.md ("RDO questions answered by the owner"). 1: Company flags for e-commerce and for the EIS, with a warning when a non-micro e-commerce company is not on the EIS. 2: Sales Invoice "Manual invoice number", typed by the user, required at submit and unique per company and document type unless the company is on the EIS; the invoice prints it as the number with the BIR serial below as the system control number. 5: the year-end pack adds FILE-LAYOUT.txt (each field's name, type, width and decimals, as RR 16-2006 asks) and the transmittal lists each file's type and the USB label (RMO 9-2021). 7: ten years everywhere (already the backup and offboarding figure; runbook updated). 8b: alphalist DAT files carry the full 5-digit branch code with its leading zeroes, in records and file names. 8c: the unknown-ATC report is empty, since the BIR patched module 7.4 with WV080 to WV110 and WI/WC 840 to 860. 9: Company "Collection Receipt ATP number" and date; with an ATP the receipt prints it, without one it prints THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX. 11: the SLSP is one file per month, three per quarter, and the 2550Q tie-out adds the three months.
- Tests: +7 (test_b48_rdo_answers); SAWT, QAP, master data, e-books and 2550Q tests follow the 5-digit branch, the extra pack file and the monthly SLSP files.
- Assumed: the manual invoice number applies to credit and debit notes too, unique within each document type. Under the test runner an empty manual number is filled from the serial (tests of the rule switch this off).
- Left out: 3 (the client's notice of third-party custody) and 4 (the release method for major and minor updates) are proposed, not built; 6 and 10 are owner items.

## B47 RELIEF (SLSP) files verified against the BIR's own module (14 Nov 2026)
- PR: #88
- Built: downloaded RELIEF 2.3 (BIRReliefv2.3.exe, job aid, patch 21C) from bir-cdn.bir.gov.ph, ran its Data Entry module under Wine with invented data, and kept the three files it generated (sales, purchases, importations) as golden files; all three pass its Validation module. The old writer failed that validator on all three: no owner address in the header ("Owner Address is empty") and no H,I header on the importations file ("No Header record found in file!"). The writer now matches RELIEF byte for byte: owner address from the company's registered address and ZIP, blank name fields as empty unquoted fields in detail rows, addresses, entry numbers, countries and OR numbers quoted, zero amounts in detail rows as a bare 0, rows sorted by registered name then last, first and middle name, and the importations header. Formatting is now separate from the queries (sales_file, purchases_file, importations_file), and the writer refuses a missing owner address or a customer or supplier row with no address, naming the parties.
- Tests: +5 (three byte-for-byte golden tests, the party and owner address refusals); the B29 tests follow the corrected format.
- Assumed: an individual owner's header carries the names in the last, first and middle fields with the registered name blank (not yet seen in RELIEF); a quarter's list is one file named for its last month, as before.
- Left out: the validator's e-Submission copy (the same file plus a V stamp line the validator writes; the CAS never writes it).

## B46 Fixes found while recording the tutorials (LDG-95, LDG-96, LDG-97) (14 Nov 2026)
- PR: #72
- Built: LDG-95: the PH Sales Invoice, PH Collection Receipt and PH BIR 2307 print formats called frappe.get_attr, which Frappe v16 no longer exposes in safe Jinja, so every print failed. They now call ph_attr, a jinja method that resolves only the seven listed print helpers (ph_cas.invoicing.printing.PRINT_HELPERS). The print tests used to pass the full frappe module into the template, which hid the failure; they now render with the safe globals only, the way the print view does. LDG-96: an issued Sales Invoice, Credit Note or Debit Note (one with a BIR serial) cannot be cancelled by any role, Administrator included (before_cancel refusal naming the serial and the correction document); the form hides Cancel and says how to correct it. LDG-97: a free-text field on a BIR blank can wrap over up to two lines inside its row (map keys lines and rowHeight), used when it prints larger than one shrunk line; the 2307 Part III description fields use it, so a 68-character ATC description prints at 5.9 pt on two lines instead of failing. The setup_philippine_company action also ticks its onboarding step.
- Tests: +3 (no-cancel for invoice and credit note, print helpers through ph_attr only, 2307 long description wraps inside its row); four tests that cancelled an invoice now cancel a journal entry or use the test unlock.
- Assumed: D6 (cancel and reissue) stays for journal entries and other vouchers; for invoices the correction is a credit or debit note only, as B21 already said for amendments and as the user guide and tutorials say.
- Left out: nothing in scope.

## B37 Website restructure for sentire.solutions (LDG-43) (11 Nov 2026)
- PR: #41
- Built: website/index.html is the Sentire Solutions front page (product family); the Ledger site moved to website/ledger/ with links rewritten; served at sentire.solutions/ledger/
- Tests: test_b37_website adjusted to the ledger/ layout
- Assumed: sentire.solutions had no site behind it (old Hetzner A record, dead Sliplane www CNAME); it now points at the Dokploy server
- Known limit: AAAA and www records are the owner's to fix in GoDaddy

## B45 G4 Approval chains: chain engine, requests, panel, home card, filed-return change chain, demo chains, module toggle (LDG-89 to LDG-93) (12 Nov 2026)
- PR: #46 (with B40 to B44)
- Built: doctypes PH Approval Chain (document type, company or all, enabled, applies-when expression, steps), PH Approval Step (step, title, condition, recipients by Role, User, Group or Dynamic field with an optional PH Approval Lookup, receiving order Sequential, Any one or Everyone, role type Approver or Notify, self-approval, private note), PH Approval Group and Group User, PH Approval Lookup, PH Approval Request (chain snapshot, document fingerprint, status Pending, Approved, Rejected, Withdrawn, Consumed, Void) and PH Approval Decision; ph_cas/approvals: chains (module switch on PH CAS Settings, single-user site, safe_eval conditions, chain_for with the company's chain first, recipients incl. Employee reports-to and lookups, snapshot, templates, demo install), requests (open, advance step by step with Notify steps passing at once and empty steps skipped, decide with Any one skipping the rest, Everyone waiting for all, Sequential waking the next, reject with reason, withdraw, change voids, the last approval submits on behalf or opens the PH Tax Return amendment, every move in the PH Event Log, mails through frappe.sendmail when an outgoing account exists), gate (before_submit on every doctype: refuses with "Request approval" unless the engine is posting or an approved unchanged request is consumed; on_update voids a changed document's request; PH Tax Return filing stays gated by the confirmation, its chain gates changes), api; approvals.js on every form (panel with the steps and decisions, Request approval replacing Submit, Approve, Reject, Withdraw, Request change on a filed return, history on posted documents); Awaiting your approval card on the home page; sidebar entries; open_amendment accepts the approved request; demo site gets Journal Entry and Purchase Order chains above 50,000; user guide section
- Tests: ph_cas/tests/test_g4_approvals.py (6): nothing on by default and the module switch, manager above an amount posting on approval with the event log, sequential, everyone, any one, notify and branching, reject, withdraw, change voids and self-approval, dynamic lookup and templates, a filed 2307 run changed through the chain into an amendment. 279 in all. Browser: request, panel, approve as the manager, posted; home card
- Assumed: a site with one enabled system user (Administrator counted) is the single-user case; a Role step goes to every enabled user with the role, not filtered by company; conditions are Python expressions over the document's fields, evaluated with frappe.safe_eval; an approver without submit permission still posts through the engine (the chain approved it); a request on a draft PH Tax Return is refused (filing is the confirmation's job)
- Known limit: no per-company filter on Role recipients; the mail is plain HTML through the site's outgoing account (none in tests, the error is swallowed); the Approval Chains list has no settings page of its own yet, templates are reached from the API (from_template) until the settings page lands with M5.2

## B44 G3 Income tax bundle: 1701Q, 1702Q, 1701, 1701A, 1702-RT exported, printed and fed from the books (LDG-73, 76, 74, 75, 77) (12 Nov 2026)
- PR: #46 (with B40 to B43)
- Built: ph_cas/forms/income.py (the shared pieces ported from the Portal's income-tax engine: the two graduated tables, 2018 to 2022 and 2023 onward, in whole pesos; the ATC lists per form and the refusal that names the item; taxpayer type, civil status, the three name shapes the forms print, birth date parts; the books feed from ph_cas.tax.income_tax split into quarters, the quarter's own figures being the year-to-date less the previous quarter's year-to-date; the row writer and the four eBIRForms layouts: 1701Q tab-trailed, 1702Q and 1702-RT with CR LF and the 2012.0 or 2014.0 tail, 1701 tab-trailed, 1701A two-space-trailed with the 2014. tail), f1701q (columns A and B, graduated or 8% with the 250,000 reduction for the filer only, OSD 40% of sales, Items 36 to 68 and 26 to 31, 172 keys), f1702q (Schedules 1 to 4, MCIT 2% on the quarters' gross income only when the Company's year of operations start says it applies, 106 keys), f1701 (837 keys over four pages and the 1701-M attachment pages, compensation plus business, 8% option with the compensation taxed on the table, Schedules 1 to 6 and Parts VI to IX, itemized total = ordinary + special + NOLCO), f1701a (OSD or 8% only, Items 36 to 65 and 20 to 30, 194 keys), f1702rt (Items 27 to 59, Schedules 1 to 5 with the NOLCO and MCIT rows, two signatories, 258 keys, zero printed as "0"); each export matched key for key, in order, against the Portal's fixtures, and round-trips through the parser; PH Tax Return writes each form's own layout through the engine's write_export; Company field ph_individual_type (Single Proprietorship or Professional) for the 1701 forms' taxpayer type box; BUILT now 12 forms
- Tests: ph_cas/tests/test_g3_income_tax.py (6): the tables, every export against its fixture's keys and printable, 1701Q graduated and 8% with the Q4 and ATC refusals, 1702Q MCIT on and off and the 1702-RT year, 1701 and 1701A annual with the married needs, 1702Q and 1702-RT from the books with the export file in the CR LF layout. 273 in all
- Assumed: the quarterly feed takes "this quarter" as year-to-date less the previous quarter's year-to-date (the engine is cumulative); the annual feeds give sales, cost of sales, itemized deductions, NOLCO, the first three quarters' tax (filed quarterly returns) and the 2307 credits split at the third quarter's end; the 1701's Schedule 4 lines, Schedule 5 and the NOLCO rows are typed, the books giving the itemized total when Schedule 4 is blank; compensation income (1701) is typed, since the Ledger holds no payroll; the 1702-RT's Schedule 1 lines are typed, the books giving Item 34 when the schedule is blank; the 1701A warns when the Company uses itemized deductions
- Known limit: a fiscal-year 1702Q feeds from 1 January of the quarter's year (the engine's cumulative start), as the tax engine itself does; the 1701-M attachment pages print blank

## B43 G2 Withholding bundle: 0619-E, 1601-EQ with QAP, 2307 certificates, 1600-VT and 1604-E with new maps (LDG-70, 71, 78, 72, 86, 79, 87) (12 Nov 2026)
- PR: #46 (with B40 to B42)
- Built: ph_cas/forms/withholding.py (the shared pieces ported from the Portal's withholding-print: common taxpayer block, yes/no marks, signatory and payment rows, centavo text, negative refusals naming the item); f0619e (feed from the month's supplier withholding, due date the 10th of next month moved off weekends and holidays, third-month warning), f1601eq (feed one row per ATC with rate, Items 20 and 21 from the two months, Item 23 from the previous filed quarter of the year, over-remittance choice never "carried" in Q4, six rows on the paper, QAP .DAT written at filing and on demand, alphalist rows kept in the filed snapshot), f2307 (certificates printed from PH 2307 Issued on page 1 of the blank, blocks A and B, one page per certificate; the quarter's run merges them into one PDF; Print on BIR form button on PH 2307 Issued; a run is issued without a BIR confirmation), f1600vt (feed from reverse-charge purchases by ATC, five rows, MAP .DAT), f1604e (Schedule 1 from the year's filed 1601-EQ returns, Schedule 2 typed, annual alphalist .DAT); two new overlay maps made from the blanks' own geometry with the ported tool (1600VT-2018-01, 77 fields, 2 pages; 1604E-2018-01, 129 fields, schedules as text cells), proofs inspected; Generate QAP / alphalist button; BUILT now 7 forms
- Tests: ph_cas/tests/test_g2_withholding.py (5): 0619-E rows and negatives, 1601-EQ over-remittance and six rows, 1600-VT and 1604-E on the new maps, books to 0619-E and 1601-EQ with QAP, 2307 certificates one page each and the run issued; the two new maps join the pinned-blank and proof tests. 267 in all
- Assumed: the 1604-E's Schedule 2 (1606 remittances) is typed, the Ledger holds no real-property sales; the 1600-VT rate prints as a whole number; the 2307 run (one record per quarter) is the way to print every certificate at once, and it does not publish figures
- Known limit: 1601-C, 1604-C, 2316 stay parked (LDG-80, LDG-88)

## B42 G1 VAT bundle: 2550Q end to end, the inputs editor, SLSP tie-out (LDG-68, LDG-81) (12 Nov 2026)
- PR: #46 (with B40, B41)
- Built: ph_cas/forms/f2550q.py: feed from the tax engine's 2550Q computation (17 items as books figures with records and filters, Schedule 3 from the 2307s received for VAT, Item 18 from the original on an amendment, below-zero shown as 0, more certificates than rows warned), compute ported from the Portal (Items 15 to 26 and 31 to 61, Schedules 1 to 4 feeding 39, 52, 53, 16, 17, whole pesos), needs (classification, rows over the paper's room, specify labels for 19, 42, 47, 56, relief kind and specify), export_rows with the frm2550qv2024 keys in the Portal's verified order (calendar or fiscal, year ended month, quarter range, classification boxes, 47B and the result keys, dateFiled), file name rule with the fiscal end month; the inputs editor on PH Tax Return (form_spec, set_inputs: every typed figure and schedule of the form as fields written into the data JSON, books figures shown with their value and flagged when typed over, schedules as editable grids with add and remove; the 2551Q gets its INPUTS and SCHEDULES too); Generate SLSP (.dat) on the 2550Q (RELIEF S, P, I files as PH Alphalist File records, the sales and input tax totals tied out against Items 34A and 44B, differences kept as warnings on every refresh); BUILT = {2551Q, 2550Q}
- Tests: ph_cas/tests/test_g1_2550q.py (5): item flow with schedules feeding their items, export keys equal to the Portal's fixture and printable, fiscal year shape, needs and row refusal, books feed with the inputs editor and SLSP. 262 in all
- Assumed: Schedule 1 (capital goods over 1M, deferred input tax) is typed, since purchases after 2022 are no longer amortised and the Ledger's 52B is 0; Schedule 2 direct attribution is typed and the ratable share comes from the books; the SLSP tie-out compares totals only (sales 34A, input tax 44B), a party without a TIN makes the writer refuse and the tie-out says so without blocking
- Known limit: the e-books .dat formats stay with the year-end pack (B25); nothing new was needed for them

## B41 BIR Form 2551Q end to end: books feed, compute, eBIRForms file, print, filing, amendment (LDG-69, F1) (12 Nov 2026)
- PR: #46 (with B40)
- Built: ph_cas/forms/f2551q.py: feed (Schedule 1 one row from the quarter's sales subject to percentage tax at the company's ATC and the rule in force on the quarter's last day, Item 15 from the 2307s received, Item 16 from the original on an amendment, CREATE-window warning, below-zero shown as 0), compute (rows' due and Items 14 to 24, whole pesos, ported from the Portal's compute2551Q), needs (row without ATC, unlisted ATC, more than six rows, overpayment disposition, Item 17 label, relief specify, Item 13 for an individual in Q1), export_rows (the package's frm2551Qv2018 keys in the Portal's verified order, eight-ATC dropdown, six rows, refusals that name the row, file name <tin><branch3>2551Qv201812<yyyy>Q<n>.xml), filed snapshot carries Schedule 1; Company field ph_pt_atc; BUILT = {2551Q}
- Tests: ph_cas/tests/test_f1_2551q.py (5): whole-peso rounding and item flow, needs and refusals, export keys equal to the Portal's fixture in order and printable, books to filed return to amendment (feed, hand change kept and flagged, export with txtFinalFlag 0 then 1, DRAFT preview text, confirmation required then attached, filed date from the e-mail, clear copy, snapshot survives a company rename, figures published, sealed against refresh and delete, amendment with Item 16 and the amended box), wrong confirmation named. 251 in all
- Assumed: One ATC per company for percentage tax (ph_pt_atc, default PT010); invoices carry no ATC of their own, so a company with several percentage-tax streams edits the rows by hand; the 2551Q follows the calendar whatever the fiscal year (as the Portal and the tax estimate do)
- Known limit: Part III payment details and the tax agent block are typed in the data JSON only (no fields on the form yet); a change to the data JSON by hand is the editor until the per-item form view lands with the 2550Q

## B40 BIR forms common layer: overlay print engine, PH Tax Return, confirmation, needs (LDG-82, F0) (12 Nov 2026)
- PR: #46
- Built: ph_cas/birpdf (the overlay engine ported from the Portal's @portal/bir-pdf: parse, validate, layout, render with pypdf and reportlab, watermark; the 11 field maps and 18 fixtures verbatim; the blanks read from ph_cas/tax/BIR Templates, SHA-256 pinned; proof tool), ph_cas/forms (registry of 13 forms, exact money, periods with fiscal years, needs, eBIRForms export writer with both package layouts and the file-name rule, confirmation e-mail reader and checks, engine dispatcher), PH Tax Return doctype (period, data JSON, lines, needs, DRAFT preview limited to 40 a minute per user, eBIRForms export, confirmation basis or System Manager override, filed snapshot of the taxpayer block, clear copy rendered at filing, figures published to PH Tax Return Figures, no cancel, no delete, amendment opened by a manager with a reason), PH BIR Confirmation doctype, 17 taxpayer fields on Company (names, birthdate, civil status, citizenship, incorporation date, registered address, ZIP, contact, email, line of business, PSIC, fiscal year start), BIR Returns in the sidebar
- Tests: ph_cas/tests/test_f0_birpdf.py (9): blanks pinned, maps match blanks, every fixture renders byte-identically, 2307 page 1 only, DRAFT stamp and footer, errors name the field, whole-peso refusal of centavos, parse refusals, proofs; ph_cas/tests/test_f0_tax_return.py (8): money, periods, export layouts, needs, confirmation names and text, registry, a return's period and needs and refusal to file unbuilt, preview limit. 246 in all
- Assumed: The owner's blanks are the Portal's (verified byte for byte), so the maps port without geometry work; dependencies reportlab and fonttools are declared in pyproject and installed by the image; a confirmation is read from an .eml, a PDF print or a text file and checked for sender, title, sentence, file name, TIN, branch, form, period and received time; the amendment path is a manager's direct action until the approval chain (M5.3) replaces it
- Known limit: No per-form engine is built yet (BUILT is empty), so every return reports "engine not built" as a need and cannot be filed; F1 (2551Q) fills the first one. Proofs are generated on demand, not committed. The 1600-VT, 1604-E, 1604-C, 2316 and 2306 blanks have no map (LDG-86 to LDG-88)

## B39 Home page: dashboard landing, one data call, PH prefix dropped from labels (LDG-64) (11 Nov 2026)
- PR: #39, #40
- Built: ph_cas/home/dashboard.py (get, hide_onboarding), Page sentire-home (JS, CSS in ph_cas/public/css/sentire.css), sidebar Home -> Page with the workspace as Overview, branding.js landing redirect and boot 'home', onboarding and workspace labels without the PH prefix, collapse arrow always visible
- Tests: ph_cas/tests/test_b39_home.py (5): page and sidebar order, one-call payload, periods, onboarding checklist and dismiss, no PH prefix
- Assumed: VAT and withholding cards are account balances from the PH Account Mapping, not computed returns; receivable and payable count positive outstanding only; the greeting uses the user's first name
- Dock and sidebar (after frappe-ui's Sidebar, studied on request; PR #40): the dock, the pinned column of shell icons, names its tiles on hover: the labels fly out beside the tiles over the page (`.sl-dock-peek`, no reflow), tooltips hidden meanwhile, our tile titled with the product (patched in `extend_bootinfo`, which runs after the dock is built; `boot_session` runs before it). The dock hover is pure CSS (`:hover`) with the script only closing it on click; the collapse arrow moves to a tab on the page edge at mid height while the menu is hidden, instead of sitting under the avatar. The module sidebar collapses to the desk's icon rail (Cmd+/ or the edge arrow) and opens on hover (`.sl-peek`). The Floating dock mode was tried in #39 and reverted (it hides the column); users switched by that build are put back to Pinned once. The "Switch to Helpdesk" advert in the Support menu is hidden.
- Known limit: DocType form titles still carry the internal PH names; a label layer for them is a later bundle

## B38 No framework branding: Sentire Ledger logo, titles, footers, emails, About (LDG-62, LDG-63) (11 Nov 2026)
- PR: #36 (number assigned at ship time)
- Built: ph_cas/branding.py (apply on every start and migrate: Website Settings, Navbar Settings, System Settings, Email Accounts, default workspace; boot_session; website context), ph_cas/public/images (provisional original mark: logo.svg, wordmark.svg/png, favicon.ico, icons), ph_cas/public/js/branding.js (About dialog with licences), hooks (app_title, app_logo_url, app_include_js, boot_session, update_website_context, User.validate), deploy_config (Email Account named after the product, branding.apply), audit.header.platform_version for the registration pack, demo/pilot/alert mails with the product header and container
- Tests: ph_cas/tests/test_b38_branding.py (8): settings, login logo and desk boot, email header and footer, legacy account rename, print version, default workspace, no framework strings in templates
- Assumed: The provisional mark is Claude's original drawing, replaced by overwriting the files in ph_cas/public/images; the GPL v3 and MIT licence line stays in About; prints show the product version only while the registration pack states the platform
- Known limit: Strings inside Frappe's own JS (setup wizard, system messages that say ERPNext) are not rewritten; the HTML comment in base.html stays

## B37 Client-facing website (10 Nov 2026)
- PR: #TBD
- Built: website/ static site (index, pricing, demo, terms, privacy, data processing terms; one stylesheet; nginx Dockerfile for Dokploy with build path /website); /pilot page and request_pilot API on the application site (CSV log, provider mail, webhook); README
- Tests: 2 (test_b37_website), 229 in all
- Assumed: Prices and tier contents from the 9 Nov proposal; demo and pilot forms live on the application site because a static site cannot send mail; legal pages are drafts for counsel; contact address is the firm's Gmail until a sentireledger.com mailbox exists
- Known limit: No analytics or CMS; copy changes are edits to the HTML files

## B36 Enterprise dedicated pair (10 Nov 2026)
- PR: #TBD
- Built: scripts/enterprise/provision-pair.sh (hardening, Docker, swap, firewall on both servers; Dokploy remote-server or own-Dokploy on production; standby restore-test timer and env file); scripts/enterprise/standby-restore-test.sh (fetch newest encrypted set, decrypt with the site key, restore into a fresh container of the published image, prove ping and monitor status, keep as UAT on 8080); Image workflow publishing ghcr.io/markchrc2025/ph-cas on every push to main; docs/runbooks/enterprise-pair.md (shape, provisioning, restore test, manual failover, SLA, costs)
- Tests: 3 (test_b36_enterprise), 227 in all
- Assumed: Servers in MCRC's Contabo account (decision C3); Singapore primary; manual DNS failover with 99.5 percent SLA; the GHCR package is private and servers pull with a read-only token
- Known limit: Automatic failover and MariaDB replication are not built; the restore test needs the image to be published first (first Image workflow run after merge)

## B35 Subscription and offboarding tooling (10 Nov 2026)
- PR: #TBD
- Built: PH Subscription DocType (client, site, tier, status, dates, fees, limits, usage, offboarding dates, deletion certificate; validation per status; set-tier command text; due list); ph_cas.hosting.offboard (export_site: backup with files, books per company and year, registration packs, audit trail, registers, manifest with SHA-256, README; deletion_certificate); ledger-site offboard, certificate, report; docs/runbooks/offboarding.md
- Tests: 3 (test_b35_offboarding), 224 in all
- Assumed: Subscription records live on MCRC's own site; usage is read with ledger-site report and pasted, not pulled automatically; suspension for non-payment is a manual step
- Known limit: The export runs inside the client's site, so a site that cannot start cannot be exported with this tool (use the last encrypted backup instead)

## B34 Onboarding videos (placeholders) and Sentire Ledger onboarding module (10 Nov 2026)
- PR: #TBD
- Built: ph_cas.setup.onboarding (video overrides from setup/data/onboarding_videos.json applied on install and migrate; Module Onboarding 'Get to know Sentire Ledger' with six steps; Sentire Ledger workspace with onboarding card, shortcuts and link cards); user guide section
- Tests: 4 (test_b34_onboarding), 221 in all
- Assumed: All 30 video overrides are null placeholders until the recordings exist (owner records them later); the workspace is created as a record at setup rather than a fixture so it is not overwritten by ERPNext upgrades
- Known limit: Step completion is per step record, as in ERPNext; the Watch Video action type is not used, videos play from the step card

## B33 Open demo and pilot (10 Nov 2026)
- PR: #TBD
- Built: ph_cas.hosting.demo_access (guest signup API with rate limit, Demo User role, per-request demo company with user permission, 24-hour login token, CSV lead log, provider mail, leads webhook, hourly expiry, recreate after reset, daily pilot check); /demo and /demo_login pages; ledger-site snapshot-demo and reset-demo; nightly reset loop in the entrypoint; runbook
- Tests: 6 (test_b33_demo), 217 in all
- Assumed: Demo users keep provider-staff status so they never count against a tier; demo site is the primary site with PH_DEMO=1 and ph_demo_site in site_config; leads are kept outside the database because the database is restored nightly
- Known limit: Master data (Customers, Items) is shared between demo users within a day; only transactions are separated by company. Pilot sites are not dropped automatically.

## B32 Multi-site hosting (10 Nov 2026)
- PR: #TBD
- Built: ph_cas.hosting.tiers (tier table, set_tier, limits, usage, enforcement on User, Company, Branch, Sales Invoice; provider staff flag); PH CAS Settings subscription fields; deploy_config.apply_shared; multi-site entrypoint; nginx host map; ledger-site command (new, set-tier, usage, list, backup, password, drop); rclone in the image; monitor reports subscription status; runbook
- Tests: 6 (test_b32_tiers), 211 in all
- Assumed: Tier limits per the 9 Nov pricing proposal (Solo 1 user 150 invoices, Team 5 users 3 branches 1000 invoices, Business 15 users, Enterprise unlimited); client hostnames are <name>.CLIENT_DOMAIN; unknown hostnames fall back to the primary site
- Known limit: Wildcard TLS and DNS are set in Dokploy and GoDaddy by the owner; the invoice limit counts Sales Invoices only (POS Invoices are not counted)

## B31 Hosting, backups, restore drill, runbooks (9 Nov 2026)
- PR: #29
- Built: ph_cas.ops.backup: run_backup takes database plus private and public files through Frappe's backup, writes a manifest with SHA-256 hashes, encrypts each file with AES-256 (openssl, key in site_config ph_backup_key), copies to the Philippine bucket in site_config ph_backup_remote with rclone, records the time on PH CAS Settings and logs it; verify_backup decrypts and checks every hash; a daily scheduler job runs it. ph_cas.ops.monitor.status reports backup age, chain check, disk, scheduler and draft rules on production, and an hourly job emails System Managers when a check fails. scripts/ops: new_client_site.sh (one site per client with production flag, backup key and remote, ten-year local retention, encryption key, scheduler), backup_now.sh, restore_drill.sh (restore the latest backup into a scratch site, migrate, run the chain check, drop it, append to the drill log). Runbooks: hosting, onboarding, upgrades (minor versus major) with the notice-of-minor-enhancement template; a short user guide.
- Tests: 205 on main (+3).
- Assumed: Provider-neutral (G9): the bucket and servers are placeholders in site_config. Retention ten years per the Annex B form until the RDO answers question 7.
- Known limit: Backups are database and files; the bench itself (code) is restored from the repository at the pinned tags. The restore drill script is exercised by hand on the production bench, not in CI.

## B30 Registration pack (9 Nov 2026)
- PR: #28
- Built: ph_cas.registration.pack builds the client's CAS application pack from the site: Annex C-1 system description drafted from Company and PH CAS Settings; the Annex B answers with remarks read from docs/CONFORMANCE.md (YES only for items marked built or verified, the rest listed as gaps); the joint sworn statement prefilled with the provider (new PH CAS Settings fields: provider name, TIN, address, signatory, position, TIN; decision D10) and the client, including the no-suppression clause and the termination clause; the conformance report with the pinned versions; specimen prints of the latest issued invoice, credit note, collection receipt and 2307 (rendered as specimens, not counted as prints); each book for the current month; the audit trail of the last 30 days and the chain check; a manifest. Downloaded as a zip from the Company form (PH CAS menu, which also gained the year-end e-books download) and logged. The CONFORMANCE.md table rows were repaired (stray pipes from the logging helper) and the helper fixed.
- Tests: 202 on main (+3).
- Assumed: Annex B answers are derived from the conformance file's status column, so a bundle that forgets to tick its row produces a NO: a conservative default.
- Known limit: Item 6 (e-invoicing) and the .dat half of item 5 are NO until CAS-13 and the RR 16-2006 format. The pack is text and HTML; the owner prints to PDF for the RDO.

## B29 SLSP (RELIEF): summary lists of sales, purchases and importations (9 Nov 2026)
- PR: #27
- Built: ph_cas.dat.relief builds the three RELIEF files named TIN9 + S, P or I + MMYYYY from the quarter's invoices and bills, rows merged per TIN, with the header totals (sales: exempt, zero-rated, taxable, output VAT; purchases: exempt, zero-rated, services, capital goods, goods, input VAT, creditable and non-creditable input VAT, the non-creditable part taken from the quarter's 2550Q item 53 when computed) and the importation rows (entry number, assessment date, supplier, importation date, country, dutiable value, charges, exempt, taxable, VAT, OR number, payment date). Purchase Invoice gets the importation fields; an import bill books the VAT paid to Customs to Input VAT - Importation, and the 2550Q items 46A and 46B now fill from them.
- Tests: 199 on main (+4).
- Assumed: Layouts are from the sample doc (status sample): the BIR's own RELIEF format and module (gate G7) override them, in particular the purchases detail row, which the sample described only through its header.
- Known limit: Customers and suppliers without a TIN are written as 000000000, which the BIR module may reject; the owner's golden files decide.

## B28 QAP 1601-EQ, 1604-E, MAP 1600-VT (9 Nov 2026)
- PR: #26
- Built: ph_cas.dat.qap. build_1601eq writes Schedules 1 and 2 in one file (HQAP header; D1 rows per payee and ATC from bills and advances with the rate as tax over income; C1 totals; D2 rows for bills booked without withholding under DI900 for individuals and EI900 for non-individuals; C2 total). build_1604e writes the annual file (H1604E with the N amended flag, D3 rows with the payee's TIN and branch, C3 total withheld, D4 rows for income not subjected, C4 total income) named with the 12/31 date. build_1600vt writes the MAP from the reverse-charge fields (HMAP, DMAP with unquoted names, non-resident providers without a TIN as 000000000, CMAP totals). generate stores each file as a PH Alphalist File with its layout status. unknown_atcs lists the codes in use that module 7.4 lacks (WV080 and the 840 to 860 series) for RDO question 8c.
- Tests: 195 on main (+4).
- Assumed: Schedule 2 ATCs DI900 and EI900 by payee type are an assumption from the sample layout (RDO 8c). The 1604-E D3 row writes the registered name quoted-empty for individuals, as the sample showed.
- Known limit: The 1601-EQ layout matches the validator rules in the reference doc; the 1604-E and 1600-VT layouts are sample-only until the golden files (G5).

## B27 DAT framework and SAWT (9 Nov 2026)
- PR: #25
- Built: ph_cas.dat.writer: field formatting per kind (quoted, unquoted, quoted-empty, amount 2 decimals, integer, MM/YYYY, MM/DD/YYYY, empty), record and file assembly with CRLF, file names per RMC 15-2025 Annex B (TIN9 + 4-digit branch + MMYYYY + form, or MMDDYYYY for annual files), the withholding agent's and parties' name fields as the alphalist wants them, and store(), which keeps every generated file as a PH Alphalist File (period, file name, SHA-256, row count, layout status, attachment, and the owner's Validation-module result and eSubmission reference) and logs the export. ph_cas.dat.sawt builds the SAWT for 2550Q (VAT withheld), 2551Q (percentage tax withheld) and 1701Q, 1702Q, 1701, 1702 (income tax withheld) from PH 2307 Received: HSAWT header, DSAWT rows sorted by TIN with the registered name or the split name, the rate as tax over income, CSAWT totals. docs/dat/VERIFICATION.md records each layout's status: SAWT is sample-only until the golden files (G5).
- Tests: 191 on main (+5).
- Assumed: The 2550Q SAWT uses form code 2550Q (RDO question 8a). A 5-digit branch code with a leading zero is written as 4 digits; others are refused (8b).
- Known limit: Byte-for-byte tests compare against the sample layouts, not the BIR module; the golden files replace them when the owner produces them.

## B26 2307 on the BIR layout (9 Nov 2026)
- PR: #24
- Built: Submittable DocType PH 2307 Issued (payor company, payee supplier, one quarter, payee TIN-branch, name as the form wants it for individuals and non-individuals, address, ZIP; Part III lines per ATC with the three months' bases, total and tax withheld, block A or B) generated from the bills and advances of the quarter; one issued certificate per payee per quarter, reissue only after cancellation (the reissue gets a numbered name and records what it replaces). generate_quarter creates the missing certificates for every payee withheld from. Print format PH BIR 2307 reproduces the January 2018 ENCS face from the project's cell-by-cell reference: header block, items 1 to 8A with digit boxes (14 for TINs, 8 for dates, 4 for ZIP), Part III with blocks A and B of ten rows and totals in the reference's column proportions, the declaration, both signature blocks with the tax-agent lines, the data-privacy note; default print format of the DocType.
- Tests: 186 on main (+4).
- Assumed: The face is rebuilt in HTML at the reference's dimensions (538 pt wide, legal paper) rather than overlaid on the BIR PDF, so the owner's paper check decides whether it passes as the BIR's blank or whether an overlay is needed. Block B stays empty (business-tax withholding by a private payor does not arise in release 1).
- Known limit: Page 2 (the ATC schedules) is not printed with the certificate.

## B25 Year-end e-books pack and transmittal (format pending) (9 Nov 2026)
- PR: #23
- Built: ph_cas.books.yearend. build_pack writes the seven books for the year as CSV files named TIN+branch_year_code with the Annex B header, a MANIFEST.json with SHA-256 hashes and sizes, and the RMO 9-2021 transmittal text (taxpayer, TIN, year, due date 30 days after year-end, file list with hashes, software and version, a placeholder for the ORUS QR stamp, signature block). download_pack zips it and logs the export; verify_pack reads a pack back and checks every hash. FORMAT_WRITERS is the slot where the RR 16-2006 record-format writer goes per book when the spec arrives (gate G7), without changing the pack.
- Tests: 182 on main (+2).
- Assumed: Built now in CSV because the RR 16-2006 record format was not supplied; the bundle text said to wait, but a CSV pack with hashes and the transmittal is usable at the pilot's first year-end if the RDO accepts it, and the slot for the BIR format is ready.
- Known limit: Annex B item 5's .dat half stays pending until the BIR format is in hand.

## B24 Books 2: Sales Journal, Purchase Journal, Inventory Book (9 Nov 2026)
- PR: #22
- Built: Script reports PH Sales Journal (one line per invoice: date, serial, type, customer TIN and name, address, description, VATable or percentage-tax base, exempt, zero-rated, output VAT, tax withheld by the customer, total; credit notes negative; totals and a tie-out of output VAT against the ledger), PH Purchase Journal (one line per bill: date, supplier invoice number, supplier TIN and name, net purchases by kind, purchases without input VAT, input VAT, EWT ATC and amount, reverse-charge VAT, amount payable; tie-out of EWT against the ledger) and PH Inventory Book (periodic per D7: per item and warehouse, opening quantity, in, out, closing quantity, last valuation rate and closing value). The SLSP (B29) reads the two journals' sources.
- Tests: 180 on main (+4).
- Assumed: The Purchase Journal shows a Non-VAT buyer's VAT-inclusive cost under services (net) since no input VAT exists; importations join once B29 adds the import fields.
- Known limit: Inventory value uses the last Stock Ledger valuation rate, which ERPNext maintains even with perpetual inventory off.

## B23 Books 1: General Journal, General Ledger, Cash Receipts, Cash Disbursements (9 Nov 2026)
- PR: #21
- Built: Script reports PH General Journal (every posting in date order: date, reference as the BIR serial where one exists, document, particulars with party, account, debit, credit; a TOTAL line and a tie-out line against the ledger), PH General Ledger Book (per account: opening balance, each posting with running balance, closing balance checked against the ledger), PH Cash Receipts Book (receipts into cash and bank accounts: date, Collection Receipt serial, payor and TIN, particulars, cash debit, each account credited) and PH Cash Disbursements Book (payments out of cash and bank: voucher and check number, payee and TIN, cash credit, each account debited). All print with the BIR Header letter head and export with the header lines through ph_cas.audit.export.download_report. ph_cas.books.common holds the shared queries and the tie-out.
- Tests: 176 on main (+5).
- Assumed: Columns follow RR 9-2009 as read in the review: date, reference, particulars, account, debit, credit, with party TIN on the cash books.
- Known limit: Page numbering is the report print's own; a dedicated paginated PDF per book is left to B25's year-end pack if the RDO asks for it.

## B22 Senior citizen and PWD discounts (9 Nov 2026)
- PR: #20
- Built: ph_cas.tax.sc_pwd. A Sales Invoice flagged as a sale to a senior citizen or PWD requires the holder type, name and OSCA or PWD ID; every line becomes VAT-exempt and the 20% discount (rule SC-PWD-20) on the VAT-exclusive price is booked as a negative tax row to the Senior Citizen and PWD Discounts expense account, so revenue stays gross and the discount is a deduction from gross income. The 5% special discount on basic necessities (SC-PWD-5-SPECIAL) keeps the VAT and refuses sales over the weekly cap. The invoice print shows the holder block with a signature line. Report PH SC PWD Sales is the record the law requires.
- Tests: 171 on main (+4).
- Assumed: D8 said SC/PWD later; built now since the whole plan was asked for. The 20% applies to all lines of the flagged invoice (a mixed receipt is split into two invoices); the weekly cap is checked per sale, not across the week.
- Known limit: H4: the JAO number and the computation base are the CPA's to confirm; the rules stay draft.

## B21 Invoicing rules (9 Nov 2026)
- PR: #19
- Built: ph_cas.invoicing.rules. A VAT seller's invoice of 1,000 or more (threshold from INV-BUYER-DETAILS-1000) to a VAT-registered customer is refused until the customer record carries TIN, registered name and address. An issued invoice is never amended: amendment of a Sales Invoice is refused; the credit note (decrease) and a new invoice (increase) are the correction path (D6). make_end_of_day_invoice builds the Non-VAT seller's one invoice for the day's small sales (threshold INV-NONVAT-500) to the walk-in customer set on the Company, by VAT class, dated today. The Collection Receipt is a per-company switch (default on, RDO question 9): off, a customer payment takes no serial and cannot be printed. Earlier tests that amended invoices now amend journal entries.
- Tests: 167 on main (+6).
- Assumed: Printing a Collection Receipt or a sales invoice for a sale below the threshold on the buyer's request is simply printing it; the ph_on_request flag records that it was asked for.
- Known limit: The end-of-day totals are typed from the cash count or POS tape (POS itself is out of release 1).

## B20 Invoice print formats and REPRINT (9 Nov 2026)
- PR: #18
- Built: Standard Jinja print formats PH Sales Invoice (Sales Invoice, credit note and debit note by title) and PH Collection Receipt (Payment Entry of type Receive), set as the default formats. Each prints an ORIGINAL and a DUPLICATE page with: seller's registered name, business style, address, VAT or NON-VAT REG TIN with 5-digit branch; the BIR serial, date, document title; buyer name, TIN-branch and address; lines with quantity, unit, description, VAT class, unit price, amount; the VAT buckets (VATable, VAT-exempt, zero-rated, VAT amount) or the percentage-tax base, EXEMPT, VAT-EXEMPT SALE and ZERO-RATED SALE marks; total, the RR 6-2026 Less: Withholding Tax line and the net amount due when applicable; the SC/PWD block when B22 fills it; ACCN, date issued and the registered series range; the five-year validity note; the Annex B header on the duplicate. The collection receipt lists the invoices paid by serial and carries THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX. ph_cas.invoicing.printing counts every server-side render of a submitted document in the insert-only PH Print Record; the second print onward shows REPRINT with its number and the date of the first print.
- Tests: 161 on main (+8).
- Assumed: What counts as a print: any server-side render of the format for a submitted document (print view, PDF, e-mail), excluding drafts, which B04 refuses. Letter size.
- Known limit: The owner's paper check (margins, both copies, long descriptions) is pending; tests render the Jinja directly because the test bench has no built assets.

## B18 Period figures: income tax (1701Q, 1702Q, 1701, 1701A, 1702-RT), MCIT, caps, NOLCO, book-to-tax (9 Nov 2026)
- PR: #17
- Built: ph_cas.tax.income_tax. Account gets a tax class (ordinary, entertainment amusement and recreation, interest expense, non-deductible, income tax expense, interest income subject to final tax, exempt or final-taxed income, cost of sales; Cost of Goods Sold accounts are classed automatically). Company gets the income-tax options: Corporate, Graduated (individual) or the 8% option; Itemized or OSD; mixed-income flag; primary business for the EAR cap; year operations began (MCIT from the fourth year after); the 20% small-corporation flag. compute_income_tax reads the ledger by root type and class, cumulative for the year on quarterly returns: sales, cost of sales, gross income, excluded income; itemized deductions with the EAR cap (0.5% goods, 1% services), the 20% interest-arbitrage reduction, non-deductible and income tax expense added back; OSD at 40% of gross sales (individuals) or gross income (corporations); NOLCO applied oldest first on annual itemized returns from PH NOLCO (3 years, 5 for 2020 and 2021 losses, expiry computed from the rule); RCIT at 25% or 20%, MCIT at 1% or 2% of gross income when applicable, the higher due, excess MCIT shown; the 2023 graduated table; the 8% option with or without the 250,000 reduction; credits from PH 2307 Received income-tax lines and from earlier quarters' figures. Report PH Book to Tax Reconciliation whose unexplained difference is zero.
- Tests: 153 on main (+9).
- Assumed: The figures use descriptive item keys (Sales, Gross income, Taxable income, Tax due, Payable) rather than the BIR item numbers of each income-tax form; the mapping to item numbers is done at verification against eBIRForms (G6). Excess MCIT carry-forward is shown but not yet applied against later years' RCIT; capital-gains and final-tax schedules are out of scope.
- Known limit: NOLCO balances are not written back when a return is computed (the compute is re-runnable); the manager records usage on the PH NOLCO record when the return is filed.

## B17 Period figures: 2551Q, 0619-E, 1601-EQ, 1600-VT; compliance calendar (9 Nov 2026)
- PR: #16
- Built: ph_cas.tax.returns: compute_2551q (Schedule 1 row for PT010 from the invoices' percentage-tax base at the rule rate in force at quarter end, items 14, 15 from 2307 Received percentage-tax lines, 18, 19, 24); compute_0619e (tax withheld in the month by ATC from bills and advances, items 14 and 18); compute_1601eq (ATC rows 13 to 18 with base, rate and tax, 19, 20 and 21 from the months' figures, 23 over-remittance carried within the year, 25, 26, 31; a note when more than six ATCs); compute_1600vt (base and VAT per WV code from the reverse-charge fields). ph_cas.tax.calendar: due dates for every return from the DUE-* rules (offsets, end of month, fixed dates, months 1 and 2), the next-working-day rule over weekends and PH Holiday (seeded with the fixed regular holidays of this year and next; movable ones are added by the manager each year), the forms a company must file from its regime and type, and a status per period from PH Tax Return Figures. Report PH Compliance Calendar. The government income-tax withholding codes were corrected from the 1601-EQ ATC schedule: goods WI640/WC640 at 1%, services WI157/WC157 at 2%; the wrong placeholder rules were withdrawn.
- Tests: 144 on main (+6).
- Assumed: 0619-E item numbers follow the Portal's reading of the form (14 amount of remittance, 18 total still due); the 2551Q and 1601-EQ numbers are from the forms in the project. eFPS staggered deadlines are not modelled.
- Known limit: Holiday proclamations (movable holidays) must be entered yearly; without them a due date on such a day shows one day early.

## B16 Period figures: 2550Q (9 Nov 2026)
- PR: #15
- Built: DocType PH Tax Return Figures (company, form, period, computed lines in the BIR form's item order with a source of computed, carried or typed; a separate table of typed adjustments each with a reason; computed on and by; a manual filed tick with the eBIRForms reference, after which the figures freeze and a recompute is refused). ph_cas.tax.returns.compute_2550q for the April 2024 ENCS form: 31A/B VATable sales and output tax, 32A zero-rated, 33A exempt, 34, 35B output VAT credit on uncollected receivables claimed this quarter, 36B recoveries, 37B, 38B carry-over of the previous quarter's excess (item 61), 39B deferred capital goods from the previous quarter (item 52), 43B, 44A/B domestic purchases and input tax (RBE purchases counted only once paid), 45A/B services by non-residents (the reverse-charge input VAT), 46A/B importations (zero until B29 adds import bills), 48A purchases without input tax, 50, 51B, 52B, 53B input tax attributable to exempt sales by the ratable method, 55B input VAT on unpaid payables the supplier credited, 57B, 58B settled add-back, 59B, 60B, 61, and Part II items 15, 16 (creditable VAT withheld from PH 2307 Received VAT lines), 20, 21, 26. ph_cas.tax.ovc: the agreed credit term on the invoice and claim_output_vat_credit (allowed only in the quarter after the term lapses, for sales from 27 Apr 2024, uncollected, with VAT); the buyer-side flag for a supplier's claimed credit. get_or_create and the whitelisted compute_return.
- Tests: 138 on main (+8).
- Assumed: Item 53 uses the ratable method only (no directly-attributable tracking, H9). Advance VAT payments (17), transitional and presumptive input tax (40, 41) and amended-return credits (18) are typed adjustments. The filed tick is manual: filing is not integrated.
- Known limit: Expected figures come from the catalogue's arithmetic; the eBIRForms expected answers (G6) will replace them when the owner produces them. Figures are stored as the user computed them, so a recompute after new documents is the user's action.

## B15 Reverse-charge VAT: digital services and RBE purchases (9 Nov 2026)
- PR: #14
- Built: ph_cas.tax.reverse_charge. Suppliers flagged non-resident digital service provider or registered business enterprise get a pair of tax rows on the Purchase Invoice that leave the amount due to the supplier unchanged: Add 12% to Input VAT - Withheld on Purchases (VAT buyer) or to Taxes and Licenses (Non-VAT buyer), Deduct 12% to Withholding VAT Payable, at the rule rate (RC-DSP-WV080, RC-DSP-WV090, RC-RBE-WV110). Recorded: kind, ATC, base, VAT to remit, input VAT claimable, the claimable-after-payment flag for RBE purchases, the 1600-VT period and the rule. B17's 1600-VT figures and B28's MAP read these fields.
- Tests: 130 on main (+5).
- Assumed: WV110 and the RR 1-2026 amendment are unverified (H10). RBE goods remitted on Form 0605 per transaction are treated like services here (one period figure); the CPA decides whether the 0605 path needs its own handling.
- Known limit: The RBE input VAT is booked at bill time and the claimable-after-payment flag is honoured by the 2550Q compute, not by a separate deferral account.

## B14 Purchase side: input VAT, EWT by supplier profile, timing (9 Nov 2026)
- PR: #13
- Built: ph_cas.tax.purchase. Supplier: withholding category (professional, rent, contractor, goods, services, reduced_wholesale, or none) and the over-threshold flag for professionals. Purchase Invoice: a VAT buyer booking a VAT supplier gets input VAT rows by kind (goods, services, capital goods, each to its mapped account; capital goods claimed in full per VAT-IN-CAPITAL-FULL); a Non-VAT buyer books the VAT as cost (Taxes and Licenses); purchases from Non-VAT suppliers, non-resident digital service providers and RBEs carry no input VAT row here (B15 handles the reverse charge). Expanded withholding is a Deduct tax row to Withholding Tax Payable - Expanded from the supplier's category and payee type and the rule in force on the bill date, so the payable and the payment are net of it; goods and services categories apply only when the company is a top withholding agent. Recorded on the bill: ATC, rate, base net of VAT, amount, rules, the withholding period (YYYY-MM for the 0619-E and the QAP). Booking without withholding needs a written reason. An advance payment to a supplier with a category withholds at payment (negative deduction to the EWT payable), the earlier event under RR 4-2024.
- Tests: 125 on main (+9).
- Assumed: A Non-VAT buyer's VAT cost goes to Taxes and Licenses rather than the line's expense account (one tax row cannot split by line); the CPA may prefer the expense account. Purchase prices are VAT-exclusive.
- Known limit: When an advance was withheld on, the later bill must be flagged no-withholding with the reason; the two are not matched automatically.

## B13 Sales side: withholding by customers, 2307s received (9 Nov 2026)
- PR: #12
- Built: ph_cas.tax.customer_withholding. On Sales Invoice a withholding block (ATC, rate, base net of VAT, income tax withheld, VAT withheld, percentage tax withheld, total, amount due net of withholding, rules applied) is filled from the customer's profile: government customers withhold income tax by goods and services (placeholder ATCs WI640 and WI650, H6) plus 5% VAT (WV010, WV020) from a VAT seller or percentage tax (WB080) from a Non-VAT seller; top withholding agents 1% on goods and 2% on services with WI or WC codes by the seller's taxpayer type; platforms 0.5% of the gross (WI/WC 820); on request, the user ticks the flag and gives ATC and rate. The receivable stays gross; when the customer pays net, the Payment Entry hook books the withheld part as deductions to Creditable Withholding Tax, Creditable VAT Withheld or Creditable Percentage Tax Withheld (two new mapping purposes and accounts) and allocates it so the invoice closes. shows_less_withholding_line decides the RR 6-2026 line by date (B20 prints it). Submittable DocType PH 2307 Received (payor, period within one quarter, ATC lines with monthly bases and tax, totals, scan) warns when it exceeds what payments booked. Report PH 2307 Received Reconciliation per customer and quarter.
- Tests: 116 on main (+10).
- Assumed: Goods versus services is decided per line by the item's stock flag. For platform sellers the invoice shows the expected 0.5% on the gross; the actual withholding happens on the platform's remittance.
- Known limit: Platform remittance statements are not imported; the 2307 Received record is the reconciliation point.

## B12 Sales side: VAT classes, output VAT, percentage tax base (9 Nov 2026)
- PR: #11
- Built: ph_cas.tax.vat. On Sales Invoice and POS Invoice, before ERPNext computes totals, the seller's regime (Company VAT status) and every line's VAT class (line override, else item) decide the tax rows: a VAT company gets one Actual tax row Output VAT on the VATable and Government lines at the rule rate in force on the posting date (VAT-OUT-12), posted to the mapped output VAT account; a Non-VAT company gets no VAT row and the percentage-tax base is recorded. Buckets stored on the invoice: regime, VATable sales, VAT amount, sales to government, zero-rated, VAT-exempt, sales subject to percentage tax, VAT rate and rule applied. A Non-VAT seller cannot issue zero-rated or government lines. Report PH VAT Threshold Watch (gross sales of the last 12 months against VAT-THRESHOLD-3M). resolve() now also filters by base.
- Tests: 106 on main (+8).
- Assumed: Prices are VAT-exclusive and the Output VAT row is added on top; VAT-inclusive pricing (Included in Print Rate) is not supported in release 1. Discounts at document level are not split across classes yet (line discounts are).
- Known limit: Rules are draft, so this works on test and development sites only until the CPA sign-off (G4).

## B11 Tax rules table, resolver, sign-off check (9 Nov 2026)
- PR: #10
- Built: DocType PH Tax Rule (rule id, kind, title, status draft or confirmed, sign-off file, catalogue row, ATC, rate, base, selector of key=value pairs, threshold, return and line, effective from and to, legal basis, notes). Seed of 72 rules from the catalogue in ph_cas/setup/data/tax_rules.json, all draft: VAT classes, input VAT and capital goods, the VAT threshold, percentage tax in its three dated versions, government withholding (WV010, WV020, income tax and percentage tax), platform and card withholding (WI/WC 820, 156), expanded withholding by category and payee type (WI/WC 010, 011, 100, 120, 158, 160, the reduced 0.5%), timing rules, reverse-charge VAT (WV080, WV090, WV110), corporate and individual income tax (25%, 20%, MCIT 1% and 2%, 8% option, the 2023 graduated table), OSD, the EAR caps, interest arbitrage, NOLCO, final tax on interest, SC/PWD discounts, invoicing thresholds, the RR 6-2026 line, accrual VAT on services, output VAT credit, the due-date rules per return, the weekend rule and retention. ph_cas.tax.rules.resolve(kind, date, atc, **selectors) returns the one rule in force, most specific selector first, and raises on none or ambiguity; a draft rule raises PHDraftRuleError on a production site. Overlap check on rate rules. bench ph-cas-sign-off <file> flips the listed ids to confirmed when the file says who signed; confirmed rules cannot be edited, re-drafted or deleted. Report PH Draft Tax Rules.
- Tests: 98 on main (+9).
- Assumed: Each catalogue row that carries a rate became one dated rule; open points H2 to H12 are carried in the rules' notes. The government income-tax ATCs (WI640, WI650) and the reduced-rate code WC840 are placeholders the CPA must confirm (H6).
- Known limit: The seed inserts missing ids only and never edits existing rows, so a corrected rule is a new id or an edit by the manager before sign-off.

## B10 Philippine chart of accounts and account mapping (9 Nov 2026)
- PR: #9
- Built: ph_cas.setup.chart: 19 accounts added under ERPNext's Standard chart (output VAT, output VAT on uncollected receivables, VAT payable, percentage tax payable, withholding payables for expanded, compensation, final and VAT, income tax payable; input VAT for goods, services, capital goods, importation, deferred and reverse charge; creditable withholding tax; SC/PWD discounts; taxes and licenses; income tax expense). DocType PH Account Mapping (company, purpose, account) validated for company, non-group and root type; account_for(company, purpose) is what the tax engine posts through. Whitelisted setup_philippine_company runs accounts, mapping and the head office's four BIR series in one click from the Company form (PH CAS menu), idempotent and logged.
- Tests: 89 on main (+5).
- Assumed: Accounts extend the Standard chart instead of a separate chart template, so the pilot's existing setup-wizard company is extended rather than recreated. Tax templates carry no rates yet (B12).
- Known limit: A company on a chart other than Standard needs the parent groups Duties and Taxes, Tax Assets, Direct Expenses and Indirect Expenses, or the setup refuses with the missing parent named.

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
- PR: #88
- Built: scripts/bootstrap.sh (uv Python 3.14, Node 24 from the npm registry, bench init at the pinned tags, ERPNext, ph_cas, test site); the ph_cas app skeleton (hooks, after_install and after_migrate through ph_cas.setup.install.setup_all, patches.txt, tests); VERSIONS.md; docs/DECISIONS.md; docs/CONFORMANCE.md with every Annex B item pending; docs/reference with the six reference documents; CI on GitHub Actions.
- Tests: 3 (ph_cas.tests.test_install), run on a real bench; a before_tests hook completes the ERPNext setup wizard for "_Test PH Company" (Philippines, PHP, Asia/Manila) because Frappe runs before_tests only for the app under test.
- Assumed: D1 and D2 as recommended. Node binaries come from the npm registry because nodejs.org was not reachable from the build workspace. The bootstrap points bench at the system Redis on 6379 instead of the 11000 and 13000 instances bench start would run; bench refuses to run as root, so the script exits early with that message.
- Left out: nothing in scope. The em-dash check covers docs/ only; reference documents copied in were cleaned of em and en dashes on the way in.
