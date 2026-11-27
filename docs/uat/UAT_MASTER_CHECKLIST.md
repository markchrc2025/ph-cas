# Sentire Ledger: full UAT checklist

Build 0.1.0+cb9827a95550 (commit 6d4d4b0). Made by tools/uat/make_workbooks.py; do not edit by hand.

Run the workbooks in this order, one UAT chat per workbook ("Run UAT for LDG-n"), on staging restarted once before the first. Later workbooks use data the earlier ones made; never deploy to staging during the run. The role sets and what each may do: [ROLE_MATRIX.md](ROLE_MATRIX.md). How to run: [UAT_RUNNER_GUIDE.md](UAT_RUNNER_GUIDE.md).

| # | Workbook | UAT task | Cases | P1 | HUMAN | Owner A | Accounting Manager A | Accountant A | Staff A | Accountant B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | [Company setup and modules](setup-company/UAT_LDG_setup-company_0.1.0+cb9827a95550.xlsx) | LDG-163 | 8 | 2 | 1 | 6 | 1 | 1 | 0 | 0 |
| 2 | [Paid in full now, credit card and counter views](paid-now-card-counter/UAT_LDG_paid-now-card-counter_0.1.0+cb9827a95550.xlsx) | LDG-148 | 15 | 7 | 0 | 10 | 0 | 1 | 3 | 1 |
| 3 | [Record an expense](record-expense/UAT_LDG_record-expense_0.1.0+cb9827a95550.xlsx) | LDG-144 | 9 | 7 | 0 | 0 | 0 | 7 | 1 | 1 |
| 4 | [Roles and permissions](roles-permissions/UAT_LDG_roles-permissions_0.1.0+cb9827a95550.xlsx) | LDG-154 | 40 | 29 | 0 | 5 | 11 | 15 | 14 | 4 |
| 5 | [Role homes, counter view and Help menu](role-homes/UAT_LDG_role-homes_0.1.0+cb9827a95550.xlsx) | LDG-147 | 10 | 2 | 0 | 4 | 1 | 2 | 3 | 0 |
| 6 | [Reports page](reports-page/UAT_LDG_reports-page_0.1.0+cb9827a95550.xlsx) | LDG-155 | 12 | 7 | 1 | 6 | 1 | 3 | 3 | 0 |
| 7 | [Sales and collections](sales-collections/UAT_LDG_sales-collections_0.1.0+cb9827a95550.xlsx) | LDG-156 | 15 | 9 | 1 | 2 | 1 | 9 | 2 | 1 |
| 8 | [Masters and stock](masters-stock/UAT_LDG_masters-stock_0.1.0+cb9827a95550.xlsx) | LDG-161 | 11 | 7 | 0 | 0 | 2 | 6 | 4 | 1 |
| 9 | [Purchases and payables](purchases-payables/UAT_LDG_purchases-payables_0.1.0+cb9827a95550.xlsx) | LDG-157 | 11 | 7 | 1 | 0 | 1 | 7 | 2 | 1 |
| 10 | [Approvals](approvals/UAT_LDG_approvals_0.1.0+cb9827a95550.xlsx) | LDG-162 | 11 | 7 | 0 | 0 | 6 | 7 | 1 | 0 |
| 11 | [Journals and periods](journals-periods/UAT_LDG_journals-periods_0.1.0+cb9827a95550.xlsx) | LDG-158 | 8 | 4 | 0 | 3 | 2 | 3 | 1 | 0 |
| 12 | [BIR returns](bir-returns/UAT_LDG_bir-returns_0.1.0+cb9827a95550.xlsx) | LDG-159 | 17 | 10 | 0 | 1 | 5 | 10 | 1 | 1 |
| 13 | [Books and audit](books-audit/UAT_LDG_books-audit_0.1.0+cb9827a95550.xlsx) | LDG-160 | 14 | 10 | 2 | 3 | 2 | 8 | 1 | 0 |
| 14 | [Subsidiary ledgers and cash position](ledgers-cash-position/UAT_LDG_ledgers-cash-position_0.1.0+cb9827a95550.xlsx) | LDG-146 | 10 | 7 | 5 | 5 | 0 | 2 | 1 | 2 |
| 15 | [Import templates and batch edit](import-templates/UAT_LDG_import-templates_0.1.0+cb9827a95550.xlsx) | LDG-145 | 16 | 11 | 1 | 6 | 0 | 8 | 1 | 1 |
| 16 | [Go-live and opening balances](go-live/UAT_LDG_go-live_0.1.0+cb9827a95550.xlsx) | LDG-143 | 14 | 10 | 0 | 12 | 0 | 1 | 0 | 1 |
| 17 | [Print pack for the paper check](paper-check-pack/UAT_LDG_paper-check-pack_0.1.0+cb9827a95550.xlsx) | LDG-149 | 7 | 6 | 4 | 5 | 0 | 1 | 0 | 1 |
| 18 | [Sentire Framework branding](framework-branding/UAT_LDG_framework-branding_0.1.0+cb9827a95550.xlsx) | LDG-184 | 6 | 4 | 0 | 2 | 0 | 0 | 0 | 0 |
| 19 | [Get to know Sentire Ledger checklist](get-to-know/UAT_LDG_get-to-know_0.1.0+8e95ac63624c.xlsx) | LDG-153 | 10 | 7 | 0 | 8 | 0 | 1 | 0 | 1 |
| | **Total** | | **244** | **153** | **16** | **78** | **33** | **92** | **38** | **16** |

