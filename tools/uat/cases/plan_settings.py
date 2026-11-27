"""UAT cases: the provider's settings are locked from the client; Security; the Owner changes the plan (B93, D14)."""

from _common import TODAY, URL, case, cover

SLUG = "plan-and-settings"
COVER = cover(
    "The provider's settings (Sentire Ledger Settings, Subscriptions) are closed to the client; the client's Security page; Help > Your plan > Change plan by the Owner (Company A; staging runs as a client on Team, paid 30 days ahead)",
    "LDG-153",
    "Defining what each tier holds (the future Sentire Ledger Tenant Control Portal); billing; a downgrade that reaches its date (checked by the automated tests). Dates: " + TODAY + ".",
)
I = "LDG-153"
CASES = [
    case("LDG-PS-001", "Sidebar", I, "The client does not see the provider's settings", "Owner A", "None",
         ["Sign in as Owner A; sidebar Home; scroll the sidebar to the bottom",
          "Paste " + URL + "/desk/ph-cas-settings in the address bar; Enter",
          "Paste " + URL + "/desk/ph-subscription in the address bar; Enter"],
         "None",
         ["Step 1: the sidebar ends with Users, Security, Modules and Tutorial Videos; there is no \"Sentire Ledger Settings\" and no \"Subscriptions\"",
          "Step 2: Not Permitted (no settings form opens)", "Step 3: Not Permitted"], "P1", "", "None"),
    case("LDG-PS-002", "PH Security Settings", I, "The Owner sets the failed sign-ins limit on Security", "Owner A", "None",
         ["Sidebar Security", "Set \"Failed sign-ins before the user is deactivated\" to 2; press Ctrl+S (Cmd+S)", "Set it to 5; press Ctrl+S (Cmd+S)"],
         "2, then 5",
         ["Step 1: the page \"PH Security Settings\" shows one field with 5", "Step 2: message \"Allow at least 3 failed sign-ins before a user is deactivated.\"; not saved",
          "Step 3: \"Saved\""], "P2", "", "Saves the setting (unchanged at the end)"),
    case("LDG-PS-003", "Help > Your plan", I, "Your plan shows Team and offers Change plan", "Owner A", "None",
         ["Click the menu at the top of the sidebar (Sentire Ledger (staging) with the arrow) > Your plan"],
         "None",
         ["A dialog titled \"Your plan: Team\"; rows Users, Companies, Branches besides the head office, Invoices this month, each \"no limit\" (staging's add-ons)",
          "\"Paid until\" with a date 30 days after the staging site was set up", "A link \"Change plan\""], "P2", "", "None"),
    case("LDG-PS-004", "Help > Your plan", I, "The Accountant cannot change the plan", "Accountant A", "None",
         ["Sidebar menu (top) > Your plan > Change plan"],
         "None",
         ["A dialog \"Change plan\" lists Solo, Team, Business and Enterprise; Team says \"Your plan\"",
          "Solo and Business say \"Only the Owner can change the plan\"; Enterprise says \"Write to us from Help > Get help\"; there are no buttons"], "P1", "", "None"),
    case("LDG-PS-005", "Help > Your plan", I, "The Owner upgrades to Business; it applies at once", "Owner A", "LDG-PS-003 done",
         ["Sidebar menu (top) > Your plan > Change plan", "On the Business row click \"Upgrade now\"; confirm \"Upgrade to Business now? The new fee starts today.\" with Yes",
          "Sidebar menu (top) > Your plan"],
         "None",
         ["Step 1: Business has an \"Upgrade now\" button; Solo has \"Downgrade at the end of the paid period\" or \"Not yet:\" with what to reduce",
          "Step 2: green alert \"You are now on Business.\"",
          "Step 3: \"Your plan: Business\"; Users of 15; Companies of 1; Branches no limit; Invoices this month no limit",
          "Event Log (sidebar): the newest row has Event plan_change, with Team to Business in its details"],
         "P1", "LDG-PS-003", "Changes the staging tier to Business"),
    case("LDG-PS-006", "Help > Your plan", I, "A downgrade the site does not fit is refused with what to reduce", "Owner A", "LDG-PS-005 done",
         ["Sidebar menu (top) > Your plan > Change plan", "Look at the Team row"],
         "None",
         ["The Team row shows \"Not yet:\" and, among its lines, \"Reduce companies from 4 to 1 (for example, disable 3).\" (staging has 4 companies), and no button",
          "The tier stays Business"], "P1", "LDG-PS-005", "None"),
    case("LDG-PS-007", "Help > Your plan", I, "Enterprise is not self-service", "Owner A", "LDG-PS-005 done",
         ["Sidebar menu (top) > Your plan > Change plan; look at the Enterprise row"],
         "None", ["\"Write to us from Help > Get help\"; no button"], "P3", "LDG-PS-005", "None"),
]
