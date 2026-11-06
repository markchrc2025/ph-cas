# CAS on ERPNext: the owner's action items before development (6 Nov 2026)

Prepared by Claude at the owner's request.
- **What it is:** every open item that only the owner, the firm's CPA or the BIR can close, gathered in one place.
- **Gathered from:** the build plan, the tax-rules catalogue, the ERPNext review and the alphalist analysis.
- **What it replaces:** the build plan's "What only the owner does" and "Questions for the RDO" lists. The RDO questions keep their numbers.
- **"Needed for":** the build unit in `claude/ph-cas-build-plan-2026-10-24.md` that waits for the item.

## What actually blocks the start
- **Before the first unit (CAS-1, repository and development setup):**
  - decisions D1 and D2;
  - a private code repository.
- **Before the second unit (CAS-2, the lock-down):**
  - decisions D4 to D8;
  - the point-of-sale decision.
- **Everything else** can run alongside development. The letter to the RDO and the CPA review take the longest, so start them now.

## 1. Decide
| # | Decision | Recommendation | Needed for |
|---|---|---|---|
| D1 | ERPNext version | Version 16, fixed at one release | CAS-1 |
| D2 | Delivery | The firm hosts it, one site per client; no copies on client servers | CAS-1, CAS-11 |
| D3 | Server location | Servers and backups in the Philippines | CAS-11 |
| D4 | Invoice numbers | 8 digits, continuous (no yearly reset), one series per document type per branch | CAS-3 |
| D5 | Dates | Invoices and receipts carry the day they are posted | CAS-2 |
| D6 | Corrections | Cancel and reissue, or an adjusting journal entry; never rewrite the ledger | CAS-2 |
| D7 | Inventory | Perpetual inventory off at first; back-dated stock entries blocked | CAS-2, CAS-5 |
| D8 | First clients | Micro taxpayers, VAT and non-VAT; senior citizen/PWD discounts and payroll later | CAS-6, CAS-12 |
| New | Point of sale | Leave ERPNext's point-of-sale screen out of release 1; invoices are issued from the back office (reason below) | CAS-2, CAS-6 |
| D9 | Product name | Your choice, without "ERPNext" (trademark). The code keeps a neutral internal name, so this doesn't block coding. | CAS-10 |
| D10 | Signatory | The officer who signs every client's joint sworn statement | CAS-10 |
| D11 | E-invoicing route | Later, after the e-invoicing spec spike: connect directly or through a service provider | CAS-13 |
| Later | Payroll | In or out of the product | CAS-14 |

**Why point of sale is a separate decision.**
- **What RMO 24-2023 covers.** The RMO 24-2023 checklist saved in the project covers accreditation of cash register machines, POS, bundled POS and "Sales Receipting System Software".
- **What it asks for:**
  - an online application through eAccReg;
  - X and Z readings;
  - an e-journal;
  - sample receipts for every discount type;
  - a sworn statement from the supplier.
- **What that means here.** Selling a counter POS would likely put the firm under that accreditation, on top of each client's CAS registration. RDO question 10 asks where the line is.

## 2. Set up
1. **Code repository.** Create a private GitHub repository for the app and connect it to this workspace, so the build sessions can push to it. Keep the eBIRForms and Alphalist installers out of it. (Needed for CAS-1.)
2. **The CPA.** Engage your CPA formally for the tax-rules review in section 4: scope, fee and turnaround. (Needed for CAS-5b.)

## 3. Send the RDO one letter
Send it now: written answers take weeks and several units wait for them. Questions 1 to 8 keep the build plan's numbers. The alphalist questions (8a to 8e) may be passed to the BIR head office.

1. **E-invoicing (RMC 98-2026, Sec. III):** are micro taxpayers using a CAS excluded? Are small and medium CAS users covered even if they don't issue electronic invoices? (D8, CAS-13)
2. **Numbering:** is one continuous series per document type per branch, with no yearly reset, acceptable as the AC's series range? (CAS-3)
3. **Hosting:** servers and backups would be in the Philippines, run by the firm. Is a notice of third-party custody needed under RR 9-2009, and to whom? (CAS-11)
4. **Updates:** which ERPNext or app updates count as minor (written notice) and which as major (new application)? (CAS-11)
5. **E-books:** what are the exact file format, layout and submission channel under RR 16-2006 and RMO 9-2021? (CAS-8)
6. **The firm's own registration:** does the firm, as the software provider, need to register anything itself? (CAS-10)
7. **Retention:** EOPT says five years, the Annex B form ten. Which governs the sworn statement? (CAS-11)
8. **Alphalists** (CAS-9):
   - a. SAWT for 2550Q: which form code does module 7.4 expect? Its annex lists 2550M, not 2550Q.
   - b. Branch code: alphalist files take 4 digits, the forms 5. How is a 5-digit branch code written in a DAT file?
   - c. Codes created after version 7.4 (WI/WC 840 to 860, WV080 to WV110): how should they be reported until the module is updated?
   - d. WI/WC 820, 830 and 156: which base and rate does the validator expect since RR 5-2025?
   - e. What separator, quoting and line ending do DAT records use?
