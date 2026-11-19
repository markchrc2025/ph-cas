"""B78: the print pack for the paper check at 100% (LDG-52).

One PDF the owner prints to check, on paper, that the invoice, the credit note, the collection
receipt and the 2307 come out at their true size with every BIR item in place:

- page 1: how to print it (Actual size / 100%, no "fit to page"), a 100 mm scale bar, and the
  checklist;
- then the company's latest invoice, credit note, collection receipt and 2307, each through its
  own print format and page settings.

Every document page is stamped, without moving anything on it, with a light diagonal "SPECIMEN,
PAPER CHECK" and, in its bottom margin, a 100 mm bar. The pages are rendered the way the
on-screen preview is, so no print is counted (ph_cas.invoicing.printing): a specimen is not a
copy of the invoice, and the original stays unprinted. The download is recorded in the audit
trail. Accounting Managers and System Managers only.
"""

from __future__ import annotations

import io

import frappe
from frappe import _
from frappe.utils import escape_html

DOCS = [
    ("Sales Invoice", "PH Sales Invoice", {"is_return": 0, "is_debit_note": 0}, "Sales invoice"),
    ("Sales Invoice", "PH Sales Invoice", {"is_return": 1}, "Credit note"),
    ("Payment Entry", "PH Collection Receipt", {"payment_type": "Receive", "bir_serial": ("is", "set")}, "Collection receipt"),
    ("PH 2307 Issued", None, {}, "BIR Form 2307"),  # on the BIR's own blank (ph_cas.forms.f2307)
]

BAR = '<div style="width:100mm;height:3mm;background:#000"></div>'
MARK = "SPECIMEN, PAPER CHECK"
MM = 72 / 25.4

CHECKS = [
    "The 100 mm bar on this page measures 100 mm with a ruler (if not, the printer scaled the page: print again at Actual size / 100%).",
    "No page is cut at an edge, and each document fits the paper size it was printed on.",
    "Header of the invoice, credit note and collection receipt: registered name, business style, registered address, VAT or NON-VAT REG TIN with the branch code.",
    "Title and serial: SALES INVOICE / CREDIT NOTE / COLLECTION RECEIPT, the 8-digit serial and the date.",
    "Buyer: name, TIN and address.",
    "Lines and totals: quantity, unit price, description; VATable sales, VAT, VAT-exempt and zero-rated sales and the total, each where the preview shows it.",
    "Footer: the ACCN and its date issued, and the software name and version, as on the screen preview.",
    "Credit note: the original invoice's number is printed.",
    "BIR Form 2307: every figure and name sits inside its box on the BIR face (payee and payor TIN, ATC, the three months, totals).",
]


def _latest(company, doctype, filters):
    # a 2307 is printed for the supplier from its record (issued, or still a draft of the quarter);
    # invoices, notes and receipts only once submitted
    for docstatus in ((1, 0) if doctype == "PH 2307 Issued" else (1,)):
        rows = frappe.get_all(doctype, filters={"company": company, "docstatus": docstatus, **filters}, order_by="creation desc", pluck="name", limit=1)
        if rows:
            return rows[0]
    return None


def _page(doctype, name, print_format) -> str:
    frappe.flags.ph_in_print_preview = True  # a specimen is not a print: nothing is counted
    try:
        html = frappe.get_print(doctype, name, print_format)
    finally:
        frappe.flags.ph_in_print_preview = False
    return _self_contained(html)


def _self_contained(html: str) -> str:
    """Inline the site's own stylesheets and drop scripts, so the engine fetches nothing (the page is
    the same; it no longer depends on reaching the site's own address while rendering)."""
    import os
    import re

    def inline(m):
        href = m.group(1).split("?")[0]
        path = os.path.join(frappe.local.sites_path, href.lstrip("/"))
        if href.startswith("/assets/") and href.endswith(".css") and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f"<style>{f.read()}</style>"
        return m.group(0)

    html = re.sub(r'<link[^>]+href=["\']([^"\']+)["\'][^>]*>', inline, html)
    return re.sub(r'<script[^>]*src=["\'][^"\']+["\'][^>]*>\s*</script>', "", html)


