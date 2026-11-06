# ERPNext and BIR CAS registration: structural review (2026-10-24)

Prepared by Claude at the owner's request: does ERPNext (github.com/frappe/erpnext) meet what the BIR requires of a Computerized Accounting System (CAS)? An independent fact-check of every claim was run against the code and the sources before this was saved; its corrections are folded in.

## What was reviewed
- **ERPNext**, cloned 24 Oct 2026:
  - `develop` at 7d3361c (17.0.0-dev)
  - stable `version-16` at ade850b (v16.52.1, the latest tag)
  - `version-15` at 4e0dce9 (15.124.1), for the version in the RDO 041 application below
- **Frappe Framework**, the platform ERPNext runs on: `develop` 8bfa016, `version-16` e8d41dd (16.53.0), `version-15` f1cf50c (15.124.0).
- **Method:** the source was read; no site was installed or run. Behaviours are traced to a file and line on `develop` (paths relative to the `erpnext/` or `frappe/` package). The controls that matter were re-checked on `version-16`, and the deletion controls on `version-15`.
- **BIR side:**
  - RMO 9-2021 and RMC 5-2021 with Annex B: the functional and technical requirements a CAS user swears to.
  - RR 7-2024 and RR 11-2024: EOPT invoicing.
  - RR 5-2014: retention.
  - RMC 98-2026: e-invoicing, 22 Sep 2026.
  - Secondary summaries are used only where the BIR text was not reachable, and are marked.

## Bottom line
- **Not CAS-ready as shipped.**
  - RMO 9-2021 defines the Acknowledgment Certificate (AC) as issued to a taxpayer upon registration of its system (Sec. III.10). Nothing in it approves a software product, so "ERPNext is BIR-approved" is not a meaningful claim.
  - A real application for ERPNext v15 was received by RDO 041 Mandaluyong with every general requirement marked complied (see Field evidence). The route is open; the photo does not show the AC or how the system fared afterwards.
- **The accounting core is a sound base.**
  - Posted documents are locked, except for "allow-on-submit" fields. Changing the accounting ones re-posts the ledger automatically (see 10c).
  - The system numbers documents.
  - Every row carries who created and changed it and when.
  - Field-level change history is kept for the main documents.
  - A voucher whose debits and credits differ beyond a small rounding allowance is refused.
- **Three things stand between ERPNext and a truthful Annex B sworn statement:**
  1. Remove or lock seven stock features that can erase posted records, rewrite their ledger or reuse their numbers (below).
  2. Build a Philippine compliance app: BIR invoice layouts, BIR-format books, a printable audit trail, 2307, the annual e-books file.
  3. Operate it with discipline: one pinned release, real backups kept for the retention period, change notices to the RDO.
- **E-invoicing is the next requirement.** RMC 98-2026 sets 31 Dec 2026 for covered taxpayers, and the category for CAS/CBA users is worded ambiguously (open question 1). E-invoices need a separate Permit to Issue (PTI) and EIS certification within six months. ERPNext has nothing for this.
- **The AC itself is quick:** three working days after complete documents, with no system demo. The risk is post-evaluation: the taxpayer swears the system meets Annex B, and as shipped it does not.

## The repository
| Item | Finding |
|---|---|
| What it is | A Frappe "app": Python server code and JavaScript desk UI on the Frappe Framework, with MariaDB or Postgres and Redis. Installed, upgraded and backed up with the `bench` tool. |
| Owner and licence | Frappe Technologies Pvt Ltd. GPL-3.0. The ERPNext name and logo are trademarks: they may not be used in a product or company name without permission (TRADEMARK_POLICY.md). |
| Size | 21 modules; 534 DocTypes (83 submittable, mostly transactions plus ledger-entry and process records; 168 masters and other; 31 single DocTypes, i.e. settings and tools; 252 child tables); 195 reports. About 282,000 lines of Python outside `test_*.py` files, 230,000 inside them, and 91,000 lines of JavaScript. 38.6k GitHub stars. |
| Largest modules | Accounts (191 DocTypes, 56 reports), Stock (78, 54), Manufacturing (49, 21). |
| Releases | `version-16` is the stable line with frequent minor tags (v16.52.1); `version-15` is still maintained (15.124.1); `develop` is 17.0.0-dev. v16 and develop declare Python ≥ 3.14. Upgrades run data patches (557 lines in patches.txt). |
| Not in this repo | HR and payroll live in a separate app (frappe/hrms), so BIR Form 2316 and the payroll alphalist are outside ERPNext. |

