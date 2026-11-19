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
    case("LDG-AP-003", "Purchase Invoice", I, "A bill above the amount cannot be submitted directly", "Accountant A", "LDG-AP-002 done; supplier UAT-PU-001 exists",
         ["New bill: UAT-PU-001 Makati Janitorial Corp.; service, Rate 60,000.00; Supplier invoice no UAT-AP-003; Save", "Submit"], "None",
         ["Working: 60,000.00 + 7,200.00 VAT - 1,200.00 EWT = 66,000.00 > 50,000.00",
          "Message: \"Purchase Invoice <name> needs approval (UAT-AP-002 Bills over 50k). Use Request approval; it posts when the chain approves it.\"",
          "The primary button reads \"Request approval\""], "P1", "LDG-AP-002", "Leaves a draft bill"),
    case("LDG-AP-004", "Purchase Invoice", I, "The Accountant requests approval", "Accountant A", "LDG-AP-003 done",
         ["Click Request approval; reason UAT-AP-004"], "None",
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
         ["As Accountant A, Request approval again (reason UAT-AP-008)", "As Accounting Manager A, Approve"], "None",
         ["The request reads \"Approved and posted\"", "The bill is Submitted; Grand Total 66,000.00"], "P1", "LDG-AP-007", "IRREVERSIBLE: posts the bill"),
    case("LDG-AP-009", "Purchase Invoice", I, "A bill at or under the amount needs no approval", "Accountant A", "LDG-AP-002 done",
         ["New bill: UAT-PU-001; Rate 10,000.00; Supplier invoice no UAT-AP-009; Submit"], "None",
         ["Working: 10,000 + 1,200 - 200 = 11,000.00 <= 50,000.00", "Submitted directly"], "P2", "LDG-AP-002", "IRREVERSIBLE: posts a bill"),
    case("LDG-AP-010", "Approval Chain", I, "The Accounting Manager disables the chain", "Accounting Manager A", "LDG-AP-008 done",
         ["Open UAT-AP-002 Bills over 50k; untick Enabled; Save"], "None", ["Saved; later bills above 50,000.00 submit directly"], "P2", "LDG-AP-008",
         "Disables the chain"),
]
