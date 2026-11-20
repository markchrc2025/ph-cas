"""UAT cases: bills, withholding, payments out and the 2307 issued, across the role sets (LDG-153)."""

from _common import TODAY, URL, case, cover, refused

SLUG = "purchases-payables"
COVER = cover(
    "Bills with input VAT and expanded withholding, payments out, the 2307 issued and its print, done by each role set that may (Company A)",
    "LDG-157",
    "Record an expense (record-expense workbook); purchase orders and receipts. Dates: " + TODAY + ".",
)
CO = "Tala Trading Corporation"
I = "LDG-153"
CASES = [
    case("LDG-PU-001", "Supplier / Item", I, "The Accountant adds a VAT supplier of services with expanded withholding, and the service bought", "Accountant A", "None",
         ["Buying > Supplier > + Add Supplier as in Test Data (supplier); Save", "Stock > Item > + Add Item as in Test Data (item); Save"],
         "Supplier: UAT-PU-001 Makati Janitorial Corp.; Non-individual; registered name UAT-PU-001 MAKATI JANITORIAL CORP.; TIN 000-777-201; branch 00000; VAT; EWT category services; address 5 Ayala Ave, Makati City 1226\nItem: Item Code UAT-PU-001-JAN; Item Name UAT-PU-001 Janitorial service; Item Group Services; Maintain Stock unticked; VAT class VATable",
         ["Saved", "Reload: TIN 000-777-201, EWT category services"], "P2", "", "Creates a supplier"),
    case("LDG-PU-002", "Purchase Invoice", I, "A bill with input VAT and 2% withholding", "Accountant A", "LDG-PU-001 done",
         ["Buying > Purchase Invoice > + Add", "Supplier UAT-PU-001 Makati Janitorial Corp.; item UAT-PU-001-JAN, Qty 1, Rate 20,000.00; Supplier invoice no UAT-PU-002", "Save, then Submit"],
         "Rate 20,000.00 (VAT-exclusive)",
         ["Working: input VAT 12% of 20,000.00 = 2,400.00; EWT 2% of 20,000.00 (RR 2-98 Sec. 2.57.2(C), services by a juridical person) = 400.00; payable 20,000.00 + 2,400.00 - 400.00 = 22,000.00",
          "Taxes table: \"Input VAT (services)\" Add 2,400.00; \"EWT <ATC> 2%\" Deduct 400.00 (ATC WC160 for services by a juridical person)", "Grand Total 22,000.00",
          "Outstanding Amount 22,000.00", "Reload: Submitted"], "P1", "LDG-PU-001", "IRREVERSIBLE: posts a bill"),
    case("LDG-PU-003", "Purchase Invoice", I, "The Accountant cannot back-date a bill", "Accountant A", "LDG-PU-001 done",
         ["New bill as LDG-PU-002 with Supplier invoice no UAT-PU-003 and Posting Date T-1; reason filled; Save"],
         "Reason UAT-PU-003 late bill",
         ["Message: \"Purchase Invoice: only a Accounting Manager may post with an earlier date.\"", "Not saved"], "P1"),
    case("LDG-PU-004", "Purchase Invoice", I, "The Accounting Manager back-dates a bill with a reason", "Accounting Manager A", "LDG-PU-001 done",
         ["New bill as LDG-PU-002: Rate 1,000.00, Supplier invoice no UAT-PU-004, Posting Date T-1, reason as in Test Data; Save; Submit"],
         "Reason UAT-PU-004 bill received late",
         ["Submitted with Posting Date T-1", "Working: VAT 12% of 1,000.00 = 120.00; EWT 2% = 20.00; Grand Total 1,000.00 + 120.00 - 20.00 = 1,100.00; Outstanding 1,100.00"], "P2", "LDG-PU-001",
         "IRREVERSIBLE: posts a back-dated bill"),
    case("LDG-PU-005", "Payment Entry", I, "The Accountant pays the bill", "Accountant A", "LDG-PU-002 done",
         ["Open LDG-PU-002 > Create > Payment; Mode Cash; Reference No UAT-PU-005; Submit"],
         "None", ["Paid Amount 22,000.00", "LDG-PU-002 status Paid; Outstanding 0.00"], "P1", "LDG-PU-002", "IRREVERSIBLE: posts a payment"),
    case("LDG-PU-006", "Purchase Invoice", I, "Staff cannot see the bill button or post a bill", "Staff A", "None",
         ["Open " + URL + "/desk/purchase-invoice/new; supplier UAT-PU-001 Makati Janitorial Corp., item UAT-PU-001-JAN, Qty 1, Rate 100.00; Save"],
         "None", ["On Save " + refused("Purchase Invoice")], "P1"),
    case("LDG-PU-007", "Purchase Invoice", I, "The Accountant can cancel an unpaid bill (bills carry no BIR serial)", "Accountant A", "None",
         ["New bill: supplier UAT-PU-001 Makati Janitorial Corp., item UAT-PU-001-JAN, Qty 1, Rate 500.00, Supplier invoice no UAT-PU-007; Submit", "Cancel; confirm"],
         "None", ["The bill becomes Cancelled", "The Purchase Journal for today has no UAT-PU-007 row"], "P2", "LDG-PU-001", "Posts and reverses a bill"),
    case("LDG-PU-008", "PH 2307 Issued", I, "The quarter's 2307 for the supplier carries the 400.00", "Accountant A", "LDG-PU-002 done",
         ["Sentire Ledger > Tax returns > 2307 Issued > + Add (or generate for the quarter)", "Company " + CO + "; supplier UAT-PU-001 Makati Janitorial Corp.; this quarter; Save"],
         "None",
         ["The month of LDG-PU-002 shows income 20,000.00 and tax 400.00 under ATC WC160", "Total tax withheld 400.00 (plus 20.00 if LDG-PU-004 falls in the same quarter)"],
         "P1", "LDG-PU-002", "Creates a 2307 record"),
    case("LDG-PU-009", "PH 2307 Issued", I, "HUMAN: the 2307 prints on the BIR form", "Accountant A", "LDG-PU-008 done",
         "HUMAN: 1. Open the 2307 > Print on BIR form\n2. Look at the PDF",
         "None",
         ["The BIR's 2307 (January 2018 ENCS) with payee TIN 000-777-201, payor TIN of " + CO, "The quarter's dates and 400.00 in the right month column and in the total"],
         "P1", "LDG-PU-008", "Opens a PDF"),
    case("LDG-PU-010", "PH 2307 Issued", I, "Staff cannot make a 2307", "Staff A", "None",
         ["Open " + URL + "/desk/ph-2307-issued/new; Company Tala Trading Corporation; supplier UAT-PU-001 Makati Janitorial Corp.; Save"],
         "None", ["On Save " + refused("PH 2307 Issued")], "P2"),
    case("LDG-PU-011", "Purchase Invoice", I, "Company B cannot open Company A's bill", "Accountant B", "LDG-PU-002 done",
         ["Open " + URL + "/desk/purchase-invoice/<LDG-PU-002 name>"],
         "None", ["Not Permitted or Not found"], "P1", "LDG-PU-002"),
]