**How it is built.**
- Every record type is a DocType:
  - a JSON definition: fields, permissions, naming rule, whether changes are tracked;
  - a Python controller with life-cycle methods: validate, on_submit, on_update_after_submit, on_cancel, on_trash;
  - a JavaScript form script.
- Transactions share controllers in `erpnext/controllers`. AccountsController → StockController → SellingController, and StockController → SubcontractingController → BuyingController; taxes_and_totals computes the amounts.
- Other apps change behaviour through `hooks.py`: document events, class overrides, permission hooks, fixtures for custom fields and property setters.
- ERPNext also has `regional_overrides`, keyed by country. It is used today for Italy, the UAE, Saudi Arabia and France.
- A Philippine app can therefore be built beside ERPNext without forking it.

**Accounting engine.**
- Only controllers write the General Ledger, through `make_gl_entries`; users cannot create or edit GL Entry rows.
- A voucher is refused when debits and credits differ by more than 0.5 (0.05 for Journal and Payment Entries at two decimals). Smaller differences go to the Round Off account, and "Exchange Gain Or Loss" journals are exempt (`accounts/general_ledger.py:397-465`).
- Sub-ledgers: Payment Ledger Entry (receivables and payables) and Stock Ledger Entry.
- Period controls (`accounts/services/gl_validator.py:39, 96`):
  - Period Closing Voucher.
  - Accounting Period, which closes chosen document types and has an exempt role.
  - "Accounts Frozen Till Date" on the Company, with a role allowed past it.
- Cancelling a document posts reversing entries (`accounts/general_ledger.py:609`).
  - **By default** both the original and the reversal are flagged cancelled, and the General Ledger report hides them unless "Show Cancelled Entries" is ticked.
  - **With Enable Immutable Ledger** (Accounts Settings, off by default) the reversal posts on the cancellation date and both stay visible. On v16 and develop, cancelled transactions then cannot be deleted (`controllers/accounts_controller.py:530-537`).
  - **On v15** the setting exists but does not block deletion: v15's `on_trash` has no such check (`controllers/accounts_controller.py:577` on version-15).
  - **Side effect:** with Immutable Ledger on, the frozen-date and Period Closing Voucher checks use the cancellation date. So a voucher dated in a frozen or PCV-closed period can be cancelled without the frozen-entries role, with the reversal dated today. A closed Accounting Period still blocks, because it is checked against the original date (`general_ledger.py:644-654`).

**Philippine content.**
- A "verified" Philippine chart of accounts: 176 accounts, apparently taken from one company (it has AUB and HSBC loan payables, "Canteen", "Mockup Expenses"). It has no creditable-withholding-tax asset, no deferred input VAT and no percentage-tax payable.
- One setup tax template: "VAT" at 12 %.
- Nothing else: no ATC codes, no expanded-withholding template, no BIR print formats, no BIR reports, no e-invoicing.
- Other countries ship more in the same repo: Italy has an e-invoice XML, the UAE a VAT 201 report, the US an IRS 1099 report.

## What the BIR requires (as of 24 Oct 2026)
- **Registration (RMO 9-2021; RMC 5-2021).**
  - File with the RDO or LT Office, on paper or by email. There is no BIR Form 1900 and no demo or pre-evaluation.
  - The AC is issued within three working days of complete documents. Its control number (ACCN) must appear on system-generated invoices.
- **Documents (the Annex A checklist).**
  - A sworn statement (Annex C, system used and maintained by the taxpayer) or a joint sworn statement (Annex E), with the system description, invoice and report specification (Annex C-1).
  - Sample principal and supplementary invoices.
  - Sample books.
  - A printed audit trail (activity log).
  - The signed Annex B.
  - A certification if the software licence is in a parent's or affiliate's name.
  - This list is as printed on the RDO 041 checklist in the photo below, matching Grant Thornton's summary; the RMO body text refers to the annexes without listing them.
