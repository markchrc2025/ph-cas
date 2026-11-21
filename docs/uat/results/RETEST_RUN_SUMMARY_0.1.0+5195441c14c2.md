# Sentire Ledger UAT retest: run summary

- Build: 0.1.0+5195441c14c2, staging (ledger-staging.apps.sentire.solutions)
- Date: 11-21-2026 (Manila), about 13:00 to 16:15
- Scope: the Retest and "Also run first" cases in RETEST_0.1.0+5195441c14c2.md, run in master checklist order
- Results are in columns M to S of each _RESULTS.xlsx. Three workbooks had no cases in scope (reports-page, ledgers-cash-position, paper-check-pack); they are included unchanged.

## Totals

78 cases run: 63 Pass, 9 Fail, 3 Blocked, 3 Not tested (HUMAN).

| # | Workbook | UAT task | Pass | Fail | Blocked | Not tested |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | setup-company | LDG-163 | 1 | 1 | 0 | 0 |
| 2 | paid-now-card-counter | LDG-148 | 1 | 0 | 0 | 0 |
| 3 | record-expense | LDG-144 | 6 | 0 | 0 | 0 |
| 4 | roles-permissions | LDG-154 | 10 | 1 | 0 | 0 |
| 5 | role-homes | LDG-147 | 3 | 0 | 0 | 0 |
| 6 | reports-page | LDG-155 | - | - | - | - |
| 7 | sales-collections | LDG-156 | 6 | 1 | 1 | 1 |
| 8 | masters-stock | LDG-161 | 2 | 0 | 0 | 0 |
| 9 | purchases-payables | LDG-157 | 7 | 0 | 0 | 1 |
| 10 | approvals | LDG-162 | 7 | 2 | 1 | 0 |
| 11 | journals-periods | LDG-158 | 2 | 1 | 0 | 0 |
| 12 | bir-returns | LDG-159 | 7 | 2 | 0 | 1 |
| 13 | books-audit | LDG-160 | 3 | 1 | 1 | 0 |
| 14 | ledgers-cash-position | LDG-146 | - | - | - | - |
| 15 | import-templates | LDG-145 | 1 | 0 | 0 | 0 |
| 16 | go-live | LDG-143 | 7 | 0 | 0 | 0 |
| 17 | paper-check-pack | LDG-149 | - | - | - | - |

RP-031 and RP-033 (roles-permissions) were run as "Also run first" cases for books-audit and are counted in roles-permissions.

## Failures (most severe first)

| Case | Severity | Issue | What happens |
| --- | --- | --- | --- |
| LDG-RP-010 | Medium | LDG-230 (new) | Add Child on Indirect Expenses creates the account under Expenses, not under Indirect Expenses. |
| LDG-JP-008 | Medium | LDG-210 (back to New) | General Journal Particulars is blank for ACC-JV-2026-00001 although its User Remark is set. |
| LDG-SU-007 | Low | LDG-165 | See the setup-company workbook remark. |
| LDG-SL-010 | Low | LDG-231 (new) | After the credit note the invoice shows "Credit Note Issued", not Paid. |
| LDG-AP-003 | Low | LDG-232 (new) | No Submit button, so the "needs approval" message cannot be seen. |
| LDG-AP-007 | Low | LDG-233 (new) | "Missing Values Required: Reason" instead of the expected message. |
| LDG-BR-009 | Low | LDG-214 (back to New) | Filing works and seals the return, but the list's Actions menu has no Delete, so the sealed message cannot be reached. |
| LDG-BR-011 | Low | LDG-216 (back to New) | Amendment A1 works and the original shows Amended by; Open amendment is then hidden, so the "already amends" message cannot be seen. Possible checklist wording issue. |
| LDG-BA-013 | Low | LDG-222 (back to New) | List delete of a posted invoice gives Frappe's "Submitted Record cannot be deleted. You must Cancel it first." instead of the posted-document message. Deletion is still prevented. |

No Critical or High failures.

## Blocked and not tested

- LDG-SL-013 Not tested (HUMAN, print). LDG-SL-014 Blocked: needs SL-013.
- LDG-PU-009 Not tested (HUMAN).
- LDG-BR-005 Not tested (HUMAN, eBIRForms download).
- LDG-AP-010 Blocked: the second half needs a new bill that no step creates.
- LDG-BA-012 Blocked: needs SL-013 and SL-014 (print and reprint).

## Issues closed in this retest (set to Done)

LDG-185, 186, 187, 188, 189, 190, 194, 195, 197, 198, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 212, 213, 215, 217, 219, 220, 221, 225, 227, 228.

## Observations worth a look (not blocking)

- Reports > Income Statement opens the Accounts workspace (Profit and Loss Statement), leaving Sentire Ledger.
- "Not permitted" messages for Staff name "Page" instead of the doctype.
- Staff A sees a Cancel button on a submitted stock receipt.
- The Go-live date field sits on the Company's Stock and Manufacturing tab.
- Customer and Supplier BIR fields still need a second save (LDG-229).
- Q3 2026 has no postings, so the 2550Q and 1702Q tie-outs were 0.00 against 0.00.

## Data created on staging (nothing deleted)

- TTC: customer UAT-SL-001 Antipolo Builders Inc.; supplier UAT-PU-001 Makati Janitorial Corp.; items UAT-SL-001-CEM, UAT-MS-004-NAIL, UAT-PU-001-JAN, UAT-RP-031-BOX; sales invoices ACC-SINV-2026-00003, 00004 (credit note), 00005; payments ACC-PAY-2026-00001 to 00003; bills ACC-PINV-2026-00003 to 00006; 2307 Issued for UAT-PU-001 (draft); approval chain CHAIN-00001 (disabled); stock entries MAT-STE-2026-00001 to 00003; stock count MAT-RECO-2026-00001.
- TTC BIR: 2550Q-2026-Q3-TTC is now Filed (IRREVERSIBLE, owner approved); amendment draft 2550Q-2026-Q3-TTC-A1; draft 1702Q-2026-Q3-TTC.
- UAT Bagong Simula Corp.: go-live date 11-21-2026; customer UAT-GL-005 Marikina Builders Inc.; supplier UAT-GL-005 Cebu Tiles Corp.; item UAT-GL-007-TILE; opening stock MAT-RECO-2026-00002 (11-20-2026).

## Recommendation

Ready with conditions: no Critical or High failures remain. Two Medium fails (RP-010 account parent, JP-008 blank Particulars) and seven Low fails need a decision, and the HUMAN cases (prints, downloads, the paper check pack) are still for the owner. Sign-off is yours.
