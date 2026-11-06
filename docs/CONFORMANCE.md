# Annex B conformance (RMC 5-2021)

One row per Annex B item, as itemised in docs/reference/erpnext-bir-cas-review.md. Status: pending (nothing built), built (tests pass on a non-production site), verified (checked against the BIR's own tool, paper blank or the RDO's answer). Evidence names the test module, report or document that proves it. A bundle may tick only the rows it ships.

| Item | Requirement (short) | Status | Bundle | Evidence |
|---|---|---|---|---|
| 1 | Invoice face: seller details, VAT or NON-VAT REG TIN with 5-digit branch, serial of at least 6 digits, date, buyer details, lines, VAT split, EXEMPT, SC/PWD block, ACCN and series range, REPRINT | pending | B06, B09, B12, B20, B22 | |
| 2 | Commercial invoices at least in duplicate | pending | B20 | |
| 3 | Books: General Journal, General Ledger, Sales Journal, Purchase Journal, Inventory Book with the RR 9-2009 columns | pending | B23, B24 | |
| 4 | Every printout or e-copy shows name, address, TIN-branch, software name and version, user ID, date and time | pending | B08 (D9 for the name) | |
| 5 | Books and reports saved as .csv or .dat; annual e-books per RR 16-2006 | pending | B23, B24, B25 | |
| 6 | Sales data sent to the BIR in its format (EIS) | pending | CAS-13 (not bundled yet) | |
| 7 | Backups kept ten years | pending | B31 | |
| 8 | Printable audit trail of all transactions and activities | pending | B07, B08 | |
| 9 | Generates 2306, 2307, 2316 | pending | B26 (2307); 2306 and 2316 out of release 1 | |
| 10a | System controls invoice numbering; no reuse, no reset | pending | B03, B06 | |
| 10b | Posting date is the date entered | pending | B04 | |
| 10c | Void, not modify, once posted; no ledger rewrite | pending | B02, B03 | |
| 10d | Run date on reports | pending | B08 | |
| 10e | Users cannot edit system-generated reports | pending (ERPNext meets as shipped; B08 records the evidence) | B08 | |
| 10f | Users cannot override program edits | pending | B02 to B04 (bypass roles removed) | |
| 10g | Creator's user ID on every record | pending (ERPNext meets as shipped; B07 records the evidence) | B07 | |
| 10h | Automatic totals, out-of-balance detection | pending (ERPNext meets as shipped; B23 records the evidence) | B23 | |
| 11 | Security: one session per user, deactivation after failed sign-ons, 30-day password change, letters and numbers, role-based access, protected audit trail, infrastructure | pending | B05, B07, B31 | |
| 12 | Sales adjustments through supplementary documents with unique serials | pending | B06, B21 | |