- **The joint sworn statement** is required when the taxpayer uses tax service providers or third-party software providers (Sec. V.6). Sec. III.14 counts software suppliers, developers and professionals among them; hosting is not mentioned. Both parties must state that the system has **no facility that may suppress sales/income**.
- **Post-evaluation.** The BIR may evaluate the system after the AC is issued; non-compliance can lead to revocation and penalties.
- **Changes (Sec. V.8 and V.9).**
  - A major enhancement needs a new application. That covers changed financial functions, financial modules added or removed, a new version or release with financial changes, and anything the BIR's evaluators deem major.
  - A minor one (user interface, bug fixes, performance) needs a written notice to the RDO.
  - Grant Thornton (Jul 2024) reads the EOPT invoice changes as a major enhancement needing a new AC.
- **Invoices from a CAS (RR 7-2024).**
  - "REPRINT" at the top of reprints.
  - At the bottom: the PTU or ACCN, the series range and the date issued (mm/dd/yyyy).
  - Supplementary documents carry "THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX".
  - The other content rules (seller and buyer details, VAT breakdown) are in the Annex B table below.
- **Books.** General Journal, General Ledger, Sales Journal, Purchase Journal and Inventory Book, with the columns listed in Annex B item 3.
- **Annual e-books.** A soft copy in Standard Audit File format on a USB drive within 30 days after the year ends (RMO 9-2021). It is registered through ORUS, with the QR stamp on the transmittal letter.
- **Retention (corrected 26 Oct 2026).**
  - The EOPT Act cut the period to five years (RA 11976 Sec. 235; RR 7-2024 Secs. 4-5). It runs from the day after the filing deadline, or from the filing date if the return was late.
  - Records tied to a pending protest or refund claim are kept until it is resolved.
  - Computerized books are kept as electronic copies.
  - The ten-year rule of RR 5-2014 is superseded, but the Annex B form (RMC 5-2021) still asks for database backups kept ten years. Keep ten until the RDO says the form follows EOPT.
- **E-invoicing (RMC 98-2026, under RR 8-2022 and RR 11-2025 as amended by RR 26-2025).**
  - Covered: e-commerce taxpayers (except micro), Large Taxpayers Service, large taxpayers under EOPT, taxpayers "using CAS or CBA with Accounting Records (with electronic invoicing), and other invoicing software", and others the Commissioner requires. That wording comes from an OCR scan.
  - Deadline: 31 Dec 2026.
  - A PTI Electronic Invoice is required, separate from the CAS AC; the BIR evaluates it in 20 working days. EIS certification must follow within six months.
  - An issued e-invoice may not be deleted or altered. Decreases go through a credit note, increases through a new invoice.
  - The EIS prescribes JSON. Sales-data transmission starts only once the BIR issues implementing rules; EIS certification tests the ability to transmit.

## Annex B (RMC 5-2021), item by item
Status: **Meets** · **Config** (a setting, no code) · **Build** (custom work) · **Lock** (stock behaviour conflicts and must be removed).

