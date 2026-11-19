# Sentire UAT Standard

Version 1.0, 12 Nov 2026. Markdown copy of the "Sentire UAT Standard" doc; the doc is the master. Save this file in every Sentire repo as `docs/uat/UAT_STANDARD.md`, with `UAT_TEMPLATE.xlsx` beside it.

## Why and who

Every process built in any Sentire product ships with a UAT document, and a separate session tests it before the owner signs off. The document is the contract between the session that builds and the session that tests, so the builder never marks its own work.

| Role | Who | Responsible for |
| --- | --- | --- |
| Developer session | A Claude Code track or a build chat | Building, deploying to the test environment, writing the UAT document, handing off, fixing bugs |
| UAT runner | A separate Claude session using the uat-runner skill | Running every case like a user, marking the workbook, logging bugs in Sentire Projects, recommending |
| Owner | The product owner | Approving each run plan, deciding sign-off, setting fix priority |

The developer never marks results or changes an expected result to match the app. The runner never fixes code or data. Only the owner signs off.

It applies to every process that changes what a user sees or does: a screen, workflow, calculation, permission, report, export, email or integration. A bug fix gets a short retest document. A refactor with no visible change needs none; the session report says "No UAT: no user-visible change".

The cycle:

```
Developer: build and deploy -> write the UAT workbook -> hand off
Runner:    show the plan (cases and side effects)
Owner:     approve the plan
Runner:    run every case, mark the workbook, log bugs
Owner:     ready?  yes -> accept (UAT task set to Done)
                   no  -> Developer: fix, new build, retest block -> Runner runs again
```

## The flow, step by step

A development session follows these eight steps for every process. Steps 7 and 8 repeat until the owner signs off.

1. **List the acceptance criteria before coding.** Take them from the build plan or the Sentire Projects issue. Each criterion becomes at least one test case; cases are written from the criteria, never from the code.
2. **Deploy to the test environment, never production.** Confirm the migrations ran, the seed data and test accounts exist, the test mailbox receives mail, and the build number shows in the app (footer or /api/health).
3. **Copy the template.** `docs/uat/UAT_TEMPLATE.xlsx` becomes `docs/uat/<process-slug>/UAT_<KEY>_<process-slug>_<build>.xlsx`.
4. **Fill the Cover sheet.** Every field; nothing left as TBD.
5. **Write the test cases.** One row per case on the Test Cases sheet, columns A to L only, following the case rules below. Columns M to S stay empty for the runner.
6. **Check the Definition of Ready.** Every item met, or the gap named in the handoff.
7. **Hand off.** Commit the workbook, create the UAT task in Sentire Projects with the handoff block, and print the same block at the end of the session report.
8. **Fix and retest.** After the run, fix each bug (commit with "fixes KEY-n"), deploy a new build, and post a retest block. An expected result changes only with the owner's approval, never to match the app.

## The UAT document

The UAT document is one Excel workbook per process and build, copied from `UAT_TEMPLATE.xlsx` and never restructured.

| Item | Rule |
| --- | --- |
| File type | .xlsx, copied from `docs/uat/UAT_TEMPLATE.xlsx` |
| File name | `UAT_<KEY>_<process-slug>_<build>.xlsx`, for example `UAT_PAY_leave-filing_0.9.4.xlsx` |
| Folder | `docs/uat/<process-slug>/` in the product's repo; marked copies from runs go in `docs/uat/<process-slug>/results/` |
| Sheets | Cover, Test Cases and How to fill. More case sheets are allowed as "Test Cases - Module name", with the same headers |
| Size | Up to 40 cases. A bigger process is split into sub-processes, one workbook each |
| Never | Rename, reorder or delete columns; merge cells in the case table; spread one case over several rows; type anything in columns M to S |

The Cover sheet tells the runner where and how to test. Every field is filled; passwords never go in the workbook.

