# UAT retest 2, build 0.1.0+87b488a53272 (B83)

Retest 1: build 0.1.0+5195441c14c2, 2026-11-21, 78 cases (63 passed, 9 failed, 3 blocked, 3 human). Marked workbooks: `docs/uat/<slug>/results/*_0.1.0+5195441c14c2_RESULTS.xlsx`. Summary: `docs/uat/results/RETEST_RUN_SUMMARY_0.1.0+5195441c14c2.md`.

This build also carries B81: Sentire Ledger now runs on Sentire Framework v16.60.2-sentire.1.

The deploy rebuilt staging. Restart staging once, then run each workbook below in the master checklist order: the Retest cases and, first, the cases that rebuild their data.

## Workbooks and cases

| Workbook | UAT task | Retest | Also run first (their data) |
| --- | --- | --- | --- |
| setup-company | LDG-163 | SU-007 | |
| paid-now-card-counter | LDG-148 | PN-001 (BIR details tab, LDG-229) | |
| roles-permissions | LDG-154 | RP-010, RP-022 | |
| sales-collections | LDG-156 | SL-001 (BIR details tab), SL-010 | SL-002, SL-003, SL-009 |
| purchases-payables | LDG-157 | PU-001 (BIR details tab) | |
| approvals | LDG-162 | AP-003, AP-007, AP-010 | AP-002, AP-004, AP-008; purchases-payables PU-001 |
| journals-periods | LDG-158 | JP-008 | roles-permissions RP-010, RP-022 |
| bir-returns | LDG-159 | BR-009, BR-011 | BR-001, BR-007, BR-008, BR-010 |
| books-audit | LDG-160 | BA-013 | sales-collections SL-003 |

Still with the owner (HUMAN): SL-013 (print), then SL-014 and BA-012 (reprint); PU-009 and BR-005 (eBIRForms files).

New for this build: the framework-branding workbook (B81, `docs/uat/framework-branding/`), run in full.

## Changed cases (owner approval needed before the run)

| Case | Change | Why |
| --- | --- | --- |
| AP-003 | No Submit button; the primary button reads Request approval (the server still refuses a direct submit) | The form offers Request approval up front (LDG-232) |
| AP-010 | Adds a step: a new 60,000.00 bill after the chain is disabled submits directly | The case had no step to check it (Blocked in retest 1) |
| BR-011 | The original no longer offers Open amendment once an amendment exists | By design (LDG-216) |
| SL-010 | Status "Credit Note Issued", Outstanding 0.00 | ERPNext's status for an invoice with a credit note (LDG-231) |
| BA-013 | "Sales Invoice <name> (BIR serial <serial>) has been issued and cannot be deleted. Correct it with a credit note or a debit note." | The new message (LDG-222) |
