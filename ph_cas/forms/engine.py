"""The dispatcher between a PH Tax Return and its form's engine.

A form's engine is the module ph_cas.forms.f<key> (f2551q, f2550q, f0619e ...)
and offers:

    feed(ctx) -> {"figures": {key: value}, "lines": [BookLine...], "warnings": [str]}
    compute(data, ctx) -> list[Line]           every item in the paper's order
    needs(data, ctx) -> list[Need]             what the draft still lacks, beyond the Company's
    export_rows(data, comp, ctx) -> (rows, file_name)    exported forms
    print_rows(data, comp, ctx) -> rows                  printed forms and certificates

ctx is a Context: the Company as a dict (or the filed snapshot), the Period,
the FormSpec, the return's own flags. Line is a dict: item, label, amount
(Decimal), kind ("books", "typed", "derived"), source (a route or text).
"""

import importlib
from dataclasses import dataclass, field

from ph_cas.forms import needs as needs_mod
from ph_cas.forms.period import Period
from ph_cas.forms.registry import BUILT, FormSpec

TAXPAYER_FIELDS = (
    "name",
    "company_name",
    "tax_id",
    "ph_branch_code",
    "ph_rdo",
    "ph_registered_name",
    "ph_business_style",
    "ph_taxpayer_type",
    "ph_taxpayer_class",
    "ph_vat_status",
    "ph_top_withholding_agent",
    "ph_last_name",
    "ph_first_name",
    "ph_middle_name",
    "ph_birthdate",
    "ph_civil_status",
    "ph_individual_type",
    "ph_citizenship",
    "ph_incorporation_date",
    "ph_registered_address",
    "ph_zip",
    "ph_contact_number",
    "ph_email",
    "ph_line_of_business",
    "ph_psic",
    "ph_pt_atc",
    "ph_fiscal_year_start",
)


@dataclass
class Context:
    spec: FormSpec
    period: Period
    company: dict
    is_amended: bool = False
    contact_number: str = ""
    date_filed: str | None = None  # yyyy/mm/dd, Manila
    final: bool = False  # the export's txtFinalFlag: 1 once filed
    return_name: str = ""
    extra: dict = field(default_factory=dict)


def taxpayer_block(company_doc) -> dict:
    """The Company's taxpayer fields as a plain dict: what a return prints, and what
    the filed snapshot keeps."""
    out = {}
    for f in TAXPAYER_FIELDS:
        v = company_doc.get(f) if hasattr(company_doc, "get") else getattr(company_doc, f, None)
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        out[f] = v
    return out


def module(spec: FormSpec):
    if spec.code not in BUILT:
        return None
    return importlib.import_module(f"ph_cas.forms.f{spec.key.lower()}")


def refresh(data: dict, ctx: Context) -> dict:
    """lines, needs and warnings for a draft; the engine's when the form is built,
    the Company's needs and a note otherwise."""
    needs = [n.as_dict() for n in needs_mod.company_needs(ctx.spec, ctx.company)]
    mod = module(ctx.spec)
    if mod is None:
        needs.append(needs_mod.refusal_need("engine", f"The {ctx.spec.code} engine is not built yet in this version; the return cannot be computed.").as_dict())
        return {"lines": [], "needs": needs, "warnings": []}
    warnings: list[str] = list((data.get("_source") or {}).get("warnings") or [])
    lines = mod.compute(data, ctx)
    needs += [n.as_dict() for n in mod.needs(data, ctx)]
    return {"lines": lines, "needs": needs, "warnings": warnings}