| # | Requirement | ERPNext as shipped | Status |
|---|---|---|---|
| 1 | Invoice face: seller name, style, address, VAT/NON-VAT REG TIN + 5-digit branch; serial ≥ 6 digits; date; buyer name, address, TIN; qty, description, unit price, amount; VAT; VATable / exempt / zero-rated split; "EXEMPT"; SC/PWD details; ACCN, series range, date issued; REPRINT | The data mostly exists (Company and Customer TIN, addresses, lines, taxes). Standard print formats are generic. The default series `ACC-SINV-.YYYY.-` has 5 digits and restarts every year. No branch-code field, no exempt/zero-rated class on lines, no REPRINT mark. Drafts print by default (with a "Draft" heading). | Build + Config |
| 2 | Commercial invoices at least in duplicate | Printing practice | Process |
| 3 | Books: GJ, GL, Sales J (date, customer TIN, name, address, description, doc no., amount, discount, output VAT, net), Purchase J, Inventory book | General Ledger; Sales Register (posting date, customer, Tax Id, net, per-tax-account columns, total); Purchase Register (adds supplier invoice no.); Stock Ledger. The data is there; the BIR layout is not. | Build |
| 4 | Every printout or e-copy shows name, address, TIN-branch, software name and version, user ID, date-time | The General Ledger, Trial Balance, financial statements and AR/AP prints already end with "Printed on" plus date and time (13 report templates). Grid-printed reports (Sales and Purchase Registers, Stock Ledger) do not. A report Letter Head is a Jinja template rendered on each print, so name, address, TIN-branch, software name, the printing user and the time can be added by configuration. The installed version and the BIR layouts need code. | Config + Build |
| 5 | Save books and reports as .csv or .dat (Annex B, under RR 16-2006); annual e-books in SAF (RMO 9-2021) | Any report exports to CSV or Excel, which meets the .csv half. No .dat, no SAF. | Meets (.csv) + Build |
| 6 | Send sales data to the BIR in its format | None | Build (EIS) |
| 7 | Backups kept 10 years | `bench backup` dumps the database only unless `--with-files` is given. Each run deletes backups older than about 23 hours unless `keep_backups_for_hours` is set, keeping at most 3 sets; encryption is off by default. On develop, Access Log and Activity Log sit in a separate `sqlite.db` that database backups exclude (on v16 they are ordinary tables). | Ops + Config |
| 8 | Printable audit trail of all transactions and activities | Version records (field-by-field changes, user, time) on Sales and Purchase Invoice, Journal Entry, Payment Entry, Customer, Supplier, Item, Account, Company, Accounts Settings and more. The Audit Trail page compares a submitted document with its amended copies (up to 5). Activity Log (logins; purged after 90 days by default). Access Log (prints, PDFs, exports, downloads). Deleted Document (the final JSON of anything deleted through the normal path). A document's Version rows and comments are deleted with it. No single printable report across all of it. | Build + Lock + Config |
| 9 | Generates 2306, 2307, 2316 | None. Tax Withholding Category can model expanded withholding (rates with from/to dates, thresholds, net-of-VAT base). 2316 belongs to payroll (HRMS). | Build |
| 10a | System controls receipt numbering | Naming series, yes, but: a System Manager can reset a counter (logged as a Version); deleting the latest document in a series gives its number back; an amended document is named `<original>-1` by default; numbers are taken when the draft is saved, so deleting a draft leaves a gap, or hands the number back if it was the latest. | Lock + Build |
| 10b | Posting date is the date entered | Users may back-date with "Edit Posting Date and Time" (Sales Invoice) or by typing the date (Journal Entry, Payment Entry). The creation time is kept separately. | Lock |
| 10c | Void, not modify, once posted | Submit/cancel model; cancelled documents kept. But fields stay editable after submission: Sales Invoice 20 header fields and 10 line fields (3 are read-only stock displays), including line income and expense accounts and cost centre, plus the tax table's `account_head` and the payments table's `account`; Purchase Invoice 12 header and 7 line fields (including expense account and valuation rate); Payment Entry 4 (including party name). Editing an accounting field on a posted Sales Invoice, Purchase Invoice, Journal Entry or Payment Entry automatically creates and submits a Repost Accounting Ledger, permissions bypassed, rebuilding its ledger. Any user with submit rights can do this, Accounts Users included. | Lock |
| 10d | Run date on reports | Printed on the GL, Trial Balance, financial statements and AR/AP prints; missing on grid-printed registers | Config + Build |
| 10e | Users cannot edit system-generated reports | Reports are computed; exports are copies | Meets |
| 10f | Users cannot override program edits | Validation is server-side; bypass roles exist by design (credit limit, frozen accounts, closed periods) | Config |
| 10g | Creator's user ID on every record | `owner`, `creation`, `modified_by`, `modified` on every row | Meets |
| 10h | Automatic totals, out-of-balance detection | Unbalanced vouchers refused; Trial Balance; General and Payment Ledger Comparison; Invalid Ledger Entries | Meets |
| 11 | Security: no concurrent sessions; deactivation after failed sign-ons; password change every 30 days; letters and numbers; role-based access; audit trail protected; firewall, encryption, server room | One session per user: off by default. Failed sign-ons: login is blocked only after more than 10 failures within 60 seconds of the first, and slow guessing never locks the account (no deactivation). Forced password reset after N days: blank. Passwords: a strength-score policy, not a letters-and-numbers rule. Two-factor sign-in: off. Version rows: System Manager read-only, Administrator may delete, and they go when their document is deleted. Deleted Document and Access Log: System Manager may delete. Infrastructure depends on hosting. | Config + Build + Ops |
| 12 | Sales adjustments through supplementary documents with unique serials | Credit notes take the invoice series unless someone picks `ACC-SINV-RET-.YYYY.-` by hand; debit notes share the invoice series. A Document Naming Rule can assign separate series by condition. | Config |

