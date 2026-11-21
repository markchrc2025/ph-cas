# UAT retest, build 0.1.0+5195441c14c2 (B82)

First run: build 0.1.0+1d56e40d2b40, 2026-11-20 to 21, 227 cases (158 passed, 37 failed, 14 blocked, 18 not tested). Marked workbooks: `docs/uat/<slug>/results/`. Summary: `docs/uat/results/UAT_RUN_SUMMARY_0.1.0+1d56e40d2b40.md`.

The deploy of this build rebuilt staging, so the data the first run created is gone. Restart staging once, then run each workbook below in the master checklist order. Run the cases named under Retest, and the cases they depend on (column K, Depends On), since those must be done again to rebuild their data.

## Workbooks and cases

| Workbook | UAT task | Retest (fixed or changed) | Also run first (their data) |
| --- | --- | --- | --- |
| setup-company | LDG-163 | SU-002, SU-007 | |
| paid-now-card-counter | LDG-148 | PN-001 (customer now has an address) | |
| record-expense | LDG-144 | EX-001, EX-003, EX-004, EX-005, EX-008 | EX-002 |
| roles-permissions | LDG-154 | RP-016, RP-022, RP-026, RP-030, RP-035, RP-039 | RP-014, RP-034 |
| role-homes | LDG-147 | RH-005, RH-006 | RH-004 |
| sales-collections | LDG-156 | SL-009, SL-010, SL-011, SL-012, SL-014 | SL-001 to SL-003 |
| masters-stock | LDG-161 | MS-006 | MS-004 |
| purchases-payables | LDG-157 | PU-001, PU-002, PU-004, PU-005, PU-006, PU-008, PU-009, PU-010 | |
| approvals | LDG-162 | AP-001 to AP-010 | |
| journals-periods | LDG-158 | JP-001, JP-007, JP-008 | RP-022 (roles-permissions) |
| bir-returns | LDG-159 | BR-002, BR-006, BR-009, BR-010, BR-011, BR-014 | BR-001, BR-005, BR-007, BR-008 |
| books-audit | LDG-160 | BA-001, BA-005, BA-006, BA-012, BA-013 | RP-031, RP-033 (roles-permissions), SL-003 (sales-collections) |
| import-templates | LDG-145 | IM-015 | |
| go-live | LDG-143 | GL-005, GL-007, GL-008 | GL-001 to GL-004 |

Cases marked Not tested in the first run because they need a person (HUMAN: printing, PDFs, zips: LG-001 to LG-005, PC-001 to PC-005, BA-007, BA-014, SL-013, BR-005, IM-001, JP-003, PU-009, RE-009, SU-004) are still open; the owner does them.

## Changed cases (owner approval needed before the run)

| Case | Change | Why |
| --- | --- | --- |
| All "refused" results | Also accept the new form note "Your role cannot add new <doctype> records. Nothing here will be saved. Ask an Accounting Manager or the Owner." with no Save button | B82 shows the refusal on the form instead of only on save (LDG-187, 193, 206) |
| EX-003 | Grand Total 10,700.00 (10,000.00 + 1,200.00 VAT - 500.00 withheld) | ERPNext's Grand Total is net of the tax deducted (LDG-179) |
| EX-004 | Adds Creditors credit and debit 10,700.00; totals 21,900.00 | A paid bill posts the bill and its payment in one voucher (LDG-180) |
| PU-001 (data) | EWT category Contractor or subcontractor services, not services | Janitorial is WC120 for every agent; "services" (WC160) applies only to top withholding agents (LDG-200 to 203, 207) |
| PU-002, PU-008 | ATC WC120 and its basis RR 2-98 Sec. 2.57.2(E); figures unchanged | Same |
| PU-010 | Step gives the period | The form needs it (LDG-204) |
| RP-016 | No Cancel button; the banner "Issued with BIR serial <serial>. It cannot be cancelled: correct it with a credit note or a debit note." | The button is hidden by design (LDG-185) |
| BA-013 | Delete from the list's Actions menu | A submitted form has no Delete (LDG-222) |
| BR-009 | Delete from the list; also checks no "modified after you opened it" | Same, and LDG-214 |
| RP-026 | Uses the common refused wording | LDG-186 |
| RP-035, BR-006 | The form's note "You prepare this return. An Accounting Manager or the Owner marks it as filed, after the BIR confirmation is attached." and no Submit | A role without submit rights gets no Submit button (LDG-188, 213) |
| RH-005, RH-006 | The Payments, Address & Contact and Terms tabs; Currency and Price List shows once a customer is picked | ERPNext behaviour (LDG-194, 195) |
| BA-001 | Names the GRAND TOTAL row | LDG-219 |
| BA-005 | Every posting of the day appears, and the book ties | The General Journal is built that way (LDG-220) |
| BA-006 | One summary row per item with the Stock count adjustment column | The Inventory book is a summary (LDG-221) |
| BR-002 | Names the new 2550Q output VAT lines | LDG-212 |
| BR-014 | Accepts "No 2307 received for the 1702Q in this period, so there is no SAWT to write." when none was received | Staging has none in Q-1 (LDG-217) |
| JP-001 | Quotes the new message | LDG-208 |
| GL-007 | Drops the Difference Account step (periodic inventory) | LDG-228 |
| GL-008 | Expects Is Opening Entry to be absent | LDG-228 |
| PN-001 (data) | Customer 2 gets an address | Unblocks SL-011 (RR 7-2024 needs the buyer's address) |
