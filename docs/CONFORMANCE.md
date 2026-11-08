# Annex B conformance (RMC 5-2021)

One row per Annex B item, as itemised in docs/reference/erpnext-bir-cas-review.md. Status: pending (nothing built), built (tests pass on a non-production site), verified (checked against the BIR's own tool, paper blank or the RDO's answer). Evidence names the test module, report or document that proves it. A bundle may tick only the rows it ships.

| Item | Requirement (short) | Status | Bundle | Evidence |
|---|---|---|---|---|
|| 1 | Invoice face: seller details, VAT or NON-VAT REG TIN with 5-digit branch, serial of at least 6 digits, date, buyer details, lines, VAT split, EXEMPT, SC/PWD block, ACCN and series range, REPRINT | pending (data in place: serial B06, seller and buyer fields B09; the face itself in B20) | B06, B09, B12, B20, B22 | ||
| 2 | Commercial invoices at least in duplicate | pending | B20 | |
| 3 | Books: General Journal, General Ledger, Sales Journal, Purchase Journal, Inventory Book with the RR 9-2009 columns | pending | B23, B24 | |
|| 4 | Every printout or e-copy shows name, address, TIN-branch, software name and version, user ID, date and time | built (default letter head and export helpers; the product name waits for D9) | B08 | ph_cas.tests.test_b08_audit_header ||
| 5 | Books and reports saved as .csv or .dat; annual e-books per RR 16-2006 | pending | B23, B24, B25 | |
| 6 | Sales data sent to the BIR in its format (EIS) | pending | CAS-13 (not bundled yet) | |
| 7 | Backups kept ten years | pending | B31 | |
||| 8 | Printable audit trail of all transactions and activities | built | B07, B08 | ph_cas.tests.test_b07_event_log, test_b08_audit_header |||
| 9 | Generates 2306, 2307, 2316 | pending | B26 (2307); 2306 and 2316 out of release 1 | |
|| 10a | System controls invoice numbering; no reuse, no reset | built | B03, B06 | ph_cas.tests.test_b03_posted_fields, test_b06_serial ||
| 10b | Posting date is the date entered | built | B04 | ph_cas.tests.test_b04_dates |
| 10c | Void, not modify, once posted; no ledger rewrite | built | B02, B03 | ph_cas.tests.test_b02_locks, test_b03_posted_fields |
|| 10d | Run date on reports | built (Printed on in the default letter head) | B08 | ph_cas.tests.test_b08_audit_header ||
|| 10e | Users cannot edit system-generated reports | verified (reports are computed on each run from the ledger; exports are copies that carry the header) | B08 | frappe.desk.query_report.run ||
| 10f | Users cannot override program edits | built (no bypass role: closed periods exempt nobody, back-dating needs the manager role and a reason, drafts never print) | B02 to B04 | ph_cas.tests.test_b02_locks, test_b04_dates |
|| 10g | Creator's user ID on every record | verified (Frappe owner, creation, modified_by, modified on every row; the event log adds the user to every event) | B07 | frappe.model.base_document standard fields ||
| 10h | Automatic totals, out-of-balance detection | pending (ERPNext meets as shipped; B23 records the evidence) | B23 | |
|| 11 | Security: one session per user, deactivation after failed sign-ons, 30-day password change, letters and numbers, role-based access, protected audit trail, infrastructure | built (sign-in controls; audit trail in B07, infrastructure in B31) | B05, B07, B31 | ph_cas.tests.test_b05_security ||
|| 12 | Sales adjustments through supplementary documents with unique serials | built (own series per credit note, debit note and collection receipt; the rules in B21) | B06, B21 | ph_cas.tests.test_b06_serial ||