## Features to remove or lock before signing
Each one can erase posted records, rewrite their ledger or reuse their numbers: exactly what the sworn statement denies. All seven exist on `version-16` as well as `develop`.

1. **Company → Delete Transactions** (System Manager).
   - Deletes every transaction of a company, with its Version history, comments and communications, by raw SQL.
   - Leaves no Deleted Document copy, and Immutable Ledger does not stop it.
   - Invoice, Journal Entry and Payment Entry counters are not reset, so numbering continues after the gap.
   - Code: `setup/doctype/company/company.py:1240`; `setup/doctype/transaction_deletion_record/transaction_deletion_record.py:788, 845-848, 931-938`.
2. **Deleting cancelled vouchers.**
   - Who: Accounts Managers may delete Sales Invoices; Accounts Users and Managers may delete Journal and Payment Entries, once cancelled.
   - Deleting a document also deletes its Version history and comments; only the final JSON survives, in Deleted Document (Frappe `model/delete_doc.py:212-226, 545-551`).
   - If the deleted voucher was the latest in its series, the counter steps back and the next document gets the same number (`model/delete_doc.py:205`, `model/naming.py:455-507`).
   - The fix: Immutable Ledger blocks this on v16 and develop, but **not on v15**. Delete rights should go in every version.
3. **"Delete Accounting and Stock Ledger entries on deletion of transaction"** (Accounts Settings, off by default).
   - When on, deleting a voucher physically removes its GL, payment-ledger and stock-ledger rows (`controllers/accounts_controller.py:543-567`).
   - Keep it off and make it unchangeable.
4. **Repost Accounting Ledger.**
   - What it does: rebuilds the ledger of submitted vouchers. The default allowed types are Sales and Purchase Invoice, Payment Entry, Journal Entry and Purchase Receipt, and the list can be changed. It can optionally delete the old rows ("Delete Cancelled Ledger Entries", `repost_accounting_ledger.py:327`).
   - Who: a System Manager can run it directly. It also runs automatically, permissions bypassed, whenever a user with submit rights edits an accounting field on a posted voucher (10c; `controllers/accounts_controller.py:1575-1581`; `sales_invoice.py:1256-1274`; `purchase_invoice.py:768-779`).
   - What blocks it:
     - a submitted Period Closing Voucher
     - a closed Accounting Period, unless the user has the exempt role
     - Accounts Frozen Till Date, unless the user has the frozen-entries role
     - deferred revenue or expense invoices
     - types outside the allowed list
     - A failed voucher rolls back.
5. **Document Naming Settings → Update Series Number** (System Manager).
   - Sets any counter value; the change is logged as a Version (`core/doctype/document_naming_settings/document_naming_settings.py:222`).
6. **Smaller locks.**
   - Accounts Users can create, edit, disable or delete Accounting Periods and untick closed document types, which reopens a closed period.
   - The allow-on-submit fields in 10c.
   - "Allow Print for Draft" is on by default.
   - Amended documents keep the original number with a suffix; "Amended Document Naming Settings" can switch them to the normal series.
7. **Stock re-valuation (Repost Item Valuation).** Added 24 Oct 2026, after the fact-check.
   - When a stock transaction is back-dated or cancelled, ERPNext re-values the later stock entries.
   - With perpetual inventory on (the Company default), it then deletes and re-creates the ledger rows of every later stock voucher whose values change (`accounts/utils.py:1699-1738`; `version-16` `:1663`).
   - Fix: block back-dated stock transactions, or run perpetual inventory off (stock ledger kept, ledger adjusted by period-end entries).

## Settings that close gaps without code
- **Accounts Settings:** Enable Immutable Ledger on (v16 or later for the deletion block); keep ledger deletion off.
- **Period locks:**
  - Set Accounts Frozen Till Date and its role on the Company.
  - Close each filed period with an Accounting Period, which still blocks cancellations under Immutable Ledger.
  - Restrict Accounting Periods to one manager role.
- **Numbering:**
  - Series of at least 6 digits, e.g. `SI-.########`.
  - Document Naming Rules for separate credit-note and debit-note series.
  - Amended documents on Default Naming.
