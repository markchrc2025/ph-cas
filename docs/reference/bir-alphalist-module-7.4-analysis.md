# BIR Alphalist Data Entry and Validation Module 7.4: structural analysis (5 Nov 2026)

Prepared by Claude at the owner's request: a structural analysis of the BIR's Alphalist Data Entry and Validation Module, version 7.4, and the issuances that came with it, and what they mean for the firm's CAS. Read it with `claude/ph-cas-build-plan-2026-10-24.md` (unit CAS-9) and `claude/ph-tax-rules-catalogue-2026-10-26.md`.

## Update, 16 Nov 2026 (B62): the module was run
The module was installed under Wine and run (docs/dat/VERIFICATION.md, ph_cas/tests/golden/alphalist/). That settles several open points below:
- **Record format:** comma-separated, CR LF line ends including the last line, amounts with two decimals, names quoted when they have a value and empty unquoted fields when blank.
- **Branch code:** 4 digits. The validator rejects 5.
- **SAWT for the 2550Q:** form code 2550Q (the module lists 1700, 1701, 1701Q, 1702, 1702Q, 2550M, 2550Q, 2551Q, 2553).
- **QAP:** one file per month of the quarter, named for that month; a file with no detail fails validation.
- **Names:** the validator rejects ' & , and Ñ.
- **Codes after 7.4:** WV080 fails the unpatched module ("ATC is invalid"); the BIR publishes an ATC patch for 7.4 on its Downloadables page.

## What was reviewed
| File | What it is |
|---|---|
| Alphalist_Data_Entry_and_Validation_ver._7.4.zip | One installer, `Alphalist Data Entry and Validation ver. 7.4.exe` (13.3 MB, dated 25 Feb 2025). SHA-256: zip b4591c13...7cbe9, installer 6fb71a5a...00ef9 |
| RMC No. 15-2025 | 1-page scan dated 25 Feb 2025: availability of version 7.4 |
| RMC No. 15-2025 Annex A | 2-page scan: the SAWT file structure, and lists of values |
| RMC No. 15-2025 Annex B | 1-page scan: the standard file naming convention |
| RMC No. 7-2021 Annex C, DE | 18-page job aid for the Data Entry module, version 7.0 (January 2020) |
| RMC No. 7-2021 Annex C, Val | 7-page job aid for the Validation module, version 7.0 (January 2020) |

Method:
- **Unpacked statically.** The installer was unpacked without installing or running anything.
- **What was inventoried:** the file list and types, version resources, table schemas and record counts, menu labels, and the reference tables' codes and rates.
- **Program code:** the code inside the screen files was not read for logic or copied. Formats and rules here come from the RMCs and job aids; the module itself serves as the validator.
- **Taxpayer data:** tables that can hold it were counted, not opened (see "Data handling").

## Bottom line
- **What the module is.** The BIR's own desktop tool for alphalists. It has two programs: Data Entry (type the records in, generate the DAT files) and Validation (check a DAT file and prepare it for submission). Both are built in Visual FoxPro 6 on local .dbf tables.
- **What it means for the CAS.** The BIR provides for exactly this case. RMC 15-2025: "those taxpayers with their own extract program shall strictly observe the attached revised file structures and standard naming conventions" (Annexes A and B). The CAS is an own extract program: it writes the DAT files straight from the books, so no client re-types a payee.
- **The Validation module stays in the workflow.** Every DAT file must pass it before submission; RMC 55-2026 says an incomplete or erroneous list may count as non-submission. It also makes the encrypted copy that eSubmission needs. So the CAS produces the file, the client or the firm runs it through the module, then files it.
- **What the CAS must generate for MSMEs:**
  - the QAP for 1601-EQ (quarterly) and the annual 1604-E;
  - the SAWT for 2550Q, 2551Q, 1701Q/1701 and 1702Q/1702;
  - the MAP for 1600-VT (monthly; digital services from non-residents).
  - 1601-FQ and 1604-F are rarer for MSMEs; 1604-C waits for payroll.
- **The specs in hand are incomplete.** The uploaded Annex A covers only the SAWT, and its control record is cut off after field 7. The layouts for MAP, QAP and the annual alphalists are in earlier annexes (RMC 61-2024 for version 7.3; RMC 25-2024). Collect those before coding.
- **Version 7.4 predates the 2025 to 2026 withholding changes.**
  - Its ATC table is dated 6 Feb 2025. It has no WI/WC 840 to 860 (the 0.5% top withholding agent codes, Oct 2025) and no WV080 to WV100 (VAT on digital services), nor WV110 (reported for VAT on purchases from registered enterprises).
  - Files using those codes may fail validation until the BIR ships a newer module. No version newer than 7.4 was found on 5 Nov 2026.

