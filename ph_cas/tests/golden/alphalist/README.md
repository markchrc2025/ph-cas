# Alphalist golden files

Generated on 16 Nov 2026 by the BIR's Alphalist Data Entry module, version 7.4
(`Alphalist Data Entry and Validation ver. 7.4.exe`, SHA-256 6fb71a5a...00ef9,
from the package the owner supplied),
installed and run under Wine, from invented data only:

- Withholding agent: TIN 474-079-835, branch 0000, SAMPLE TAXPAYER CORP, private,
  non-individual, RDO 047.
- Payees: BAYANI RETAIL STORES INC (123-456-789), the individual DELA CRUZ, JUAN
  SANTOS (234-567-890), MABUHAY MULTIPURPOSE COOPERATIVE (345-678-901), and the
  non-resident GLOBAL ADS PTE LTD (no TIN, written 000-000-000).

| File | What was typed |
|---|---|
| `47407983500000720261601EQ.DAT` | 1601-EQ, July 2026: Bayani WC158 50,000.00 |
| `47407983500000920261601EQ.DAT` | 1601-EQ, September 2026: Bayani WC120 20,000.50 and WC158 100,000.00, Dela Cruz WI010 50,000.00; Schedule 2: Mabuhay IC010 30,000.00 |
| `4740798350000123120261604E.DAT` | 1604-E for 2026, made by the module's "Generate 1604E File" from the QAP data above |
| `47407983500000920262550Q.DAT` | SAWT for the 2550Q, September 2026: Bayani WV010 100,000.00, Dela Cruz WV020 40,000.00 |
| `47407983500001020261600VT.DAT` | MAP for the 1600-VT, October 2026: Global Ads WV070 10,000.00, Bayani WV050 5,000.00 |

All five pass the Alphalist Validation module 7.4 ("No Errors Encountered").

What the run showed:
- The QAP is monthly. The Data Entry module records each row under a month and
  "Generate File" writes one file per month of the quarter. The August file it wrote
  had a header and no rows, and the validator rejects it ("No Detail Record found in
  file!"), so the CAS writes no file for a month without payees.
- The branch code is 4 digits. The same September QAP with a 5-digit branch code
  (00000) fails: "Invalid Length in Branch of Withholding Agent", "Specified Branch
  not the same!" and "Invalid length of Payees Branch Code" on every row.
- The validator accepts "" for a blank name and an unquoted MAP name too; the module
  itself writes a blank name as an empty field and quotes names that have a value,
  and the CAS does the same.
- Schedule 2 takes an income tax ATC (the module lists the IT codes); EI900 and
  IC010 both pass.
- The BIR's ATC patch for 7.4 (`ATC-Patch.zip` on the Downloadables page) was not run
  here, so the codes it adds are not covered by these files.