| Field | What to write | Example |
| --- | --- | --- |
| Product | Product name | Sentire Payroll |
| Project key | Sentire Projects key | PAY |
| Process | The process under test | Leave filing and approval |
| Build | The version the app shows | 0.9.4 |
| Commit | Branch and short SHA | main @ 3f2a9c1 |
| Environment | Test environment name, never production | staging |
| App URL | Where to test | The staging URL |
| Where the build shows | So the runner can confirm the build | Footer and /api/health |
| Test accounts | One per line as role: username, plus the seed file that holds the passwords | Employee A: emp.a.uat |
| Tenants | Test company names, with a second company for cross-tenant cases | UAT Company A, UAT Company B |
| Test mailbox | Where the app's emails go during the test | A plus-address on the test mailbox |
| Test data setup | Seed or reset done before handoff, with the time it ran | Seed script run at 10:40 |
| Feature flags and settings | What must be switched on | Leave module on |
| Out of scope | What this document does not cover | Leave accrual job |
| Known issues | Open bug keys the runner should not log again | PAY-140 |
| UAT task | Sentire Projects key of the UAT task | PAY-150 |
| Prepared by | Session and date | Claude Code Track B, 2026-11-12 |

## Test Cases columns

The developer fills columns A to L, one row per case; the runner fills M to S. The headers are exact: the runner finds the columns by these names.

| Col | Header | Filled by | What goes in |
| --- | --- | --- | --- |
| A | Case ID | Developer | `<KEY>-<MOD>-<NNN>`, for example PAY-LV-001. Unique in the product; never renumbered or reused |
| B | Module | Developer | The menu or screen name as the app shows it |
| C | Linked Issue | Developer | Sentire Projects key of the requirement or feature, for example PAY-45 |
| D | Test Scenario | Developer | One line: who can or cannot do what, under which condition |
| E | Role | Developer | One role from the Cover's test accounts |
| F | Preconditions | Developer | What must be true before step 1, naming the case that sets it up |
| G | Test Steps | Developer | Numbered, one action per line, exact on-screen labels; starts with HUMAN: when only a person can do it |
| H | Test Data | Developer | Exact values: names, amounts with centavos, dates as YYYY-MM-DD; "None" if nothing is entered |
| I | Expected Result | Developer | Numbered observable checks: exact messages, figures, statuses and where they appear |
| J | Priority | Developer | P1 core flow, money, compliance or security; P2 important; P3 minor |
| K | Depends On | Developer | Case IDs this one needs first, separated by commas; blank if none |
| L | Side Effects | Developer | What it creates, changes, sends or downloads; "None" if read-only; starts with IRREVERSIBLE: when it cannot be undone |
| M | UAT Status | UAT runner | Passed, Failed, Blocked or Not Tested |
| N | Actual Result | UAT runner | What happened |
| O | Remarks | UAT runner | Expected against actual, evidence, what is needed |
| P | Severity | UAT runner | Critical, High, Medium or Low for each failure |
| Q | Bug ID | UAT runner | Sentire Projects key of the bug it logged |
| R | Tested On | UAT runner | Date and time |
| S | Tested By | UAT runner | Claude (UAT) |

One complete case, as a developer session would write it (illustrative):

| Column | Value |
| --- | --- |
| Case ID | PAY-LV-001 |
| Module | Leave |
| Linked Issue | PAY-45 |
| Test Scenario | Employee can file a 1-day vacation leave when the balance allows |
| Role | Employee A |
| Preconditions | Employee A has 15.00 vacation leave days (seeded) |
| Test Steps | 1. Leave > File leave. 2. Type: Vacation Leave. 3. Date: 2026-11-20, whole day. 4. Click "Submit" |
| Test Data | Reason: UAT-LV-001 family errand |
| Expected Result | 1. Message "Leave request submitted". 2. My Leaves lists 2026-11-20, Vacation Leave, Pending. 3. Reload: still Pending |
| Priority | P1 |
| Depends On | (blank) |
| Side Effects | Creates a leave request; emails the approver at the test mailbox |

