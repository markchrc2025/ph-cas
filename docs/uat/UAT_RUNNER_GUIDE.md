# How to run the Sentire Ledger UAT

For the owner and the UAT chat (the uat-runner skill). The rules are the Sentire UAT Standard v1.0 ([UAT_STANDARD.md](UAT_STANDARD.md)); this page is how to apply them to Ledger, start to finish.

## 1. Before the first workbook (owner, once)

1. Check the build. Open https://ledger-staging.apps.sentire.solutions/api/method/ph_cas.qa.uat.build_info. The build must equal the one in [UAT_MASTER_CHECKLIST.md](UAT_MASTER_CHECKLIST.md). If it does not, stop: the workbooks were written for another build.
2. Restart staging once. In Dokploy, open the "Ledger Staging" app and click Restart. This restores the QA snapshot with Companies A to D and the five UAT accounts. Do not restart again until every workbook is done, because later workbooks use what earlier ones created.
3. Get the password. It is `STAGING_UAT_PASSWORD` in the Ledger Staging app's Environment tab. Give it to the UAT chat in the chat when asked, never in a file.
4. Keep the test mailbox open: mcrc.business.solutions@gmail.com. Every staging email goes there.
5. Freeze deploys. Nobody pushes to the `staging` branch or deploys staging during the run, because a deploy rebuilds the site.

## 2. The accounts

| Account | Role set | Companies |
| --- | --- | --- |
| Owner A | Owner | A, C, D |
| Accounting Manager A | Accounting Manager | A, C, D |
| Accountant A | Accountant | A, C, D |
| Staff A | Staff | A |
| Accountant B | Accountant | B (the other tenant) |

The sign-in addresses are on every workbook's Cover. What each role may do is in [ROLE_MATRIX.md](ROLE_MATRIX.md).

## 3. Run each workbook (one UAT chat per workbook)

Follow the order in the master checklist. For each workbook:

1. Open a chat in the Sentire Software Project and say: `Run UAT for LDG-<task>`. Attach the workbook from `docs/uat/<slug>/`, or give its repo path.
2. The runner shows its plan: the cases, their side effects and anything marked IRREVERSIBLE. Approve it, or strike cases.
3. The runner signs in as the role each case names.
   - One browser profile is enough: it signs out and signs in again per role.
   - The counter view choice (Sales Invoice, Payment Entry) is stored per browser, not per user, and signing out does not clear it. LDG-RH-004 to 006 and LDG-PN-013 and 014 clear it themselves.
4. The runner tests only. It never fixes, changes data a case does not ask for, edits columns A to L, restarts or deploys staging, or retries a failed step another way.
5. The runner records results in columns M to S only, exactly as the workbook's header names them:

   | Column | Header | What goes in |
   | --- | --- | --- |
   | M | UAT Status | Passed, Failed, Blocked or Not Tested |
   | N | Actual Result | What happened, with messages word for word and the figures |
   | O | Remarks | Notes, evidence (screenshot names), what a Blocked case is missing |
   | P | Severity | Critical, High, Medium or Low, for each Failed case |
   | Q | Bug ID | The LDG Bug key of the failure |
   | R | Tested On | Date and time |
   | S | Tested By | The tester |

6. Every failure is logged as one Bug in LDG: "[UAT] <case id>: <what failed>", labels uat and uat-fail, parent the workbook's UAT task. Its key goes in column Q.
7. Every gap is logged as a Task in LDG: "[UAT gap] <what is missing>", labels uat and uat-gap, parent the workbook's UAT task. A gap is something a user needs or trips over that no case covers. A gap never changes a case's status.
8. Cases that start with HUMAN: (printing, opening a downloaded file) are done by you. The runner marks them from what you report.
9. At the end of the workbook, the runner:
   - sends you the marked workbook, named as the original with "_RESULTS" before .xlsx, and commits it to `docs/uat/<slug>/results/`;
   - comments the totals, Bug keys and gap keys on the UAT task;
   - recommends Ready, Ready with conditions, or Not ready.
10. You decide. Set the UAT task to Done to accept the workbook. Otherwise leave it In review and send it back.

## 4. Fixes and retests

The build session fixes each bug ("fixes LDG-n"), deploys a new build to staging, and posts a UAT RETEST block on the task. Re-run only the cases it names, in the same chat that holds the marked workbook. An expected result changes only with your written approval, never to match the app.

## 5. Done means

- Every UAT task in the master checklist is Done, and no Critical or High bug is open.
- After that, the build that passed is the one promoted to live (ledger.sentire.solutions).

## Hints for the runner

- T is the date the run starts. T-1 is the day before. Dates in the app show as MM-DD-YYYY.
- Figures in Expected Result carry their working. Check them against the app; never the other way round.
- When a case says "a \"Not Permitted\" message", either of the two wordings it names passes. The point is that nothing is saved. Check that by reopening the list.
- Company A types a manual invoice number on every Sales Invoice. Use the one in the Test Data.
- If a precondition from an earlier workbook is missing, mark the case Blocked and name the missing case. Do not invent data.