## The package
### Installer and programs
- **Installer:** NSIS 3, carrying the Visual FoxPro 6 runtime (VFP6R.DLL, VFP6RENU.DLL, VFP6T.DLL).
- **`Alphalist Data Entry.exe`** (7.8 MB, dated 21 Jan 2025): version resource 5.0.0, "Alphalist Data Entry System", Bureau of Internal Revenue, Information Systems Group.
- **`Alphalist Validation.exe`** (1.7 MB, dated 20 Jan 2025): version resource 1.1.1, "Alphalist Validation Module".
- **Version number:** neither program's version resource says 7.4; that number appears only in the installer's name and the RMC.
- **Terms of use:**
  - No licence or terms of service ships with it, unlike eBIRForms' `tosa.html`. The About screen says "All rights reserved".
  - Under the IP Code (RA 8293, Sec. 176), using a government work for profit needs the agency's prior approval. That is one more reason the CAS implements the published formats rather than reusing the module's code or tables.

### Folders (443 files, 44 MB unpacked)
| Folder | Contents |
|---|---|
| (root) | The two programs, the VFP runtime, the uninstaller, icons, empty marker files |
| FORMS | 103 screens: data entry and inquiry per form and schedule, validation, utilities, eSubmission |
| LIBS, MENUS | 3 class libraries, one compiled application (BIR1604.APP), 2 menus |
| DATA | The working database: one alphalist detail table, header tables per form, the payee list ("TIN library"), and the reference tables in DATA/LOVAL |
| DATA/LOVAL | ATCs with rates (`reg_atcs`, 257 rows, 253 codes, dated 6 Feb 2025); ATC-to-certificate map (`regatc`, 549 rows, 6 Feb 2025); 145 RDOs; 11 pre-TRAIN personal-exemption codes (Z, S, S1 to S4, M, M1 to M4, amounts set to zero); 6 server entries (host name and IP) |
| PREDATA | An older copy of the database (3-digit branch codes, older ATC tables) |
| Templates (three folders) | 18 Excel print templates of old BIR forms (2550Q of September 2005, 1601-E, 2550M, 2551M and others), plus .xltx copies of 2306, 2307 and 2316. Legacy. |

### Screens (from the screen names and the job aids)
| Area | Screens |
|---|---|
| MAP (monthly) | 1600-VT and 1600-PT data entry and inquiry |
| QAP (quarterly) | 1601-E: Schedule 1 creditable; Schedule 2 payees exempt from withholding but subject to income tax. 1601-F: Schedules I (final tax), II (fringe benefits), III (exempt payees). 1621: tax withheld on withdrawals from a decedent's deposit (banks only). |
| SAWT | One data entry screen for all return types: 1700, 1701, 1701Q, 1702, 1702Q, 2550M, 2550Q, 2551M, 2553 |
| Annual | 1604-C: Schedule 1 employees, Schedule 2 minimum wage earners. 1604-E: Schedules 3 and 4. 1604-F: Schedules 4, 5 and 6. |
| Common | Payee list, Generate File, Print/Inquire, "Generate 1604E File" from the year's QAP data, re-index, update database, users and passwords, eSubmission |
| Validation | 1600-PT, 1600-VT, SAWT, 1601-EQ, 1601-FQ, 1621, 1604-C, 1604-E, 1604-F |

### Data model
- **One wide detail table** (`alphadtl`, 83 fields) holds the rows of every schedule:
  - form type, withholding agent's TIN and branch, return period, schedule, sequence;
  - payee TIN, branch and names; ATC, rate, income payment, tax withheld;
  - the 1604-C compensation fields: present and previous employer, taxable and non-taxable parts, 13th month and other benefits, de minimis, contributions, tax due, and a tax-credit field (version 7.2 added the PERA tax credit).
- **Header tables per form:** return period, amended or not, number of sheets, over-remittance.
- **Payee list:** TIN, branch, names, address.
- **Branch code:** 4 characters in the 7.4 tables, 3 in the older PREDATA copy.

