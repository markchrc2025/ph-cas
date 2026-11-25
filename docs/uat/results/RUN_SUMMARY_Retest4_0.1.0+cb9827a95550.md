# Sentire Ledger UAT Retest 4: run summary

- Build: 0.1.0+cb9827a95550 (staging, confirmed with ph_cas.qa.uat.build_info)
- Run: 2026-11-25, 10:05 to 10:22 Manila. Built-in browser at 1366x850.
- Scope: the Retest and "Also run first" cases in RETEST_0.1.0+cb9827a95550.md, run in master checklist order.
- The runner did not hard-reload, refetch scripts, fix anything, restart or deploy.

## Totals

| Workbook | In scope | Passed | Failed | Blocked |
|---|---|---|---|---|
| purchases-payables | 1 | 1 | 0 | 0 |
| approvals | 5 | 5 | 0 | 0 |
| framework-branding | 2 | 0 | 0 | 2 |
| **Total** | **8** | **6** | **0** | **2** |

The other 15 workbooks had no cases in scope. They are returned unchanged as _RESULTS files.

## Fixes confirmed

**LDG-244 (AP-008): Done.** Accountant A requested approval at 10:13 and Accounting Manager A approved at 10:14.
- The panel reads "Approved and posted".
- ACC-PINV-2026-00002 is Submitted, Grand Total 66,000.00.
- Request APR-2026-00002 is Consumed.

The request and the approval were on the same day. The plan allows that, and the day-change path was not repeated.

**LDG-243: Done.** The ph_cas scripts load as `/assets/ph_cas/js/*.js?v=cb9827a95550`. No stale script was seen anywhere in the run.

**AP-010: now passes (was Blocked).**
- CHAIN-00001 is disabled.
- ACC-PINV-2026-00003 showed Submit with no Request approval and submitted directly. Grand Total 66,000.00.

## Blocked

**FW-004 and FW-005.** These sign in as Administrator with STAGING_ADMIN_PASSWORD. Only STAGING_UAT_PASSWORD was given in the chat, even though it was asked for twice. The UAT password was not tried on the Administrator account.

## Deviation

AP-007 (reject, then request again) is not in this retest's scope. So AP-008 approved the pending request that AP-004 opened, instead of a second request.

## Observations (not blocking)

- After signing in, the login page kept loading for about 40 s. It only moved on when Home was opened.
- Right after Save, a bill showed a plain Submit for about 1 s (Accountant) to 5 s (approver) before the Approval panel drew and Request approval or Approve appeared. A quick click in that moment could reach the server's submit refusal.
- These were already seen in Retest 3:
  - the "Submit this document to confirm" banner shows while a request is pending;
  - admin@example.com and qa.admin@sentire.solutions are listed as pending approvers.

## Test data created (nothing deleted)

- Supplier: UAT-PU-001 Makati Janitorial Corp. (TIN 000-777-201, EWT contractor)
- Item: UAT-PU-001-JAN
- Approval chain: CHAIN-00001 "UAT-AP-002 Bills over 50k" (now disabled)
- Bills:
  - ACC-PINV-2026-00002: UAT-AP-003, posted through approval APR-2026-00002
  - ACC-PINV-2026-00003: UAT-AP-010, posted directly

## Issue changes

| Issue | Change |
|---|---|
| LDG-244 | Done |
| LDG-243 | Done |
| LDG-157 | Totals commented |
| LDG-162 | Totals commented |
| LDG-184 | Totals commented |
| LDG-153 | Totals commented |

No new bugs.

## Recommendation

**Ready with conditions.** Every case that could run passed, and both Retest 3 bugs are fixed. What is left:

1. FW-004 and FW-005 need the Administrator password.
2. The HUMAN cases are still with the owner:
   - SL-013: print
   - SL-014 and BA-012: reprint checks
   - PU-009 and BR-005: eBIRForms files

Sign-off stays with the owner.