- **Role permissions:**
  - Remove delete on Sales and Purchase Invoices, Journal and Payment Entries and Period Closing Vouchers.
  - Keep cancel to one role.
  - Remove allow-on-submit on accounting fields through Customize Form.
  - Hide back-dating.
- **Company:** Enable Perpetual Inventory off for clients with stock, unless back-dated stock transactions are blocked.
- **Print Settings:** Allow Print for Draft off.
- **Report Letter Head:** name, address, TIN-branch, software name, `frappe.session.user` and the time.
- **System Settings:** two-factor sign-in, one session per user, password reset every 30 days.
- **Log Settings:** Activity Log kept 10 years, not 90 days. Access Log and Deleted Document are not purged unless someone adds them.
- **Backups:**
  - Run with files.
  - Set `keep_backups_for_hours` or, better, copy off-site.
  - Encrypt, and keep 10 years.
  - On develop, also copy `sqlite.db`, which holds the access and activity logs.

## What has to be built: a Philippine compliance app
Relative size: S small, M medium, L large.
| Component | Size |
|---|---|
| Lock-down hooks: block Delete Transactions, repost-with-delete, automatic reposts from edits after posting, back-dated stock transactions, and deletion of cancelled accounting documents (needed on v15, where Immutable Ledger does not block it); guard counter changes | S |
| BIR serial number assigned on submit in its own locked counter, so drafts never consume or return numbers | M |
| BIR invoice set: Sales Invoice, credit and debit notes, supplementary collection receipt. Fields for branch code, ACCN, series range, date issued and SC/PWD. VATable / exempt / zero-rated / government buckets through `regional_overrides` for "Philippines". A REPRINT count on every print after the first | M |
| Books in BIR layout (GJ, GL, Sales J, Purchase J, Inventory book), with the installed version added to the header and CSV export | M |
| Printable audit-trail report across Version, Deleted Document, Access Log and Activity Log | M |
| Withholding: one Tax Withholding Category per ATC with dated rates; 2307 print; QAP and SAWT files | M |
| Annual e-books file in the BIR's Standard Audit File format | M |
| E-invoicing: JSON for the EIS, PTI paperwork, EIS certification, QR | L |
| Payroll and 2316, only if payroll is in scope (HRMS plus Philippine payroll rules) | L |

The Portal's ATC schedule and 2307 layout work carries over as data and design; the code does not (ERPNext is Python/Frappe).

## Operating conditions
- **Who signs.**
  - A system used and maintained by the taxpayer: the taxpayer's sworn statement.
  - A tax service provider or third-party software provider (supplier, developer or professional): a joint sworn statement (RMO 9-2021 Sec. V.6, III.14).
  - Whether hosting alone (e.g. Frappe Cloud) triggers it is not in the RMO. One Philippine user reported the BIR treating self-hosting as in-house and Frappe Cloud as needing a joint statement (forum, Apr 2026).
- **Upgrades are enhancements.**
  - ERPNext ships minor releases often. Pin one release, batch updates, and send the RDO a written notice for bug-fix updates.
  - Treat a version change (v15 → v16 → v17) as a new application.
- **Year-end.** The SAF e-books on USB within 30 days, registered through ORUS.
- **Retention.** Five years under EOPT; ten while the Annex B form says so. This applies to real backups (database and files) and to the logs above.

## Field evidence
- **RDO 041 application (photo shared by the owner, 24 Oct 2026, from a public post).**
  - The BIR's Checklist of Documentary Requirements (Annex A), filed at RDO 041 Mandaluyong by a corporation. The software is declared as "ERPNext - Version 15 (V15)".
  - All five general requirements are ticked as complied; the parent/affiliate licence item is N/A.
  - Stamped received on 21 October; the year is not legible.
  - The return slip is also signed. Nothing appears marked lacking, but the photo cannot confirm it.
  - It shows the application passed the completeness check. It does not show the AC, the Annex B answers, the customisations or any post-evaluation.
  - On v15, Immutable Ledger does not block deleting cancelled vouchers, so that applicant depends on role permissions.
