# CAS on ERPNext: build bundles, one prompt each (6 Nov 2026)

Prepared by Claude at the owner's request: "Can you do it in bundles that can be built in one prompt, but not breaking the build flow?"

- **What it is:** the build plan's units CAS-1 to CAS-11 re-cut into 31 bundles. Each bundle is sized for one build session (one prompt, one branch, one pull request) and leaves `main` installable, migratable and green, so the next bundle can start from it.
- **What it does not change:** the decisions D1 to D11, the units' content, or the owner items in `claude/cas-owner-action-items-2026-11-06.md`. It only changes the slicing and the order.
- **Companion files:** `claude/ph-cas-build-plan-2026-10-24.md` (units, decisions, risks), `claude/ph-tax-rules-catalogue-2026-10-26.md` (rules), `claude/erpnext-bir-cas-review-2026-10-24.md` (what ERPNext lacks and where), `claude/bir-alphalist-module-7.4-analysis-2026-11-05.md` and `claude/bir-dat-sample-layouts-2026-11-06.md` (DAT files).

## 1. How the flow stays unbroken

Three rules, taken from the Portal's track practice (`claude/portal-build-log-2026-10-27.md`), adapted to a Frappe app:

1. **One bundle, one prompt, one PR, squash-merged to `main`.** Every prompt starts with "merge `main` into your branch first". Nothing is built on an unmerged branch.
2. **`main` is always installable.** The CI job on every PR runs `bench new-site`, `bench install-app ph_cas`, `bench migrate`, then the test suite. A bundle is not done until that job is green. A bundle that adds a field or a DocType ships its patch in the same PR, so an existing site migrates forward.
3. **Nothing waits on a rule that is not confirmed.** The tax engine is built with rules marked `draft`. Production refuses to apply a draft rule (B11). So the CPA's sign-off never blocks a build; it only unlocks production.

Two consequences:
- A bundle never half-builds a contract between two layers. Where an API side and a print or screen side exist (B08 header and books, B26 and B27), the same bundle ships both halves.
- The bundles that have an owner gate (section 3) are placed so that work exists on either side of each gate. If a gate is still open when its bundle comes up, the build moves to the next bundle that is not gated; the table in section 4 shows what each bundle depends on.

## 2. The common preamble (paste at the top of every prompt)

```
You are building ph_cas, a Frappe app that makes ERPNext a BIR-registrable
computerized accounting system (CAS) for Philippine micro and small taxpayers.

Fixed facts
- ERPNext v16 and Frappe v16, pinned to the tags recorded in VERSIONS.md
  (first pin: ERPNext v16.54.0, Frappe v16.55.2, the latest v16 tags on
  6 Nov 2026). Python 3.14, Node 24, MariaDB 10.11 or later, Redis.
- Never modify ERPNext or Frappe. Everything lives in ph_cas: hooks.py
  (doc_events, override_doctype_class, permission hooks, regional_overrides),
  custom fields and property setters defined in code (after_install plus a
  patch), fixtures, patches, server scripts are not used.
- Every rule is enforced server side (validate, before_submit, on_cancel,
  on_trash, permission query). Client scripts only improve the screen.
- Tests first: write the failing test, see it fail, then build.
  Run with bench --site test_site run-tests --app ph_cas.
- One branch per bundle, named bundle/<id>-<slug>. Merge main first.
  Squash-merge through a PR when CI is green. Record the PR and the counts
  in docs/BUILD-LOG.md and tick the Annex B items in docs/CONFORMANCE.md.
- Documents: no em dashes or en dashes anywhere (code comments included).
- Never commit a BIR installer, the eBIRForms package, the Alphalist module
  or any real taxpayer data. Dummy TINs only (000-000-000 pattern).
- Tax rules are data (B11). A rule's status is draft until the CPA sign-off
  file names it. Production sites refuse to apply a draft rule.
- Do not ask the owner questions mid-build. Take the recorded decision
  (docs/DECISIONS.md) or the safe default written in the bundle, record the
  choice in docs/BUILD-LOG.md under "Assumed", and continue.

Read before building: docs/DECISIONS.md, docs/CONFORMANCE.md, the "Read
first" list of this bundle, and the bundle immediately before it in
docs/BUILD-LOG.md.

Report at the end: PR number, what was built, test counts before and after
on main, the Annex B items ticked, anything assumed, anything left out.
```

Then the bundle's own text (section 5), which has the same five headings every time: goal, read first, build, tests, done when, out of scope.

## 3. Gates (what each phase needs from the owner)

| Gate | Needed before | What satisfies it | Safe default if still open |
|---|---|---|---|
| G1 repository | B01 | A private GitHub repository connected to the build workspace (action item 2.1) | None. B01 cannot start. |
| G2 D1 and D2 | B01 | Version 16 pinned; firm-hosted, one site per client | Recorded as the recommendation; the owner confirms in `docs/DECISIONS.md` |
| G3 D4 to D8 and the POS decision | B02 | Recorded in `docs/DECISIONS.md` | Each bundle names its default, all of them the recommendations in the action items |
| G4 CPA sign-off | Production use of B12 to B18, B27 to B29 | The file `docs/rules/SIGNOFF-<date>.md` signed by the CPA listing the confirmed rule ids | Build continues with `draft` rules; tests use the catalogue's figures |
| G5 golden files | B27 to B29 "done" | Alphalist and Validation module outputs from dummy data (action item 6.1) | Build against the sample layouts doc; the bundle stays "built, not verified" until the files arrive |
| G6 eBIRForms answers | B16 to B18 "done" | Saved eBIRForms results from dummy scenarios (action item 6.2) | Same as G5 |
| G7 specs | B25 (e-books), B29 (SLSP) | RR 16-2006 record format; the BIR SLSP format (action items 5.4, 5.5) | B25 waits. B29 builds the RELIEF layout from the sample and is marked unverified |
| G8 D9 product name | B08 ticks the header item | Any name without "ERPNext" | The header reads the name from a setting; code uses "PH CAS" |
| G9 D3 and hosting provider | B31 | A provider in the Philippines | B31 builds provider-neutral scripts and a runbook; the provider is filled in later |
| G10 D10 signatory | B30 | The officer's name and position | Prefilled from a setting; blank until set |

