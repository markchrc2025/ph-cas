# UAT retest 3, build 0.1.0+742f9d22845a (B86)

Retest 2: build 0.1.0+b8680cc281fc, 34 cases (22 passed, 9 failed, 3 blocked). Marked workbooks: `docs/uat/<slug>/results/*_0.1.0+b8680cc281fc_RESULTS.xlsx`. Summary: `docs/uat/results/RUN_SUMMARY_Retest2_0.1.0+b8680cc281fc.md`.

The deploy rebuilt staging, so the data of retest 2 is gone. Restart staging once, then run each workbook below in the master checklist order: the Retest cases and, first, the cases that rebuild their data.

## Workbooks and cases

| Workbook | UAT task | Retest | Also run first (their data) |
| --- | --- | --- | --- |
| setup-company | LDG-163 | SU-007 (LDG-165) | |
| paid-now-card-counter | LDG-148 | | PN-001 (customer for RP-016) |
| roles-permissions | LDG-154 | RP-016 (LDG-235) | RP-014 |
| sales-collections | LDG-156 | SL-008 (was Blocked) | SL-001 |
| purchases-payables | LDG-157 | | PU-001 |
| approvals | LDG-162 | AP-004, AP-007, AP-008 (LDG-236, 233), AP-010 (was Blocked), AP-011 (LDG-237) | AP-001, AP-002, AP-003 |
| framework-branding | LDG-184 | FW-001 to FW-005 (LDG-238 to 241; FW-004 and FW-005 need the Administrator password) | |

Still with the owner (HUMAN): SL-013 (print), then SL-014 and BA-012 (reprint); PU-009 and BR-005 (eBIRForms files).

## Changed cases (owner approval needed before the run)

| Case | Change | Why |
| --- | --- | --- |
| AP-004, AP-008 | Steps no longer ask for a reason: a bill's Request approval takes none | The step could not be done (retest 2 remark) |
| FW-003 | Steps say where Help is in this desk (the menu under the product name at the top of the sidebar) and also check the apps screen's avatar menu (Get help, Your plan, no "Frappe Support") | The desk has no Help in the top bar (LDG-240, LDG-242) |
| FW-004, FW-005 | Preconditions name the Administrator password (STAGING_ADMIN_PASSWORD, given in the chat) | Blocked in retest 2 (LDG-241) |
