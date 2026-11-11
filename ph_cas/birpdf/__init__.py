"""birpdf: print a BIR return onto the BIR's own blank form.

    rows = parse_ebir_export(export_text)           # [(key, value), ...] in file order
    pdf = render_return("2551Q", "2018-01", rows)    # bytes

The engine never redraws a form. It writes characters into the boxes of the
official blank PDF (ph_cas/tax/BIR Templates, byte for byte as the owner
committed them) in Liberation Sans Bold, black. Deterministic: no network, no
clock, no random ids; the same rows always give the same bytes.

The field maps in maps/ hold resolved box geometry (PDF points, origin bottom
left) read from the blank's own vector drawing. Ported from the MCRC Portal's
@portal/bir-pdf (same maps, same blanks, same rules).
"""

from ph_cas.birpdf.errors import BirPdfError
from ph_cas.birpdf.layout import SQUEEZE_MIN, layout_ghost, layout_return
from ph_cas.birpdf.parse import ENCODED_KEYS, parse_ebir_export
from ph_cas.birpdf.render import TEMPLATES, load_map, render_proof, render_return, template_path
from ph_cas.birpdf.validate import validate_map
from ph_cas.birpdf.watermark import DRAFT_STAMP, manila_stamp, preview_footer

__all__ = [
    "BirPdfError",
    "DRAFT_STAMP",
    "ENCODED_KEYS",
    "SQUEEZE_MIN",
    "TEMPLATES",
    "layout_ghost",
    "layout_return",
    "load_map",
    "manila_stamp",
    "parse_ebir_export",
    "preview_footer",
    "render_proof",
    "render_return",
    "template_path",
    "validate_map",
]
