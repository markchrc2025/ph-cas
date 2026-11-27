# UAT retest 5, build 0.1.0+59b5edaaee39 (B89 to B95)

From the owner's human tests of 25 to 27 Nov 2026 (build 0.1.0+8d5b69494d4e). Case changes and new cases approved by the owner on 27 Nov 2026.

The deploy rebuilt staging (fresh data; staging now runs as a client on Team). Run the workbooks below in this order. A case whose Depends On is not in the Retest column is run first for its data, also when it sits in another workbook (added 27 Nov after the run found two missing: RP-010's account and the UAT-PN-001 customer).

## Workbooks and cases

| # | Workbook | Retest | Also run first (their data) |
| --- | --- | --- | --- |
| 1 | journals-periods | JP-003 (Delete message), JP-007 (Staff reads journals, changed) | roles-permissions RP-010 (account UAT-RP-010 Seminar fees - TTC) |
| 2 | sales-collections | SL-013, SL-014 (server PDF print, Download PDF; HUMAN), SL-016 (new: customer's 2307 upload; HUMAN) | SL-001, SL-002, SL-003, SL-011, SL-012; and first the case that creates customer UAT-PN-001 Pasig Corp. (its customer step only) |
| 3 | purchases-payables | PU-009 (lock and direct print, changed; HUMAN), PU-012, PU-013 (HUMAN), PU-014 (new) | PU-001, PU-002, PU-008 |
| 4 | bir-returns | BR-005 (XML download, changed), BR-018, BR-019 (new; BR-019 HUMAN) | BR-001 |
| 5 | import-templates | IM-001 (template, changed; HUMAN), IM-002 (TIN message, changed), IM-015 (Staff reads suppliers, changed), IM-017 (new) | |
| 6 | get-to-know | GK-001 to GK-010 (new, B91) | |
| 7 | plan-and-settings | PS-001 to PS-007 (new, B93) | |
| 8 | framework-branding | FW-004, FW-005 (Administrator sign-in, STAGING_ADMIN_PASSWORD given in the chat) | |

Cases marked HUMAN are for the owner (print, files, uploads).
