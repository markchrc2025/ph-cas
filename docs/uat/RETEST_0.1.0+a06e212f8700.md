# UAT retest 6, build 0.1.0+a06e212f8700 (B96)

From UAT retest 5 (build 0.1.0+59b5edaaee39): 5 failed, 2 blocked. Fixes in B96; BR-018 and PS-001 expected results changed with the owner's approval (28 Nov 2026). Retest files approved by the owner on 28 Nov 2026.

The deploy rebuilt staging (fresh data; staging runs as a client on Team again). Run in this order. "Also run first" cases are run for their data only, also when they sit in another workbook.

| # | Workbook | Retest | Also run first (their data) |
| --- | --- | --- | --- |
| 1 | journals-periods | JP-007 (LDG-245: Staff offered no Add, Submit, Cancel, Amend or Delete on journals; also open a bill and a supplier as Staff A: read-only) | |
| 2 | import-templates | IM-015 (LDG-247: no Import from a template on the Supplier list for Staff A) | |
| 3 | get-to-know | GK-007 (LDG-248: Confirm your tax rules ticked when Draft Tax Rules is empty) | |
| 4 | bir-returns | BR-018 (LDG-246, expected changed: 2 invoices, 570.00 with DEMO-0001) | the case that creates customer UAT-PN-001 Pasig Corp. (customer step only); sales-collections SL-011, SL-012, SL-016 (SL-016 is HUMAN: the owner uploads a PDF) |
| 5 | plan-and-settings | PS-001 (LDG-249, expected changed: Not found or Not Permitted) | |
| 6 | framework-branding | FW-004, FW-005 (Administrator, STAGING_ADMIN_PASSWORD given in the chat) | |

Also check on the side (retest 5 observations, no case): Help > Your plan > Change plan opens on the first click; an amended 2307 starts at Times printed 0.