## 4. The bundles in order

Sizes: S is a short session, M a full session, L a full session that may need one follow-up PR for leftovers (the follow-up is still "one prompt").

| Id | Bundle | Unit | Depends on | Gate | Size |
|---|---|---|---|---|---|
| B01 | Repository, bench, CI, bootstrap, reference docs | CAS-1 | none | G1, G2 | M |
| B02 | Lock-down 1: nothing posted can be deleted or reposted | CAS-2 a, b, c, e | B01 | G3 | M |
| B03 | Lock-down 2: nothing posted can be changed or renumbered | CAS-2 d, f | B02 | G3 | M |
| B04 | Lock-down 3: dates, drafts, periods, inventory | CAS-2 g, h, i; D5, D7 | B02 | G3 | M |
| B05 | Security baseline | CAS-2 j | B01 | none | M |
| B06 | BIR serial number | CAS-3 | B03 | G3 (D4) | M |
| B07 | Hash-chained event log | CAS-4 part 1 | B02 | none | M |
| B08 | Audit trail report and the Annex B print header | CAS-4 part 2 | B07 | G8 (tick only) | M |
| B09 | Philippine master data | CAS-5 part 1 | B01 | none | M |
| B10 | Philippine chart of accounts and account mapping | CAS-5 part 2 | B09 | none | S |
| B11 | Tax rules table, resolver, sign-off check | CAS-5b core | B09 | none | M |
| B12 | Sales side: VAT classes, output VAT, percentage tax | CAS-5b | B10, B11 | G4 for production | M |
| B13 | Sales side: withholding by customers, 2307s received | CAS-5b | B12 | G4 | M |
| B14 | Purchase side: input VAT, EWT by supplier profile, timing | CAS-5b | B12 | G4 | M |
| B15 | Reverse-charge VAT: digital services (1600-VT) and RBE purchases | CAS-5b | B14 | G4 | M |
| B16 | Period figures: 2550Q | CAS-5b | B13, B15 | G4, G6 | M |
| B17 | Period figures: 2551Q, 0619-E, 1601-EQ, 1600-VT; compliance calendar | CAS-5b | B16 | G4, G6 | M |
| B18 | Period figures: income tax (1701Q, 1702Q, 1701, 1701A, 1702-RT), MCIT, caps, NOLCO, book-to-tax | CAS-5b | B17 | G4, G6 | L |
| B20 | Invoice print formats and REPRINT | CAS-6 part 1 | B06, B08, B12 | G3 | M |
| B21 | Invoicing rules | CAS-6 part 2 | B20, B13 | G3, RDO q9 (default below) | M |
| B22 | Senior citizen and PWD discounts | CAS-6b | B21 | later (D8) | S |
| B23 | Books 1: General Journal, General Ledger, Cash Receipts, Cash Disbursements | CAS-7 | B08, B10 | none | M |
| B24 | Books 2: Sales Journal, Purchase Journal, Inventory Book | CAS-7 | B23, B12 | none | M |
| B25 | Year-end e-books and transmittal | CAS-8 | B24 | G7 | M |
| B26 | 2307 on the BIR layout | CAS-9 part 1 | B14, B08 | none | M |
| B27 | DAT framework and SAWT | CAS-9 part 2 | B13, B26 | G5 | M |
| B28 | QAP 1601-EQ, 1604-E, MAP 1600-VT | CAS-9 part 3 | B27, B15 | G5 | M |
| B29 | SLSP (RELIEF) | CAS-9 part 4 | B27, B24 | G5, G7 | M |
| B30 | Registration pack | CAS-10 | B02 to B29 | G8, G10 | M |
| B31 | Hosting, backups, restore drill, runbooks | CAS-11 | B05 | G9 | M |

Not bundles: CAS-12 (the pilot is run, not built), CAS-13 (e-invoicing waits for the EIS specs and D11; it will be sliced the same way when the spec spike is done), CAS-14 (payroll, out unless the owner decides otherwise). B19 is deliberately unused so that the numbering survives if a tax-engine bundle has to be split.

### Order and parallel tracks

The dependency column allows three tracks after B02, the way the Portal runs tracks A, B and C. Run them as three sessions or one after the other; the merges stay clean because each bundle merges `main` first.

- **Track 1, controls:** B01 → B02 → B03 → B04 → B06 → B07 → B08 → B20 → B21 → B22 → B30.
- **Track 2, tax and books:** B09 → B10 → B11 → B12 → B13 → B14 → B15 → B16 → B17 → B18 → B23 → B24 → B25.
- **Track 3, outputs and operations:** B05 → B31, then B26 → B27 → B28 → B29 once B13, B14 and B24 are on `main`.

Strictly serial order if there is one session at a time: B01, B02, B05, B09, B03, B04, B07, B10, B11, B06, B08, B12, B13, B14, B15, B23, B20, B21, B24, B26, B16, B17, B27, B28, B18, B29, B25, B31, B30, B22.

Two bundles pair across tracks and should be merged in the same day: B08 and B23 (the header component and its first consumer), and B26 and B27 (the 2307 figures and the SAWT that reports them).

## 5. The bundles

Every bundle below is written to be pasted under the preamble. "Annex B" means the BIR's CAS checklist in RMC 5-2021 Annex B, as itemised in `docs/CONFORMANCE.md` (B01 creates that file from the ERPNext review).