Role columns count the cases that sign in as that account (in the Role column or in the steps).

## Every case

| Case | Workbook | Priority | Role | Scenario |
| --- | --- | --- | --- | --- |
| LDG-SU-001 | setup-company | P1 | Owner A | Set up Philippine company is safe to run again on a company already set up |
| LDG-SU-002 | setup-company | P2 | Accountant A | The Accountant cannot create a BIR series |
| LDG-SU-003 | setup-company | P1 | Accounting Manager A | A disabled series stops invoicing until it is enabled again |
| LDG-SU-004 | setup-company | P2 | Owner A | HUMAN: the registration pack holds the expected files |
| LDG-SU-005 | setup-company | P2 | Owner A | Your plan counts a new user and stops counting it when disabled |
| LDG-SU-006 | setup-company | P2 | Owner A | An industry preset sets the starting modules |
| LDG-SU-007 | setup-company | P2 | Owner A | A switched-off module's page opened by URL goes Home with a notice |
| LDG-SU-008 | setup-company | P3 | Owner A | The go-live checklist counts the users that have a role set, and not one without |
| LDG-PN-001 | paid-now-card-counter | P2 | Owner A | Owner adds a walk-in customer, a withholding customer and a service item |
| LDG-PN-002 | paid-now-card-counter | P2 | Owner A | Owner notes the starting numbers before the cash sale |
| LDG-PN-003 | paid-now-card-counter | P1 | Staff A | The Staff user makes a sale paid in full now |
| LDG-PN-004 | paid-now-card-counter | P1 | Owner A | No collection receipt and no payment entry are made for the paid sale |
| LDG-PN-005 | paid-now-card-counter | P1 | Owner A | The paid sale posts cash, sales and output VAT |
| LDG-PN-006 | paid-now-card-counter | P1 | Owner A | The cash sale reaches the Cash Receipts Book and the cash position |
| LDG-PN-007 | paid-now-card-counter | P1 | Owner A | A customer who withholds tax cannot be paid in full now |
| LDG-PN-008 | paid-now-card-counter | P2 | Owner A | A credit note from a paid sale is not itself paid now; ticking it is refused |
| LDG-PN-009 | paid-now-card-counter | P2 | Owner A | A payment mode with no account for the company is refused |
| LDG-PN-010 | paid-now-card-counter | P2 | Owner A | The Philippine setup has added the company credit card |
| LDG-PN-011 | paid-now-card-counter | P1 | Accountant A | An expense paid by card goes on the card, not on cash |
| LDG-PN-012 | paid-now-card-counter | P3 | Owner A | The go-live checklist shows the credit card |
| LDG-PN-013 | paid-now-card-counter | P2 | Staff A | A Staff user's Payment Entry opens in the counter view |
| LDG-PN-014 | paid-now-card-counter | P3 | Staff A | The Payment Entry view can be switched and is remembered |
| LDG-PN-015 | paid-now-card-counter | P1 | Accountant B | Company B's user cannot open Company A's paid sale by its link |
| LDG-EX-001 | record-expense | P2 | Accountant A | Accountant adds an individual lawyer and a non-VAT driver as suppliers |
| LDG-EX-002 | record-expense | P1 | Accountant A | Preview works the VAT back from the receipt and the EWT on the net, without posting |
| LDG-EX-003 | record-expense | P1 | Accountant A | Post makes one paid bill |
| LDG-EX-004 | record-expense | P1 | Accountant A | The bill's postings are right |
| LDG-EX-005 | record-expense | P1 | Accountant A | The expense reaches the books |
| LDG-EX-006 | record-expense | P2 | Accountant A | A small fare from a non-VAT driver carries no VAT and no EWT |
| LDG-EX-007 | record-expense | P1 | Accountant A | Without an expense account or item the expense is refused (never cost of goods sold by default) |
| LDG-EX-008 | record-expense | P1 | Staff A | A Staff user cannot record an expense |
| LDG-EX-009 | record-expense | P1 | Accountant B | Company B's user cannot open Company A's expense by its link |
| LDG-RP-001 | roles-permissions | P1 | Owner A | Each UAT account carries exactly one role set |
| LDG-RP-002 | roles-permissions | P1 | Owner A | The four role sets exist and the old names are gone |
| LDG-RP-003 | roles-permissions | P1 | Owner A | The Owner adds a user and gives a role set |
| LDG-RP-004 | roles-permissions | P1 | Accounting Manager A | The Accounting Manager, the Accountant and Staff cannot add users |
| LDG-RP-005 | roles-permissions | P1 | Accounting Manager A | The Accounting Manager reads the module switches but cannot change them |
| LDG-RP-006 | roles-permissions | P1 | Owner A | The Owner switches a module off and on; the Home page names it while it is off |
| LDG-RP-007 | roles-permissions | P2 | Accountant A | Only the Owner changes Sentire Ledger Settings |
| LDG-RP-008 | roles-permissions | P2 | Accounting Manager A | The Accounting Manager edits the company's details |
| LDG-RP-009 | roles-permissions | P1 | Accountant A | The Accountant and Staff read the company but cannot change it |
| LDG-RP-010 | roles-permissions | P1 | Accounting Manager A | The Accounting Manager adds an account to the chart |
| LDG-RP-011 | roles-permissions | P1 | Accountant A | The Accountant cannot add or change an account |
| LDG-RP-012 | roles-permissions | P2 | Staff A | Staff cannot add a cost center |
| LDG-RP-013 | roles-permissions | P2 | Accountant A | Only the Owner and the Accounting Manager change the tax account mapping |
| LDG-RP-014 | roles-permissions | P1 | Staff A | Staff issues a sales invoice |
| LDG-RP-015 | roles-permissions | P2 | Accountant A | The Accountant and the Accounting Manager issue a sales invoice |
| LDG-RP-016 | roles-permissions | P1 | Staff A | Staff cancels an issued invoice; it keeps its serial (owner rule of 21 Nov 2026) |
| LDG-RP-017 | roles-permissions | P1 | Staff A | Staff records a collection |
| LDG-RP-018 | roles-permissions | P1 | Staff A | Staff cannot pay money out |
| LDG-RP-019 | roles-permissions | P1 | Accountant A | The Accountant records a bill |
| LDG-RP-020 | roles-permissions | P2 | Accountant A | The Accountant pays a supplier |
| LDG-RP-021 | roles-permissions | P1 | Staff A | Staff cannot record a bill or an expense |
| LDG-RP-022 | roles-permissions | P1 | Accountant A | The Accountant posts a journal entry dated today |
| LDG-RP-023 | roles-permissions | P1 | Staff A | Staff cannot post a journal entry |
| LDG-RP-024 | roles-permissions | P1 | Accountant A | The Accountant cannot post with an earlier date |
| LDG-RP-025 | roles-permissions | P1 | Accounting Manager A | The Accounting Manager posts with an earlier date and a reason |
| LDG-RP-026 | roles-permissions | P1 | Accountant A | The Accountant cannot close a period |
| LDG-RP-027 | roles-permissions | P1 | Accounting Manager A | The Accounting Manager closes an old month |
| LDG-RP-028 | roles-permissions | P2 | Staff A | Staff adds a walk-in customer |
| LDG-RP-029 | roles-permissions | P1 | Staff A | Staff cannot add a supplier; the Accountant can |
| LDG-RP-030 | roles-permissions | P2 | Staff A | Staff reads items but cannot add one or change a price |
| LDG-RP-031 | roles-permissions | P2 | Staff A | Staff receives and issues stock |
| LDG-RP-032 | roles-permissions | P1 | Accountant A | The Accountant cannot post a stock count |
| LDG-RP-033 | roles-permissions | P2 | Accounting Manager A | The Accounting Manager posts a stock count |
| LDG-RP-034 | roles-permissions | P1 | Accountant A | The Accountant prepares a return; Staff cannot |
| LDG-RP-035 | roles-permissions | P1 | Accountant A | The Accountant cannot mark a return filed |
| LDG-RP-036 | roles-permissions | P1 | Accounting Manager A | The Accounting Manager reaches the filing step |
| LDG-RP-037 | roles-permissions | P1 | Accountant B | Company B cannot open Company A's invoice by URL |
| LDG-RP-038 | roles-permissions | P1 | Accountant B | Company B cannot open Company A's journal entry |
| LDG-RP-039 | roles-permissions | P1 | Accountant B | Company B cannot run Company A's books |
| LDG-RP-040 | roles-permissions | P2 | Accountant B | Company B's user does not see Company A at all |
| LDG-RH-001 | role-homes | P1 | Staff A | The Staff user's home shows only the counter |
| LDG-RH-002 | role-homes | P2 | Owner A | The Owner's home shows the whole business |
| LDG-RH-003 | role-homes | P2 | Accountant A | The Accountant's home also shows the whole business |
| LDG-RH-004 | role-homes | P1 | Staff A | A Staff user's new Sales Invoice opens in the counter view |
| LDG-RH-005 | role-homes | P2 | Staff A | The view can be switched and the choice is remembered on the browser |
| LDG-RH-006 | role-homes | P3 | Owner A | An Owner's new Sales Invoice opens in the full form |
| LDG-RH-007 | role-homes | P2 | Owner A | Help > Your plan shows the tier, its limits, the use and the build |
| LDG-RH-008 | role-homes | P2 | Accountant A | Help > Get help offers the tutorials and the page details |
| LDG-RH-009 | role-homes | P3 | Owner A | The Help menu shows no framework items |
| LDG-RH-010 | role-homes | P2 | Accounting Manager A | The Accounting Manager's home shows the whole business and the approvals |
| LDG-RE-001 | reports-page | P1 | Owner A | The Reports tile opens the Reports page |
| LDG-RE-002 | reports-page | P2 | Owner A | The Sentire Ledger sidebar has Reports under Home |
| LDG-RE-003 | reports-page | P1 | Owner A | The Owner sees every group |
| LDG-RE-004 | reports-page | P1 | Owner A | Each financial statement opens from the page |
| LDG-RE-005 | reports-page | P1 | Accountant A | The Accountant sees the books and statements but not the audit trail |
| LDG-RE-006 | reports-page | P2 | Accounting Manager A | The Accounting Manager sees the audit trail |
| LDG-RE-007 | reports-page | P1 | Staff A | Staff sees only the counter's reports |
| LDG-RE-008 | reports-page | P1 | Staff A | Staff cannot open other reports by URL |
| LDG-RE-009 | reports-page | P2 | Staff A | Staff cannot export another report |
| LDG-RE-010 | reports-page | P3 | Accountant A | The search box filters the list |
| LDG-RE-011 | reports-page | P1 | Owner A | A switched-off module hides its reports and the page says so |
| LDG-RE-012 | reports-page | P3 | Accountant A | A user who is not a System Manager is told nothing about modules |
| LDG-SL-001 | sales-collections | P2 | Accountant A | The Accountant adds a VAT customer and a goods item |
| LDG-SL-002 | sales-collections | P2 | Accountant A | Note the next Sales Invoice serial |
| LDG-SL-003 | sales-collections | P1 | Accountant A | The Accountant issues a VAT invoice; VAT is computed at 12% |
| LDG-SL-004 | sales-collections | P1 | Staff A | Serials run without gaps across users |
| LDG-SL-005 | sales-collections | P1 | Accountant A | A draft cannot be printed |
| LDG-SL-006 | sales-collections | P1 | Accounting Manager A | The posting date cannot be changed |
| LDG-SL-007 | sales-collections | P2 | Accountant A | A manual invoice number cannot be used twice |
| LDG-SL-008 | sales-collections | P2 | Accountant A | A cancelled invoice is reissued with the next serial |
| LDG-SL-009 | sales-collections | P1 | Accountant A | The Accountant issues a credit note for part of an invoice |
| LDG-SL-010 | sales-collections | P1 | Staff A | A collection pays the rest of the invoice |
| LDG-SL-011 | sales-collections | P1 | Accountant A | A top withholding agent's invoice shows the tax it withholds, and the net payment books it |
| LDG-SL-012 | sales-collections | P2 | Accountant A | The 200.00 shows in the 2307 received reconciliation |
| LDG-SL-013 | sales-collections | P1 | Owner A | HUMAN: the printed invoice carries the BIR details |
| LDG-SL-014 | sales-collections | P2 | Owner A | A second print is marked as a reprint |
| LDG-SL-015 | sales-collections | P1 | Accountant B | Company B's Accountant does not see Company A's sales |
| LDG-MS-001 | masters-stock | P1 | Accountant A | A TIN that is not 9 digits is refused |
| LDG-MS-002 | masters-stock | P2 | Accountant A | An individual supplier needs last and first names |
| LDG-MS-003 | masters-stock | P2 | Staff A | A VAT customer needs a TIN and address for the invoice |
| LDG-MS-004 | masters-stock | P2 | Accountant A | The Accountant adds an item with its VAT class |
| LDG-MS-005 | masters-stock | P1 | Accountant A | The Accountant changes a price; Staff cannot |
| LDG-MS-006 | masters-stock | P1 | Accountant A | The Accountant receives stock |
| LDG-MS-007 | masters-stock | P1 | Accounting Manager A | Stock documents carry today's date |
| LDG-MS-008 | masters-stock | P1 | Staff A | Staff sells from stock and the quantity drops |
| LDG-MS-009 | masters-stock | P1 | Accounting Manager A | The Accounting Manager counts and corrects the stock |
| LDG-MS-010 | masters-stock | P1 | Accountant A | The Accountant and Staff cannot count stock |
| LDG-MS-011 | masters-stock | P2 | Accountant B | Company B's Accountant does not see Company A's suppliers' bills |
| LDG-PU-001 | purchases-payables | P2 | Accountant A | The Accountant adds a VAT supplier of services with expanded withholding, and the service bought |
| LDG-PU-002 | purchases-payables | P1 | Accountant A | A bill with input VAT and 2% withholding |
| LDG-PU-003 | purchases-payables | P1 | Accountant A | The Accountant cannot back-date a bill |
| LDG-PU-004 | purchases-payables | P2 | Accounting Manager A | The Accounting Manager back-dates a bill with a reason |
| LDG-PU-005 | purchases-payables | P1 | Accountant A | The Accountant pays the bill |
| LDG-PU-006 | purchases-payables | P1 | Staff A | Staff cannot see the bill button or post a bill |
| LDG-PU-007 | purchases-payables | P2 | Accountant A | The Accountant can cancel an unpaid bill (bills carry no BIR serial) |
| LDG-PU-008 | purchases-payables | P1 | Accountant A | The quarter's 2307 for the supplier carries the 400.00 |
| LDG-PU-009 | purchases-payables | P1 | Accountant A | HUMAN: the 2307 prints on the BIR form |
| LDG-PU-010 | purchases-payables | P2 | Staff A | Staff cannot make a 2307 |
| LDG-PU-011 | purchases-payables | P1 | Accountant B | Company B cannot open Company A's bill |
| LDG-AP-001 | approvals | P1 | Accountant A | The Accountant cannot set up a chain |
| LDG-AP-002 | approvals | P1 | Accounting Manager A | The Accounting Manager sets up "Manager approves above an amount" for bills |
| LDG-AP-003 | approvals | P1 | Accountant A | A bill above the amount cannot be submitted directly |
| LDG-AP-004 | approvals | P1 | Accountant A | The Accountant requests approval |
| LDG-AP-005 | approvals | P2 | Accounting Manager A | The request waits on the Accounting Manager's home |
| LDG-AP-006 | approvals | P2 | Staff A | Staff cannot decide |
| LDG-AP-007 | approvals | P1 | Accounting Manager A | A rejection needs a reason; the bill stays a draft |
| LDG-AP-008 | approvals | P1 | Accounting Manager A | After a new request, approval posts the bill |
| LDG-AP-009 | approvals | P2 | Accountant A | A bill at or under the amount needs no approval |
| LDG-AP-010 | approvals | P2 | Accounting Manager A | The Accounting Manager disables the chain |
| LDG-AP-011 | approvals | P1 | Accounting Manager A | A cancellation chain: an issued invoice is cancelled only when approved |
| LDG-JP-001 | journals-periods | P1 | Accountant A | An unbalanced entry is refused |
| LDG-JP-002 | journals-periods | P1 | Owner A | No one posts a future date |
| LDG-JP-003 | journals-periods | P1 | Owner A | A posted entry can be cancelled but never deleted |
| LDG-JP-004 | journals-periods | P2 | Accountant A | A draft journal entry cannot be printed |
| LDG-JP-005 | journals-periods | P1 | Owner A | Posting into a closed month is refused for every role |
| LDG-JP-006 | journals-periods | P2 | Accounting Manager A | No role can be exempted from a closed period |
| LDG-JP-007 | journals-periods | P3 | Staff A | Staff does not see Journal Entry in its menus |
| LDG-JP-008 | journals-periods | P2 | Accountant A | The journal entry shows in the General Journal book |
| LDG-BR-001 | bir-returns | P1 | Accountant A | The Accountant creates the 2550Q for the last quarter |
| LDG-BR-002 | bir-returns | P1 | Accountant A | The 2550Q's output VAT ties to the Sales Journal |
| LDG-BR-003 | bir-returns | P2 | Accountant A | Preview prints the draft on the BIR form |
| LDG-BR-004 | bir-returns | P1 | Accountant A | The SLSP files tie out with the return |
| LDG-BR-005 | bir-returns | P2 | Accountant A | The 2550Q exports for eBIRForms |
| LDG-BR-006 | bir-returns | P1 | Accountant A | The Accountant cannot mark it filed (role) |
| LDG-BR-007 | bir-returns | P1 | Accounting Manager A | The Accounting Manager cannot file without the BIR confirmation |
| LDG-BR-008 | bir-returns | P2 | Accounting Manager A | The Accounting Manager cannot use the override; only a System Manager can |
| LDG-BR-009 | bir-returns | P1 | Owner A | The Owner files with an override reason; the return is sealed |
| LDG-BR-010 | bir-returns | P1 | Accountant A | The Accountant cannot open an amendment; Request change is offered when a chain applies |
| LDG-BR-011 | bir-returns | P1 | Accounting Manager A | The Accounting Manager opens an amendment |
| LDG-BR-012 | bir-returns | P1 | Accountant A | The 1601-EQ and its QAP for the quarter |
| LDG-BR-013 | bir-returns | P2 | Accountant A | The 0619-E for the last month |
| LDG-BR-014 | bir-returns | P2 | Accounting Manager A | The 1702Q for the last quarter |
| LDG-BR-015 | bir-returns | P2 | Staff A | Staff opens a return read only |
| LDG-BR-016 | bir-returns | P1 | Accountant B | Company B does not see Company A's returns |
| LDG-BR-017 | bir-returns | P2 | Accountant A | The compliance calendar lists what is due |
| LDG-BA-001 | books-audit | P1 | Accountant A | The General Ledger book balances |
| LDG-BA-002 | books-audit | P1 | Accountant A | The Sales Journal ties to the Sales Register |
| LDG-BA-003 | books-audit | P1 | Accountant A | The Purchase Journal ties to the Purchase Register |
| LDG-BA-004 | books-audit | P1 | Accountant A | The cash books tie to the cash accounts |
| LDG-BA-005 | books-audit | P2 | Accountant A | The General Journal lists every posting of the day with its accounts |
| LDG-BA-006 | books-audit | P3 | Accountant A | The Inventory book lists stock movements |
| LDG-BA-007 | books-audit | P1 | Accountant A | The Accountant downloads the loose-leaf books |
| LDG-BA-008 | books-audit | P1 | Staff A | Staff cannot download the books |
| LDG-BA-009 | books-audit | P1 | Accounting Manager A | The audit trail records who changed what |
| LDG-BA-010 | books-audit | P1 | Accounting Manager A | The event log chain is unbroken |
| LDG-BA-011 | books-audit | P1 | Accountant A | The Accountant cannot open the audit trail |
| LDG-BA-012 | books-audit | P2 | Owner A | Print records count each print |
| LDG-BA-013 | books-audit | P1 | Owner A | A posted document cannot be deleted by anyone |
| LDG-BA-014 | books-audit | P3 | Owner A | HUMAN: the year-end e-books pack |
| LDG-LG-001 | ledgers-cash-position | P1 | Owner A | The loose-leaf pack adds both subsidiary ledgers when asked |
| LDG-LG-002 | ledgers-cash-position | P3 | Owner A | Without the tick the pack keeps the six books |
| LDG-LG-003 | ledgers-cash-position | P1 | Owner A | The customers' ledger carries the BIR header and ties to Accounts Receivable |
| LDG-LG-004 | ledgers-cash-position | P1 | Owner A | The suppliers' ledger runs credit-positive and ties to Accounts Payable |
| LDG-LG-005 | ledgers-cash-position | P2 | Owner A | Each customer's running balance adds up |
| LDG-LG-006 | ledgers-cash-position | P1 | Accountant A | Each cash and bank account adds up for the day and the total ties to the ledger |
| LDG-LG-007 | ledgers-cash-position | P1 | Accountant A | A cash payment today moves Paid out by exactly its amount |
| LDG-LG-008 | ledgers-cash-position | P2 | Staff A | The Staff user sees today's cash from the home tile |
| LDG-LG-009 | ledgers-cash-position | P1 | Accountant B | Company B's user cannot see Company A's cash |
| LDG-LG-010 | ledgers-cash-position | P1 | Accountant B | Company B's user cannot download Company A's loose-leaf books |
| LDG-IM-001 | import-templates | P2 | Accountant A | Accountant downloads the customers and suppliers template |
| LDG-IM-002 | import-templates | P1 | Accountant A | Check the file lists every bad line with its reason and saves nothing |
| LDG-IM-003 | import-templates | P1 | Accountant A | Importing a file with bad lines saves nothing |
| LDG-IM-004 | import-templates | P1 | Accountant A | A good file imports customers and suppliers with their BIR details |
| LDG-IM-005 | import-templates | P1 | Accountant A | Importing the same file again updates and never duplicates |
| LDG-IM-006 | import-templates | P1 | Accountant A | Items import with VAT class and the company's accounts; a bad row is refused |
| LDG-IM-007 | import-templates | P2 | Owner A | Owner sets Company D's go-live date (setup for the opening imports) |
| LDG-IM-008 | import-templates | P1 | Owner A | An old trial balance that does not balance is refused |
| LDG-IM-009 | import-templates | P1 | Owner A | Opening account balances import as one opening entry on the cut-over day |
| LDG-IM-010 | import-templates | P1 | Owner A | An old invoice dated after the cut-over day is refused |
| LDG-IM-011 | import-templates | P1 | Owner A | Open items import by customer and supplier and clear Temporary Opening |
| LDG-IM-012 | import-templates | P2 | Owner A | The go-live checklist shows the balances and open items done |
| LDG-IM-013 | import-templates | P1 | Accountant A | Batch edit runs each record through its own validation |
| LDG-IM-014 | import-templates | P2 | Accountant A | Batch edit changes a valid field on all ticked records |
| LDG-IM-015 | import-templates | P2 | Staff A | A Staff user cannot import suppliers |
| LDG-IM-016 | import-templates | P1 | Accountant B | Company B's user cannot open Company D's opening entry by its link |
| LDG-GL-001 | go-live | P2 | Owner A | Owner sees what is missing before the go-live date is set |
| LDG-GL-002 | go-live | P1 | Owner A | An opening entry is refused while the company has no go-live date |
| LDG-GL-003 | go-live | P1 | Owner A | Owner sets the go-live date; the checklist then shows the cut-over day |
| LDG-GL-004 | go-live | P1 | Owner A | An opening entry dated any day other than the cut-over day is refused |
| LDG-GL-005 | go-live | P2 | Owner A | Owner adds the customer and supplier that carry old balances |
| LDG-GL-006 | go-live | P1 | Owner A | Opening balances post on the cut-over day without a back-date reason |
| LDG-GL-007 | go-live | P1 | Owner A | Opening stock count posts on the cut-over day |
| LDG-GL-008 | go-live | P1 | Owner A | An old invoice cannot be entered as an opening Sales Invoice |
| LDG-GL-009 | go-live | P1 | Owner A | The old balances show by customer and supplier |
| LDG-GL-010 | go-live | P1 | Owner A | An old balance is collected against the opening entry |
| LDG-GL-011 | go-live | P1 | Owner A | The checklist shows the go-live complete |
| LDG-GL-012 | go-live | P2 | Owner A | The trial balance on the cut-over day balances |
| LDG-GL-013 | go-live | P2 | Accountant A | An Accountant cannot post a stock count (manager only) |
| LDG-GL-014 | go-live | P1 | Accountant B | Company B's user cannot open Company C's opening entry by its link |
| LDG-PC-001 | paper-check-pack | P1 | Owner A | Owner downloads the print pack |
| LDG-PC-002 | paper-check-pack | P1 | Owner A | Every document page is marked as a specimen and carries a 100 mm bar |
| LDG-PC-003 | paper-check-pack | P1 | Owner A | The pack does not use up an invoice's original print |
| LDG-PC-004 | paper-check-pack | P1 | Owner A | The cover's bar prints at 100 mm |
| LDG-PC-005 | paper-check-pack | P1 | Owner A | Each document page's bar prints at 100 mm and nothing is cut |
| LDG-PC-006 | paper-check-pack | P2 | Accountant A | An Accountant cannot download the pack (Accounting Managers only) |
| LDG-PC-007 | paper-check-pack | P1 | Accountant B | Company B's user cannot download Company A's pack |
| LDG-FW-001 | framework-branding | P1 | Signed out | The login page shows the product only |
| LDG-FW-002 | framework-branding | P1 | Owner A | About names Sentire Framework and credits Frappe |
| LDG-FW-003 | framework-branding | P1 | Owner A | Get help shows the build |
| LDG-FW-004 | framework-branding | P1 | Administrator | No update popup after sign-in |
| LDG-FW-005 | framework-branding | P2 | Administrator | No Frappe product ads in the sidebar |
| LDG-FW-006 | framework-branding | P2 | Signed out | Website pages carry the Sentire footer |
| LDG-GK-001 | get-to-know | P2 | Owner A | Set up the Philippine company is ticked for a company with a TIN and a BIR Series |
| LDG-GK-002 | get-to-know | P1 | Owner A | Print your first BIR invoice ticks only after an invoice of that company is printed |
| LDG-GK-003 | get-to-know | P1 | Accountant A | Compute your first BIR return ticks after a return is saved for that company |
| LDG-GK-004 | get-to-know | P1 | Owner A | Export the books ticks after the loose-leaf books are downloaded |
| LDG-GK-005 | get-to-know | P1 | Owner A | Build the registration pack ticks after the pack is downloaded |
| LDG-GK-006 | get-to-know | P2 | Owner A | Choose what you use ticks once the Modules page is saved |
| LDG-GK-007 | get-to-know | P2 | Owner A | Confirm your tax rules follows the Tax Rules list |
| LDG-GK-008 | get-to-know | P1 | Owner A | Another company's work does not tick this company's steps |
| LDG-GK-009 | get-to-know | P1 | Owner A | Clicking a step's link does not tick it |
| LDG-GK-010 | get-to-know | P1 | Accountant B | The other tenant sees only its own progress |
