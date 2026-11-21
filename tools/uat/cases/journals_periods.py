"""UAT cases: journal entries, dates and closing a period, across the role sets (LDG-153)."""

from _common import TODAY, URL, case, cover

SLUG = "journals-periods"
COVER = cover(
    "Journal entries, the posting-date rules and closing a month with an Accounting Period (Company A)",
    "LDG-158",
    "Opening entries (go-live workbook); year-end closing (Period Closing Voucher). Dates: " + TODAY + ".",
)
CO = "Tala Trading Corporation"
I = "LDG-153"
CASES = [
    case("LDG-JP-001", "Journal Entry", I, "An unbalanced entry is refused", "Accountant A", "None",
         ["New Journal Entry, Company " + CO + ", Posting Date T", "Debit Cash - TTC 1,000.00; Credit Sales - TTC 900.00", "Save"],
         "User Remark UAT-JP-001",
         ["Message titled \"Debit and credit are not equal\": \"Total debit 1,000.00 and total credit 900.00 are not equal (difference 100.00). A journal entry is saved only when it balances.\" (the amounts carry the peso sign: ₱ 1,000.00, ₱ 900.00, ₱ 100.00)", "Not saved"], "P1"),
    case("LDG-JP-002", "Journal Entry", I, "No one posts a future date", "Owner A", "None",
         ["New Journal Entry as LDG-JP-001 but balanced at 1,000.00 and Posting Date T+1; Save"],
         "User Remark UAT-JP-002",
         ["Message: \"Journal Entry: the posting date <T+1> is in the future. Documents carry the day they are posted.\"", "Not saved"], "P1"),
    case("LDG-JP-003", "Journal Entry", I, "A posted entry can be cancelled but never deleted", "Owner A", "Account UAT-RP-010 Seminar fees - TTC exists (roles-permissions LDG-RP-010, run before this workbook)",
         ["Accounting > Journal Entry > + Add: Company " + CO + "; Posting Date T; Debit UAT-RP-010 Seminar fees - TTC 500.00; Credit Cash - TTC 500.00; User Remark UAT-JP-003; Save, then Submit",
          "Cancel it; confirm", "Menu (...) > Delete; confirm"],
         "None",
         ["Step 1: Submitted", "Step 2: status Cancelled (the reversing ledger rows are posted)",
          "Step 3: message \"Journal Entry <name> has been posted and cannot be deleted. Cancel it, or correct it with a new document.\"; the entry stays in the list as Cancelled"],
         "P1", "", "IRREVERSIBLE: posts and cancels a journal entry"),
    case("LDG-JP-004", "Journal Entry", I, "A draft journal entry cannot be printed", "Accountant A", "None",
         ["New balanced Journal Entry dated T, User Remark UAT-JP-004; Save; Print"],
         "None",
         ["Message: \"Journal Entry <name> is a draft. Drafts cannot be printed; submit the document first.\""], "P2", "", "Leaves a draft (delete it after)"),
    case("LDG-JP-005", "Accounting Period", I, "Posting into a closed month is refused for every role", "Owner A", "LDG-RP-027 done in the roles-permissions workbook (run before this one): the month two months before T's month is closed",
         ["As Accounting Manager A, new balanced Journal Entry dated the 15th of the closed month, reason filled; Save; Submit"],
         "User Remark UAT-JP-005; reason UAT-JP-005",
         ["Refused: the month is closed by Accounting Period UAT-RP-027", "Not submitted"], "P1", ""),
    case("LDG-JP-006", "Accounting Period", I, "No role can be exempted from a closed period", "Accounting Manager A", "LDG-RP-027 done (roles-permissions workbook, run before this one)",
         ["Open Accounting Period UAT-RP-027; in Closed Documents untick Closed for Journal Entry; Save"],
         "None",
         ["Message: \"Accounting Period: no role may be exempted from a closed period.\" (or every row stays Closed after the save)"], "P2"),
    case("LDG-JP-007", "Journal Entry", I, "Staff does not see Journal Entry in its menus", "Staff A", "None",
         ["Open the sidebar and the Create chips on Home"],
         "None", ["No \"Journal entry\" chip on Home; a direct URL is refused (LDG-RP-023)"], "P3"),
    case("LDG-JP-008", "General Ledger", I, "The journal entry shows in the General Journal book", "Accountant A", "LDG-RP-022 done (roles-permissions workbook, run before this one)",
         ["Reports page > General Journal; Company " + CO + "; from T to T"],
         "None", ["A row with remark UAT-RP-022: debit 1,000.00 to the expense account, credit 1,000.00 to Cash - TTC"], "P2", ""),
]
