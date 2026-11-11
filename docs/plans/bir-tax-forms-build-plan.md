# BIR Tax Forms in Sentire Ledger: structural build plan (M5.1)

Written 11 Nov 2026 from (a) the MCRC Portal's BIR Forms module (repo markchrc2025/accounting-firm-portal, HEAD 19c45e6: apps/api/src/bir-forms, packages/bir-pdf, docs/bir-integration-spec.md, docs/system-design.md), (b) the BIR filing stack analysis of 11 Nov (Alphalist 7.4, eBIRForms 7.9.6.2, RMC 15-2025, RMC 7-2021), and (c) what ph_cas already ships (B01 to B39).

The Portal is the proof that the approach works: it files real returns for MCRC's clients today. Sentire Ledger ports the design, not the code, because the Ledger sits on ERPNext (Python, Frappe doctypes, MariaDB) and its books are posted documents with GL entries, not a transaction list.

## 1. What the Portal does (the logic to keep)

### 1.1 One rule that prevents conflict
The books summarize; the form module computes the filing. A books figure is an input the user can see the source of and override; a figure computed by a form (totals, tax due, carry-overs) is never typed and never stored as truth, it is derived on every read. A form marked filed publishes its figures back to the tax view and is sealed.

### 1.2 Three kinds of figure on every form
| Kind | Where it comes from | Stored? |
|---|---|---|
| Books figure | a deterministic sum over posted records in the period, by tax class, ATC or purchase category, with the record count and a filter the user can open | yes, as the draft's data, with `_source` saying it came from the books and when |
| Typed figure | the user: penalties, prior-period credits, choices (8 percent or graduated, over-remittance disposition), schedules that have no books source | yes, as typed strings |
| Derived figure | the compute function: output tax, totals, net payable, bracket tax | never; recomputed from data on each read |

Money is exact. Whole-peso forms (all income-tax returns, 2550Q, 2551Q: "do not enter centavos") round half up once at the line; centavo forms (0619-E, 1601-EQ, 1601-C, 2307, 2316) carry exact decimals and never round. The books total that falls below zero is shown as 0 with a warning, never as a negative.

### 1.3 The per-form engine, three files per form
- `compute<Form>`: pure function, draft data in, every item number out (Comp2550Q has i31a..i61, i15..i26 and the Part V schedule totals that feed Items 16, 17, 39, 52, 53). Schedule totals fall back to the flat typed field when there are no rows.
- `build<Form>`: the eBIRForms export file, the authentic key list of the offline package (namespace `frm2550qv2024:`, global keys for the schedule grids, the "All Rights Reserved BIR 2012.0" tail), with the dateFiled on the Manila calendar and the client's fiscal year deciding calendar or fiscal. A return the export cannot carry faithfully (more rows than the form has, an ATC the form does not list) is refused with a sentence, never silently truncated (ExportRefusal).
- `print rows` for the forms that are printed rather than exported (0619-E, 1601-EQ, 1601-C, 2307): the same key, value list, built from the draft instead of parsed from an export.

### 1.4 PDF overlay, the part the owner asked about
The engine never redraws a form. It writes characters into the boxes of the BIR's own blank PDF:
- Templates: the BIR blanks byte for byte, SHA-256 pinned by a test, never edited. One per form version (`2550Q-2024-04.pdf`, `2551Q-2018-01.pdf`, ...). An old version keeps printing on its old blank.
- Maps: one JSON per template, every eBIRForms key placed once or more. Field kinds: `comb` (one character per box, `cells` are the n+1 x boundaries, `rows` wrap addresses between words, `pad` zero-pads a branch code, `date` prints M/D/YYYY as MMDDYYYY, `strip` removes a pre-printed "20"), `money` (pesos right-aligned in `cells`, centavos left-aligned in `cents` after the printed decimal point; no `cents` and non-zero centavos is an error), `mark` (an X centred in a checkbox when the value equals `when`), `choice` (a dropdown index printed as its label), `text` (free text that shrinks from `size` to `minSize`, then errors), `none` (a key with no place on the paper, with a `reason` and an optional `expect` regex). `blankIf` keeps unused schedule rows clean. `squeeze` prints a too-long name whole on one line down to 5.5 pt instead of per box; digit combs never squeeze. Text prints in capitals unless `case: keep` (email).
- Geometry is read from the template's vector drawing by a tool (`geometry.py`: a comb is a run of tick marks between two cell borders; a checkbox is a stroked 9 to 16 pt square), never by eye, and a second test re-reads the drawing to check every committed cell boundary.
- Proofs: a ghost value in every field (8 in digit boxes, W in letter boxes, X in checkboxes, the item label on free lines), rasterized at 300 dpi and inspected; committed with the map. A long-name proof and a DRAFT proof per form.
- Every key in the export must have a map entry; a value that does not fit, a centavo where the paper has none, an unknown dropdown index, or a character the font cannot print is an error naming the field. Nothing is cut off silently.
- Output is deterministic: fixed metadata, Liberation Sans Bold, same input gives byte-identical bytes. A draft preview is the same render plus a diagonal "DRAFT, NOT FILED" at 15 percent and a footer with the Manila print time passed in by the caller (the engine reads no clock). A filed return's "clear copy" is the same render without the stamp, from the stored export, so the PDF shows exactly what was filed.

