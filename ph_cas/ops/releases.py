"""LDG-99: the release log and the quarterly notice of minor enhancements.

The owner's method (15 Nov 2026, docs/DECISIONS.md, docs/runbooks/upgrades.md):
- A major release is a new major version (the first number). It is the only kind
  of release that may add or remove a module, change a function with financial
  effect or change the database framework (RMO 9-2021 V.8). Clients are told
  ahead, choose whether to move, and file an update of registration with their
  RDO before they use it. Each major version runs in its own container.
- A minor release is a bug fix or a small field change within the same major
  version. Minor releases are listed in one combined written notice per client
  per quarter (RMO 9-2021 V.9), generated here from the release log.
- Enterprise clients follow the same rules.
"""

import io
import json
import os

import frappe
from frappe import _
from frappe.utils import getdate, today

import ph_cas

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "setup", "data", "releases.json")
CLASSES = ("major", "minor")


def releases() -> list[dict]:
    with open(LOG, encoding="utf-8") as f:
        return json.load(f)["releases"]


def major(version: str) -> int:
    return int(version.split(".")[0])


def check_log(items: list[dict] | None = None) -> list[str]:
    """Problems in the release log: classes, order, and the major-version rule."""
    items = items if items is not None else releases()
    out, prev = [], None
    for r in items:
        v = r.get("version", "?")
        if r.get("class") not in CLASSES:
            out.append(f"{v}: class must be major or minor")
        if prev:
            pv, cv = [int(x) for x in prev["version"].split(".")], [int(x) for x in v.split(".")]
            if cv <= pv:
                out.append(f"{v}: versions must increase")
            if r.get("class") == "major" and cv[0] != pv[0] + 1:
                out.append(f"{v}: a major release starts the next major version")
            if r.get("class") == "minor" and cv[0] != pv[0]:
                out.append(f"{v}: a minor release stays within major version {pv[0]}")
            if getdate(r["date"]) < getdate(prev["date"]):
                out.append(f"{v}: dates must not go back")
        prev = r
    return out


def quarter_bounds(year: int, quarter: int):
    if quarter not in (1, 2, 3, 4):
        frappe.throw(_("Quarter is 1 to 4."))
    first = getdate(f"{year}-{3 * quarter - 2:02d}-01")
    last = getdate(f"{year + (quarter == 4)}-{(3 * quarter) % 12 + 1:02d}-01")
    return first, frappe.utils.add_days(last, -1)


def minor_releases_in(year: int, quarter: int, items: list[dict] | None = None, running: str | None = None) -> list[dict]:
    """The minor releases of the running major version (ph_cas.__version__ unless given) dated within the quarter."""
    start, end = quarter_bounds(year, quarter)
    running = major(running or ph_cas.__version__)
    return [r for r in (items if items is not None else releases())
            if r["class"] == "minor" and major(r["version"]) == running and start <= getdate(r["date"]) <= end]


def version_before(day, items: list[dict] | None = None) -> str:
    """The last release dated before the given day."""
    older = [r for r in (items if items is not None else releases()) if getdate(r["date"]) < getdate(day)]
    return older[-1]["version"] if older else ""


def quarterly_notice(company: str, year: int, quarter: int, items: list[dict] | None = None, running: str | None = None) -> str | None:
    """The combined written notice of minor enhancements for one client and quarter,
    or None when the quarter had no minor release (nothing to notify)."""
    from ph_cas.audit.header import software_name

    rel = minor_releases_in(year, quarter, items, running)
    if not rel:
        return None
    c = frappe.get_cached_doc("Company", company)
    s = frappe.get_single("PH CAS Settings")
    rdo = c.get("ph_rdo") or ""
    rdo_name = frappe.db.get_value("PH RDO", rdo, "rdo_name") if rdo else ""
    tin = f"{c.tax_id or ''}-{c.get('ph_branch_code') or '00000'}"
    product = software_name()
    old = version_before(rel[0]["date"], items) or rel[0]["version"]
    lines = [
        getdate(today()).strftime("%d %B %Y"),
        "",
        "The Revenue District Officer",
        f"Revenue District Office No. {rdo}{f', {rdo_name}' if rdo_name else ''}",
        "",
        f"Re: Notice of minor enhancements to the registered Computerized Accounting System of {c.get('ph_registered_name') or c.company_name}, "
        f"TIN {tin}, ACCN {c.get('ph_accn') or '(not yet issued)'}, quarter {quarter} of {year}",
        "",
        "Sir or Madam:",
        "",
        f"Pursuant to Section V.9 of RMO No. 9-2021, we give notice that the Computerized Accounting System registered under the "
        f"above ACCN, {product}, received the following minor enhancements during the quarter, from version {old} to version {rel[-1]['version']}. "
        "They are bug fixes and small changes to how fields are entered. None adds or removes a module, changes a function with "
        "financial effect, changes the formats of the invoices and books, or changes the controls sworn to in the joint sworn statement.",
        "",
    ]
    for r in rel:
        lines.append(f"Version {r['version']}, {getdate(r['date']).strftime('%d %B %Y')}: {r.get('summary') or ''}".rstrip(": "))
        for it in r.get("items") or []:
            lines.append(f"  - {it}")
    lines += [
        "",
        "The taxpayer and the provider remain bound by the joint sworn statement on file.",
        "",
        "Very truly yours,",
        "",
        "",
        f"{s.get('provider_signatory') or '[Provider signatory]'}, {s.get('provider_signatory_position') or '[Position]'}",
        f"{s.get('provider_name') or '[Provider]'}, TIN {s.get('provider_tin') or '[TIN]'}",
        "",
        "Conforme:",
        "",
        "",
        "____________________________, ____________________",
        f"{c.get('ph_registered_name') or c.company_name}",
    ]
    return "\r\n".join(lines) + "\r\n"


@frappe.whitelist()
def download_quarterly_notice(company: str, year: int, quarter: int):
    frappe.has_permission("Company", "write", company, throw=True)
    text = quarterly_notice(company, int(year), int(quarter))
    if text is None:
        frappe.throw(_("No minor enhancements were released in quarter {0} of {1}: no notice is needed.").format(quarter, year), title=_("Nothing to notify"))
    frappe.response["type"] = "binary"
    frappe.response["filename"] = f"notice_of_minor_enhancements_{company}_{year}Q{quarter}.txt".replace(" ", "_")
    frappe.response["filecontent"] = text.encode("utf-8")
    from ph_cas.audit.events import record

    record("export", "Company", company, 0, {"notice_of_minor_enhancements": f"{year}Q{quarter}"})
