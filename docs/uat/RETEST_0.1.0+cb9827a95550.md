# UAT retest 4, build 0.1.0+cb9827a95550 (B87)

Retest 3: build 0.1.0+742f9d22845a, 20 cases (16 passed, 1 failed, 3 blocked). Marked workbooks: `docs/uat/<slug>/results/*_0.1.0+742f9d22845a_RESULTS.xlsx`. Summary: `docs/uat/results/RUN_SUMMARY_Retest3_0.1.0+742f9d22845a.md`.

No case changes in this retest. The deploy rebuilt staging, so restart staging once, then run each workbook below in the master checklist order.

Scripts now load with the build in their address (LDG-243), so no hard reload or fresh fetch is needed after this deploy; note it in Remarks if a stale script is still seen.

## Workbooks and cases

| Workbook | UAT task | Retest | Also run first (their data) |
| --- | --- | --- | --- |
| purchases-payables | LDG-157 | | PU-001 |
| approvals | LDG-162 | AP-008 (LDG-244), AP-010 (was Blocked) | AP-002, AP-003, AP-004 |
| framework-branding | LDG-184 | FW-004, FW-005 (were Blocked: Administrator sign-in with STAGING_ADMIN_PASSWORD, given in the chat) | |

AP-008 was failed by a day change between the request and the approval. To check that case on purpose, the request may be made one day and approved the next; on the same day it should also pass.

Still with the owner (HUMAN): SL-013 (print), then SL-014 and BA-012 (reprint); PU-009 and BR-005 (eBIRForms files).