In the workbook each numbered step and check sits on its own line inside the cell.

## Writing good test cases

A case is good when a stranger can run it without asking anything and two testers would reach the same verdict.

1. **One behaviour, one verdict.** "Create and approve" is two cases, linked with Depends On.
2. **Cover every acceptance criterion** with a happy path, its main validation or error path, and a permission case where roles exist.
3. **Write what the user clicks and sees.** No database queries, code or API calls, unless the process is itself an API; then Test Steps say so.
4. **Make every check observable:** exact message text, figures to the centavo, status names, and where each appears. "Works correctly", "displays properly" and "is fast" are not checks; "opens within 3 s" is.
5. **Prove persistence.** After a save, add "Reload: still shows ..." as a check.
6. **Compute figures outside the app.** Calculations show their working and the rule's source (statute or table, with its date), computed by hand or a separate script. A figure copied from the app proves nothing.
7. **Test permissions both ways.** For each restriction: one case where the allowed role can, one where another role cannot, and a check that the record exists. In multi-tenant products, every process that shows records gets at least one cross-tenant case: company B cannot open company A's record by URL.
8. **Use fake data, tagged with the case ID,** such as "Juan UAT-LV-001 Dela Cruz". Never real employee, client or customer data.
9. **Send emails and notifications to the test mailbox.** The expected result names the subject line.
10. **Name exports.** The expected result names the file and the fields or values to check inside it.
11. **Keep human-only cases.** Printing, SMS or authenticator codes, real payments, native mobile and other browsers are still cases, with HUMAN: at the start of Test Steps.
12. **Order the cases** so dependencies come first, grouped by module.
13. **Bug-fix retests** hold the original failing case (same ID) plus two or three regression cases around it.

## Definition of Ready

The developer session confirms all of these before handing off; anything it cannot confirm is named in the handoff block.

- Deployed to the test environment, and the build the app shows matches the Cover.
- Migrations applied, seed data loaded, and every test account signs in.
- Every acceptance criterion has at least one case, with its Linked Issue filled.
- Every case has Test Steps, Test Data (or "None") and checkable Expected Results.
- Expected figures were computed outside the app.
- Permission and cross-tenant cases are present wherever the process has roles or shows records.
- Side Effects are filled on every case, and irreversible steps are marked IRREVERSIBLE:.
- Columns M to S are empty.
- Known issues are listed on the Cover.
- The file is named and placed as above and committed, and the UAT task exists in Sentire Projects.

## Handoff, results and retest

**Handoff.** When the workbook is ready, the developer session creates a Task in the product's Sentire Projects project titled "UAT: <process> <build>", label `uat-ready`, status In review, with this block as its description. It prints the same block at the end of its report.

```
UAT HANDOFF
Product / key: Sentire Payroll / PAY
Process: Leave filing and approval
Workbook: docs/uat/leave-filing/UAT_PAY_leave-filing_0.9.4.xlsx
Repo / commit: <owner>/<repo> @ 3f2a9c1
Build / URL: 0.9.4 at <staging URL> (build shown in the footer)
Accounts: HR, Approver, Employee A, Employee B (UAT Company B); passwords in <seed file>
Test mailbox: <test mailbox>
Cases: 18 (P1: 9, HUMAN: 2)
Side effects: creates leave requests and approvals; 4 emails to the test mailbox; nothing irreversible
Known issues: PAY-140
Not ready: (anything from the Definition of Ready not met, or "none")
UAT task: PAY-150
```

**Starting the run.** The owner opens a chat in the Sentire Software Project and says "Run UAT for PAY-150", attaching the workbook or pointing to its repo path. The runner shows its plan and side effects and waits for the go-ahead before it changes any data.

**What comes back.**