### 1.5 Filing lifecycle and the seal
draft -> (needs empty) -> filed. Marking filed requires the BIR confirmation e-mail (parsed: form, TIN, period, reference, received-at become the filed date) or a Super Admin override with a reason; it takes a filed snapshot of the taxpayer block (name parts, TIN, branch, RDO, address, dates, contact) so later exports and prints read the copy, never the client as it is today. A filed return is sealed at the database (trigger), never edited; a change is an amendment (new return, `amends` link). Undo is one transition, Super Admin only, override-only, kept as history. A 1601-EQ is filed with its alphalist rows stored in the snapshot (the .DAT is made from the snapshot later; an incomplete alphalist does not block the filing, the refusals are kept as a warning). Contact number is required before any return is submitted.

### 1.6 Needs: what is missing, as questions
Every draft answers a `needs` list built from the client record, the draft's data, the form's own compute and refusals, never from the books: "What is the client's RDO code (3 digits)?", why it is asked, which field writes the answer, and the answer kind (text, number, date, choice, atc, tin). This is what makes the MCP connector and the UI the same thing: both just ask the questions. Figures the books give are never asked.

### 1.7 Due dates and eligibility, in one place
`due-rules.ts`: 0619-E 10th of next month (months 1 and 2 of a quarter), 1601-C 10th (December on 15 Jan), 1601-EQ last day of the month after the quarter, 2550Q and 2551Q 25 days after the quarter, 1701Q 15 May, 15 Aug, 15 Nov, 1702Q 60 days after the quarter (fiscal), 1701 and 1701A 15 April, 1702-RT 15th of the 4th month after year end (fiscal), 1604-C and 2316 31 Jan, 1604-E 1 March, 2307 20 days after the quarter. Weekend moves to Monday (the Portal has no holiday table; the Ledger has PH Holiday). `eligibility.ts`: which forms a client must file from its kind (individual or not), VAT or percentage, and the registered withholding types on the 2303.

### 1.8 Attachments
QAP .DAT for the 1601-EQ written exactly as the Validation program's val1601e expects (HQAP, D1, C1, D2, C2 lines, CRLF, quoted text, two-decimal amounts, 4-digit branch), never adding a validation key: the owner runs the BIR program before eSubmission. The same for SAWT and the 1604-E annual.

## 2. What Sentire Ledger already has
- `PH Tax Return Figures` doctype (company, form, period, lines table item/label/amount/source/reason, adjustments table, computed_on, filed check, filed_reference, filed_on) and `ph_cas.tax.returns` with compute_2550q, compute_2551q, compute_0619e, compute_1601eq, compute_1600vt, plus `ph_cas.tax.income_tax` (compute_1701q, 1702q, annual with graduated tax, 2307 credits, NOLCO, prior quarters). These are the books feed (layer A below), already with per-line `source` and `reason`.
- Tax rules engine (74 dated rules), ATC on every invoice and purchase, PH 2307 Issued and Received, PH Alphalist File doctype with `ph_cas/dat/{qap,sawt,relief}.py` writers, PH Compliance Calendar (`ph_cas.tax.calendar`) with PH Holiday, Company fields ph_tin, ph_branch_code, ph_rdo, ph_taxpayer_type, ph_taxpayer_class, ph_vat_status, ph_top_withholding_agent, registered name, and the 2307 HTML print format.
- The BIR blank PDFs for every form in scope are in the project files (13 BIR Templates).

What is missing is everything from "figures" to "a return": the typed layer, the per-form compute with every item number, the eBIRForms export file, the overlay print, the needs list, the seal, the confirmation, amendments.

## 3. Target architecture in ph_cas

