# Sentire Ledger (ph_cas)

BIR-registrable computerized accounting system on ERPNext v16. Build log: docs/BUILD-LOG.md. Staging and the QA connector: docs/STAGING.md.

## UAT (Sentire UAT Standard v1.0)
Every process that changes what a user sees or does ships with a UAT document. A separate UAT session runs it; you never mark your own UAT. Full rules: docs/uat/UAT_STANDARD.md.
1. Before coding, list the process's acceptance criteria. Each becomes at least one test case.
2. Deploy to the test environment, never production. Confirm the build number shows in the app.
3. Copy docs/uat/UAT_TEMPLATE.xlsx to docs/uat/<process-slug>/UAT_<KEY>_<process-slug>_<build>.xlsx.
4. Fill every Cover field. Write one row per case on Test Cases, columns A to L only; leave M to S empty. Never rename, reorder or merge columns.
5. Follow the case rules: one behaviour per case; exact, checkable expected results; figures computed outside the app; permission and cross-tenant cases; Side Effects on every case; HUMAN: for steps only a person can do; fake data tagged with the case ID; no passwords in the workbook.
6. Meet the Definition of Ready, commit, create the Sentire Projects task "UAT: <process> <build>" (label uat-ready, status In review) with the UAT HANDOFF block, and print the block at the end of your report.
7. After the run: fix with "fixes KEY-n", deploy a new build, and post a UAT RETEST block. Never change an expected result to match the app without the owner's approval.

### How it works in Ledger
- Build: `python3 ph_cas/buildstamp.py --git <commit>` gives the build the image shows (Help > Get help, Help > Your plan, and /api/method/ph_cas.qa.uat.build_info). Docs-only commits keep the build.
- Test accounts: seeded on staging by ph_cas/qa/uat.py, kept to their companies by User Permissions; password STAGING_UAT_PASSWORD in the Ledger Staging app's Environment (Dokploy). Check them with ph_cas.qa.uat.check_accounts.
- Companies: A Tala Trading Corporation (demo, has history), B UAT Company B Corp. (the other tenant), C UAT Bagong Simula Corp. (fresh, go-live), D UAT Bagong Bukas Corp. (fresh, imports).
- Test mailbox: on staging every outgoing mail goes to mcrc.business.solutions@gmail.com; mails also show in Email Queue.
- Never deploy to staging during a UAT run: a deploy rebuilds the site. A restart restores the snapshot.
- Workbooks are made with tools/uat/make_workbooks.py from the case lists in tools/uat/cases/.
