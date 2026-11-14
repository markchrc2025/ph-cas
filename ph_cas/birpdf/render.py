"""render_return: write a return onto the BIR's own blank form; with the DRAFT
watermark, a draft's preview.

Loads the template (never changed), lays out every mapped key, draws each
piece of text in Liberation Sans Bold, black, on an overlay page made with
reportlab, and merges the overlay onto the template page with pypdf. Pure: no
network, no clock, no random ids; the same rows always give the same bytes.
"""

import io
import json
import os
import re
from datetime import datetime
from functools import lru_cache

from fontTools.ttLib import TTFont as FTFont
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from ph_cas.birpdf.errors import BirPdfError
from ph_cas.birpdf.layout import DrawOp, Metrics, layout_ghost, layout_return
from ph_cas.birpdf.validate import validate_map
from ph_cas.birpdf.watermark import stamp_draft

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(ROOT, "fonts", "LiberationSans-Bold.ttf")
FONT_NAME = "LiberationSans-Bold"
# The blanks live where the owner committed them (ph_cas/tax/BIR Templates), under
# their BIR file names; a map names the blank by form and ENCS version.
TEMPLATE_DIR = os.path.join(ROOT, "..", "tax", "BIR Templates")
TEMPLATES: dict[str, str] = {
    "0619E-2018-01.pdf": "0619-E Jan 2018 rev final.pdf",
    "1600VT-2018-01.pdf": "1600-VT January 2018 ENCS final.pdf",
    "1601C-2018-01.pdf": "1601C final Jan 2018 with DPA.pdf",
    "1601EQ-2019-01.pdf": "1601-EQ January 2019 ENCS final.pdf",
    "1604C-2018-01.pdf": "1604-C Jan 2018 Final.pdf",
    "1604E-2018-01.pdf": "1604E Jan 2018 ENCS Final2.pdf",
    "1701-2018-01.pdf": "1701 Jan 2018 final with rates.pdf",
    "1701A-2018-01.pdf": "1701A Jan 2018 v5 with rates.pdf",
    "1701Q-2018-01.pdf": "1701Q Jan 2018 final rev2_copy.pdf",
    "1702Q-2018-01.pdf": "1702Q 2018ENCS final2.pdf",
    "1702RT-2018-01.pdf": "1702-RT Jan 2018 ENCS Final v3.pdf",
    "2306-2018-01.pdf": "2306 Jan 2018 ENCS v4.pdf",
    "2307-2018-01.pdf": "2307 Jan 2018 ENCS v3.pdf",
    "2316-2021-09.pdf": "2316 Sep 2021 ENCS_Final_corrected.pdf",
    "2550Q-2024-04.pdf": "2550Q  April 2024 ENCS_Final.pdf",
    "2551Q-2018-01.pdf": "2551Q Jan 2018 ENCS final rev 3_copy.pdf",
}
CREATOR = "Sentire Ledger"
PRODUCER = "Sentire Ledger birpdf"


def template_path(template: str) -> str:
    """The blank on disk for a map's `template` name."""
    try:
        return os.path.normpath(os.path.join(TEMPLATE_DIR, TEMPLATES[template]))
    except KeyError:
        raise BirPdfError(f"no blank for template {template}") from None


def load_map(form: str, version: str) -> dict:
    """Read and validate the field map for a form version."""
    if not re.fullmatch(r"[0-9A-Z]+", form or "") or not re.fullmatch(r"\d{4}-\d{2}", version or ""):
        raise BirPdfError(f"unknown form version {form} {version}")
    path = os.path.join(ROOT, "maps", f"{form}-{version}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        raise BirPdfError(f"no field map for BIR Form {form} version {version}") from None
    return validate_map(json.loads(text))


class _FontMetrics:
    def __init__(self):
        if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_FILE))
        ft = FTFont(FONT_FILE)
        self._cmap = ft.getBestCmap()
        self._cap = ft["OS/2"].sCapHeight / ft["head"].unitsPerEm

    def width(self, text: str, size: float) -> float:
        return pdfmetrics.stringWidth(text, FONT_NAME, size)

    def cap_height(self, size: float) -> float:
        return self._cap * size

    def has(self, ch: str) -> bool:
        return ord(ch) in self._cmap


@lru_cache(maxsize=1)
def metrics() -> _FontMetrics:
    return _FontMetrics()


def _draw(form: str, version: str, plan, watermark: str | None = None, printed_at: datetime | None = None) -> bytes:
    m = load_map(form, version)
    reader = PdfReader(template_path(m["template"]))
    pages = reader.pages
    sizes = [(float(p.mediabox.width), float(p.mediabox.height)) for p in pages]
    if len(pages) != len(m["pages"]) or any(
        abs(w - mp["width"]) > 0.5 or abs(h - mp["height"]) > 0.5 for (w, h), mp in zip(sizes, m["pages"])
    ):
        raise BirPdfError(f"map {form}-{version} does not match its template's pages ({m['template']})")

    met = metrics()
    ops: list[DrawOp] = plan(m, met)
    if watermark == "DRAFT" and not isinstance(printed_at, datetime):
        raise BirPdfError("birpdf: a DRAFT preview needs printed_at, the time it is printed")
    if watermark not in (None, "DRAFT"):
        raise BirPdfError(f"birpdf: unknown watermark {watermark}")

    print_pages = m.get("printPages") or list(range(1, len(pages) + 1))
    by_page: dict[int, list[DrawOp]] = {}
    for op in ops:
        by_page.setdefault(op.page, []).append(op)

    writer = PdfWriter()
    for n in print_pages:
        page = pages[n - 1]
        w, h = sizes[n - 1]
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h), invariant=1, pageCompression=0)
        c.setFillColorRGB(0, 0, 0)
        for op in by_page.get(n, []):
            c.setFont(FONT_NAME, op.size)
            c.drawString(op.x, op.y, op.text)
        if watermark == "DRAFT":
            stamp_draft(c, w, h, FONT_NAME, met, printed_at)
        c.showPage()
        c.save()
        overlay = PdfReader(io.BytesIO(buf.getvalue())).pages[0]
        writer.add_page(page).merge_page(overlay)

    writer.add_metadata(
        {
            "/Title": m["title"],
            "/Subject": m.get("subject") or f"BIR Form {form} ({version}), printed from its eBIRForms export",
            "/Creator": CREATOR,
            "/Producer": PRODUCER,
        }
    )
    info = writer._info
    for k in ("/CreationDate", "/ModDate"):
        if k in info:
            del info[NameObject(k)]
    # a fixed document id: the same return always gives the same bytes
    writer._ID = None
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def render_return(form: str, version: str, rows: list[tuple[str, str]], watermark: str | None = None, printed_at=None) -> bytes:
    """Render a return: the blank for `form` `version` with every mapped key of `rows` written in.
    watermark "DRAFT" stamps every page and adds the preview footer (printed_at required)."""
    return _draw(form, version, lambda m, met: layout_return(m, rows, met), watermark, printed_at)


def render_proof(form: str, version: str) -> bytes:
    """Render the proof: a ghost value in every mapped field (see layout_ghost)."""
    return _draw(form, version, layout_ghost)
