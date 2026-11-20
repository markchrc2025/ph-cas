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
    case("LDG-BA-006", "Books", I, "The Inventory book lists stock movements", "Accountant A", "roles-permissions LDG-RP-031 and LDG-RP-033 done (UAT-RP-031-BOX: in 10, out 1, counted to 8)",
         ["Reports page > Inventory book; Company " + CO + "; " + YR + "; find UAT-RP-031-BOX"], "None",
         ["Rows for UAT-RP-031-BOX dated T: in 10, out 1, and the count adjustment of 1 out", "Its running balance ends at 8"], "P3"),
    case("LDG-BA-007", "Company", I, "The Accountant downloads the loose-leaf books", "Accountant A", "None",
         "HUMAN: 1. Company " + CO + " > Sentire Ledger menu > Loose-leaf books (Excel / PDF)\n2. From <year of T>-01-01, To T; Format xlsx; leave the subsidiary-ledgers box unticked; download\n3. Open the zip and list its files; open SJ_ and PAGES.txt", "None",
         ["The file loose-leaf-books_000111222_<from>-<to>_xlsx.zip downloads (<from> and <to> as YYYYMMDD)",
          "It holds exactly 7 files: SJ_Sales-Journal_<from>-<to>.xlsx, PJ_Purchase-Journal_<from>-<to>.xlsx, CRJ_Cash-Receipt-Journal_<from>-<to>.xlsx, CDJ_Disbursement-Journal_<from>-<to>.xlsx, GJ_General-Journal_<from>-<to>.xlsx, GL_General-Ledger_<from>-<to>.xlsx and PAGES.txt",
          "The Sales Journal sheet's header shows OWNER'S NAME, OWNER'S ADDRESS, the TIN, PERIOD, NAME OF USER, RUN DATE, PAGE \"Page 1 of n\", APPLICATION SOFTWARE and PERMIT TO USE NO.",
          "PAGES.txt lists the six books with a page count each and \"Total pages: <sum>\""],
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
    case("LDG-BA-012", "Audit", I, "Print records count each print", "Owner A", "sales-collections LDG-SL-013 and LDG-SL-014 done (the LDG-SL-003 invoice printed twice)",
         ["Reports page > Audit > Print records; filter Reference = the LDG-SL-003 invoice"], "None", ["Two rows: the original and the reprint, each with user and time"], "P2"),
    case("LDG-BA-013", "Audit", I, "A posted document cannot be deleted by anyone", "Owner A", "sales-collections LDG-SL-003 done (a submitted invoice)",
         ["Open the LDG-SL-003 invoice; menu (...) > Delete; confirm"], "None", ["Message: \"Sales Invoice <name> has been posted and cannot be deleted. Cancel it, or correct it with a new document.\"", "It stays in the list, Submitted"], "P1"),
    case("LDG-BA-014", "Company", I, "HUMAN: the year-end e-books pack", "Owner A", "None",
         "HUMAN: 1. Company " + CO + " > Sentire Ledger menu > Year-end e-books (zip); Year: <year of T>\n2. Open the zip and list its files",
         "None", ["The file ebooks_<year>_Tala_Trading_Corporation.zip downloads",
                  "It holds exactly 10 files: 00011122200000_<year>_GJ.csv, _GL.csv, _CRB.csv, _CDB.csv, _SJ.csv, _PJ.csv and _INV.csv (each name starting 00011122200000_<year>), FILE-LAYOUT.txt, MANIFEST.json and TRANSMITTAL.txt",
                  "TRANSMITTAL.txt names " + CO + " and the taxable year"], "P3", "", "Downloads a file"),
]
