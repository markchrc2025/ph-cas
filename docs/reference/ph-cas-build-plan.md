# Philippine CAS on ERPNext: build plan (2026-10-24)

Prepared by Claude after the owner's decision of 24 Oct 2026: the firm will offer clients a CAS built on ERPNext. Read it with `claude/erpnext-bir-cas-review-2026-10-24.md`, which holds the code evidence behind every item here.

## The decision
- **What the firm will sell.** Clients get a CAS built from three parts:
  - ERPNext, unchanged;
  - the firm's own Philippine compliance app;
  - hosting, support and the BIR registration paperwork for each client.
- **Registration is per client.** Each client registers its own system and receives its own Acknowledgment Certificate (AC).
- **The firm signs with every client.** As the third-party software provider, the firm signs a joint sworn statement with each client (RMO 9-2021, Sec. V.6). It includes the statement that the system has no facility that may suppress sales.
- **A client who leaves loses its registration.** Ending the contract with a client cancels that client's registration (same section).

## What gets built
A separate Frappe app (working name `ph_cas`; the product name may not contain "ERPNext"), installed on one pinned ERPNext v16 release. It has nine parts, plus hosting and operations:
1. **Lock-down.** Nothing posted can be deleted, re-pointed or renumbered, not even by an administrator.
2. **BIR serial.** Invoice numbers are issued at posting, without gaps.
3. **Event log and audit trail.** A tamper-evident event log and a printable BIR audit trail.
4. **Philippine setup and tax engine.** TIN and branch, RDO, AC details, chart of accounts, and every rule in the tax-rules catalogue (`claude/ph-tax-rules-catalogue-2026-10-26.md`). The rules are applied at invoice, bill, payment and period-end, so the system is ready to use for MSMEs.
5. **Invoice set.** Invoices, credit and debit notes and receipts that meet RR 7-2024.
6. **Books.** The books of accounts in BIR format, with the Annex B header.
7. **Withholding.** The 2307 certificate and the BIR attachment files (QAP, SAWT, SLSP).
8. **Year-end e-books.** The annual electronic books file.
9. **Registration pack and conformance tests.** The registration pack, plus an automated test for every Annex B item.
10. **E-invoicing (EIS)**, later, for clients who need it.

## Who the first release is for
- **The e-invoicing deadline.** E-invoicing is mandatory by 31 Dec 2026 for covered taxpayers, and **micro taxpayers are excluded** (RMC 98-2026; BIR press release of 23 Sep 2026). Micro means gross sales under ₱3 million (RR 8-2024).
- **The open question.** Small and medium clients may become covered just by using a CAS. RMC 98-2026 Sec. III covers "taxpayers using CAS or CBA with Accounting Records (with electronic invoicing), and other invoicing software". The independent check of 26 Oct reads that as covering non-micro clients who invoice from a CAS. Plan on that reading until the RDO answers question 1.
- **What follows.** The first release is for micro clients, and for anyone else the RDO confirms is not covered. E-invoicing (CAS-13) comes before selling to covered clients. Getting a brand-new product EIS-certified for clients by 31 Dec 2026 is not realistic.

## Where the BIR logic comes from
- **What the CAS does.** It applies every Philippine tax rule to the books: VAT, percentage tax, withholding and income tax. It then produces the figures and BIR files each return needs. Filing stays outside it. The rules are listed, with sources and open questions, in `claude/ph-tax-rules-catalogue-2026-10-26.md`.
- **Its rules come from the BIR's public sources:**
  - the Tax Code and regulations (RR 7-2024 for invoices, RR 9-2009 for books and electronic records, the withholding regulations for ATCs and rates);
  - the guidelines printed on the forms themselves;
  - the BIR's published file layouts (alphalist, SLSP, e-books);
  - the EIS specifications from the certification portal.
- **Not from the Offline eBIRForms package.**
  - Its terms (`tosa.html`, read on 24 Oct 2026) say the package is for personal, non-commercial use. They prohibit copying, reproducing or creating derivative works from any information in it, for a fee or otherwise, and say tampering will be dealt with under the law.
  - Under the IP Code (RA 8293, Sec. 176.1), works of the government carry no copyright, but exploiting them for profit needs the prior approval of the agency that made them, which may charge royalties.
  - A product that resells logic or data taken from the package would need the BIR's approval first. The plain data files the 6 Oct reference workbook came from fall under the same clause, so anything the firm ships takes its codes and rates from the issuances instead.