9. **Collection receipts:** after EOPT, does a client still need a supplementary collection receipt, or only invoices and credit and debit notes? (CAS-6)
10. **Point of sale:** does invoicing from the back office stay under RMO 9-2021 alone? If a client issues invoices at a counter through the system, does it become sales machine software needing accreditation under RMO 24-2023? (the point-of-sale decision, CAS-6)

## 4. Have the CPA sign off the tax rules
- **What to review:** `claude/ph-tax-rules-catalogue-2026-10-26.md` (v1.1), row by row. The CPA confirms or corrects each rate, base and effective date, and no rule is coded before that. (Needed for CAS-5b and CAS-9.)
- **The twelve open points (section H):**
  1. E-invoicing coverage of non-micro CAS users (also RDO question 1).
  2. RR 6-2026: what "applicable" means for the "Less: Withholding Tax" line, and the transition for system-generated invoices.
  3. RR 5-2025: whether the ₱500,000 threshold and the sworn declaration for online sellers survive.
  4. Senior citizen/PWD: the Joint Administrative Order's number, and the base of the 20% discount.
  5. NOLCO for taxpayers on OSD.
  6. The ATC for each withholding category; the rates and ATCs of tax withheld by government.
  7. The effective date of the 20% interest-arbitrage rate.
  8. The Sec. 232 audit threshold, from the statute's text.
  9. Input VAT allocation for mixed sales.
  10. The RR 1-2026 amendment to RR 9-2025, and ATC WV110.
  11. Debit notes for invoices that are not e-invoices.
  12. Retention: five or ten years (also RDO question 7).
- **The Portal gets answered too.** The same review answers the Portal's statute-table questions (U5): percentage tax dates, the TRAIN tables, the 8% option, corporate rates, MCIT dates and VAT.

## 5. Collect documents and specifications
1. RMC 61-2024 Annexes A and B: the alphalist file structures for MAP, QAP, 1604-C, 1604-E and 1604-F. (CAS-9)
2. RMC 25-2024 Annexes A and B. (CAS-9)
3. RMC 15-2025 Annex A, complete: your copy stops partway through the SAWT control record. (CAS-9)
4. The BIR's module and file format for the summary lists of sales and purchases. (CAS-9)
5. The RR 16-2006 e-books record format, and the RMO 9-2021 submission requirements. (CAS-8)
6. The e-invoicing technical specifications: register on the BIR's EIS certification portal. (CAS-13)
7. RMO 24-2023 itself, only if point of sale comes into scope; you have its annexes. (Point-of-sale decision)
8. Before each filing season: check for an alphalist module newer than 7.4. (Ongoing)

## 6. Produce test material (on a Windows PC, dummy data only)
Claude can write the dummy scenarios so they cover every case in the catalogue; you run them.
1. **Alphalist golden files** (CAS-9):
   - type dummy payees into the BIR Alphalist Data Entry module;
   - generate the QAP (1601-EQ), 1604-E, SAWT (2550Q, 2551Q, 1701Q, 1702Q) and MAP (1600-VT) files;
   - run each through the Validation module;
   - keep the files and the reports.
2. **eBIRForms expected answers** (the tests in CAS-5b):
   - for each return the tax engine feeds (2550Q, 2551Q, 1601-EQ, 1701Q, 1702Q and the annual returns), enter a dummy scenario in eBIRForms the normal way;
   - save the result: the saved file, and a screenshot of the computed tax.

## 7. Before the pilot
1. **Pilot client:** a micro client willing to run a full quarter on the system, or the firm's own books. (CAS-12)
2. **Client contract,** reviewed by a lawyer. It covers:
   - registration being cancelled when a client leaves;
   - data hand-back;
   - retention;
   - hosting terms and fees.
   (CAS-12)
3. **Data privacy.** As the host, the firm processes its clients' payee and employee data. (CAS-11)
   - Appoint a data protection officer.
   - Put a data processing agreement in the client contract.
   - Check whether NPC registration applies to the firm.
4. **Hosting provider:** a provider in the Philippines for production servers and backups (D3). (CAS-11)
5. **Optional:** contact the RDO 041 applicant who registered ERPNext v15. Ask for their AC, Annex B answers, Annex C-1, a sample invoice and the audit-trail printout. (CAS-10)

## Sources
- `claude/ph-cas-build-plan-2026-10-24.md` (decisions D1 to D11; units)
- `claude/ph-tax-rules-catalogue-2026-10-26.md` (section H)
- `claude/erpnext-bir-cas-review-2026-10-24.md` (open questions; the RDO 041 application)
- `claude/bir-alphalist-module-7.4-analysis-2026-11-05.md` (documents to collect; alphalist questions)
- `claude/portal-build-log-2026-10-10.md` (U5 statute-table questions)
- `13 BIR Templates/RMO 24-2023 Annex B_Checklist of Documentary Requirements v2.docx`