- **Frappe forum, threads 18092 and 57771, 2016-2026.**
  - Several Philippine users asked about CAS for ERPNext. None posted an AC number.
  - A May 2025 post said ERPNext "is now approved by the BIR", with no source.
  - An April 2026 post: the user's ERPNext registration was classed as **CBA with invoicing** rather than CAS, for lacking the expected audit-trail format "and other functionalities". Self-hosting was treated as in-house development, while Frappe Cloud would need a joint sworn statement. This is an unverified, second-hand account, but it matches the gaps above.

## Open questions (for the RDO or tax adviser)
1. Does RMC 98-2026 cover every CAS user, or only those already issuing electronic invoices? The OCR'd text puts "(with electronic invoicing)" after CBA, and summaries read it differently.
2. Will the RDO accept a series that restarts each year (e.g. SI-2026-000001), or does it want one continuous range for the AC's series range?
3. Self-hosted or hosted: which sworn statement, and where must the retained copies sit?
4. Which ERPNext updates does the RDO treat as minor (notice) and which as major (new application)?
5. After EOPT, does the client need a supplementary collection receipt at all, or only invoices and credit notes?
6. If obtainable, ask the RDO 041 applicant for: the AC, their Annex B answers, Annex C-1, a sample invoice and the audit-trail printout.

## Sources
- ERPNext: https://github.com/frappe/erpnext (develop 7d3361c; version-16 ade850b, v16.52.1; version-15 4e0dce9, v15.124.1)
- Frappe Framework: https://github.com/frappe/frappe (develop 8bfa016; version-16 e8d41dd, 16.53.0; version-15 f1cf50c, 15.124.0)
- RMC 5-2021 Annex B: https://bir-cdn.bir.gov.ph/local/pdf/RMC%20No.%205-2021%20Annex%20B.pdf
- RMO 9-2021 (text via KPMG): https://assets.kpmg.com/content/dam/kpmg/ph/pdf/InTAX/2021/RMO%20No.%209-2021.pdf
- RMC 5-2021 (PwC tax alert): https://www.pwc.com/ph/en/tax/tax-publications/tax-alerts/2021-tax-alerts/tax-alert-8.html
- CAS application documents (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/line-of-sight/cas-application-made-simple/
- RR 7-2024 invoice requirements (supplier notice reproducing RR 7-2024 Annex B): https://teamenergy.ph/file-manager/files/Notice%20to%20Suppliers_EOPT%20Invoicing%20Requirements.pdf
- RR 11-2024 (KPMG; Grant Thornton): https://kpmg.com/ph/en/insights/2024/06/special-intax-june-2024-issue-1-volume-1.html ; https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/amendments-and-extension-of-deadlines-for-compliance-with-the-invoicing-requirements-under-eopt-act/
- EOPT changes as major enhancements (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/lets-talk-tax/eopt-on-computerized-accounting-system-cas-to-secure-or-not-to-secure-new-acknowledgment-certificate/
- RR 5-2014: https://bir-cdn.bir.gov.ph/BIR/pdf/RR%205-2014.pdf ; superseded on retention by EOPT (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/eopt-is-here-updates-on-the-preservation-of-book-of-accounts-and-changes-in-taxpayer-registration/
- ORUS registration of books (Grant Thornton): https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/required-online-registration-of-books-of-accounts-via-orus/ ; RMC 6-2025 deadlines (KPMG): https://kpmg.com/ph/en/insights/2025/01/special-intax-january-2025-issue-1-volume-1.html
- RMC 98-2026: https://bir-cdn.bir.gov.ph/BIR/pdf/RMC%20No.%2098-2026%20redacted.pdf ; BIR press release 23 Sep 2026: https://bir-cdn.bir.gov.ph/BIR/pdf/PR101SEP2326.pdf ; summaries: https://www.reyestacandong.com/rmc-no-98-2026-electronic-invoicing-guidelines/ and https://www.grantthornton.com.ph/insights/articles-and-updates1/tax-notes/rmc-no-98-2026-prescribing-policies-and-guidelines-on-the-issuance-of-electronic-invoice-under-rr-no-8-2022-and-rr-no-11-2025-as-amended-by-rr-no-26-2025/
- Frappe forum: https://discuss.frappe.io/t/sharing-frappe-erpnext-in-philippines/18092 ; https://discuss.frappe.io/t/erpnext-bir-bureau-of-internal-revenue-registration-philippines/57771
- RDO 041 Checklist of Documentary Requirements: photo shared by the owner on 24 Oct 2026 (not stored here)
