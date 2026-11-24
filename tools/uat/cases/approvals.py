"""UAT cases: approval chains, by role (M5.3; regression for the full UAT, LDG-153)."""

from _common import TODAY, URL, case, cover, refused

SLUG = "approvals"
COVER = cover(
    "Approval chains: who sets them up, a document that needs approval, approve and reject, by role (Company A)",
    "LDG-162",
    "Group approvers and multi-step bands beyond one template. Dates: " + TODAY + ". Restart staging after this workbook if later workbooks must post bills above 50,000.00 without approval.",
)
CO = "Tala Trading Corporation"
I = "LDG-153"
CASES = [
    case("LDG-AP-001", "Approval Chain", I, "The Accountant cannot set up a chain", "Accountant A", "None",
         ["Open " + URL + "/desk/ph-approval-chain/new; Title UAT-AP-001; Save"], "None", [refused("PH Approval Chain")], "P1"),
    case("LDG-AP-002", "Approval Chain", I, "The Accounting Manager sets up \"Manager approves above an amount\" for bills", "Accounting Manager A", "None",
         ["Sentire Ledger > Tax rules > Approval Chains > + Add", "Title UAT-AP-002 Bills over 50k; Document type Purchase Invoice; Company " + CO + "; Enabled; Applies when doc.grand_total > 50000",
          "Steps: step 1, title Accounts manager, Recipient type Role, Role Accounts Manager, Any one, Approver", "Save"], "None",
         ["Saved and enabled", "Reload: same values"], "P1", "", "Creates an approval chain (affects later bills above 50,000.00)"),
    case("LDG-AP-003", "Purchase Invoice", I, "A bill above the amount cannot be submitted directly", "Accountant A", "LDG-AP-002 done; supplier UAT-PU-001 Makati Janitorial Corp. and item UAT-PU-001-JAN exist (purchases-payables workbook, run before this one)",
         ["New bill: UAT-PU-001 Makati Janitorial Corp.; item UAT-PU-001-JAN, Qty 1, Rate 60,000.00; Supplier invoice no UAT-AP-003; Save", "Look for Submit (top right and the ... menu)"], "None",
         ["Working: 60,000.00 + 7,200.00 VAT - 1,200.00 EWT = 66,000.00 > 50,000.00",
          "Grand Total 66,000.00",
          "There is no Submit button: the primary button reads \"Request approval\" (the server also refuses a submit sent any other way: \"Purchase Invoice <name> needs approval (UAT-AP-002 Bills over 50k). Use Request approval; it posts when the chain approves it.\")"], "P1", "LDG-AP-002", "Leaves a draft bill"),
    case("LDG-AP-004", "Purchase Invoice", I, "The Accountant requests approval", "Accountant A", "LDG-AP-003 done",
         ["Click Request approval (a bill asks no reason; a cancellation or a change of a filed return does)"], "None",
         ["The Approval section shows Pending, requested by Accountant A", "Step 1 Accounts manager: Pending", "The Accountant sees no Approve button (only Withdraw request)"],
         "P1", "LDG-AP-003", "Opens an approval request"),
    case("LDG-AP-005", "Home", I, "The request waits on the Accounting Manager's home", "Accounting Manager A", "LDG-AP-004 done",
         ["Sign in as Accounting Manager A; Home"], "None",
         ["\"Awaiting your approval\" lists Purchase Invoice <name> with step Accounts manager, from Accountant A"], "P2", "LDG-AP-004"),
    case("LDG-AP-006", "Purchase Invoice", I, "Staff cannot decide", "Staff A", "LDG-AP-004 done",
         ["Open the bill by URL"], "None", ["Read only or Not Permitted; no Approve or Reject"], "P2", "LDG-AP-004"),
    case("LDG-AP-007", "Purchase Invoice", I, "A rejection needs a reason; the bill stays a draft", "Accounting Manager A", "LDG-AP-004 done",
         ["Open the bill; Reject with an empty comment", "Reject with comment UAT-AP-007 wrong rate"], "None",
         ["Step 1: \"Give the reason for the rejection.\"", "Step 2: request Rejected; the bill stays Draft; Request approval shows again"], "P1", "LDG-AP-004",
         "Rejects the request"),
    case("LDG-AP-008", "Purchase Invoice", I, "After a new request, approval posts the bill", "Accounting Manager A", "LDG-AP-007 done",
         ["As Accountant A, Request approval again", "As Accounting Manager A, Approve"], "None",
         ["The request reads \"Approved and posted\"", "The bill is Submitted; Grand Total 66,000.00"], "P1", "LDG-AP-007", "IRREVERSIBLE: posts the bill"),
    case("LDG-AP-009", "Purchase Invoice", I, "A bill at or under the amount needs no approval", "Accountant A", "LDG-AP-002 done",
         ["New bill: UAT-PU-001 Makati Janitorial Corp.; item UAT-PU-001-JAN, Qty 1, Rate 10,000.00; Supplier invoice no UAT-AP-009; Submit"], "None",
         ["Working: 10,000 + 1,200 - 200 = 11,000.00 <= 50,000.00", "Submitted directly"], "P2", "LDG-AP-002", "IRREVERSIBLE: posts a bill"),
    case("LDG-AP-010", "Approval Chain", I, "The Accounting Manager disables the chain", "Accounting Manager A", "LDG-AP-008 done",
         ["Open UAT-AP-002 Bills over 50k; untick Enabled; Save",
          "As Accountant A, new bill: UAT-PU-001 Makati Janitorial Corp.; item UAT-PU-001-JAN, Qty 1, Rate 60,000.00; Supplier invoice no UAT-AP-010; Save; Submit"], "None",
         ["Step 1: saved; reload shows Enabled off", "Step 2: the bill shows Submit (no Request approval) and submits directly; Grand Total 66,000.00"], "P2", "LDG-AP-008",
         "Disables the chain; IRREVERSIBLE: posts a bill"),
    case("LDG-AP-011", "Approval Chain", I, "A cancellation chain: an issued invoice is cancelled only when approved", "Accounting Manager A", "LDG-AP-001 done; customer UAT-SL-001 Antipolo Builders Inc. and item UAT-SL-001-CEM exist (sales-collections workbook)",
         ["As Accounting Manager A: new Approval Chain, Title UAT-AP-011 Cancel invoices, Document type Sales Invoice, Action Cancel, Company Tala Trading Corporation, Enabled; step 1 Accounts manager (Role Accounts Manager, Any one, Approver); Save",
          "As Accountant A: issue an invoice (customer UAT-SL-001 Antipolo Builders Inc., UAT-SL-001-CEM Qty 1, Manual invoice number UAT-AP-011); Submit; look for Cancel",
          "Click Request cancellation; reason UAT-AP-011 wrong customer",
          "As Accounting Manager A: open the invoice; Approve",
          "Open UAT-AP-011 Cancel invoices; untick Enabled; Save"], "None",
         ["Step 2: no Cancel button; a Request cancellation button shows", "Step 3: the Approval section shows Pending, requested by Accountant A",
          "Step 4: the invoice is Cancelled, keeping its BIR serial", "Step 5: saved; reload shows Enabled off"],
         "P1", "LDG-AP-001", "IRREVERSIBLE: issues and cancels a BIR invoice; adds and disables a chain"),
]
