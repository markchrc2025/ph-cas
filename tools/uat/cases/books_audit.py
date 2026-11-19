"""UAT cases: the books of accounts, the loose-leaf and e-books packs, and the audit controls (LDG-153)."""

from _common import TODAY, URL, case, cover

SLUG = "books-audit"
COVER = cover(
    "The seven books of accounts, the loose-leaf and year-end packs, and the audit trail, chain check and print records, by role (Company A)",
    "LDG-160",
    "Subsidiary AR/AP ledgers and the cash position (ledgers-cash-position workbook). Dates: " + TODAY + ".",
)
CO = "Tala Trading Corporation"
I = "LDG-153"
YR = "from <year of T>-01-01 to T"
CASES = [
    case("LDG-BA-001", "Books", I, "The General Ledger book balances", "Accountant A", "None",
         ["Reports page > General Ledger book; Company " + CO + "; " + YR], "None",
         ["Each account shows opening, debits, credits and closing", "The grand totals of debit and credit are equal"], "P1"),
    case("LDG-BA-002", "Books", I, "The Sales Journal ties to the Sales Register", "Accountant A", "None",
         ["Sales Journal, " + YR + "; note the net sales and VAT totals", "Sales register (Reports page > Sales), same dates; note the net total and the tax total"], "None",
         ["Net sales equal; VAT equals the output VAT tax total (credit notes subtracted in both)"], "P1"),
    case("LDG-BA-003", "Books", I, "The Purchase Journal ties to the Purchase Register", "Accountant A", "None",
         ["Purchase Journal, " + YR, "Purchase register, same dates"], "None",
         ["Net purchases, input VAT and EWT totals are equal in both"], "P1"),
    case("LDG-BA-004", "Books", I, "The cash books tie to the cash accounts", "Accountant A", "None",
         ["Cash Receipts book and Cash Disbursements book for T", "Cash position for T"], "None",
         ["Receipts total = Cash position \"Received\" for all cash and bank accounts; Disbursements total = \"Paid out\"",
          "The Company Credit Card does not appear in either book (it is a liability)"], "P1"),
    case("LDG-BA-005", "Books", I, "The General Journal lists the journal entries only", "Accountant A", "None",
         ["General Journal for T"], "None", ["Only Journal Entries appear (no invoices, bills or payments)"], "P2"),
    case("LDG-BA-006", "Books", I, "The Inventory book lists stock movements", "Accountant A", "stock moved this year (any)",
         ["Inventory book, " + YR], "None", ["Each row has date, item, quantity in or out and the running balance"], "P3"),
    case("LDG-BA-007", "Company", I, "The Accountant downloads the loose-leaf books", "Accountant A", "None",
         ["Company " + CO + " > Sentire Ledger menu > Loose-leaf books (Excel / PDF)", "Dates " + YR + "; Excel"], "None",
         ["A zip (or workbook) downloads holding the seven books, each with the Annex B header (registered name, TIN, address, CAS permit line) and page numbers"],
         "P1", "", "Downloads a file"),
    case("LDG-BA-008", "Company", I, "Staff cannot download the books", "Staff A", "None",
         ["Open " + URL + "/api/method/ph_cas.books.looseleaf.download?company=Tala%20Trading%20Corporation&from_date=<year>-01-01&to_date=<T>"], "None",
         ["No file; a permission error (Staff runs only the counter's reports)"], "P1"),
    case("LDG-BA-009", "Audit", I, "The audit trail records who changed what", "Accounting Manager A", "Some cases of this run done today",
         ["Reports page > Audit trail; from T to T"], "None",
         ["Rows for today's documents with the user (e.g. Accountant A's address), the action (insert, submit, cancel) and the time"], "P1"),
    case("LDG-BA-010", "Audit", I, "The event log chain is unbroken", "Accounting Manager A", "None",
         ["Reports page > Chain check"], "None", ["The report states the chain is intact (no broken link)"], "P1"),
    case("LDG-BA-011", "Audit", I, "The Accountant cannot open the audit trail", "Accountant A", "None",
         ["Open " + URL + "/desk/query-report/BIR Audit Trail"], "None", ["A permission message; no rows"], "P1"),
    case("LDG-BA-012", "Audit", I, "Print records count each print", "Owner A", "sales-collections LDG-SL-013 and 014 done (or any invoice printed twice)",
         ["Reports page > Audit > Print records; filter the invoice"], "None", ["Two rows: the original and the reprint, with user and time"], "P2"),
    case("LDG-BA-013", "Audit", I, "A posted document cannot be deleted by anyone", "Owner A", "Any submitted Sales Invoice",
         ["Open it; menu (...) > Delete"], "None", ["Refused with a message that posted documents are never deleted", "It stays in the list"], "P1"),
    case("LDG-BA-014", "Company", I, "HUMAN: the year-end e-books pack", "Owner A", "None",
         "HUMAN: 1. Company > Sentire Ledger menu > Year-end e-books (zip) for <year of T>\n2. Open the zip",
         "None", ["The zip holds the books as PDF and Excel with the Annex B header, and a summary file"], "P3", "", "Downloads a file"),
]