### B01 Repository, bench, CI, bootstrap, reference docs (CAS-1)
- **Goal:** a repository anyone can clone and have a working ERPNext v16 site with `ph_cas` installed in one command, with CI proving it on every PR.
- **Read first:** `claude/ph-cas-build-plan-2026-10-24.md` (decisions, units); `claude/erpnext-bir-cas-review-2026-10-24.md` (the Annex B items and the seven locks); `claude/cas-owner-action-items-2026-11-06.md` section 1.
- **Build:**
  - `bench init` scripted in `scripts/bootstrap.sh`: Python 3.14 via `uv`, Node 24, `bench get-app` for frappe and erpnext at the pinned tags, `--skip-assets` for CI, `bench new-site test_site`, `install-app erpnext ph_cas`. Record the tags in `VERSIONS.md`.
  - `ph_cas` app skeleton: `hooks.py` with `required_apps = ["erpnext"]`, `after_install`, `patches.txt`, `ph_cas/setup/` for custom fields, `tests/` with one smoke test (the app installs; a Company can be created).
  - `docs/DECISIONS.md` carrying D1 to D11 and the POS decision with the status "recommended" or "confirmed".
  - `docs/CONFORMANCE.md`: every Annex B item, with the columns item, status (pending, built, verified), bundle, evidence.
  - `docs/reference/`: the project's rule catalogue, the review, the alphalist analysis and the DAT layouts copied in as Markdown (no BIR installers, no PDFs of forms with real data).
  - CI (GitHub Actions): MariaDB and Redis services, bootstrap, migrate, run-tests, and a check that fails on any em dash or en dash in `docs/`.
- **Tests:** smoke test; CI green on the PR.
- **Done when:** a fresh clone reaches a logged-in ERPNext site with `ph_cas` installed by running one script; CI runs the suite; `docs/CONFORMANCE.md` lists every Annex B item as pending.
- **Out of scope:** any control, any field.

### B02 Lock-down 1: nothing posted can be deleted or reposted (CAS-2 a, b, c, e)
- **Goal:** no user, Administrator included, can remove or regenerate a posted accounting document or its ledger rows.
- **Read first:** the review's lock features 1, 2, 3 and 4 (Delete Transactions; deleting cancelled vouchers; the ledger-deletion setting; Repost Accounting Ledger) with the file and line references.
- **Build:**
  - `on_trash` hooks on Sales Invoice, Purchase Invoice, Payment Entry, Journal Entry, Stock Entry, Delivery Note, Purchase Receipt and every other DocType that writes GL Entry or Stock Ledger Entry, refusing deletion when `docstatus` is 1 or 2, by anyone. Also refuse deletion of GL Entry, Stock Ledger Entry and Payment Ledger Entry rows directly.
  - Transaction Deletion Record: `before_insert` refuses creation; the Company form's "Delete Transactions" action hidden by a client script and blocked on the server.
  - Repost Accounting Ledger and Repost Item Valuation: `before_insert` refuses creation on a production site; the whitelisted entry points (`repost_accounting_ledger`, the `validate_accounts` path) are wrapped in an override that raises.
  - Accounts Settings: Immutable Ledger forced on and "Delete Accounting and Stock Ledger Entries on deletion of Transaction" forced off, with a `validate` hook on Accounts Settings that refuses to turn them back and a patch that sets them on migrate.
  - A `ph_cas.is_production_site()` helper read from `site_config.json` (`ph_cas_production: 1`); tests run with it off where the test needs to create data the lock would refuse.
- **Tests:** for each DocType, delete as Administrator fails after submit and after cancel; a cancelled Sales Invoice cannot be deleted even with the setting toggled; Transaction Deletion Record and Repost Accounting Ledger cannot be inserted; the settings patch is idempotent.
- **Done when:** every test passes, the Annex B items on data integrity and ledger permanence are ticked "built".
- **Out of scope:** editing posted fields (B03), dates (B04).

### B03 Lock-down 2: nothing posted can be changed or renumbered (CAS-2 d, f)
- **Goal:** a submitted document's accounting content cannot change, no automatic repost can be triggered, and no number can be reused.
- **Read first:** the review's notes on allow-on-submit fields and the automatic repost path; the naming-series number reuse and "Update Series Number".
- **Build:**
  - Property setters that turn `allow_on_submit` off on every accounting-relevant field of the accounting DocTypes (cost center, project, accounts, dimensions, due date and the like). Keep it on only for non-accounting notes fields, listed in `ph_cas/setup/allowed_on_submit.py` so the exception is explicit.
  - A `before_update_after_submit` hook that diffs the document against the database and refuses any change outside that list.
  - Document Naming Settings: "Update Series Number" refused on the server for any series used by an accounting DocType; `before_naming` guard that a reused name raises.
  - Deleting a draft that already consumed a number: leave ERPNext's draft deletion alone (drafts are not accounting documents) but log it (B07 will consume the log; here, write to the Frappe `Deleted Document` as normal and add a comment on the next document of that series).
- **Tests:** after submit, setting a cost center through the API fails; an amendment carries the `-1` suffix and the original stays cancelled; Update Series Number fails for `ACC-SINV-`; a repost is never created when a posted document is saved.
- **Done when:** tests pass; the Annex B items on modification of posted data are ticked "built".
- **Out of scope:** the BIR serial (B06).

### B04 Lock-down 3: dates, drafts, periods, inventory (CAS-2 g, h, i; D5, D7)
- **Goal:** documents carry the day they are posted, drafts cannot be printed as if they were invoices, closed periods stay closed, and stock cannot rewrite history.
- **Read first:** D5, D6, D7 in `docs/DECISIONS.md`; the review's note on stock re-valuation deleting and recreating GL rows (accounts/utils.py).
- **Build:**
  - Posting date rule: on submit, `posting_date` must equal today (site time zone Asia/Manila) for Sales Invoice, credit and debit notes and receipts; `set_posting_time` is refused. Journal Entries may be back-dated inside an open Accounting Period only by the role `Accounting Manager`, with the reason captured in a mandatory field.
  - Drafts: print formats of accounting documents render a full-page "DRAFT, NOT AN INVOICE" watermark when `docstatus = 0`; PDF and print endpoints refuse to print a draft Sales Invoice at all (the watermark covers the other DocTypes).
  - Accounting Period: creation and closing limited to `Accounting Manager`; a closed period refuses any posting, cancellation or amendment dated inside it, for every GL-writing DocType.
  - Inventory per D7: `Enable Perpetual Inventory` off on new companies and refused on; Stock Entry, Delivery Note and Purchase Receipt refuse a posting date earlier than today; Stock Reconciliation is limited to `Accounting Manager` and refuses back-dating; Repost Item Valuation already refused in B02.
