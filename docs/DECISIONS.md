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
