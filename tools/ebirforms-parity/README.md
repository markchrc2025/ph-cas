# eBIRForms parity harness (LDG-49)

Runs the BIR's own eBIRForms forms and records what they compute, so Ledger can be
held to the same figures. The fixtures it writes live in
`ph_cas/tests/data/ebirforms_parity/`. `ph_cas.tests.test_b59_ebirforms_parity` checks
every Ledger figure against them.

## Where the forms come from

1. Take the eBIRForms package, for example `Offline_eBIRForms_Package_v7.9.6.2.1.zip`
   from the MCRC TAS project files. Extract the installer with `innoextract`.
2. Run `BIRForms.exe` once under wine with a virtual display. It unpacks the forms
   (`forms/*.hta`, `js/`, `jq/`, `css/`, `xml/`) into `%TEMP%\{GUID}\`.
3. Copy that folder to `/tmp/ebir/app`, or point `EBIR_APP` at the copy.
4. Copy each form you need from `.hta` to `.html`. The HTA host (mshta) is a stub
   under wine, so the forms run in the pre-installed Chromium instead.

The BIR's files are never added to this repository; only the figures they produce are.

## What `load.js` makes up for

The forms were written for mshta and JScript. The shim in `load.js` supplies:

- `ActiveXObject`: FileSystemObject reads the package's own `xml/` files, such as the
  ATC lists.
- `alert`, `confirm` and `MsgBox`: their messages are collected and reported.
- Two JScript behaviours the forms depend on:
  - `Date#getYear` gives the full year from 2000 on.
  - `Number#toLocaleString` gives "1,234.00".

## How to run

There are two drivers. Both need Ledger's figures for the scenario first:

```
cp scenarios/s2550q.json /tmp/ebirpar/scen.json
# on the bench (test_site), run ledger_side.py; it writes /tmp/ebirpar/ledger.json
```

**`compare.js`** types the inputs listed in `<scenario>.steps.json` into the form, the
way a person would. It is used for 2550Q, 2551Q, 0619-E, 1601-EQ, 1600-VT and 1702Q:

```
EBIR_APP=/tmp/ebir/app node compare.js /tmp/ebir/app/forms/BIR-Form2550Qv2024.html "frm2550qv2024:" scenarios/s2550q.steps.json /tmp/ebirpar/ledger.json
```

**`replay.js`** works from Ledger's exported file. It is used for 1701Q, 1701A, 1701 and
1702-RT. It does three things:

1. Marks every radio and checkbox Ledger set, and picks every dropdown Ledger picked.
2. Types every amount the form leaves open, in two passes.
3. Compares every amount.

`x<form>.json` adds steps the form needs (`before`, `mid`, `after`). Set `WHOLE=1` for
the 1702-RT, whose figures carry no centavos.

```
EBIR_APP=/tmp/ebir/app WHOLE=1 node replay.js /tmp/ebir/app/forms/BIR-Form1702RTv2018C.html "frm1702RT:" /tmp/ebirpar/ledger.json scenarios/x1702rt.json
```

Both drivers print what matched and what differed. They also write
`<ledger>.ebir.json` (the form's figures) and `<ledger>.saved.json` (the file eBIRForms
would save). To compare the saved file with Ledger's export key by key, run
`filediff.py <ledger.json> <ledger.saved.json> <namespace>`.

When everything matches, write the fixture:

```
python3 fixture.py <name> scenarios/<scenario>.json <ledger>.ebir.json [deviations.json]
```

`deviations.json` records where eBIRForms' own code breaks and Ledger keeps to the
form's intended rule. Today there is one such case: the 1702-RT Schedule 3 recursion
(`scenarios/dev1702rt.json`).

## Two notes on realistic inputs

- File an annual return for a year that has ended (2025 when testing in 2026). Both
  the 1701 and the 1701A clear a year that is still running and fall back to the old
  tax table.
- On the 1702Qv2018C the year is two digits ("26").
