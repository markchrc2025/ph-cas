# Sentire Ledger UAT run summary

Build 0.1.0+1d56e40d2b40, staging (https://ledger-staging.apps.sentire.solutions), pack r2. Run 2026-11-20 to 2026-11-21 (Manila). Tester: Claude (UAT). Results only in columns M to S of each workbook copy.

## Per workbook

| # | Workbook | UAT task | Cases | Pass | Fail | Blocked | Not tested | Not run | Recommendation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | setup-company | LDG-163 | 8 | 6 | 1 | 0 | 1 | 0 | Ready with conditions |
| 2 | paid-now-card-counter | LDG-148 | 15 | 15 | 0 | 0 | 0 | 0 | Ready |
| 3 | record-expense | LDG-144 | 9 | 4 | 5 | 0 | 0 | 0 | Not ready |
| 4 | roles-permissions | LDG-154 | 40 | 35 | 5 | 0 | 0 | 0 | Ready with conditions |
| 5 | role-homes | LDG-147 | 10 | 8 | 2 | 0 | 0 | 0 | Ready with conditions |
| 6 | reports-page | LDG-155 | 12 | 11 | 0 | 0 | 1 | 0 | Ready with conditions |
| 7 | sales-collections | LDG-156 | 15 | 9 | 1 | 4 | 1 | 0 | Not ready |
| 8 | masters-stock | LDG-161 | 11 | 10 | 1 | 0 | 0 | 0 | Ready with conditions |
| 9 | purchases-payables | LDG-157 | 11 | 5 | 4 | 1 | 1 | 0 | Not ready |
| 10 | approvals | LDG-162 | 10 | 1 | 3 | 6 | 0 | 0 | Not ready |
| 11 | journals-periods | LDG-158 | 8 | 4 | 3 | 0 | 1 | 0 | Not ready |
| 12 | bir-returns | LDG-159 | 17 | 10 | 6 | 0 | 1 | 0 | Not ready |
| 13 | books-audit | LDG-160 | 14 | 7 | 4 | 1 | 2 | 0 | Ready with conditions |
| 14 | ledgers-cash-position | LDG-146 | 10 | 5 | 0 | 0 | 5 | 0 | Ready with conditions |
| 15 | import-templates | LDG-145 | 16 | 14 | 1 | 0 | 1 | 0 | Not ready |
| 16 | go-live | LDG-143 | 14 | 12 | 1 | 1 | 0 | 0 | Ready with conditions |
| 17 | paper-check-pack | LDG-149 | 7 | 2 | 0 | 1 | 4 | 0 | Ready with conditions |
| | **Total** | | 227 | 158 | 37 | 14 | 18 | 0 | |

Overall: **Not ready.** Seven workbooks are Not ready, led by two Critical permission or control failures (LDG-205 approval chain bypass, LDG-183 Staff sees Purchase Invoices) and the EWT and credit note figures (LDG-200, LDG-197).

## Bugs (uat-fail), P1 cases first

| Key | Case priority | Issue priority | Title |
|---|---|---|---|
| LDG-205 | P1 | urgent | [UAT] LDG-AP-003: Enabled approval chain is ignored; a 67,200.00 bill submits directly |
| LDG-179 | P1 | high | [UAT] LDG-EX-003: Paid expense bill shows Grand Total 10,700.00, not 11,200.00 before withholding |
| LDG-180 | P1 | high | [UAT] LDG-EX-004: Accounting Ledger totals 21,900.00, not 11,200.00 (extra Creditors pair) |
| LDG-181 | P1 | high | [UAT] LDG-EX-005: PH Purchase Journal tie-out row is blank on screen |
| LDG-183 | P1 | high | [UAT] LDG-EX-008: Staff user can open the Purchase Invoice list and sees Record an expense |
| LDG-185 | P1 | high | [UAT] LDG-RP-016: Owner has no Cancel on an issued invoice, so the expected refusal message is never shown |
| LDG-186 | P1 | high | [UAT] LDG-RP-026: Accountant's Accounting Period refusal shows a generic permission message |
| LDG-188 | P1 | high | [UAT] LDG-RP-035: Accountant has no Submit on a return, so the expected refusal message is never shown |
| LDG-189 | P1 | high | [UAT] LDG-RP-039: PH General Ledger Book opened for another company shows a blank page with no message |
| LDG-197 | P1 | high | [UAT] LDG-SL-009: Credit note does not reduce the invoice's outstanding (Update Outstanding for Self is ticked by default) |
| LDG-198 | P1 | high | [UAT] LDG-MS-006: Accountant A cannot see the Stock Balance result after a stock receipt |
| LDG-200 | P1 | high | [UAT] LDG-PU-002: Bill to a VAT services supplier gets no 2% EWT (Grand Total 22,400.00, not 22,000.00) |
| LDG-202 | P1 | high | [UAT] LDG-PU-005: Payment of the PU-002 bill is 22,400.00, not 22,000.00 |
| LDG-203 | P1 | high | [UAT] LDG-PU-008: 2307 Issued for the quarter cannot be made: "Nothing was withheld" |
| LDG-206 | P1 | high | [UAT] LDG-AP-001: Accountant gets a blank chain form with no Save and no Not Permitted message |
| LDG-208 | P1 | high | [UAT] LDG-JP-001: Unbalanced journal entry saves as a draft without an error |
| LDG-212 | P1 | high | [UAT] LDG-BR-002: Book to tax reconciliation has no 2550Q output VAT view |
| LDG-213 | P1 | high | [UAT] LDG-BR-006: Accountant gets no message when trying to file a return |
| LDG-214 | P1 | high | [UAT] LDG-BR-009: Filed return has no Delete action, sealed message cannot be shown; conflict error on submit |
| LDG-215 | P1 | high | [UAT] LDG-BR-010: Accountant cannot open a filed return at all (Not permitted, redirect to desk) |
| LDG-216 | P1 | high | [UAT] LDG-BR-011: A filed return can be amended twice (A1 and A2); original shows no Amended by |
| LDG-219 | P1 | high | [UAT] LDG-BA-001: General Ledger book shows no grand total of debits and credits |
| LDG-222 | P1 | high | [UAT] LDG-BA-013: Posted invoice has no Delete action, so the posted-document message cannot be seen |
| LDG-165 | P2 | normal | [UAT] LDG-SU-007: a switched-off module's URL lands on the Desktop app page, not Home |
| LDG-178 | P2 | normal | [UAT] LDG-EX-001: Supplier list shows no TIN column |
| LDG-187 | P2 | normal | [UAT] LDG-RP-030: Staff gets an Item form with no Save and no message |
| LDG-194 | P2 | normal | [UAT] LDG-RH-005: Full form on a new Sales Invoice does not show the Currency and Price List section |
| LDG-195 | P3 | normal | [UAT] LDG-RH-006: Owner's new Sales Invoice opens full form but Currency and Price List is not visible |
| LDG-201 | P2 | normal | [UAT] LDG-PU-004: Back-dated bill posts but without 2% EWT (1,120.00, not 1,100.00) |
| LDG-207 | P2 | normal | [UAT] LDG-AP-009: Bill under the limit submits, but at 11,200.00 not 11,000.00 |
| LDG-209 | P3 | normal | [UAT] LDG-JP-007: Staff sees Journal Entry in the sidebar and can open the full list |
| LDG-210 | P2 | normal | [UAT] LDG-JP-008: General Journal shows the RP-022 entry with a blank remark |
| LDG-217 | P2 | normal | [UAT] LDG-BR-014: Generate SAWT gives No SAWT instead of a written file |
| LDG-220 | P2 | normal | [UAT] LDG-BA-005: General Journal lists invoices, bills and payments, not only journal entries |
| LDG-221 | P3 | normal | [UAT] LDG-BA-006: Inventory book has no movement rows and leaves out stock reconciliations |
| LDG-225 | P2 | normal | [UAT] LDG-IM-015: Staff can open the Supplier list and the Import from a template dialog |
| LDG-227 | P2 | normal | [UAT] LDG-GL-005: Customer and Supplier lists do not show the TIN |

## Gaps (uat-gap)

| Key | Priority | Title |
|---|---|---|
| LDG-166 | high | [UAT gap] The Owner's user form shows the full raw role list, including System Manager |
| LDG-228 | normal | [UAT gap] go-live: hidden opening fields and checklist steps (GL-007, GL-008) plus minor observations |
| LDG-226 | normal | [UAT gap] Import templates: observations from the import-templates run |
| LDG-224 | normal | [UAT gap] Record an expense offers other companies (UAT Bagong Bukas, UAT Bagong Simula) to Accountant A |
| LDG-223 | normal | [UAT gap] Cash books count cancelled journal entry lines in TOTAL without listing them |
| LDG-218 | normal | [UAT gap] BIR returns: [object Object] in 0619-E figures; form renders behind Not permitted; Q4 2550Q already computed |
| LDG-211 | normal | [UAT gap] Journal Entry User Remark is hidden; closed period table duplicates rows |
| LDG-199 | normal | [UAT gap] Supplier Connections shows another company's Purchase Invoice count |
| LDG-204 | normal | [UAT gap] Staff can open the 2307 Issued form; PU-010 steps omit the period |
| LDG-196 | normal | [UAT gap] Staff sees the full Sentire Ledger sidebar (Purchase Invoice, Journal Entry, books, BIR Returns, Approvals) |
| LDG-193 | normal | [UAT gap] Roles without create rights get full forms with Save/Add, refused only on save |
| LDG-191 | normal | [UAT gap] PH Tax Return header buttons push Save/Submit off-screen at 1366 px |
| LDG-190 | normal | [UAT gap] Journal Entry User Remark field is hidden, so remarks like UAT-RP-022 cannot be entered |
| LDG-182 | normal | [UAT gap] Supplier Withholding category list shows raw codes (professional, reduced_wholesale) |
| LDG-174 | normal | [UAT gap] The Accountant sees a Cancel button on a posted, paid bill |
| LDG-170 | normal | [UAT gap] The Owner sees provider accounts and system areas (admin users, Provider staff box, System tools) |
| LDG-167 | normal | [UAT gap] Go-live checklist seems to count a disabled user in "Users with a role set" |
| LDG-192 | low | [UAT gap] Stock Reconciliation has no Remarks field |
| LDG-177 | low | [UAT gap] Cash Position has no menu entry; BIR Series list hides Next number |
| LDG-176 | low | [UAT gap] Customers made for one company are offered in another company's invoices and payments |
| LDG-175 | low | [UAT gap] "Include Payment (POS)" is ticked by itself on a paid-now invoice and carried to its credit note |
| LDG-173 | low | [UAT gap] In a narrow window the Help menu and Log out could not be found |
| LDG-172 | low | [UAT gap] Help > Your plan shows Branches 0 while every company has branch 00000 |
| LDG-171 | low | [UAT gap] Customer: Payee type and VAT status sit under the Settings tab, not Tax |
| LDG-169 | low | [UAT gap] Internal and upstream names show in the app (PH Modules, PH CAS, Decision D4, ERPNext, TDS/TCS) |
| LDG-168 | low | [UAT gap] The Accountant gets a read-only "New BIR Series" page with no message |

## Notes

- Not tested cases are HUMAN steps (printing, measuring, PDF and zip checks) or steps the test browser cannot do; they need a person.
- Several Fails are marked in their remarks as possible checklist errors (for example LDG-185, 186, 187, 188, 194, 195, 212, 214, 217, 222). The owner decides.
- Irreversible staging data was created only where a case asked and the run was approved; each UAT task comment lists it.