- **How the package is used.**
  - Its release notes serve as an index of every rule change the BIR built into its forms. The 26 Oct catalogue checked each MSME-relevant entry against the issuances.
  - eBIRForms is the test oracle: the same figures entered in the normal way must give the same tax due.
  - The pilot compares the CAS's figures with the returns filed through eBIRForms in the normal course.
  - The BIR's tax software provider route (eTSP) gives the XML specifications for e-filing.
  - A written request to the BIR covers any specific use of the package's content the firm wants.
- **The re-uploaded package.** `Offline_eBIRForms_Package_v7.9.6.2.1.zip` (uploaded 24 Oct 2026) is the same v7.9.6.2 package reviewed on 9 Oct: its latest release note is v7.9.6.2. It stays out of the CAS repo.
- **The Alphalist Data Entry and Validation module** (version 7.4, reviewed 5 Nov 2026) stays in the filing workflow:
  - Its Validation program checks every DAT file the CAS writes and makes the eSubmission copy.
  - Its Data Entry program makes the golden files for testing.
  - The DAT layouts come from the RMC annexes, not from the module's code (`claude/bir-alphalist-module-7.4-analysis-2026-11-05.md`).
  - Its installer carries leftover payee data, so it stays out of the CAS repo too.

## Proposed decisions (owner to confirm)
| # | Decision | Recommendation | Why |
|---|---|---|---|
| D1 | ERPNext base | v16, one pinned tag | v16 blocks deleting cancelled transactions under Immutable Ledger; v15 does not. Each client's AC is tied to the version. |
| D2 | Delivery | Firm-hosted, one site per client. No copies installed on client servers in the first release. | The no-suppression oath holds only if the firm keeps the administrator accounts. Hosted use is not "conveying" under GPL-3.0, so the app can stay private. |
| D3 | Where it runs | Servers and backups in the Philippines | RR 9-2009 asks that records and their backups stay in the Philippines, with prior notice to the BIR when a third party keeps them (summary via jur.ph; confirm with the RDO). |
| D4 | Invoice numbers | A BIR serial taken at posting from its own counter: continuous (no yearly reset), 8 digits, one series per document type (invoice, credit note, debit note, collection receipt) per branch | Drafts never consume or hand back numbers; an amendment gets a new number. |
| D5 | Dates | Invoices and receipts carry the day they are posted. Journal entries may be dated inside an open period; the entry time is kept and shown in the audit trail. | Annex B 10b. |
| D6 | Corrections | No ledger reposting. Corrections are made by cancel-and-reissue or an adjusting journal entry. | RR 9-2009: changes to recorded transactions go through a journal entry. Removes the repost paths. |
| D7 | Inventory | Clients with stock start with perpetual inventory off: the stock ledger is kept, and the ledger is adjusted by period-end entries. Back-dated stock transactions are blocked. | With perpetual inventory on, re-valuing stock deletes and re-creates the ledger rows of later stock vouchers (`accounts/utils.py:1699-1738`). |
| D8 | First market | Micro clients, VAT and non-VAT, goods and services. Senior citizen/PWD discounts and payroll come later. | E-invoicing exclusion; the smallest scope a client can register. |
| D9 | Product name | Owner's choice, without "ERPNext" | ERPNext trademark policy |
| D10 | Signatory and contract | One officer signs the joint sworn statements. The client contract covers cancellation on exit, data hand-back and record retention: five years under EOPT, ten while the Annex B form says so. | RMO 9-2021 Sec. V.6 |
| D11 | EIS route | Decide after the spec spike: connect directly to the EIS, or through an accredited e-invoicing service provider once the BIR issues those rules | RMC 98-2026 allows both. |

## Units
- **Same practice as the Portal.** Each unit merges itself, with its tests seen to fail first.
- **Annex B coverage.** Every Annex B item gets at least one automated test. The suite's report goes into each client's registration pack and backs each change notice to the RDO.

