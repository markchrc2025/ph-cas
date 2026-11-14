"""The eBIRForms export file: the file the offline package reads ("Load" in
eBIRForms) and what the overlay prints from, so the PDF shows what was filed.

A builder gives rows [(key, value), ...] in the package's own order; this
module writes the file in the package's two layouts and names it the way the
package does: <tin><branch3><form>v<yyyy><mm><yyyy>Q<n>.xml.

ExportRefusal: a return the file cannot carry faithfully (more rows than the
form has, an ATC the form does not list). The builders raise it instead of
writing a file that differs from the return; the user reads the message as it is.
"""

import re
from datetime import date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from ph_cas.forms.money import amt

MANILA = ZoneInfo("Asia/Manila")
TAIL = "All Rights Reserved BIR 2012.0"


class ExportRefusal(Exception):
    pass


def enc(v) -> str:
    """URL-encode a value the eBIRForms way (comma to %2C, space to %20)."""
    if v is None:
        return ""
    return quote(str(v), safe="-_.!~*'()")


def rb(cond) -> str:
    """Radio or checkbox boolean: "true" or "false"."""
    return "true" if cond else "false"


def dob(d) -> str:
    """A date as the forms print it: mm/dd/yyyy. Accepts a date or "yyyy-mm-dd"."""
    if not d:
        return ""
    if isinstance(d, (date, datetime)):
        return f"{d.month:02d}/{d.day:02d}/{d.year}"
    p = str(d).split("-")
    return f"{p[1]}/{p[2]}/{p[0]}" if len(p) == 3 else str(d)


def manila_date(at: datetime | None = None) -> str:
    """A date as eBIRForms writes dateFiled, yyyy/mm/dd, on the Manila calendar."""
    at = at or datetime.now(MANILA)
    if at.tzinfo is None:
        at = at.replace(tzinfo=MANILA)
    return at.astimezone(MANILA).strftime("%Y/%m/%d")


def tin_parts(tin: str, branch: str = "00000") -> dict:
    """The TIN as three groups plus the branch code in three and in five digits."""
    d = re.sub(r"\D", "", tin or "")
    b = re.sub(r"\D", "", branch or "0") or "0"
    return {"t1": d[0:3], "t2": d[3:6], "t3": d[6:9], "branch3": b.rjust(3, "0")[-3:], "branch5": b.rjust(5, "0")[-5:]}


def write_tabbed(rows: list[tuple[str, str]]) -> str:
    """The 2551Q layout: one line; header then TAB TAB, divs joined by TAB TAB, tail after four TABs."""
    body = "\t\t".join(f"<div>{k}={v}{k}=</div>" for k, v in rows)
    return f"<?xml version='1.0'?>\t\t{body}\t\t\t\t{TAIL}"


def write_lined(rows: list[tuple[str, str]]) -> str:
    """The 2550Q and income-tax layout: first div on the header line, the rest one per line."""
    divs = [f"<div>{k}={v}{k}=</div>" for k, v in rows]
    first = divs[0] if divs else ""
    rest = "\n".join(divs[1:])
    return f"<?xml version='1.0'?>        {first}" + (f"\n{rest}" if rest else "") + f"\n        {TAIL}"


def file_name(tin: str, branch: str, form_key: str, version_year: str, mm: str, yyyy: str, qn: int | None) -> str:
    """<tin><branch3><form>v<version year><mm><yyyy>[Q<n>].xml, as the package names its files."""
    t = tin_parts(tin, branch)
    q = f"Q{qn}" if qn else ""
    return f"{t['t1']}{t['t2']}{t['t3']}{t['branch3']}{form_key}v{version_year}{mm}{yyyy}{q}.xml"


__all__ = ["ExportRefusal", "TAIL", "amt", "dob", "enc", "file_name", "manila_date", "rb", "tin_parts", "write_lined", "write_tabbed"]
