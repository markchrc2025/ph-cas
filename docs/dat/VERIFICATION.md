# DAT layout verification

Status of each alphalist layout the CAS writes. "verified" means byte-for-byte against a golden file from the BIR's own Data Entry module that passes its Validation module, and a file from the real code path validated as well.

| File | Builder | Status | Notes |
|---|---|---|---|
| SAWT (2550Q, 2551Q, 1701Q, 1702Q, 1701, 1702) | ph_cas.dat.sawt | verified (16 Nov 2026, B62) | Golden file from the Alphalist Data Entry module 7.4 (2550Q) in ph_cas/tests/golden/alphalist/; test_b62_alphalist_golden matches it byte for byte. Ledger's own 2550Q and 1702Q SAWTs pass the 7.4 validator. The 1702-RT files under 1702, the only annual corporate SAWT the module lists. No file when there is no 2307 (the validator rejects a file with no detail). |
| QAP 1601-EQ | ph_cas.dat.qap.build_1601eq | verified (16 Nov 2026, B62) | One file per month with payees, as the module writes it; no file for an empty month. Schedule 2 only when there are exempt payees (IC010 or II012). Ledger's own files pass the validator. |
| 1604-E | ph_cas.dat.qap.build_1604e | verified (16 Nov 2026, B62) | The year by payee and ATC, as the module's "Generate 1604E File" writes it. Ledger's own file passes. |
| MAP 1600-VT | ph_cas.dat.qap.build_1600vt | verified (16 Nov 2026, B62) | Rows sorted by name; non-resident providers written as 000000000. WV080 to WV100 fail the unpatched 7.4 ("ATC is invalid"): clients need the BIR's ATC patch for 7.4, which was not run in this check. |
| RELIEF S / P / I | ph_cas.dat.relief | verified (14 Nov 2026, B47) | Golden files from the BIR RELIEF 2.3 Data Entry module in ph_cas/tests/golden/relief/, all passing the RELIEF 2.3 Validation module; test_b47_relief_golden matches them byte for byte. Also validated: a file built from the demo company through the real code path (addresses over 30 characters and names with periods pass). The validator rejects a file with no owner address and a row with neither address line, so the writer refuses both with a message. An individual owner's header is verified too (registered name blank, the person's names quoted). One file per month, three per quarter (owner answer 11), as RELIEF captures one taxable month per file. |

Rules every alphalist file follows (from the 7.4 run):
- Branch code: 4 digits. The validator rejects 5 ("Invalid Length in Branch of Withholding Agent").
- Names: the validator rejects ' & , and Ñ ("Invalid character on field Registered Name"); the writer turns & into AND, Ñ into N, drops apostrophes and turns commas into spaces (ph_cas.dat.writer.clean_name).
- A file needs at least one detail row ("No Detail Record found in file!"), so none is written for an empty period.

Procedure to verify a layout: type the dummy scenario into the BIR Data Entry module, generate the file, run the Validation module, commit the file and report under tests/golden/, and point the layout's test at it.