| Unit | Content | Depends on | Size |
|---|---|---|---|
| CAS-0 | Owner decisions D1 to D11; written questions to the RDO (below); collect specs: the RR 16-2006 record format for e-books; the BIR alphalist file layouts (RMC 61-2024 and RMC 25-2024 Annexes A and B for MAP, QAP and 1604-C/E/F; the complete RMC 15-2025 Annex A for SAWT; see `claude/bir-alphalist-module-7.4-analysis-2026-11-05.md`); the SLSP format; the EIS technical specs (EIS certification portal) | None | S |
| CAS-1 | Repo and bench: private repo; app skeleton; pinned v16 bench (Frappe and ERPNext tags); CI with MariaDB and Redis; the Annex B conformance file listing every item as pending | CAS-0 (D1, D9) | S |
| CAS-2 | Lock-down: (a) no deletion of submitted or cancelled accounting documents by anyone, Administrator included; (b) Company → Delete Transactions blocked; (c) Repost Accounting Ledger blocked; (d) allow-on-submit off on accounting fields, so posted documents cannot be re-pointed and never trigger automatic reposts; (e) Immutable Ledger forced on, ledger deletion forced off; (f) transactional series counters protected; (g) drafts not printable; (h) Accounting Periods limited to one role; (i) back-dating blocked per D5 and D7; (j) security baseline: two-factor sign-in, one session per user, password change every 30 days, and deactivation after N failed sign-ons (Frappe only locks for 60 seconds; built on the `before_login` hook and the authentication log) | CAS-1 | M |
| CAS-3 | BIR serial: one counter per company, branch and document type, taken under a row lock at submit so it commits or rolls back with the document; field on Sales Invoice, credit and debit notes and receipts; unique; shown in lists and prints; warning before the registered range runs out; a concurrency test proving no gaps or duplicates | CAS-2 | M |
| CAS-4 | Event log and audit trail: an append-only log in which each row carries the previous row's hash. It records create, submit, cancel, amend, print, reprint, export, sign-in, settings changes and role changes. A printable "BIR Audit Trail" report merges it with Version, Deleted Document, Access Log and Activity Log; a chain-check report verifies it | CAS-2 | M |
| CAS-5 | Philippine setup: Company (registered name, business style, TIN, branch code, RDO, VAT status, ACCN, date issued, series ranges); Customer and Supplier (TIN-branch, registered name); VAT class on items and lines (VATable, exempt, zero-rated, government); a Philippine chart of accounts (creditable withholding tax, deferred input VAT, input VAT by kind, percentage tax payable, withholding payables); tax templates | CAS-1 | M |
| CAS-5b | Tax engine. Rules stored as dated data (rate, base, ATC, return line, legal basis, effective dates), confirmed by the CPA before coding. Applied at invoice (VAT classes, government sales, percentage tax, SC/PWD, platform withholding received, 2307s received), at bill and payment (input VAT, EWT by supplier profile and its timing, reverse-charge VAT on digital services and on purchases from registered business enterprises), and at period-end. Period figures for each return: VAT with output VAT credits and reversals, percentage tax, EWT with QAP, 1600-VT, income tax with MCIT, deduction caps, NOLCO, book-to-tax reconciliation. A compliance calendar. Each computation tested against eBIRForms with the same figures. | CAS-5; catalogue sign-off | L |
| CAS-6 | Invoice set (RR 7-2024 as amended by RR 6-2026): Sales Invoice (VAT and non-VAT; non-VAT at ₱500 or more, on request, or end-of-day), Credit Note, Debit Note, supplementary Collection Receipt ("THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX"); creditable withholding shown as a separate "Less: Withholding Tax" item where applicable (from 16 Oct 2026); buyer name, address and TIN for sales of ₱1,000 or more to VAT-registered buyers; VAT buckets; "EXEMPT"; ACCN, series range and date issued; "REPRINT" from the second print on, after a rule for what counts as a print (PDF, browser print, e-mail); original and duplicate copies | CAS-3, CAS-4, CAS-5 | M |
| CAS-6b | Senior citizen and PWD discounts: ID and OSCA number, the 20 % / VAT-exempt / 5 % breakdown, signature line | CAS-6 | S |
| CAS-7 | Books, with the RR 9-2009 fields: General Journal, General Ledger, Sales Journal, Purchase Journal, Cash Receipts and Cash Disbursements Books, Inventory Book. Every print and export carries the Annex B header (name, address, TIN-branch, software and version, user, date-time). Tests prove each book ties to the ledger | CAS-5 | M |
| CAS-8 | Year-end e-books: files in the RR 16-2006 record format for the USB submission within 30 days after year-end; the transmittal letter, with the ORUS QR-stamp step | CAS-7; spec from CAS-0 | M |
| CAS-9 | Withholding: one Tax Withholding Category per ATC with dated rates, taken from BIR issuances and the 2307 form's own ATC schedule, with rates and dates confirmed by the owner (the same answers U5 needs); 2307 printed on the BIR layout; capture of 2307s received; alphalist DAT files named per RMC 15-2025 Annex B: QAP for 1601-EQ, the annual 1604-E, SAWT for 2550Q, 2551Q, 1701Q/1701 and 1702Q/1702, MAP for 1600-VT. Each file goes through the BIR Validation module, which also makes the eSubmission copy. Tests compare with golden files generated in the BIR Data Entry module from dummy data. SLSP files. | CAS-5; specs from CAS-0 | M |
| CAS-10 | Registration pack: Annex C-1 drafted from the site's setup; sample prints of every invoice type and book; the audit-trail printout; Annex B answers with remarks; the Annex C or E sworn statement prefilled; the conformance report for the pinned version | CAS-2 to CAS-9 | S |
| CAS-11 | Hosting and operations: servers in the Philippines, one site per client; daily encrypted backups of database and files, kept ten years (the Annex B form's figure; EOPT requires five); a restore drill; monitoring. Two runbooks: upgrades (minor: notice letter; major: new application) and onboarding (site, opening balances, registration) | CAS-0 (D2, D3) | M |
| CAS-12 | Pilot: one micro client, or the firm's own books, registered; a full quarter run on it, with returns filed from it; fixes; then the year-end e-books | CAS-10, CAS-11 | n/a |
| CAS-13 | E-invoicing: PTI application; EIS certification-portal onboarding; JSON per the BIR schema; signing; transmission queue and retries; QR code; credit-note corrections; certification within six months of the PTI | CAS-6; specs from CAS-0; D11 | L |
| CAS-14 | Payroll and 2316 (HRMS plus Philippine payroll), only if the owner decides to offer payroll | None | L |

## Order
1. CAS-0 and CAS-1.
2. The controls that make the sworn statement true: CAS-2, CAS-3, CAS-4.
3. What a client sees and files: CAS-5, CAS-5b, CAS-6, CAS-7, CAS-9.
4. The registration pack and hosting (CAS-10, CAS-11), then the pilot (CAS-12).
5. CAS-8 before the pilot's first year-end; the e-books are due 30 days after it.
6. In parallel from the start: the EIS spec spike, so CAS-13 can start as soon as the specs are in hand.

## Build bundles
Re-cut on 6 Nov 2026 into 31 one-prompt bundles (B01 to B31) in `claude/cas-build-bundles-2026-11-06.md`. That file carries the common prompt preamble, the gates, the dependency order, three parallel tracks and the unit-to-bundle map. The units above remain the description of scope; the bundles are how they are built.

## What only the owner does
Moved on 6 Nov 2026 to `claude/cas-owner-action-items-2026-11-06.md`. That file holds the decisions, setup, CPA review, documents to collect, test material and pilot preparation, each tagged with the unit that waits for it.

## Questions for the RDO
Moved to `claude/cas-owner-action-items-2026-11-06.md`, section 3, as one letter. Questions 1 to 8 keep their numbers. Question 9 (collection receipts) and question 10 (point of sale under RMO 24-2023) are new.

## Risks
- **Upgrades become a planned yearly event.** Every major ERPNext upgrade means a new application for every client.
- **The firm co-signs every client's sworn statement.** A gap in the lock-down is the firm's exposure, not only the client's.
- **Some rules need the RDO's comfort.** REPRINT, posting dates, numbering and periodic inventory are where the pilot tests that.
- **CAS-13 is not sized yet.** The EIS specs and the e-invoicing service provider rules are still arriving, so its size is uncertain until the spike.
- **New stack.** ERPNext is Python on Frappe, while the Portal is TypeScript. Expect a learning curve in CAS-1 and CAS-2.

## Sources
- RMO 9-2021 (text via KPMG): https://assets.kpmg.com/content/dam/kpmg/ph/pdf/InTAX/2021/RMO%20No.%209-2021.pdf
- RMC 98-2026: https://bir-cdn.bir.gov.ph/BIR/pdf/RMC%20No.%2098-2026%20redacted.pdf ; BIR press release of 23 Sep 2026: https://bir-cdn.bir.gov.ph/BIR/pdf/PR101SEP2326.pdf
- RR 8-2024 thresholds (PwC Tax Alert 20): https://pwc.com/ph/en/tax/tax-publications/tax-alerts/2024/tax-alert-20.html
- RR 9-2009 (summary): https://jur.ph/law/summary/maintenance-retention-submission-electronic-records
- RR 7-2024 invoice requirements: https://teamenergy.ph/file-manager/files/Notice%20to%20Suppliers_EOPT%20Invoicing%20Requirements.pdf
- EIS onboarding overview (vendor; no BIR spec): https://rtcsuite.com/bir-e-invoicing-philippines-eis-by-2026-a-comprehensive-guide-to-scope-stages-and-technical-compliance/
- IP Code Sec. 176 (summary): https://ndvlaw.com/does-copyright-subsist-in-works-of-the-government/
- Offline eBIRForms package v7.9.6.2, terms of service (`app/xml/tosa.html` inside the installer, read statically)
- ERPNext source: https://github.com/frappe/erpnext (develop 7d3361c; version-16 ade850b)
