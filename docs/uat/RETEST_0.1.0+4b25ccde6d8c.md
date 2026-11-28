# UAT retest 7, build 0.1.0+4b25ccde6d8c (B97)

From UAT retest 6 (build 0.1.0+a06e212f8700): 5 passed, 2 blocked, side items LDG-250, LDG-251 and the LDG-183 question. Fixes in B97; retest approved by the owner on 28 Nov 2026.

The deploy rebuilt staging (fresh data, Team plan). Run in this order; "Also run first" cases are for their data only.

| # | Workbook | Retest | Also run first (their data) |
| --- | --- | --- | --- |
| 1 | record-expense | EX-008 (LDG-183: Staff A has no Record an expense, list read-only) | |
| 2 | plan-and-settings | PS-004 and PS-005 step 1 (LDG-250: Change plan opens on the first click from Help > Your plan) | PS-003 |
| 3 | purchases-payables | PU-014 (LDG-251: the amendment shows Draft and Times printed 0 before its first save) | PU-001, PU-002, PU-008, PU-009, PU-012, PU-013 (PU-009 and PU-013 are HUMAN: the owner prints) |
| 4 | framework-branding | FW-004, FW-005 (Administrator: password ADMIN_PASSWORD, not STAGING_ADMIN_PASSWORD) | |