## What the issuances prescribe
### RMC 15-2025 (25 Feb 2025)
- Version 7.4 is available on the BIR website. It "comprises the newly-created alphanumeric tax codes and updated rates for transactions under the creditable and final withholding taxes."
- Alphalists for taxable year 2024 (1604-C, 1604-F, 1601-EQ, 1601-FQ) were due 30 days after the RMC's posting. Files sent with version 7.3 that got error replies had to be resubmitted with 7.4.
- Own extract programs must follow the revised file structures and naming conventions in Annexes A and B.

### Annex B: file names
- **Pattern:** `<TIN><BC><RETURN PERIOD><FORM TYPE>.DAT`, with the withholding agent's 9-digit TIN and 4-digit branch code. In the examples below the TIN is a dummy.

| Module | Form types | Return period | Example |
|---|---|---|---|
| MAP | 1600VT, 1600PT | MMYYYY | `12345678900001020261600VT.DAT` |
| QAP | 1601EQ, 1601FQ, 1621 | MMYYYY (the job aid uses the quarter's last month) | `12345678900000920261601EQ.DAT` |
| Annual | 1604C, 1604F, 1604E | MMDDYYYY | `1234567890000123120251604E.DAT` |

- **SAWT:** Annex B gives no file name for it.

### Annex A: the SAWT file
- **Three record types:** a header (H), detail lines (D) and a control record (C).
- **Header, as printed:**
  - ALPHA_TYPE `HSAWT`;
  - FTYPE_CODE `H1700`, `H1701`, `H1701Q`, `H1702`, `H1702Q`, `H2550M`, `H2551Q` or `H2553`;
  - TIN (9) and BRANCH_CODE (4);
  - REGISTERED_NAME (50) and LAST, FIRST and MIDDLE_NAME (30 each);
  - RETRN_PERIOD `MM/YYYY`; RDO_CODE_WA (3).
- **Details, as printed:**
  - ALPHA_TYPE `DSAWT`; FTYPE_CODE `D1700` to `D2553`; SEQUENCE_NUM;
  - the withholding agent's TIN (9), branch (4), and registered name or last, first and middle names;
  - RETRN_PERIOD; NATURE_INCOME (50); ATC_CODE (5);
  - TAX_RATE `9(2).99`; INCOME_PAYMENT `9(11).99` (the tax base); ACTUAL_AMT_WTHLD `9(11).99`.
- **Control, as printed:** ALPHA_TYPE `CSAWT`; FTYPE_CODE `C1700` to `C2553`; SEQUENCE_NUM; TIN; branch; registered name; last name. The scan ends at field 7, so the totals it presumably carries are missing.
- **Lists of values (page 2):**
  - EMPLOYMENT_STATUS: R regular, C casual, CP contractual or project-based, S seasonal, P probationary, AL apprentice or learner.
  - REASON_SEPARATION: NA, T terminated or resigned, TR transferred, R retirement, D death.
  - STATUS_CODE: A citizen, B resident alien, C non-resident alien engaged in business, D non-resident alien not engaged in business, E domestic corporation, F resident foreign corporation, G non-resident foreign corporation.
  - SUBS_FILING: Y or N.
  - These values belong to the 1604-C and the final-tax layouts, which the scan doesn't include.

**Problems in the annex itself** (settle each with a module-generated sample):
1. **2550Q is missing.** FTYPE_CODE lists 2550M, which has been abolished since 2023, but not 2550Q. Both job aids show a SAWT for 2550Q.
2. **Widths don't match formats.**
   - ALPHA_TYPE is 5 wide in the header but 6 in the details.
   - FTYPE_CODE is 6 in the header but 5 in the details, yet `D1701Q` has 6 characters.
   - SEQUENCE_NUM is 2 wide with an 8-digit format.
   - RETRN_PERIOD is 50 wide in the details.
3. **Mislabelled fields.** The detail fields are named EMPLOYER_TIN and so on but described as "Payee's". In a SAWT the detail lines are the withholding agents who withheld from the filer.
4. **No separator, quoting or line ending** is stated.
5. **Branch code length.** It is 4 digits here, while the forms now use 5: the 2307's TIN boxes run 3-3-3-5, and eBIRForms 7.9.6.0 says "Increase in the length of the Branch Code of the TIN from 3 digits to 5 digits, All Forms".

### RMC 7-2021 Annex C: the job aids (version 7.0)
- **Data Entry:**
  - log in; the withholding agent's profile is captured on first run; keep a payee list;
  - MAP, QAP, SAWT and 1604-C, E and F screens;
  - Generate File saves to the install folder; for a QAP the guide says three files are saved per quarter and doesn't say which;
  - the 1604-E and 1604-F files can be generated from the year's QAP data without re-encoding;
  - Print/Inquire.
- **Validation:**
  - choose the form, browse to the DAT file, validate;
  - a text report lists line number, schedule and error description, or "No Errors Encountered"; it is saved under `reports`.
- **After a clean validation the module leaves three copies:**
  - eFPS filers: a copy in the `eAlpha` folder, "which should be zipped prior to submission as an attachment to EFPS Return";
  - eSubmission filers: an encrypted copy in `EncryptedFile`;
  - filers at the RDO: the original file.
- **The guides describe procedures only, not the validation rules.**

### Related issuances (web, 5 Nov 2026)
- **Version 7.0:** RMC 7-2021.
- **Version 7.2:** a BIR tax advisory of February 2024 (PERA tax credit; 2023 income tax rates), with its file structures in RMC 25-2024 (13 Feb 2024; Annex A file structures, Annex B naming).
- **Version 7.3:** RMC 61-2024, "Availability of the Alphalist Data Entry and Validation Module (Version 7.3) and its Updated File Structures and Standard File Naming Convention".
- **Version 7.4:** RMC 15-2025. No later version was found.
- **RMC 55-2026 (26 May 2026):** the alphalist "forms an integral part of the withholding tax return". It must be validated with the module before submission, and may be submitted as an eFPS attachment, through eSubmission or by email.
  - 1600-PT and 1600-VT: due the 10th day of the next month.
  - 1601-EQ, 1601-FQ and 1603Q: the last day of the month after the quarter.
  - 1604-C and 1604-F: 31 January.
  - 1604-E: 1 March.

## Reference data in 7.4
Codes and rates from `DATA/LOVAL/reg_atcs.dbf`, read for this analysis only. The source of record stays the issuances and the 2307's own ATC schedule.
- **Size:** 253 ATCs. By tax type: WE (expanded) 127 rows, WF (final) 37, WG (government money payments) 39, IT 49.
- **Present, at the catalogue's rates:**
  - WI010/WI011 5%/10%; WC010/WC011 10%/15%;
  - rentals WI100/WC100 5%; contractors WI120/WC120 2%;
  - top withholding agents: goods WI158/WC158 1%, services WI160/WC160 2%;
  - government: goods WI640/WC640 1%, services WI157/WC157 2%; WB080/WB082 3%; WV010/WV020 5%.
- **Absent:**
  - WI/WC 840 to 860 (RMO 46-2025, October 2025);
  - WV080, WV090 and WV100 (1600-VT, VAT on digital services);
  - WV110 (reported for RR 9-2025 purchases; not verified);
  - WI/WC 760, correctly, since RMO 18-2025 dropped them.
- **Likely to trip validation:**
  - **Platform codes.** WI820/WC820 and WI830/WC830 are 1% "On one-half (1/2) of the gross remittances" here, while eBIRForms 7.9.5.0 carries them at 1/2% on gross remittances. The tax is the same but the base and rate differ, so the CAS must report them the way the validator expects.
  - **Credit cards.** WI156 is 0.5% but WC156 1%, whereas RR 5-2025 sets 0.5% for both from 14 Mar 2025.
  - **Government VAT.** WV010/WV020 are still described as final ("FWVAT", certificate 2306), though they have been creditable on the 2307 since 2021. The ATC-to-certificate map does say 2307.

## Data handling
- **Leftover payee list.** `DATA/tp_list.dbf` (the payee list) has no live rows but still holds 347 deleted rows, of which 334 carry a 9-digit TIN and 337 a name. These were counted, not opened. A deleted row stays in a .dbf file until the table is packed, so the installer the BIR distributes appears to carry someone's payee list.
- **Smaller leftovers:** one deleted row in `DATA/alphadtl.dbf`, single rows in a few PREDATA tables, and a marker file holding a BIR staff email address.
- **What to do:**
  - keep the installer and anything unpacked from it out of the CAS repository and out of client deliverables;
  - don't open those tables;
  - delete local unpacked copies after use.
- **Telling the BIR:** whether to tell the BIR's data protection officer is the firm's call.

## What the CAS builds from this (CAS-9, with CAS-5b)
| File | When an MSME needs it | Built from |
|---|---|---|
| QAP for 1601-EQ | Whenever it withholds expanded tax: rent, professional fees, contractors, and goods and services if it is a top withholding agent | Bills and payments with EWT, by payee, ATC and month |
| 1604-E | The same clients, once a year (1 March) | The year's four QAPs |
| SAWT for 2550Q and 2551Q | When customers (government, top withholding agents, platforms) withheld VAT, percentage tax or EWT | The 2307s received, by customer and ATC |
| SAWT for 1701Q/1701 and 1702Q/1702 | When customers withheld income tax | The same records, for the EWT credits |
| MAP for 1600-VT | When it buys digital services (ads, software) from non-resident providers | Reverse-charge VAT on those purchases |
| QAP for 1601-FQ, and 1604-F | Final withholding: dividends, payments to non-residents, fringe benefits | Later, as clients need it |
| 1604-C | Clients with payroll | Out of scope until payroll |
| Summary lists of sales and purchases | Every VAT client, quarterly | Not in this module: the BIR's separate SLSP module and its own format, still to be collected |

**Pipeline:**
1. **Generate.** The CAS writes the DAT file, named per Annex B, from posted records only.
2. **Validate.** The client or the firm runs it through the BIR Validation module. The CAS says which module version it targets.
3. **Submit.**
   - eFPS: zip the `eAlpha` copy and attach it to the return.
   - eSubmission: email the encrypted copy.
   - RDO: hand in the original.
4. **Record.** The CAS keeps the file that was validated and submitted, with the validation report.

**Tests:**
- **Golden files.** Type a set of dummy records (dummy TINs and names) into the BIR Data Entry module and generate its DAT files. Keep them as fixtures.
- **Match.** For the same records, the CAS's file must match those fixtures byte for byte, and must validate clean in the Validation module.
- **Every ATC** the catalogue uses gets a validation test, including the codes 7.4 lacks, to find out how the module reacts.

## Documents to collect before coding
1. RMC 61-2024 Annexes A and B: the version 7.3 file structures for MAP, QAP, 1604-C, 1604-E and 1604-F.
2. RMC 25-2024 Annexes A and B.
3. RMC 15-2025 Annex A, complete, from the BIR website: to see whether it has more than the two pages scanned here, and the rest of the SAWT control record.
4. The SLSP data entry module and its file format.
5. Any module newer than 7.4. Check before each filing season.

## Questions for the BIR or RDO
1. **SAWT for 2550Q:** which FTYPE_CODE does 7.4 expect? The annex lists 2550M, not 2550Q.
2. **Branch code:** alphalist files take 4 digits and the forms take 5. How is a 5-digit branch code written in a DAT file?
3. **Codes created after 7.4** (WI/WC 840 to 860, WV080 to WV110): how should a withholding agent report them until the module is updated?
4. **WI/WC 820 and 830, and WI/WC 156:** which base and rate does the validator expect since RR 5-2025?
5. **Record format:** what separator, quoting and line ending do DAT records use, if the 7.3 annexes don't say?

## Sources
- RMC 15-2025 with Annexes A and B; RMC 7-2021 Annex C job aids (DE and Val); the version 7.4 installer. All supplied by the owner on 5 Nov 2026.
- Version 7.4 alert (Akrivia HCM, 17 Mar 2025): https://akriviahcm.com/resources/global-payroll/alerts/alphalist-data-entry-validation-module-update
- RMC 61-2024 (version 7.3) title (NARO, UP Law Center): https://naro.law.upd.edu.ph/documents/6020
- RMC 25-2024 (Forvis Mazars): https://forvismazars.com/ph/en/insights/tax-alerts/bir-rmc-25-2024
- Version 7.2 tax advisory (Grant Thornton copy): https://www.grantthornton.com.ph/contentassets/543c75a937294352a42b94aa0c850c2b/tax-advisory--alphalist-data-entry-and-valida.pdf
- RMC 55-2026 (PwC, 2 Jul 2026): https://www.pwc.com/ph/en/tax/tax-publications/taxwise-or-otherwise/2026/rmc-no-55-2026-every-tax-return-has-a-story.html
- BIR Form 1621 (Bank Bulletin 18-19, digest.ph): https://www.digest.ph/taxation/acceptance-of-bir-forms-nos-0620-and-1621
- Offline eBIRForms Package v7.9.6.2, Release Notes (versions 7.9.5.0 and 7.9.6.0), read on 26 Oct 2026
- BIR Form 2307 January 2018 ENCS reference: `claude/bir-2307-jan-2018-encs-reference.md`
- IP Code Sec. 176 (NDV Law): https://ndvlaw.com/does-copyright-subsist-in-works-of-the-government/