- The marked workbook: passes crossed off in green, failures in red with expected against actual and a severity, Blocked and Not Tested with what each needs, and a summary sheet. It is committed to `docs/uat/<process-slug>/results/`.
- One Bug per failure in the product's project, titled "[UAT] <case id>: <failure>", with labels `uat` and the run label.
- A comment on the UAT task with the totals and a recommendation.

**Retest.** The developer session fixes the bugs ("fixes PAY-151" in the commit), deploys a new build, and posts this block on the UAT task:

```
UAT RETEST
UAT task: PAY-150
Build / URL: 0.9.5 at <staging URL>
Fixed: PAY-151 (PAY-LV-003), PAY-152 (PAY-LV-007)
Retest: PAY-LV-003, PAY-LV-007 and the cases that depend on them
Changed cases: none (or the IDs, each approved by the owner)
```

Retests run in the same UAT chat where possible, because that chat still holds the marked workbook.

## Severity and sign-off

The runner suggests a severity for every failure and recommends a verdict; the owner decides both.

| Severity | Meaning | Bug priority |
| --- | --- | --- |
| Critical | Wrong money, tax or statutory figures; data lost or corrupted; a user sees or changes data they have no authority over; a core flow cannot be completed; a security control bypassed | Urgent |
| High | A core flow fails but has a workaround; a compliance output in the wrong format; a wrong permission that exposes no data | High |
| Medium | A non-core feature fails; a missing validation; a misleading message | Normal |
| Low | Cosmetic, wording, layout, minor slowness | Low |

| Recommendation | When |
| --- | --- |
| Not ready | Any Critical or High failure, or a core flow blocked |
| Ready with conditions | Only Medium or Low failures, or human-only checks, remain; they are listed |
| Ready | Every case in scope passed |

A process is accepted when the owner sets its UAT task to Done.

## Paste into each repo's CLAUDE.md

This block makes every Claude Code session in a repo follow the standard without being told.

```markdown
## UAT (Sentire UAT Standard v1.0)
Every process that changes what a user sees or does ships with a UAT document. A separate UAT session runs it; you never mark your own UAT. Full rules: docs/uat/UAT_STANDARD.md.
1. Before coding, list the process's acceptance criteria. Each becomes at least one test case.
2. Deploy to the test environment, never production. Confirm the build number shows in the app.
3. Copy docs/uat/UAT_TEMPLATE.xlsx to docs/uat/<process-slug>/UAT_<KEY>_<process-slug>_<build>.xlsx.
4. Fill every Cover field. Write one row per case on Test Cases, columns A to L only; leave M to S empty. Never rename, reorder or merge columns.
5. Follow the case rules: one behaviour per case; exact, checkable expected results; figures computed outside the app; permission and cross-tenant cases; Side Effects on every case; HUMAN: for steps only a person can do; fake data tagged with the case ID; no passwords in the workbook.
6. Meet the Definition of Ready, commit, create the Sentire Projects task "UAT: <process> <build>" (label uat-ready, status In review) with the UAT HANDOFF block, and print the block at the end of your report.
7. After the run: fix with "fixes KEY-n", deploy a new build, and post a UAT RETEST block. Never change an expected result to match the app without the owner's approval.
```

## Rolling it out

The standard applies to all ten products in Sentire Projects: Payroll (PAY), Ledger (LDG), POS (POS), Helpdesk (HLP), LMS (LMS), Projects (PRJ), Books (BKS), Money (MNY), Tax Filing (TAX) and Website (WEB). Track the adoption as a task in each product's Sentire Projects project.

1. Save this file in each product repo as `docs/uat/UAT_STANDARD.md`.
2. Put `UAT_TEMPLATE.xlsx` beside it in `docs/uat/`.
3. Paste the CLAUDE.md block above into the repo's CLAUDE.md.
4. Chats in the Sentire Software Project find this standard as `Sentire Software/UAT/Sentire_UAT_Standard.md`; UAT chats use the uat-runner skill.
5. To change the standard, edit the master doc, raise the version in the CLAUDE.md block's heading, and replace this file in the repos.
