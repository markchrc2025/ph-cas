# Decisions

Status: recommended (Claude's recommendation, not yet confirmed) or confirmed (the owner confirmed it, with the date). A bundle takes the recommendation when a decision is still "recommended" and records that under "Assumed" in docs/BUILD-LOG.md.

| # | Decision | Choice | Status |
|---|---|---|---|
| D1 | ERPNext version | Version 16, pinned (see VERSIONS.md) | recommended |
| D2 | Delivery | The firm hosts it, one site per client; no copies on client servers | recommended |
| D3 | Server location | Servers and backups in the Philippines | recommended |
| D4 | Invoice numbers | 8 digits, continuous, no yearly reset; one series per document type per branch | recommended |
| D5 | Dates | Invoices and receipts carry the day they are posted | recommended |
| D6 | Corrections | Cancel and reissue, or an adjusting journal entry; never rewrite the ledger. Issued invoices, credit notes and debit notes are never cancelled: they are corrected by a credit or debit note (B21, B46) | recommended |
| D7 | Inventory | Perpetual inventory off at first; back-dated stock entries blocked | recommended |
| D8 | First clients | Micro taxpayers, VAT and non-VAT; SC/PWD discounts and payroll later | recommended |
| POS | Point of sale | ERPNext's point-of-sale screen out of release 1; invoices from the back office | recommended |
| D9 | Product name | Owner's choice, without "ERPNext"; the code uses "PH CAS" until then | open |
| D10 | Signatory | The officer who signs every client's joint sworn statement | open |
| D11 | E-invoicing route | After the EIS spec spike | open |
| Later | Payroll | In or out of the product | open |

## RDO questions answered by the owner (14 Nov 2026)

No letter to the RDO: the owner answered the questions directly. Numbers follow the action items (section 3), plus 11.

| # | Question | Answer | Where it lives |
|---|---|---|---|
| 1 | E-invoicing coverage | Micro taxpayers are exempt. The others engaged in e-commerce or internet transactions must issue e-invoices through the EIS. | Company: "Engaged in e-commerce or internet transactions" and "Issues e-invoices through the BIR EIS"; a warning on save when a non-micro e-commerce company is not on the EIS (ph_cas.invoicing.rules.eis_required). EIS itself waits for its specs (LDG-58). |
| 2 | Numbering | One continuous, never-reset series per document type (the BIR serial, now the system control number). Every invoice, credit note and debit note also takes a manual invoice number typed by the user, except for companies on the EIS. | Sales Invoice "Manual invoice number", required at submit and unique per company and document type; printed as the invoice number with the system control number below. |
| 3 | Third-party custody | Researched (RR 9-2009 Secs. 6.2 and 6.3.1): the client notifies the BIR before records go to a third-party custodian; records and backups stay in the Philippines. | Registration pack notice (to build); hosting in the Philippines (LDG-54). |
| 4 | Updates | Researched (RMO 9-2021 V.8 and V.9): major enhancements (functions with financial effect, modules added or removed, version changes with financial enhancements) need an update of registration as a new application; minor ones (interface, bug fixes, performance) a written notice to the RDO. | Release method proposed to the owner; not built. |
| 5 | E-books | Researched (RMO 9-2021, RR 16-2006): soft copies within 30 days after the taxable year, on a USB drive labelled with name and year, a transmittal letter listing each file's name, type and size; any column order with a file layout description. | Year-end pack: FILE-LAYOUT.txt, transmittal with file types and the USB label. |
| 6 | Firm registration | The firm, as software provider, will be accredited. | Owner action. |
| 7 | Retention | Ten years. | Backups, offboarding letter, registration pack, hosting runbook. |
| 8a | 2550Q SAWT form code | 2550Q. | ph_cas.dat.sawt (unchanged). |
| 8b | Branch code in DAT files | The correct and complete 5-digit code, leading zeroes kept. | ph_cas.setup.master_data.dat_branch; every alphalist file name and record. |
| 8c | ATCs after module 7.4 | The BIR patched module 7.4: WV080 to WV110 (July 2025, after RMO 13-2025 and 27-2025) and WI/WC 840 to 860 (tax advisory of 18 Nov 2025). Clients run the patched module. DI900 and EI900 for Schedule 2 stay an assumption. | ph_cas.dat.qap.unknown_atcs is empty. |
| 8d | WI/WC 820, 830, 156 | The rates in the tax rules (CPA sign-off). | Tax rules. |
| 9 | Collection receipts | A per-company switch, covered by an ATP. Clients may still use other supplementary receipts. Without an ATP the receipt prints THIS DOCUMENT IS NOT VALID FOR CLAIM OF INPUT TAX. | Company: Collection Receipt ATP number and date; the print shows the ATP or the phrase. |
| 10 | Point of sale | Parked for later. | POS row above stays out of release 1. |
| 11 | SLSP files | One file per month: three files per quarterly submission. | ph_cas.dat.relief.months; PH Tax Return generate_slsp and the 2550Q tie-out. |
