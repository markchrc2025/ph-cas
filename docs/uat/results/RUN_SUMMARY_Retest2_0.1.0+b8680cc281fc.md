# UAT Retest 2: Sentire Ledger, build 0.1.0+b8680cc281fc

- Environment: staging, https://ledger-staging.apps.sentire.solutions (build confirmed through /api/method/ph_cas.qa.uat.build_info)
- Run: 2026-11-22 to 2026-11-23 (Manila), built-in browser, viewport 1366x850
- Scope: the Retest and "Also run first" cases from RETEST_0.1.0+b8680cc281fc.md, in master checklist order, then the framework-branding workbook in full
- Task: LDG-153. Test only: nothing was fixed, restarted or deployed.

## Totals

34 cases run: 22 passed, 9 failed, 3 blocked, 0 not tested. The other 12 workbooks had no cases in scope and are returned unchanged as _RESULTS files.

| Workbook (task) | Run | Pass | Fail | Blocked |
| --- | --- | --- | --- | --- |
| setup-company (LDG-163) | 1 | 0 | 1 | 0 |
| paid-now-card-counter (LDG-148) | 1 | 1 | 0 | 0 |
| roles-permissions (LDG-154) | 3 | 2 | 1 | 0 |
| sales-collections (LDG-156) | 6 | 5 | 0 | 1 |
| purchases-payables (LDG-157) | 1 | 1 | 0 | 0 |
| approvals (LDG-162) | 8 | 4 | 4 | 0 |
| journals-periods (LDG-158) | 1 | 1 | 0 | 0 |
| bir-returns (LDG-159) | 6 | 6 | 0 | 0 |
| books-audit (LDG-160) | 1 | 1 | 0 | 0 |
| framework-branding (LDG-184) | 6 | 1 | 3 | 2 |

## Failures, most severe first

| Case | What happened | Severity | Issue |
| --- | --- | --- | --- |
| RP-016 | Staff A has no Cancel on posted invoice ACC-SINV-2026-00002; no cancel permission, against the B84 rule | High | LDG-235 (new) |
| AP-011 | No Request cancellation button when a Cancel approval chain applies | High | LDG-237 (new) |
| AP-004 | Approval section is not drawn on the form (status only visible through the approvals API) | Medium | LDG-236 (new) |
| AP-008 | Bill ACC-PINV-2026-00002 posts at 66,000, but "Approved and posted" is not shown | Medium | LDG-236 |
| FW-003 | No Help menu, so Help > Get help and the build cannot be reached by a user | Medium | LDG-240 (new) |
| SU-007 | Setup dialog is right, but the page lands on /desk, not Home | Low | LDG-165 (reopened) |
| AP-007 | Message is still "Missing Values Required" | Low | LDG-233 (reopened) |
| FW-001 | Login page shows the Sentire icon but no Sentire Ledger name | Low | LDG-238 (new) |
| FW-002 | About shows the Sentire Ledger dialog; licences line right, but no framework logo, line or "Sentire Framework Version" row (possible checklist error) | Low | LDG-239 (new) |

## Blocked

- SL-008: Accountant has no Cancel (same cause as LDG-235); step 1 not run.
- FW-004 and FW-005: need an Administrator sign-in that the Cover does not provide. Gap task LDG-241.

## Issues

- New bugs: LDG-235, LDG-236, LDG-237, LDG-238, LDG-239, LDG-240
- Reopened (set back to New): LDG-165, LDG-233
- Fixed and set to Done: LDG-210, LDG-214, LDG-216, LDG-222, LDG-229, LDG-230, LDG-231, LDG-232
- New gap tasks: LDG-241 (Administrator account for FW-004 and FW-005), LDG-242 (user menu shows "Frappe Support"; no case covers it)

## Data left on staging (Tala Trading Corporation)

- Sales invoices: ACC-SINV-2026-00003 (serial 3, Credit Note Issued), ACC-SINV-2026-00004 (credit note, CN serial 1), ACC-SINV-2026-00005 (serial 4, Unpaid, from AP-011)
- Payment: ACC-PAY-2026-00001
- Purchase invoices: ACC-PINV-2026-00002 (66,000, posted), ACC-PINV-2026-00003 (submitted)
- Journal entry: ACC-JV-2026-00001
- Approval chains: CHAIN-00001 and CHAIN-00004 (both disabled after use)
- BIR returns: 2550Q-2026-Q3-TTC (filed with override), 2550Q-2026-Q3-TTC-A1 (draft amendment)
- No data was created for books-audit or framework-branding.

## Observations (not blocking)

- Full page loads take 15 to 20 seconds; some save-triggered reloads left a blank page until the URL was opened again.
- The Submit button sometimes appears briefly and the "Submitting" state lags.
- Accounting Manager sees a "Withdraw request" action.
- The Sales Invoice list Actions still offer Submit and Cancel for a posted invoice.
- /about returns 404, and the web footer is hidden on the sign-in page.
- BR-011: the bracketed refusal for a second amendment sent another way was not tried, since it needs a non-UI request.

## Recommendation

Not ready. Two High failures (Staff cannot cancel under B84, and no Request cancellation under a Cancel chain) and three Medium failures remain, and two framework cases are blocked. The BIR returns, books audit, journals and purchases fixes all held. Sign-off is the owner's call.
