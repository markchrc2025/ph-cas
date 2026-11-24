# Sentire Ledger UAT Retest 3: run summary

- Build: 0.1.0+742f9d22845a (staging, confirmed through ph_cas.qa.uat.build_info)
- Run: 2026-11-24 22:30 to 2026-11-25 00:10 Manila, built-in browser at 1366x850
- Scope: the Retest and "Also run first" cases in RETEST_0.1.0+742f9d22845a.md, in master checklist order
- Owner approval: LDG-153 (AP-004, AP-008, FW-003, FW-004, FW-005)
- Nothing was fixed, restarted or deployed by the runner.

## Totals

| Workbook | In scope | Passed | Failed | Blocked |
|---|---|---|---|---|
| setup-company | 1 | 1 | 0 | 0 |
| paid-now-card-counter | 1 | 1 | 0 | 0 |
| roles-permissions | 2 | 2 | 0 | 0 |
| sales-collections | 2 | 2 | 0 | 0 |
| purchases-payables | 1 | 1 | 0 | 0 |
| approvals | 8 | 6 | 1 | 1 |
| framework-branding | 5 | 3 | 0 | 2 |
| **Total** | **20** | **16** | **1** | **3** |

The other 11 workbooks had no cases in scope; they are returned unchanged as _RESULTS files.

## Failure

**LDG-AP-008, High, LDG-244.** Approval was recorded but the bill did not post.
- Accountant A re-requested at 23:59:22 on 11-24. Accounting Manager A approved at 00:00:30 on 11-25.
- Message: "Due Date cannot be before Supplier Invoice Date".
- The request APR-2026-00007 is saved as Approved, but ACC-PINV-2026-00004 stays Draft (66,000.00) with a plain Submit button.
- Likely cause: on submit, the posting date moves to the new day while the due date stays on the draft day. Approval and posting are not done together, so the request ends Approved with nothing posted.
- Any bill drafted on one day and approved on a later day can hit this, so it is not just a midnight edge case.

## Blocked

- **LDG-AP-010:** depends on AP-008. Chain CHAIN-00005 (UAT-AP-002 Bills over 50k) is still enabled on staging.
- **LDG-FW-004 and LDG-FW-005:** they run as Administrator, and STAGING_ADMIN_PASSWORD was not given in the chat.

## Stale browser cache (LDG-243, High)

The /assets/ph_cas/js/*.js files are served without a version in the URL and with Cache-Control max-age=604800. The browser kept the B84 copies of approvals.js, modules.js, branding.js, help.js and tutorials.js, and Ctrl+Shift+R did not refresh them.

This made the first pass fail or misbehave in several places:
- SU-007
- AP-007 and AP-011
- The panel placement in AP-004 and AP-008
- FW-002 and FW-003

After each file was re-fetched with cache 'reload', these cases were rerun. The rerun results are the ones recorded. Real users would see the same stale behaviour after a deploy.

## Issue changes

| Issue | Change |
|---|---|
| LDG-165 (SU-007) | Done |
| LDG-235 (RP-016 / SL-008) | Done |
| LDG-236 (AP-004/AP-008 reason step) | Done; correction comment added |
| LDG-233 (AP-007) | Done |
| LDG-237 (AP-011) | Done |
| LDG-243 | New, stale unversioned ph_cas assets, High |
| LDG-244 | New, AP-008 approval without posting, High |

Totals were commented on these tasks: LDG-163, LDG-148, LDG-154, LDG-156, LDG-157, LDG-162 (corrected) and LDG-184.

## Observations (not blocking)

- AP-004: the banner "Submit this document to confirm" shows while a request is pending, although the Accountant cannot submit.
- AP-004: system users admin@example.com and qa.admin@sentire.solutions are listed as pending approvers.
- AP-007: Escape on the reason message also closes the Reject dialog.
- AP-007: Accounting Manager A sees Withdraw request on a request made by Accountant A.
- AP-011: after Approve, the page stays greyed out for about 10 s before showing Cancelled.

## Test data created (nothing deleted)

**Customers and suppliers**
- Customers: UAT-PN-001 Juan Dela Cruz, UAT-PN-001 Pasig Corp.
- Supplier: UAT-PU-001 Makati Janitorial Corp.

**Items**
- UAT-PN-001-SVC
- UAT-SL-001-CEM, used with customer UAT-SL-001 Antipolo Builders Inc.
- UAT-PU-001-JAN

**Sales invoices**
| Invoice | Serial | Status |
|---|---|---|
| ACC-SINV-2026-00002 | 00000002 | |
| ACC-SINV-2026-00003 | 00000003 | Cancelled |
| ACC-SINV-2026-00004 | 00000004 | Cancelled |
| ACC-SINV-2026-00004-1 | 00000005 | |
| ACC-SINV-2026-00005 | 00000006 | Unpaid, manual no. UAT-AP-011, first run |
| ACC-SINV-2026-00006 | 00000007 | Cancelled, manual no. UAT-AP-011-R3 |

**Purchase invoices**
- ACC-PINV-2026-00002: posted
- ACC-PINV-2026-00003: posted
- ACC-PINV-2026-00004: Draft, with Approved request APR-2026-00007

**Approval chains**
- CHAIN-00001: disabled
- CHAIN-00004: disabled
- CHAIN-00005: **still enabled**
- CHAIN-00008: disabled

**Settings:** Projects module switched back on.

## Recommendation

**Not ready.**
1. Fix LDG-244, then rerun AP-008 and AP-010.
2. Fix LDG-243 (version the ph_cas assets), so users get new scripts after a deploy.
3. Provide the Administrator password for FW-004 and FW-005.

Sign-off stays with the owner.
