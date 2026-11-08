# DAT layout verification

Status of each alphalist layout the CAS writes. "verified" means byte-for-byte against a golden file from the BIR Data Entry module that passed the Validation module (gate G5); "sample" means built from docs/reference/bir-dat-sample-layouts.md only.

| File | Builder | Status | Notes |
|---|---|---|---|
| SAWT (2550Q, 2551Q, 1701Q, 1702Q, 1701, 1702) | ph_cas.dat.sawt | sample | Form code for the 2550Q SAWT is 2550Q by default (RDO question 8a). Rate is tax over income, 2 decimals. |
| QAP 1601-EQ | ph_cas.dat.qap.build_1601eq | layout verified against the validator rules; golden file pending | Schedules 1 and 2 in one file; Schedule 2 ATCs DI900 (individual) and EI900 (non-individual) are an assumption (RDO 8c). |
| 1604-E | ph_cas.dat.qap.build_1604e | sample | H, D3, C3 (total withheld), D4, C4 (total income). |
| MAP 1600-VT | ph_cas.dat.qap.build_1600vt | sample | Names unquoted per the sample; non-resident providers without a TIN are written as 000000000. |
| RELIEF S / P / I | ph_cas.dat.relief | pending B29 | The BIR's own format (gate G7) overrides the sample. |

Procedure to verify a layout: type the dummy scenario into the BIR Data Entry module, generate the file, run the Validation module, commit the file and report under tests/golden/, and point the layout's test at it.
