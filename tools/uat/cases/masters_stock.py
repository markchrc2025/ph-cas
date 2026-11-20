"""UAT cases: customers, suppliers, items, prices and stock, by role (LDG-153)."""

from _common import TODAY, URL, case, cover, refused

SLUG = "masters-stock"
COVER = cover(
    "Customers and suppliers with TIN and payee checks, items and prices, stock entries and the stock count, by role (Company A)",
    "LDG-161",
    "Importing masters (import-templates workbook); perpetual inventory switching (go-live). Dates: " + TODAY + ".",
)
CO = "Tala Trading Corporation"
I = "LDG-153"
CASES = [
    case("LDG-MS-001", "Supplier", I, "A TIN that is not 9 digits is refused", "Accountant A", "None",
         ["Buying > Supplier > + Add: name UAT-MS-001 Bad TIN Corp.; Non-individual; TIN 12345; branch 00000; VAT; Save"], "TIN 12345",
         ["Message: \"TIN must be 9 digits (000-000-000).\"", "Not saved"], "P1"),
    case("LDG-MS-002", "Supplier", I, "An individual supplier needs last and first names", "Accountant A", "None",
         ["+ Add Supplier: name UAT-MS-002 Atty. Reyes; Payee type Individual; TIN 000-777-302; leave Last name empty; Save"], "None",
         ["Message: \"An individual payee needs a last name and a first name (the alphalist reports them separately).\"", "Not saved; after filling Last name REYES and First name ANA it saves"], "P2", "", "Creates a supplier"),
    case("LDG-MS-003", "Customer", I, "A VAT customer needs a TIN and address for the invoice", "Staff A", "None",
         ["Selling > Customer > + Add: UAT-MS-003 Quezon Trading Corp.; Non-individual; VAT status VAT; no TIN; no address; Save", "New sales invoice to it: UAT-SL-001-CEM Qty 4 (sales-collections LDG-SL-001), Manual invoice number UAT-MS-003; Save"], "None",
         ["The customer saves", "Working: 4 x 250.00 = 1,000.00 + 120.00 VAT = 1,120.00, at or above the 1,000.00 threshold (RR 7-2024)",
          "Message: \"Sales of ₱ 1,000.00 or more to a VAT-registered buyer need the buyer's TIN, address on the invoice (RR 7-2024). Complete the customer record.\"", "No invoice is saved"], "P2", "",
         "May create a customer"),
    case("LDG-MS-004", "Item", I, "The Accountant adds an item with its VAT class", "Accountant A", "None",
         ["Stock > Item > + Add: UAT-MS-004-NAIL; UAT-MS-004 Common nails 1kg; Products; Maintain Stock on; VAT class VATable; Standard Selling Rate 95.00; Save"], "None",
         ["Saved", "Item Price list shows UAT-MS-004-NAIL at 95.00 in Standard Selling"], "P2", "", "Creates an item and a price"),
    case("LDG-MS-005", "Item Price", I, "The Accountant changes a price; Staff cannot", "Accountant A", "LDG-MS-004 done",
         ["Open Item Price of UAT-MS-004-NAIL; Rate 99.00; Save", "As Staff A, open the same Item Price; Rate 90.00; Save"], "None",
         ["Accountant A: saved at 99.00", "Staff A: read only or " + refused("Item Price", "write") + "; reload shows 99.00"], "P1", "LDG-MS-004"),
    case("LDG-MS-006", "Stock Entry", I, "The Accountant receives stock", "Accountant A", "LDG-MS-004 done",
         ["Stock > Stock Entry > + Add: Material Receipt; Target Stores - TTC; UAT-MS-004-NAIL Qty 50, Basic Rate 60.00; Remarks UAT-MS-006; Submit"], "None",
         ["Submitted", "Stock Balance: UAT-MS-004-NAIL in Stores - TTC = 50, value 3,000.00 (50 x 60.00)"], "P1", "LDG-MS-004", "IRREVERSIBLE: posts a stock receipt"),
    case("LDG-MS-007", "Stock Entry", I, "Stock documents carry today's date", "Accounting Manager A", "LDG-MS-004 done",
         ["New Stock Entry as LDG-MS-006 with Edit Posting Date on and date T-1; Save"], "None",
         ["Message: \"Stock Entry: Edit Posting Date and Time is not available. Documents carry the day they are posted.\""], "P1", "LDG-MS-004"),
    case("LDG-MS-008", "Sales Invoice", I, "Staff sells from stock and the quantity drops", "Staff A", "LDG-MS-006 done",
         ["New sales invoice: UAT-PN-001 Juan Dela Cruz; UAT-MS-004-NAIL Qty 5 at 99.00; tick Update Stock (warehouse Stores - TTC); Manual invoice number UAT-MS-008; Submit"],
         "None", ["Working: 5 x 99.00 = 495.00 + 59.40 VAT = 554.40", "Grand Total 554.40", "Stock Balance: 45 left"], "P1", "LDG-MS-006",
         "IRREVERSIBLE: issues a BIR invoice and moves stock"),
    case("LDG-MS-009", "Stock Reconciliation", I, "The Accounting Manager counts and corrects the stock", "Accounting Manager A", "LDG-MS-008 done",
         ["Stock Reconciliation > + Add: Stock Reconciliation; UAT-MS-004-NAIL, Stores - TTC, Quantity 44, Valuation Rate 60.00; Remarks UAT-MS-009; Submit"], "None",
         ["Submitted; difference -1 x 60.00 = -60.00", "Stock Balance: 44"], "P1", "LDG-MS-008", "IRREVERSIBLE: posts a stock count"),
    case("LDG-MS-010", "Stock Reconciliation", I, "The Accountant and Staff cannot count stock", "Accountant A", "None",
         ["Open " + URL + "/desk/stock-reconciliation/new as Accountant A, then as Staff A"], "None",
         ["Both: no form, or \"Only a Accounting Manager may create or change Stock Reconciliation.\""], "P1"),
    case("LDG-MS-011", "Supplier", I, "Company B's Accountant does not see Company A's suppliers' bills", "Accountant B", "None",
         ["Open Supplier UAT-PU-001 Makati Janitorial Corp. (if suppliers are shared) and its Purchase Invoices list"], "None",
         ["Even if the supplier record shows, no Company A bill is listed"], "P2"),
]
