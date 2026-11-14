# DAT layout verification

Status of each alphalist layout the CAS writes. "verified" means byte-for-byte against a golden file from the BIR Data Entry module that passed the Validation module (gate G5); "sample" means built from docs/reference/bir-dat-sample-layouts.md only.

| File | Builder | Status | Notes |
|---|---|---|---|
| SAWT (2550Q, 2551Q, 1701Q, 1702Q, 1701, 1702) | ph_cas.dat.sawt | sample | Form code for the 2550Q SAWT is 2550Q by default (RDO question 8a). Rate is tax over income, 2 decimals. |
| QAP 1601-EQ | ph_cas.dat.qap.build_1601eq | layout verified against the validator rules; golden file pending | Schedules 1 and 2 in one file; Schedule 2 ATCs DI900 (individual) and EI900 (non-individual) are an assumption (RDO 8c). |
| 1604-E | ph_cas.dat.qap.build_1604e | sample | H, D3, C3 (total withheld), D4, C4 (total income). |
| MAP 1600-VT | ph_cas.dat.qap.build_1600vt | sample | Names unquoted per the sample; non-resident providers without a TIN are written as 000000000. |
| RELIEF S / P / I | ph_cas.dat.relief | verified (14 Nov 2026, B47) | Golden files from the BIR RELIEF 2.3 Data Entry module in ph_cas/tests/golden/relief/, all passing the RELIEF 2.3 Validation module; test_b47_relief_golden matches them byte for byte. Also validated: a file built from the demo company through the real code path (addresses over 30 characters and names with periods pass). The validator rejects a file with no owner address and a row with neither address line, so the writer refuses both with a message. An individual owner's header is verified too (registered name blank, the person's names quoted). Open: RELIEF captures and validates one taxable month per file and its README speaks of a monthly summary submitted quarterly; RR 1-2012 says only quarterly. The writer makes one file per quarter named for its last month; three monthly files is the alternative (a question for the RDO). |

Procedure to verify a layout: type the dummy scenario into the BIR Data Entry module, generate the file, run the Validation module, commit the file and report under tests/golden/, and point the layout's test at it.
