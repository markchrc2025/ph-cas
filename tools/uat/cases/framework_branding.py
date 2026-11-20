"""UAT cases: Sentire Ledger running on Sentire Framework (B81)."""

from _common import TODAY, URL, case, cover

SLUG = "framework-branding"
COVER = cover(
    "Sentire Ledger on Sentire Framework: users still see Sentire Ledger, About names Sentire Framework with Frappe credited, no update popup and no Frappe ads",
    "LDG-184",
    "Everything else in Ledger (the other workbooks cover it; B81 changes no accounting). Dates: " + TODAY + ".",
)
I = "LDG-184"
CASES = [
    case("LDG-FW-001", "Login", I, "The login page shows the product only", "Signed out", "None",
         ["Sign out", "Open " + URL + "/login"],
         "None",
         ["The page shows the Sentire Ledger logo and name", "No text on the page says Frappe or ERPNext"], "P1"),
    case("LDG-FW-002", "About", I, "About names Sentire Framework and credits Frappe", "Owner A", "None",
         ["Sign in as Owner A", "Open the user menu (top right) and click About"],
         "None",
         ["The dialog shows the Sentire Framework logo, not Frappe's",
          "The line under the logo reads \"Sentire Framework, based on Frappe Framework (MIT).\"",
          "The version row is titled \"Sentire Framework Version\"",
          "The licences section names Sentire Framework v16.60.2-sentire.1 (based on Frappe Framework 16.60.2) (MIT) and ERPNext (GNU GPL v3)"], "P1"),
    case("LDG-FW-003", "Help", I, "Get help shows the build", "Owner A", "None",
         ["Open Help > Get help"],
         "None",
         ["The build shown matches the build on this workbook's Cover"], "P1"),
    case("LDG-FW-004", "Desk", I, "No update popup after sign-in", "Administrator", "None",
         ["Sign in as Administrator", "Wait 10 seconds on Home"],
         "None",
         ["No \"New updates are available\" dialog appears"], "P1"),
    case("LDG-FW-005", "Desk", I, "No Frappe product ads in the sidebar", "Administrator", "None",
         ["Open the CRM module from the app switcher (if it is switched on), then the Support module"],
         "None",
         ["The sidebar shows no \"Switch to Frappe CRM\" or \"Switch to Helpdesk\" box",
          "If CRM or Support is switched off, note that and mark this case Pass"], "P2"),
    case("LDG-FW-006", "Website", I, "Website pages carry the Sentire footer", "Signed out", "None",
         ["Open " + URL + "/about (or any public page of the site)", "Scroll to the footer"],
         "None",
         ["The footer shows no \"Built on Frappe\" line"], "P2"),
]
