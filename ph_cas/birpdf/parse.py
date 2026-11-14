"""parse_ebir_export: read an eBIRForms export file back into (key, value) rows.

The file is "<?xml version='1.0'?>", then one "<div>KEY=VALUEKEY=</div>" per
field (the 2551Q joins them with tabs, the 2550Q with newlines), then the tail
"All Rights Reserved BIR 2012.0". The builders URL-encode some values (the
export writer's enc()) and emit the rest raw; this parser decodes exactly the
keys the builder of that form encodes, so a literal "%" in a raw value survives.
"""

import re
from urllib.parse import unquote

from ph_cas.birpdf.errors import BirPdfError


def _ns(ns: str, keys: list[str]) -> set[str]:
    return {f"{ns}:{k}" for k in keys}


# The keys each builder passes through enc(), by eBIRForms namespace. A key
# listed here is decoded; every other key is taken verbatim.
ENCODED_KEYS: dict[str, set[str]] = {
    "frm2551Qv2018": {
        "frm2551Qv2018:registeredName",
        "frm2551Qv2018:registeredAddress",
        "frm2551Qv2018:txtTaxReliefSpecify",
        "frm2551Qv2018:txt17Specify",
        "txtTaxAgentNo",
        "txtDateIssue",
        "txtDateExpiry",
        "frm2551Qv2018:txtParticular28",
        *[f"frm2551Qv2018:txt{w}{n}" for n in (25, 26, 27, 28) for w in ("Agency", "Number", "Date")],
    },
    "frm2550qv2024": {
        "frm2550qv2024:taxpayerName",
        "frm2550qv2024:taxpayerAddress",
        "frm2550qv2024:specifyInternationalTreaty",
        "frm2550qv2024:addSpecifyNo19",
        "frm2550qv2024:addSpecifyNo42",
        "frm2550qv2024:addSpecifyNo47",
        "frm2550qv2024:addSpecifyNo56",
        "txtDescription10",
        "txtDescription11",
        "txtNameWithHoldingAgent30",
        "txtNameWithHoldingAgent31",
        "txtNameOfMiller40",
        "txtNameOfMiller41",
        "txtNameOfTaxpayer40",
        "txtNameOfTaxpayer41",
        # Encoded when the row has an OR number; "0.00" (no "%") otherwise.
        "txtOfficialReceiptNumber40",
        "txtOfficialReceiptNumber41",
    },
    "frm1701q": _ns(
        "frm1701q",
        [
            "txtTaxpayerName",
            "txtAddress",
            "txtForeignTaxNumber",
            "txtSpouseName",
            "txtSpouseCitizenship",
            "txtSpouseForeignTaxNum",
            "txtLOB",
            "txtParticular35",
            "txt43Desc",
            "txt48Desc",
            "txt61Desc",
            *[f"txt{w}{n}" for n in (32, 33, 35) for w in ("Agency", "Number", "Date")],
            "txtNumber34",
            "txtDate34",
        ],
    ),
    "frm1702q": _ns("frm1702q", ["txtDescription", "txtTaxpayerName", "txtTaxPayerAdd"]),
    "frm1701A": _ns(
        "frm1701A",
        [
            "txtTaxpayerName",
            "txtAddress",
            "txtForeignTaxNumber",
            "txtSpouseName",
            "txtSpouseTelNum",
            "txtSpouseCitizenship",
            "txtSpouseFTN",
            "txtLineBus",
            "txtParticular35",
            "txt41Desc",
            "txt42Desc",
            "txt50Desc",
            "txt51Desc",
            "txt63Desc",
            *[f"txt{w}{n}" for n in (32, 33, 35) for w in ("Agency", "Number", "Date")],
            "txtNumber34",
            "txtDate34",
        ],
    ),
    "frm1701": _ns(
        "frm1701",
        [
            "txtPg1I8TaxpayerName",
            "txtPg1I9Address",
            "txtPg1I14ForeignTaxNumber",
            "txtPg2I5SpouseName",
            "txtPg2I6TelNum",
            "txtPg2I7Citizenship",
            "txtPg2I9ForeignTaxNumber",
            "txtLineBus",
            *[f"txtPg4IPart9_{i}Particulars" for i in (2, 3, 4, 6, 7, 8, 9)],
        ],
    ),
    "frm1702RT": _ns("frm1702RT", ["txtPg1Pt1I8Name1", "txtPg1Pt1I9Address1"]),
}

_DIV = re.compile(r"<div>([\s\S]*?)</div>")


def parse_ebir_export(text: str) -> list[tuple[str, str]]:
    """Parse an eBIRForms export into (key, value) rows, in file order."""
    raw: list[tuple[str, str]] = []
    for m in _DIV.finditer(text):
        body = m.group(1)
        eq = body.find("=")
        key = body[:eq] if eq > 0 else ""
        close = f"{key}="
        if not key or len(body) < 2 * len(close) or not body.endswith(close):
            raise BirPdfError(f"eBIRForms export: malformed field <div>{body[:60]}</div>")
        raw.append((key, body[len(close) : len(body) - len(close)]))
    if not raw:
        raise BirPdfError("eBIRForms export: no <div>KEY=VALUEKEY=</div> fields found")

    ns = next((k.split(":")[0] for k, _ in raw if ":" in k), None)
    encoded = ENCODED_KEYS.get(ns) if ns is not None else None
    if encoded is None:
        raise BirPdfError(
            f'eBIRForms export: unknown form namespace "{ns if ns is not None else "(none)"}"; its encoded keys are not known'
        )
    out: list[tuple[str, str]] = []
    for k, v in raw:
        if k not in encoded:
            out.append((k, v))
            continue
        # unquote never raises; a stray "%" is kept as the TS decoder would refuse it
        if re.search(r"%(?![0-9A-Fa-f]{2})", v):
            raise BirPdfError(f'eBIRForms export: {k} is not valid URL-encoding: "{v[:40]}"', k)
        out.append((k, unquote(v)))
    return out