```
ph_cas/forms/                          the form engine (pure Python, no Frappe calls inside compute/build)
  registry.py                          FORMS: code -> version, period kind, money mode, export or print, due rule, eligibility
  money.py                             Decimal helpers: dec(), total(), whole_peso(), centavos(); never float
  period.py                            period keys "2026-Q1", "2026-03", "2026"; fiscal year shapes; quarter ranges
  needs.py                             Need dataclass + the company-record needs shared by every form
  export/                              eBIRForms export writer: enc(), amt(), rb(), tin_parts(), the file tail, ExportRefusal
  <form>/compute.py                    data in, every item out (ports Comp<Form>)
  <form>/export.py                     the eBIRForms key list (ports build<Form>), for exported forms
  <form>/print_rows.py                 the key list for printed forms (0619-E, 1601-EQ, 2307, 2316)
  <form>/feed.py                       the books feed: lines with source filters (moves out of ph_cas.tax.returns)
ph_cas/birpdf/                         the overlay engine (ports packages/bir-pdf to Python)
  templates/<form>-<yyyy-mm>.pdf       BIR blanks, SHA pinned
  maps/<form>-<yyyy-mm>.json           SAME map format as the Portal; the Portal's 11 maps are ported as they are
  fonts/LiberationSans-Bold.ttf
  parse.py, layout.py, render.py, validate.py, watermark.py
  tools/geometry.py, proof.py          dev tools, the Portal's geometry.py is Python already
ph_cas/ph_cas/doctype/
  ph_tax_return/                       the return (replaces PH Tax Return Figures as the user-facing record)
  ph_tax_return_line/                  kept: the computed items shown as a table
  ph_bir_confirmation/                 the parsed BIR e-mail or the override, with the .eml or PDF attached
```

Why a Python port and not a Node sidecar: the Ledger is one container per site family with no Node runtime at run time; pdf-lib's job (load a PDF, embed a TTF, draw text at x, y) is done in Python by `pypdf` + `reportlab` (draw an overlay page per template page, merge). The layout maths (`layout.ts`, 511 lines, pure) ports line for line. The maps need no change at all, which is the biggest saving: the geometry work for 11 forms is done.

### 3.1 The PH Tax Return doctype (one record per company, form, period)
Fields: company, form (Select from the registry), form_version, period_kind, period_key, period_start, period_end, fiscal (Check), status (Draft, Ready, Filed, Amended, Cancelled; Frappe docstatus 1 = Filed is the seal, docstatus 2 + amended_from = amendment), data (JSON: typed and books figures with `_source`), lines (computed items, refreshed on every save and on open, read-only), needs (JSON, refreshed with lines), warnings (Small Text), export_file (Attach, the eBIRForms file), preview_pdf (Attach, DRAFT-stamped), clear_copy (Attach, made at filing), filed_on, filed_reference, filed_snapshot (JSON: the Company taxpayer block as at filing, plus the alphalist model for a 1601-EQ), confirmation (Link PH BIR Confirmation), alphalist_file (Link PH Alphalist File), amends (Link PH Tax Return), contact_number.

Status flow: Draft -> Ready (needs empty) -> Filed (submit, read-only) -> Change requested -> Change approved (opens an amendment) ; Amended marks a return superseded by its amendment.

Rules enforced in the controller: validate() refuses a negative on a form with no sign boxes, a centavo on a whole-peso form, more schedule rows than the paper has; before_submit() requires needs empty, a confirmation (or a System Manager override with reason) and the contact number, takes the filed snapshot, renders the clear copy from the stored export, writes the Event Log; on_submit() publishes the figures to PH Tax Return Figures (so the home dashboard, the calendar and the reconciliation report keep reading one place); a change after filing only through the approval workflow (decision 2), which opens an amendment; the original stays filed and readable; no deletion of a submitted return (Annex B rule already enforced by ph_cas.controls).

### 3.2 Books feed contract (per form feed.py)
`feed(company, period) -> {figures: {key: value}, lines: [{key, label, amount, records, filter}], warnings: []}`. Filters are list-view routes (`/app/sales-invoice?...`) so every books figure is one click from its records, like the Portal's BookLine filter. The feed only touches the keys it owns; a user's typed keys survive a refresh; a books key the user overrode keeps the override and a warning says so. The feed is re-run on "Refresh from books" and the `_source.asOf` is shown.

### 3.3 Form UI
One Frappe form view with a custom script per form: Part II / Part IV rendered as item rows in the paper's order (label, item number, books or typed or derived badge, amount, source link), schedules as child grids, the needs list as a checklist at the top, buttons Refresh from books, Preview PDF (DRAFT), Export for eBIRForms, Mark as filed (upload confirmation), Download clear copy, Amend. The computed items are shown from `lines` so the list view and reports work without the JSON.

### 3.4 MCP and the Portal connector
The same `needs` and `compute` back `ph_cas.api.forms.*` whitelisted methods, so the Ledger's own MCP (planned in ai-integration-plan) and the Portal can draft a Ledger client's return with the identical question loop.

## 4. Build order and mapping to Sentire Projects

