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
         ["An error that debit and credit are not equal (difference 100.00)", "Not saved"], "P1"),
    case("LDG-JP-002", "Journal Entry", I, "No one posts a future date", "Owner A", "None",
         ["New Journal Entry as LDG-JP-001 but balanced at 1,000.00 and Posting Date T+1; Save"],
         "User Remark UAT-JP-002",
         ["Message: \"Journal Entry: the posting date <T+1> is in the future. Documents carry the day they are posted.\"", "Not saved"], "P1"),
    case("LDG-JP-003", "Journal Entry", I, "A posted entry cannot be deleted", "Owner A", "LDG-RP-022 done (or any submitted entry)",
         ["Open the entry; Cancel it; then Delete"],
         "None",
         ["Cancel creates the reversal (Cancelled status); Delete is refused with a message that posted documents are kept", "The entry stays in the list as Cancelled"], "P1", "",
         "IRREVERSIBLE: cancels a journal entry"),
    case("LDG-JP-004", "Journal Entry", I, "A draft journal entry cannot be printed", "Accountant A", "None",
         ["New balanced Journal Entry dated T, User Remark UAT-JP-004; Save; Print"],
         "None",
         ["Message: \"Journal Entry <name> is a draft. Drafts cannot be printed; submit the document first.\""], "P2", "", "Leaves a draft (delete it after)"),
    case("LDG-JP-005", "Accounting Period", I, "Posting into a closed month is refused for every role", "Owner A", "LDG-RP-027 done (a closed month two months back)",
         ["As Accounting Manager A, new balanced Journal Entry dated the 15th of the closed month, reason filled; Save; Submit"],
         "User Remark UAT-JP-005; reason UAT-JP-005",
         ["Refused: the month is closed by Accounting Period UAT-RP-027", "Not submitted"], "P1", ""),
    case("LDG-JP-006", "Accounting Period", I, "No role can be exempted from a closed period", "Accounting Manager A", "LDG-RP-027 done",
         ["Open Accounting Period UAT-RP-027; in Closed Documents untick Closed for Journal Entry; Save"],
         "None",
         ["Message: \"Accounting Period: no role may be exempted from a closed period.\" (or every row stays Closed after the save)"], "P2"),
    case("LDG-JP-007", "Journal Entry", I, "Staff does not see Journal Entry in its menus", "Staff A", "None",
         ["Open the sidebar and the Create chips on Home"],
         "None", ["No \"Journal entry\" chip on Home; a direct URL is refused (LDG-RP-023)"], "P3"),
    case("LDG-JP-008", "General Ledger", I, "The journal entry shows in the General Journal book", "Accountant A", "LDG-RP-022 done",
         ["Reports page > General Journal; Company " + CO + "; from T to T"],
         "None", ["A row with remark UAT-RP-022: debit 1,000.00 to the expense account, credit 1,000.00 to Cash - TTC"], "P2", ""),
]
