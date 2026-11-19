"""UAT cases: company setup, BIR series, registration pack, modules and the plan, by role (LDG-153, LDG-152)."""

from _common import TODAY, URL, case, cover, refused

SLUG = "setup-company"
COVER = cover(
    "Company setup for the Philippines, BIR series, the registration pack, module switches and the plan limits, by role (Companies A and D)",
    "LDG-163",
    "Go-live (go-live workbook); hosting and new client sites (operator tools). Dates: " + TODAY + ".",
)
A = "Tala Trading Corporation"
D = "UAT Bagong Bukas Corp."
I = "LDG-153"
CASES = [
    case("LDG-SU-001", "Company", I, "The Owner runs Set up Philippine company on a fresh company", "Owner A", D + " untouched (imports workbook not run yet, or run it after this)",
         ["Open Company " + D + " > Sentire Ledger menu > Set up Philippine company", "Confirm"], "None",
         ["A message that the chart, tax accounts and mapping are set (or already set)",
          "Chart of Accounts of " + D + " has Input VAT, Output VAT, EWT Payable and Company Credit Card (a current liability)"], "P1", "",
         "Adds accounts to Company D (safe to repeat)"),
    case("LDG-SU-002", "BIR Series", I, "Only managers create a BIR series", "Accountant A", "None",
         ["Open " + URL + "/desk/bir-series/new as Accountant A; fill Company " + D + "; Save"], "None",
         [refused("BIR Series") + " (or no form)"], "P2"),
    case("LDG-SU-003", "BIR Series", I, "A disabled series stops invoicing until it is enabled again", "Accounting Manager A", "None",
         ["Open the BIR Series list; open " + D + "'s Sales Invoice series; untick Enabled; Save",
          "Issue a Sales Invoice for " + D + " (any customer and item); Submit", "Tick Enabled on the series again; Save"], "None",
         ["Step 2: message \"BIR Series <series> is disabled.\"; not submitted", "After step 3 the series is enabled (no invoice was issued)"], "P1", "",
         "Disables and re-enables a BIR series; leaves a draft invoice (delete it)"),
    case("LDG-SU-004", "Company", I, "The registration pack downloads", "Owner A", "None",
         ["Company " + A + " > Sentire Ledger menu > Registration pack (zip)"], "None",
         ["A zip downloads holding Annex C-1, the Annex B answers, the sworn statement and specimens, each naming " + A], "P2", "", "Downloads a file"),
    case("LDG-SU-005", "Help menu", I, "Your plan shows the user count including the UAT users", "Owner A", "roles-permissions LDG-RP-003 done (one extra user)",
         ["Help > Your plan"], "None", ["Users: the number of enabled system users (UAT accounts and LDG-RP-003 included) of the tier's limit"], "P2"),
    case("LDG-SU-006", "Modules", "LDG-152", "An industry preset sets the starting modules", "Owner A", "None",
         ["Settings > Modules; note which are ticked", "Set Industry Retail and trading; Save; reload", "Restore the ticks noted in step 1; Save"], "None",
         ["After step 2: Selling, Buying and Stock on; the others off (Accounts and BIR are always on)",
          "Home shows \"Switched off, so hidden from every menu: ...\" naming the modules now off", "After step 3 the original set is back"], "P2", "",
         "Changes PH Modules; restored in step 3"),
    case("LDG-SU-007", "Modules", "LDG-152", "A switched-off module's page by URL goes Home with a notice", "Owner A", "Projects switched off (as in roles-permissions LDG-RP-006 step 2)",
         ["Open " + URL + "/desk/project"], "None",
         ["A notice that the Projects module is switched off; the browser lands on Home", "After Projects is ticked again the list opens"], "P2", "",
         "None beyond the module switch"),
    case("LDG-SU-008", "Users", I, "A user without a role set is flagged on the go-live checklist", "Owner A", "LDG-RP-003 user exists with a role set",
         ["Company " + A + " > Sentire Ledger menu > Go-live checklist"], "None",
         ["The users row reads \"<n> user(s) with Owner, Accounting Manager, Accountant or Staff\""], "P3"),
]