- **Tests:** a Sales Invoice dated yesterday fails on submit; a Journal Entry dated inside a closed period fails; a draft Sales Invoice PDF request fails; a Stock Entry dated last week fails; perpetual inventory cannot be enabled.
- **Done when:** tests pass; Annex B items on posting dates and period control ticked "built".
- **Out of scope:** the printed layout (B20).

### B05 Security baseline (CAS-2 j)
- **Goal:** the sign-in controls the sworn statement describes.
- **Read first:** the review's lockout finding (Frappe locks only for 60 seconds after more than 10 failures in 60 seconds).
- **Build:** System Settings forced on migrate: two-factor authentication on (OTP app), "Allow only one session per user", password expiry 30 days, strong password policy; a `before_login` hook counting failures from the Authentication Log and deactivating the user after N failures (N = 5, a setting) with an email to the System Manager; reactivation only by a System Manager, logged. Settings refused off by a `validate` hook on System Settings.
- **Tests:** sixth failed sign-in deactivates; a second session evicts the first; the settings patch is idempotent.
- **Done when:** tests pass; the Annex B security items ticked "built".
- **Out of scope:** the event log (B07) records these events later; here they stay in Frappe's own logs.

### B06 BIR serial number (CAS-3)
- **Goal:** one gap-free counter per company, branch and document type, consumed at submit under a row lock.
- **Read first:** D4; the review's section on serials and the RDO 041 application's numbering remark.
- **Build:** DocType `BIR Series` (company, branch code, document type, prefix, next number, registered range start and end, date issued, ACCN); field `bir_serial` on Sales Invoice, Credit Note and Debit Note (ERPNext's `is_return` and `is_debit_note` invoices), Payment Entry used as a receipt, read-only, unique index; the counter taken inside the submit transaction with `SELECT ... FOR UPDATE`; a warning banner and an email when fewer than 500 numbers remain; the serial shown in list views and the standard print. Series are per branch (D4: 8 digits, continuous, no yearly reset).
- **Tests:** a concurrency test submitting 50 invoices in parallel threads yields 50 consecutive serials with no gap or duplicate; a failed submit does not consume a number; cancellation keeps the number; the range warning fires.
- **Done when:** tests pass; the Annex B numbering items ticked "built".
- **Out of scope:** what is printed around the serial (B20).

### B07 Hash-chained event log (CAS-4 part 1)
- **Goal:** an append-only record of every accounting-relevant event, each row carrying the previous row's hash.
- **Build:** DocType `PH Event Log` (timestamp, user, event, doctype, name, docstatus, details JSON, previous hash, hash); insert-only (no update, no delete, Administrator included, enforced in `on_trash` and `validate`); writers for create, submit, cancel, amend, print, PDF, export (report export and data export), sign-in, sign-out, failed sign-in, deactivation, settings changes (System Settings, Accounts Settings, Stock Settings), role and permission changes, BIR Series changes; a `verify_chain` method and a scheduled daily chain check that emails on a break.
- **Tests:** each event writes one row; updating or deleting a row fails; the chain verifies; tampering with a row's details breaks verification; 10,000 rows verify in under 10 seconds.
- **Done when:** tests pass.
- **Out of scope:** the printable report (B08).

### B08 Audit trail report and the Annex B print header (CAS-4 part 2)
- **Goal:** the printable "BIR Audit Trail" and the header every book, report and export carries.
- **Read first:** the Annex B header requirement (name, address, TIN-branch, software name and version, user, date and time printed) as listed in the review; D9.
- **Build:** script report `BIR Audit Trail` merging PH Event Log with Version, Deleted Document, Access Log and Activity Log, filterable by period, user and document, with a print format; `PH Chain Check` report; a Jinja macro `ph_header()` and a print-format include that renders the Annex B header from Company (B09 fields) and from `PH CAS Settings` (product name, version read from the app's `__version__`, "Printed by", "Printed on"); the same header written as the first lines of every CSV and Excel export produced by `ph_cas` reports.
- **Tests:** the report returns a merged, time-ordered list; the header macro renders every field; an export's first lines carry the header.
- **Done when:** tests pass; the Annex B audit-trail and header items ticked "built" (the product name item ticks only once D9 is set).
- **Out of scope:** books themselves (B23).

### B09 Philippine master data (CAS-5 part 1)
- **Goal:** every Philippine field the forms, books and DAT files need, on Company, Customer, Supplier, Item and the invoice lines.
- **Read first:** catalogue sections A and B; the alphalist analysis (payee name split, branch codes); the DAT layouts (name fields).
- **Build:** custom fields in code with a patch: Company (registered name, business style, TIN 9 digits plus branch code 5 digits, RDO code from a seeded RDO table built from the project's Annex M list, VAT status VAT / non-VAT / exempt, taxpayer classification per RR 8-2024, ACCN, date issued, registered address lines); Customer and Supplier (TIN, branch, registered name, payee type individual or non-individual, last, first and middle name for individuals, address lines, VAT status, top withholding agent flag, government flag, RBE flag, non-resident digital service provider flag); Item (VAT class VATable, exempt, zero-rated, with a default); Sales Invoice Item and Purchase Invoice Item (VAT class, overridable). Validation: TIN digits and check, branch code digits, name split required for individuals.
- **Tests:** each validation; the RDO table seeds; a Customer with a 5-digit branch stores and shows the 4-digit DAT form through a helper.
- **Done when:** tests pass; the Annex B master-data items ticked "built".
- **Out of scope:** accounts (B10), rates (B11 onward).

### B10 Philippine chart of accounts and account mapping (CAS-5 part 2)
- **Goal:** a chart a micro taxpayer's CPA recognises, and a mapping table the tax engine posts through.
- **Read first:** catalogue section C (accounts named there); the ERPNext chart-of-accounts loader.
- **Build:** a chart template `ph_micro` (standard ERPNext template format) with output VAT, input VAT by kind (goods, services, capital goods, importation), deferred input VAT, creditable withholding tax (2307s received), percentage tax payable, withholding tax payables by type (expanded, compensation, final, VAT), VAT payable, income tax payable, SC/PWD discount; DocType `PH Account Mapping` (company, purpose, account) filled on company setup; a setup wizard step or a one-click "Set up Philippine company" action that creates the chart, the mapping, the tax templates (empty of rates) and the BIR Series rows.
- **Tests:** the chart loads; the mapping is complete after setup; the action is idempotent.
- **Done when:** tests pass.
- **Out of scope:** any rate.

### B11 Tax rules table, resolver, sign-off check (CAS-5b core)
- **Goal:** the rules engine's spine: rules as dated data with a life cycle, and a resolver every later bundle calls.
- **Read first:** the catalogue's introduction (life cycle draft → CPA confirmed → coded), section H (open points), and the Portal's statute-table practice (`claude/portal-build-log-2026-10-10.md`, U5).
- **Build:** DocType `PH Tax Rule` (rule id, kind: vat, percentage, ewt, final, compensation, income, threshold, cap; ATC; rate; base; return and line; legal basis; effective from and to; status draft or confirmed; sign-off file reference); a fixture seeded from the catalogue with every rule as `draft` and the catalogue row id as the rule id; `resolve(kind, date, **selectors)` returning exactly one rule or raising; the production refusal (a draft rule resolved on a production site raises `PHDraftRuleError` naming the rule); a CLI `bench ph-cas sign-off docs/rules/SIGNOFF-<date>.md` that flips the listed ids to confirmed and records the file; a report listing draft rules.
- **Tests:** resolution by date picks the right version; overlapping effective dates refused; production refusal; the sign-off command flips only listed ids; the seed covers every catalogue row (count asserted).
- **Done when:** tests pass; the draft-rule report shows every rule as draft (expected).
- **Out of scope:** applying rules.

### B12 Sales side: VAT classes, output VAT, percentage tax (CAS-5b)
- **Goal:** a Sales Invoice computes VAT or percentage tax from the item's class and the company's status, through rules.
- **Read first:** catalogue section C (VAT: VATable, exempt, zero-rated, government sales), section D (percentage tax, 3 % and the thresholds); D8.
- **Build:** a `validate` hook on Sales Invoice that, for a VAT company, sets the tax rows from the line VAT classes (output VAT on VATable lines only; exempt and zero-rated lines tagged; government customer flag carried); for a non-VAT company, no VAT row and a percentage-tax accrual at period end (B17), with the base recorded per line; the VAT buckets (VATable sales, VAT amount, zero-rated, exempt) stored on the invoice for B20 and B16; a threshold watch report (VAT registration threshold reached in the last 12 months).
- **Tests:** mixed invoice buckets; a non-VAT invoice; a government customer; rule resolution by invoice date; the threshold watch.
- **Done when:** tests pass with draft rules on a non-production test site.
- **Out of scope:** withholding (B13), the print (B20).

### B13 Sales side: withholding by customers and 2307s received (CAS-5b)
- **Goal:** when a customer withholds, the invoice shows it, the receivable nets it, and the 2307 received is recorded for the income-tax credit.
- **Read first:** catalogue section E (customer withholding, RR 6-2026 "Less: Withholding Tax" from 16 Oct 2026, platform withholding RR 5-2025, government withholding); open points H2 and H3.
- **Build:** on Sales Invoice, a withholding block (ATC, rate from the rule, base, amount) filled when the customer is a withholding agent (top withholding agent, government, platform) or on request; the amount posted to creditable withholding tax at payment, not at invoice (configurable, default at payment); DocType `PH 2307 Received` (payor, period, ATC, base, tax, the 2307's quarter, attachment) with a report of unclaimed 2307s; both feed B16 (2550Q items for government withholding) and B18.
- **Tests:** a top withholding agent customer gets the block with the right ATC; payment posts the credit; the receivable is net; a 2307 Received ties to its invoices.
- **Done when:** tests pass.
- **Out of scope:** the "Less: Withholding Tax" line on paper (B21 prints what B13 computes).

### B14 Purchase side: input VAT, EWT by supplier profile, timing (CAS-5b)
- **Goal:** a Purchase Invoice books input VAT by kind and withholds expanded withholding tax from the supplier profile, at the right moment.
- **Read first:** catalogue section C (input VAT kinds, capital goods amortisation, mixed sales allocation H9) and section E (EWT by supplier type and ATC, timing at accrual or payment, the no-withholding flag).
- **Build:** input VAT rows by item kind (goods, services, capital goods over the threshold deferred, importation); EWT through ERPNext's Tax Withholding Category created one per ATC from the rules table (a generator, not hand entries), the category chosen from the supplier profile (individual or non-individual, professional, rent, goods, services, top withholding agent status of the company) with an override field; timing per rule (default: whichever comes first of accrual or payment, per the catalogue); a no-withholding flag with a mandatory reason; the withheld amounts tagged with ATC and period for B26 to B28.
- **Tests:** rent from an individual; professional fees; goods from a non-individual; a capital good deferred; the flag; timing when payment precedes the invoice.
- **Done when:** tests pass.
- **Out of scope:** reverse charge (B15).

### B15 Reverse-charge VAT: digital services and RBE purchases (CAS-5b)
- **Goal:** purchases from non-resident digital service providers (RA 12023, 1600-VT, WV080) and from registered business enterprises (RR 9-2025, RR 1-2026, WV110) post the VAT the buyer must remit.
- **Read first:** catalogue section C (reverse charge) and open point H10.
- **Build:** supplier flags from B09 drive a `validate` branch that books withholding VAT payable and, for a VAT company, the matching input VAT; the amounts tagged for the 1600-VT MAP (B28); rule ids for WV080 and WV110 resolved by date.
- **Tests:** a subscription from a non-resident provider; a purchase from an RBE; a non-VAT company's treatment (VAT is a cost).
- **Done when:** tests pass.

### B16 Period figures: 2550Q (CAS-5b)
- **Goal:** the quarter's 2550Q figures, item by item, from the ledger, matching eBIRForms.
- **Read first:** catalogue section C (2550Q items, output VAT credits and reversals under RR 3-2024, items 35, 36, 55, 58); the eBIRForms review (`claude/ebirforms-package-v7.9.6.2-review.md`) for the form's arithmetic.
- **Build:** DocType `PH Tax Return Figures` (company, form, period, items as a child table item number, label, amount, source) and a compute for 2550Q from B12, B13, B14, B15 postings; the carry-over of excess input VAT; the output VAT credit on uncollected receivables and its reversal; a print of the figures in item order (not the BIR form itself) and a CSV. Figures are computed, never typed; a typed adjustment row exists with a reason and is listed separately.
- **Tests:** a quarter's fixture (the dummy scenario set in action item 6.2) with expected item values from the catalogue's worked example; once the eBIRForms answers arrive (G6), the expected values are replaced by those and the test is marked verified.
- **Done when:** tests pass against the catalogue; "verified" waits on G6.

### B17 Period figures: 2551Q, 0619-E, 1601-EQ, 1600-VT; compliance calendar (CAS-5b)
- **Goal:** the remaining periodic returns a micro client files, and the dates they are due.
- **Read first:** catalogue sections D and E; the Portal's U17 rules (0619-E only months 1 and 2; 1601-EQ items 20 and 21 from the 0619-Es; due dates, weekend rule) as a second opinion, not as authority.
- **Build:** computes for 2551Q (base by ATC PT010 and others), 0619-E (months 1 and 2 of each quarter), 1601-EQ (the quarter net of the 0619-Es, per ATC), 1600-VT (B15 amounts per ATC); `PH Compliance Calendar` (form, period, due date, status computed from the figures' existence and a "filed" tick the user sets with the BIR confirmation reference, which stays a manual tick: filing is not integrated); the weekend-to-next-working-day rule and a holiday table seeded for the current year.
- **Tests:** each compute from the fixture; the calendar's due dates for a full year; a holiday move.
- **Done when:** tests pass against the catalogue; verified on G6.

### B18 Period figures: income tax (CAS-5b)
- **Goal:** 1701Q, 1702Q, 1701, 1701A and 1702-RT figures with MCIT, deduction caps, NOLCO and the book-to-tax reconciliation.
- **Read first:** catalogue section F (graduated rates, 8 % option, OSD, corporate rates, MCIT and its dates, NOLCO, interest arbitrage, caps) and open points H5, H7, H8.
- **Build:** computes per form from the ledger and B13's 2307 Received; the option flags on Company (8 %, OSD, itemised); MCIT comparison and carry-forward; NOLCO schedule DocType; a book-to-tax reconciliation report (permanent and temporary differences from tagged accounts); the figures stored in `PH Tax Return Figures`.
- **Tests:** an individual on 8 %; an individual on graduated with OSD; a corporation with MCIT higher than RCIT; NOLCO carried; the reconciliation ties.
- **Done when:** tests pass against the catalogue; verified on G6. If the session runs long, NOLCO and the reconciliation are the follow-up PR.

### B20 Invoice print formats and REPRINT (CAS-6 part 1)
- **Goal:** the paper and PDF a client hands a buyer, carrying everything RR 7-2024 requires, with "REPRINT" from the second print on.
- **Read first:** catalogue section B (invoice contents); the review's REPRINT discussion; B06 and B08.
- **Build:** print formats (Jinja, letter size) for Sales Invoice (VAT and non-VAT variants), Credit Note, Debit Note, Collection Receipt (supplementary, with "THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX"), each with: seller's registered name, business style, address, TIN-branch, VAT status; serial from B06; ACCN, series range and date issued; buyer block; VAT buckets from B12; "EXEMPT" where applicable; original and duplicate copy marks; the Annex B header on the duplicate. Print counting: a `PH Print Record` row per print, PDF or email of a submitted document (the event log already records it; this bundle adds the counter), and the word "REPRINT" with the count and the first print's date from the second print on. The rule for what counts as a print: any server-side render of the format for a submitted document.
- **Tests:** rendered HTML contains every required element for each variant; the second render shows REPRINT; a draft cannot render (B04).
- **Done when:** tests pass; Annex B invoice items ticked "built". The owner's print check (paper at 100 %) is listed in BUILD-LOG as pending.

### B21 Invoicing rules (CAS-6 part 2)
- **Goal:** the behaviours around the paper: when an invoice must be issued, the withholding line, buyer details thresholds, corrections.
- **Read first:** catalogue section B (₱500 non-VAT threshold, buyer details at ₱1,000 for VAT buyers, end-of-day invoice, corrections by credit and debit note; RR 6-2026); D6; RDO question 9 (default: keep the Collection Receipt available, off by default per company).
- **Build:** buyer TIN, name and address mandatory on a VAT company's invoice of ₱1,000 or more to a VAT-registered buyer; the "Less: Withholding Tax" line printed from B13 where applicable (from 16 Oct 2026 by rule date); an end-of-day summary invoice action for non-VAT sales under ₱500 not invoiced individually; corrections only through Credit Note and Debit Note referencing the original serial (amendment of a submitted invoice disabled); the Collection Receipt switched per company.
- **Tests:** each rule, including the date-driven withholding line and the disabled amendment.
- **Done when:** tests pass.

### B22 Senior citizen and PWD discounts (CAS-6b)
- **Goal:** the SC/PWD block: ID and OSCA or PWD number, the 20 % discount, the VAT exemption, the 5 % special discount where it applies, the signature line.
- **Read first:** catalogue section C (SC/PWD) and open point H4.
- **Build:** a discount block on Sales Invoice; the VAT-exempt treatment of the discounted sale; a report of SC/PWD sales for the deduction; the print block.
- **Tests:** a restaurant-style sale with the breakdown; the VAT bucket moves to exempt.
- **Done when:** tests pass. Scheduled after D8's "later".

### B23 Books 1: General Journal, General Ledger, Cash Receipts, Cash Disbursements (CAS-7)
- **Goal:** the four books of accounts as printable reports with the RR 9-2009 fields and the Annex B header, proven to tie to the ledger.
- **Read first:** the review's books section; B08.
- **Build:** four script reports with print formats, each paginated with page numbers, period, the header macro, running totals and a closing "tie" line; CSV and Excel exports with the header lines; a tie-out test helper comparing each book's totals with GL Entry sums.
- **Tests:** tie-out on a fixture; the header present on print and export; page numbering.
- **Done when:** tests pass; the Annex B books items for these four ticked "built".

### B24 Books 2: Sales Journal, Purchase Journal, Inventory Book (CAS-7)
- **Goal:** the remaining books, with the VAT and withholding columns the SLSP and the returns read from.
- **Build:** Sales Journal (per invoice: serial, customer TIN and name, VATable, exempt, zero-rated, output VAT, withholding); Purchase Journal (per bill: supplier TIN, kinds of input VAT, EWT by ATC); Inventory Book (periodic, from Stock Ledger Entry quantities and the valuation per D7); exports with headers; tie-out tests.
- **Tests:** tie-out; column sums equal B12 and B14 postings.
- **Done when:** tests pass; the remaining Annex B books items ticked "built".

### B25 Year-end e-books and transmittal (CAS-8)
- **Goal:** the RR 16-2006 files and the transmittal for the USB submission within 30 days after year-end.
- **Gate:** G7. Do not start until `docs/reference/rr16-2006-record-format.md` exists.
- **Build:** writers for each book in the record format; a year-end pack action producing the files, a manifest with hashes, and the transmittal letter (with a placeholder for the ORUS QR stamp step); a reader that parses the files back and ties them to the books.
- **Tests:** round trip; tie-out; the manifest's hashes.
- **Done when:** tests pass.

### B26 2307 on the BIR layout (CAS-9 part 1)
- **Goal:** the Certificate of Creditable Tax Withheld at Source printed on the BIR's blank from B14's withheld amounts.
- **Read first:** `claude/bir-2307-jan-2018-encs-reference.md`; the Portal's C7 field map (as a worked example of positioning on a blank).
- **Build:** DocType `PH 2307 Issued` (payee, quarter, months, ATC rows with base per month and tax) generated from B14's tagged amounts per payee per quarter, with manual regeneration refused once issued (cancel and reissue instead); a PDF overlay on the BIR blank (pypdf or reportlab over the project's `2307 Jan 2018 ENCS v3.pdf` as a committed blank, which is a government form and may be committed); the overlay's field map in a data file.
- **Tests:** generation groups by payee and ATC; the PDF has text at the mapped coordinates; reissue path.
- **Done when:** tests pass; the owner's print check on paper listed as pending.

### B27 DAT framework and SAWT (CAS-9 part 2)
- **Goal:** the shared DAT writer and validator harness, and the first file: SAWT for 2550Q, 2551Q, 1701Q, 1702Q, 1701 and 1702.
- **Read first:** `claude/bir-alphalist-module-7.4-analysis-2026-11-05.md` (file names per Annex B, record types, the Validation module's role); `claude/bir-dat-sample-layouts-2026-11-06.md` (SAWT layout: HSAWT, DSAWT, CSAWT; comma-delimited; CRLF; 2 decimals; unquoted empty name fields; rows sorted by TIN); RDO question 8a (the 2550Q form code, default 2550Q until answered).
- **Build:** `ph_cas/dat/` with a record writer (field order from a layout table per file type, quoting rules per layout, CRLF, amounts to 2 decimals), the file-name builder (TIN9 + branch 4 + MMYYYY + form), a golden-file test harness that compares byte for byte, and the SAWT builder from B13's 2307 Received; a "Generate alphalist" action per form and period with the file stored as an attachment and logged in the event log; the `docs/dat/VERIFICATION.md` file recording for each layout whether it is verified against the Validation module (G5).
- **Tests:** byte-for-byte against the sample layouts now; replaced by the golden files on G5.
- **Done when:** tests pass; VERIFICATION.md says "sample only" until G5.

### B28 QAP 1601-EQ, 1604-E, MAP 1600-VT (CAS-9 part 3)
- **Goal:** the withholding-agent side files.
- **Read first:** the DAT layouts doc (1601-EQ: HQAP, D1, C1, D2, C2 in one file, confirmed against the validator; 1604-E: H, D3, C3, D4, C4; MAP: HMAP, DMAP, CMAP); RDO questions 8b to 8d (defaults: 4-digit branch written from the 5-digit by dropping the leading zero when the code is 0000x, otherwise refused with a message; codes after 7.4 reported with the nearest listed ATC and flagged in a report).
- **Build:** the three builders from B14 and B15 tagged amounts; Schedule 2 (not subject, DI900 and EI900) from the no-withholding flag; annual 1604-E from the four quarters; a report of ATCs the module does not know.
- **Tests:** byte-for-byte against the layouts; the 1601-EQ against the validator's known rules.
- **Done when:** tests pass; VERIFICATION.md updated.

### B29 SLSP (RELIEF) (CAS-9 part 4)
- **Goal:** the summary lists of sales and purchases.
- **Read first:** the DAT layouts doc's RELIEF section (H,S / H,P / H,I headers, D rows, merged rows per TIN, the non-creditable input VAT prompt); G7 (the BIR's own format file, when it arrives, overrides the sample).
- **Build:** sales and purchases lists from B24's journals, merged per TIN; the importation list from Purchase Invoices flagged as imports (fields added here); the non-creditable amount taken from B14's allocation; file naming TIN9 + S/P/I + MMYYYY.
- **Tests:** byte-for-byte against the sample; verified on G5 and G7.
- **Done when:** tests pass; VERIFICATION.md updated.

### B30 Registration pack (CAS-10)
- **Goal:** everything the client's CAS application needs, generated from the site.
- **Read first:** the review's Annex B and C-1 sections; RMO 9-2021; the action items' section 7.5.
- **Build:** a "Registration pack" action producing: Annex C-1 drafted from Company and PH CAS Settings; sample prints of every invoice type (from a sample company fixture); each book's sample print; the audit-trail printout; the Annex B answers with remarks from `docs/CONFORMANCE.md` (only items marked built or verified are answered yes); the joint sworn statement prefilled with the firm's signatory (G10) and the client's; the conformance report for the pinned version; a zip with a manifest.
- **Tests:** the pack builds on the fixture; every Annex B "no" item appears in a gaps list, not silently.
- **Done when:** the pack builds; the gaps list is empty or each gap is an open owner item.

### B31 Hosting, backups, restore drill, runbooks (CAS-11)
- **Goal:** the operations that make D2 and D3 true.
- **Read first:** the review's backup finding (database only by default, pruned after about a day); D2, D3; the action items' data-privacy list.
- **Build:** provider-neutral scripts: one site per client; daily encrypted backup of database and private and public files to an off-site bucket in the Philippines (provider filled in on G9), retention ten years (the Annex B form's figure; EOPT's five is noted); a restore script and a monthly restore drill task with a logged result; monitoring (site up, backup age, chain check result, disk); two runbooks in `docs/runbooks/`: upgrades (minor: notice letter template; major: new application) and onboarding (site creation, Philippine setup action, opening balances through a locked opening Journal Entry, registration pack).
- **Tests:** backup and restore round trip in CI on a small site; the monitoring checks.
- **Done when:** tests pass; the runbooks reviewed by the owner.

## 6. Unit to bundle map

| Unit | Bundles |
|---|---|
| CAS-1 | B01 |
| CAS-2 | B02, B03, B04, B05 |
| CAS-3 | B06 |
| CAS-4 | B07, B08 |
| CAS-5 | B09, B10 |
| CAS-5b | B11 to B18 |
| CAS-6 | B20, B21 |
| CAS-6b | B22 |
| CAS-7 | B23, B24 |
| CAS-8 | B25 |
| CAS-9 | B26, B27, B28, B29 |
| CAS-10 | B30 |
| CAS-11 | B31 |
| CAS-12, 13, 14 | not bundled (see section 4) |

## 7. The first prompt, ready to paste

```
[the common preamble from section 2]

Bundle B01: repository, bench, CI, bootstrap, reference docs.

Goal: a repository anyone can clone and have a working ERPNext v16 site with
ph_cas installed in one command, with CI proving it on every PR.

Read first: docs/reference/ph-cas-build-plan.md (decisions, units),
docs/reference/erpnext-bir-cas-review.md (the Annex B items and the seven
locks), docs/reference/cas-owner-action-items.md section 1. If docs/reference
is empty, the four reference files are attached to this prompt; copy them in
as the first commit.

Build:
1. scripts/bootstrap.sh: Python 3.14 via uv, Node 24, bench init, bench
   get-app frappe and erpnext at the tags in VERSIONS.md (write it: ERPNext
   v16.54.0, Frappe v16.55.2, or the latest v16 tags on the day, recorded),
   --skip-assets for CI, bench new-site test_site, install-app erpnext ph_cas.
2. The ph_cas app skeleton: hooks.py with required_apps = ["erpnext"],
   after_install, patches.txt, ph_cas/setup/, tests/ with one smoke test (the
   app installs; a Company can be created).
3. docs/DECISIONS.md with D1 to D11 and the point-of-sale decision, each
   marked "recommended" (the owner changes it to "confirmed").
4. docs/CONFORMANCE.md: every RMC 5-2021 Annex B item from the review, columns
   item, status (pending, built, verified), bundle, evidence. All pending.
5. docs/BUILD-LOG.md with the B01 entry.
6. CI (GitHub Actions): MariaDB and Redis services, bootstrap, migrate,
   run-tests, and a check that fails on any em dash or en dash under docs/.

Tests: the smoke test; CI green on the PR.

Done when: a fresh clone reaches a logged-in ERPNext site with ph_cas
installed by running one script; CI runs the suite; CONFORMANCE.md lists every
Annex B item as pending.

Out of scope: any control, any field, any rule.
```

## Sources
- `claude/ph-cas-build-plan-2026-10-24.md` (units CAS-0 to CAS-14, decisions, order)
- `claude/cas-owner-action-items-2026-11-06.md` (gates)
- `claude/erpnext-bir-cas-review-2026-10-24.md` (lock features and Annex B items)
- `claude/ph-tax-rules-catalogue-2026-10-26.md` (rules and open points H1 to H12)
- `claude/bir-alphalist-module-7.4-analysis-2026-11-05.md` and `claude/bir-dat-sample-layouts-2026-11-06.md` (DAT files)
- `claude/portal-build-log-2026-10-27.md` (track practice: merge main first, squash merges, pair the halves of a contract)
- ERPNext v16 `pyproject.toml` (requires-python >=3.14; frappe >=16.50.0,<17.0.0) and Frappe v16 `pyproject.toml` and `package.json` (Python >=3.14,<3.15; Node >=24), read from the local clones on 6 Nov 2026; tags from `git ls-remote` the same day.