def _bir_2307(name) -> bytes:
    """The certificate on the BIR's 2307 blank, as Print on BIR form gives it, marked SPECIMEN.
    The blank is the BIR's own page at its own size, so it needs no scale bar of its own."""
    from ph_cas.forms import f2307
    from ph_cas.forms.engine import taxpayer_block

    cert = frappe.get_doc("PH 2307 Issued", name)
    c = taxpayer_block(frappe.get_cached_doc("Company", cert.company))
    return f2307.certificate_pdf(cert, c, {}, (cert.period_from.month - 1) // 3 + 1, cert.period_from.year)


def _cover(company, found) -> str:
    rows = "".join(f"<tr><td style='padding:2mm 3mm'>{escape_html(label)}</td><td style='padding:2mm 3mm'>{escape_html(name or _('none yet: post one, then download again'))}</td></tr>"
                   for label, name in found)
    checks = "".join(f"<li style='margin:1.5mm 0'>&#9744; {escape_html(c)}</li>" for c in CHECKS)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="pdf-page-size" content="A4">
<style>body{{font:10pt sans-serif;margin:15mm}} h1{{font-size:15pt}} table{{border-collapse:collapse}} td{{border:1px solid #999}}</style></head>
<body><h1>{escape_html(_("Paper check at 100%"))}: {escape_html(company)}</h1>
<p>{escape_html(_("Print this whole file at Actual size (100%). Turn off \"Fit to page\" or \"Shrink to fit\". Then measure the bar:"))}</p>
{BAR}<p style="font-size:8pt">{escape_html(_("The bar above is exactly 100 mm wide."))}</p>
<table>{rows}</table>
<h2 style="font-size:12pt;margin-top:8mm">{escape_html(_("Check on paper"))}</h2><ol style="list-style:none;padding:0">{checks}</ol>
<p style="font-size:8pt;color:#555">{escape_html(_("The pages are specimens: they carry the SPECIMEN mark and are not counted as prints, so an invoice's original stays unprinted."))}</p>
</body></html>"""


def _stamp(page) -> None:
    """Over a document page, without moving anything on it: a light diagonal SPECIMEN mark and,
    in the bottom margin, a 100 mm bar drawn at true size (so each sheet shows if the printer
    scaled it). The cover's bar, drawn by the page engine itself, shows if the engine did."""
    import math

    from pypdf import PdfReader
    from reportlab.pdfgen import canvas

    w, h = float(page.mediabox.width), float(page.mediabox.height)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.saveState()
    c.setFillAlpha(0.12)
    c.setFont("Helvetica-Bold", 54)
    c.translate(w / 2, h / 2)
    c.rotate(math.degrees(math.atan2(h, w)))
    c.drawCentredString(0, 0, MARK)
    c.restoreState()
    c.setFont("Helvetica", 6.5)
    c.drawString(8 * MM, 7.5 * MM, f"{MARK}: NOT AN ISSUED DOCUMENT. This bar is 100 mm:")
    c.rect(8 * MM, 4 * MM, 100 * MM, 1.5 * MM, stroke=0, fill=1)
    c.showPage()
    c.save()
    page.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])


def build(company: str) -> tuple[bytes, list]:
    from frappe.utils.pdf import get_pdf
    from pypdf import PdfWriter

    found = []
    for doctype, fmt, filters, label in DOCS:
        found.append((label, _latest(company, doctype, filters), doctype, fmt))
    # a stylesheet or font the engine cannot fetch must not stop the pack (the page still renders)
    opts = {"load-error-handling": "ignore", "load-media-error-handling": "ignore"}
    writer = PdfWriter()
    get_pdf(_cover(company, [(l, n) for l, n, *_x in found]), options=dict(opts), output=writer)
    from pypdf import PdfReader

    for label, name, doctype, fmt in found:
        if not name:
            continue
        pdf = get_pdf(_page(doctype, name, fmt), options=dict(opts)) if fmt else _bir_2307(name)
        for page in PdfReader(io.BytesIO(pdf)).pages:
            _stamp(page)
            writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue(), [(label, name) for label, name, *_x in found]


@frappe.whitelist()
def download(company: str):
    frappe.only_for(("System Manager", "Accounting Manager"))
    frappe.has_permission("Company", "read", company, throw=True)
    data, found = build(company)
    from ph_cas.audit.events import record

    record("export", "Company", company, 0, {"paper_check_pack": {label: name for label, name in found}})
    frappe.local.response.filename = f"paper-check-{frappe.scrub(company)}.pdf"
    frappe.local.response.filecontent = data
    frappe.local.response.type = "download"


def bar_widths_mm(pdf: bytes, page: int = 0) -> list[float]:
    """The widths, in mm, of the rectangles on a page of the pack shaped like the bar (100 by 3 mm,
    so about 33 times as wide as high, whatever the scale),
    read from the PDF's drawing commands and the page's transformation matrices, so the full pass
    can measure the bar without a printer or a rasteriser."""
    from pypdf import PdfReader

    out = []
    reader = PdfReader(io.BytesIO(pdf))
    pg = reader.pages[page]
    widths = []

    def visit(op, args, cm, tm):
        if op == b"re" and len(args) == 4:
            w, h = abs(float(args[2]) * cm[0]), abs(float(args[3]) * cm[3])
            if h and 30 <= w / h <= 37:
                widths.append(w)

    pg.extract_text(visitor_operand_before=visit)
    for w in widths:
        out.append(round(w * 25.4 / 72, 1))
    return out
