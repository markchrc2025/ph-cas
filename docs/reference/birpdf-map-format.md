# birpdf: the overlay engine and its map format

`ph_cas/birpdf` prints a BIR return onto the BIR's own blank form. It never redraws a form: it writes characters into the boxes of the official blank PDF (kept byte for byte under `ph_cas/tax/BIR Templates`, SHA-256 pinned by `test_f0_birpdf.py`) in Liberation Sans Bold, black. Deterministic: no network, no clock, no random ids; the same rows always give the same bytes. Ported from the MCRC Portal's `@portal/bir-pdf`, whose maps apply as they are because the blanks are identical.

```python
from ph_cas.birpdf import parse_ebir_export, render_return
rows = parse_ebir_export(export_text)                    # [(key, value), ...] in file order
pdf = render_return("2551Q", "2018-01", rows)            # bytes, the clear copy
pdf = render_return("2551Q", "2018-01", rows, "DRAFT", printed_at)   # the preview, stamped
```

## Maps

One JSON per form version in `ph_cas/birpdf/maps/<form>-<version>.json`, resolved numbers only (PDF points, origin bottom left; `y` is the text baseline; `cells` are the n+1 x boundaries of n boxes). Every key an export or print carries must have an entry; a key with none is an error naming it.

| kind | prints |
|---|---|
| `comb` | one character per box; `rows` fill in order (`wrap: words` breaks between words); `align` left or right; `pad` left-pads to every box; `date` prints M/D/YYYY as MMDDYYYY; `strip` removes a pre-printed prefix such as the "20" of "/20YY"; `squeeze` prints a too-long name whole on one line down to 5.5 pt (names, addresses, email only; digit combs never squeeze); `ghost` 8 or W for proofs |
| `money` | pesos right-aligned in `cells`, centavos left-aligned in `cents` after the printed point; no `cents` and non-zero centavos is an error |
| `mark` | an X centred in `box` [x0, y0, x1, y1] when the value equals `when` (default "true") |
| `choice` | a dropdown index printed as its label, one character per box |
| `text` | free text on a line or in a cell; shrinks from `size` to `minSize`, then errors; `amount: true` whole pesos, `amount: "centavos"` pesos and centavos with separators |
| `none` | a key with no place on the paper, with its `reason`; optional `expect` regex |

`blankIf` (a list of key and equals) keeps unused schedule rows clean. `printPages` lists the pages printed (the 2307 prints page 1 only). Text prints in capitals unless `case: keep`.

## Making a map for a new blank (LDG-86 to LDG-88)

1. Add the blank's file name to `TEMPLATES` in `ph_cas/birpdf/render.py` and its SHA-256 to `BLANKS` in the test.
2. Read the geometry from the blank, never by eye: `python3 ph_cas/birpdf/tools/geometry.py "ph_cas/tax/BIR Templates/<blank>.pdf"` (needs pdfplumber; `--lines`, `--cells <page> <y>`, `--json`). A comb is a run of tick marks between two cell borders; a checkbox a stroked 9 to 16 pt square.
3. Assign every comb and checkbox to its key by the item number printed beside it, reading the form's builder for the keys, order and value formats.
4. Print the proof and look at it: `python -m ph_cas.birpdf.tools.proof <form> <out_dir>`, then `pdftoppm -r 300 -png`. Every character inside its box, centred, covering no printed text. Repeat until clean.