| Step | Issue | What lands | Depends on |
|---|---|---|---|
| F0 | LDG-82 | Common layer: registry, money, period, needs, export writer, PH Tax Return doctype with seal and confirmation, the birpdf engine with maps and templates for all 11 Portal forms, proofs pinned, tests (template SHA, map coverage, geometry re-check, byte-identical render) | nothing |
| F1 | LDG-69 | 2551Q end to end (simplest exported form, 6-row Schedule 1, 8 ATCs): feed from compute_2551q, compute, export, print, file. Proves the whole pipeline | F0 |
| F2 | LDG-68 | 2550Q (the biggest): Part IV flow, Part V schedules 1 to 4 (capital goods over 1M from Asset records, VAT withheld from PH 2307 Received with VAT ATCs, advance payments), fiscal year, April 2024 ENCS | F1 |
| F3 | LDG-70 | 0619-E: printed, centavos, calendar months 1 and 2 of the quarter, feed from PH 2307 Issued / purchase withholding | F1 |
| F4 | LDG-71 | 1601-EQ with QAP: six ATC rows, over-remittance choice, alphalist model in the snapshot, .DAT from the snapshot via ph_cas.dat.qap, 4-digit branch | F3 |
| F5 | LDG-78 | 2307: certificate print on the blank (page 1 only, centavo text fields), issued from PH 2307 Issued, received kept as credits; replaces the HTML print format for the BIR face | F0 |
| F6 | LDG-73 | 1701Q: 8 percent or graduated choice, OSD or itemised, prior quarters, 2307 credits, TRAIN tables by year | F2 |
| F7 | LDG-76 | 1702Q: corporate quarterly, MCIT, fiscal year, 60-day due | F6 |
| F8 | LDG-74, LDG-75 | 1701 and 1701A annual: NOLCO table, the Pg1m to Pg4m attachment keys as `none`, 1701A as the 1701's alternative in eligibility | F6 |
| F9 | LDG-77 | 1702-RT: annual corporate, MCIT vs RCIT, NOLCO, the "/20YY" strip rule | F7 |
| F10 | LDG-72 | 1600-VT: printed (no Portal map yet; make the map with geometry.py from the blank), feed from reverse-charge VAT | F3 |
| F11 | LDG-79 | 1604-E and the annual alphalist: from the four filed 1601-EQ snapshots of the year, .DAT via existing writer | F4 |
| F12 | LDG-81 | SLSP (RELIEF) and e-books .dat attached to the 2550Q return record | F2 |
| parked | LDG-80 | 1604-C and 2316: only when a payroll source exists (the Ledger holds no payroll; 1601-C has no books source in the Portal either) | HRMS or Sentire Payroll |

F0 is about a third of the whole: the overlay engine port, the doctype and the seal. After F1 every further form is compute + export + feed + tests on top of a finished machine, roughly a day each for the quarterly ones and two for the annual income-tax returns.

## 5. Decisions (owner, 11 and 12 Nov 2026)
1. Maps and templates: the owner put every BIR blank in the repo at `ph_cas/tax/BIR Templates` (commits 3ce5421, 852b1bf). All 11 blanks the Portal maps are byte-identical to the Portal's pinned templates (SHA-256 checked), so the Portal's maps port verbatim. New maps are needed for the 1600-VT, 1604-E, 1604-C, 2316 and 2306 (LDG-86, LDG-87, LDG-88, parked).
2. Seal strength: Frappe submit makes a filed return read-only; no database trigger (the Ledger is not an official filing system, so the owner does not want it over-restricted). A change to a filed return is still possible, but only through a manager's approval: the user raises a change request with a reason, a user with the Accounts Manager role approves or rejects it (Frappe Workflow on PH Tax Return: Filed -> Change requested -> Change approved), and an approved request opens an amendment (a new return with `amends` set, the original kept as filed and readable). Nothing is ever edited in place. An amendment filing (the BIR's amended return, with the amended box ticked and the tax paid on the original as a credit) is a normal case of the same path.
3. Confirmation: the BIR confirmation e-mail is required to mark filed, with a System Manager override that is logged with a reason.
4. Typed figures live as JSON `data` on the return.
5. Live preview: the DRAFT preview renders as the user types (debounced), with the Portal's per-user limit of 40 renders a minute kept.
6. Clear copy: the BIR blank with figures only, no Annex B header. The Annex B header stays on every other print and export.
7. 1604-C and 2316 parked until a payroll source exists; the new maps are tracked as their own issues.

## 6. Tests that gate each form (same as the Portal's T1 to T5 and C-series)
- Template SHA pinned; map validates; every export key has a map entry (coverage); geometry re-check against the blank's drawing; proof rendered and committed.
- Compute: one spec per form with the owner's golden figures (LDG-48, LDG-49 give the eBIRForms expected answers).
- Export: byte-identical to a real offline-package export for the sample taxpayer (keys, order, tail).
- Render: deterministic bytes; a draft preview carries the stamp; a filed return prints from the snapshot even after the Company record changes.
- Seal: edit, delete, re-feed on a filed return refused; amendment keeps the original.
