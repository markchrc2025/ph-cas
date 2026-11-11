"""Needs: what is missing for a return, as plain questions.

Every return answers a `needs` list. Each need is a question the user (or the
MCP connector) can ask as it is, with why it is asked, which field writes the
answer, and the kind of answer. Needs are built from what the Ledger already
knows (the Company record, the draft's data, the form's own compute and
refusals), never from a guess, and never from the books: a figure the posted
records give is not asked for.
"""

import re
from dataclasses import asdict, dataclass, field

from ph_cas.forms.registry import FormSpec

INDIVIDUAL_RETURNS = {"1701", "1701A", "1701Q"}
CONTACT_FORMS = {"0619-E", "1601-EQ", "1601-C", "1600-VT", "2551Q", "2550Q", "1701Q", "1701", "1701A", "1702Q", "1702-RT"}


@dataclass
class Need:
    key: str
    question: str
    why: str
    set_with: dict | None  # {"doctype", "name", "field"} or None when no field holds the answer
    kind: str = "text"  # text, number, date, choice, atc, tin
    options: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _blank(v) -> bool:
    return (v or "").strip() == "" if isinstance(v, str) or v is None else not v


def _company_field(company: str, fieldname: str) -> dict:
    return {"doctype": "Company", "name": company, "field": fieldname}


def company_needs(spec: FormSpec, c: dict) -> list[Need]:
    """The Company record, as far as the form prints it. `c` is the Company as a dict."""
    out: list[Need] = []
    company = c.get("name") or c.get("company_name") or ""
    printed = f"The BIR {spec.code} prints"
    individual = (c.get("ph_taxpayer_type") or "Non-individual") == "Individual"

    tin = re.sub(r"\D", "", c.get("tax_id") or "")
    if len(tin) != 9:
        out.append(Need("company.tin", "What is the company's TIN (9 digits)?", f"{printed} the taxpayer's TIN.", _company_field(company, "tax_id"), "tin"))
    branch = (c.get("ph_branch_code") or "").strip()
    if not re.fullmatch(r"\d{5}", branch):
        out.append(Need("company.branch", "What is the company's branch code (5 digits, 00000 for the head office)?", f"{printed} the branch code beside the TIN.", _company_field(company, "ph_branch_code"), "text"))
    if individual:
        if _blank(c.get("ph_last_name")) or _blank(c.get("ph_first_name")):
            out.append(Need("company.name", "What are the taxpayer's last name and first name, as registered with the BIR?", f"{printed} the individual taxpayer's registered name.", _company_field(company, "ph_last_name"), "text"))
    elif _blank(c.get("ph_registered_name")):
        out.append(Need("company.registered_name", "What is the registered name, exactly as on the BIR Certificate of Registration?", f"{printed} the registered name.", _company_field(company, "ph_registered_name"), "text"))
    if _blank(c.get("ph_rdo")):
        out.append(Need("company.rdo", "What is the company's RDO code (3 digits)?", f"{printed} the Revenue District Office code.", _company_field(company, "ph_rdo"), "text"))
    if _blank(c.get("ph_registered_address")):
        out.append(Need("company.address", "What is the registered address, as on the Certificate of Registration?", f"{printed} the registered address.", _company_field(company, "ph_registered_address"), "text"))
    if not re.fullmatch(r"\d{4}", (c.get("ph_zip") or "").strip()):
        out.append(Need("company.zip", "What is the ZIP code of the registered address (4 digits)?", f"{printed} the ZIP code.", _company_field(company, "ph_zip"), "text"))
    if spec.code in CONTACT_FORMS and _blank(c.get("ph_contact_number")):
        out.append(Need("company.contact", "What is the company's contact number?", f"{printed} a contact number, and a return without one cannot be submitted.", _company_field(company, "ph_contact_number"), "text"))
    if spec.output == "export" and _blank(c.get("ph_email")):
        out.append(Need("company.email", "What is the company's email address, as registered with the BIR?", f"{printed} the email address.", _company_field(company, "ph_email"), "text"))
    if spec.code in INDIVIDUAL_RETURNS:
        if _blank(c.get("ph_civil_status")):
            out.append(Need("company.civil_status", "What is the taxpayer's civil status?", f"{printed} the civil status.", _company_field(company, "ph_civil_status"), "choice", ["Single", "Married", "Legally Separated", "Widow/er"]))
        if _blank(c.get("ph_birthdate")):
            out.append(Need("company.birthdate", "What is the taxpayer's date of birth?", f"{printed} the date of birth.", _company_field(company, "ph_birthdate"), "date"))
        if _blank(c.get("ph_citizenship")):
            out.append(Need("company.citizenship", "What is the taxpayer's citizenship?", f"{printed} the citizenship.", _company_field(company, "ph_citizenship"), "text"))
    if spec.code in {"1702Q", "1702-RT"} and _blank(c.get("ph_incorporation_date")):
        out.append(Need("company.incorporation_date", "What is the date of incorporation or organization?", f"{printed} the date of incorporation.", _company_field(company, "ph_incorporation_date"), "date"))
    return out


def draft_need(return_name: str, key: str, question: str, why: str, kind: str = "text", options: list[str] | None = None) -> Need:
    """A need the draft's own data answers (a choice, a typed figure)."""
    return Need(f"data.{key}", question, why, {"doctype": "PH Tax Return", "name": return_name, "field": f"data.{key}"}, kind, options or [])


def refusal_need(key: str, sentence: str) -> Need:
    """A refusal of the form's own compute or export, carried as a need in its own words."""
    return Need(key, sentence, "The return cannot be produced until this is settled.", None, "text")
