"""B17: the compliance calendar. Due dates from the DUE-* rules, the weekend
and holiday rule, and the status of each return from PH Tax Return Figures."""

import re
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate

from ph_cas.tax.rules import parse_selector


def _notes(rule_id) -> dict:
    notes = frappe.db.get_value("PH Tax Rule", rule_id, "notes") or ""
    return parse_selector(notes.replace("\n", ";"))


def holidays(year: int) -> set:
    rows = frappe.get_all("PH Holiday", filters={"holiday_date": ("between", [f"{year}-01-01", f"{year}-12-31"])}, pluck="holiday_date")
    return {getdate(r) for r in rows}


def next_working_day(d, hols=None) -> date:
    d = getdate(d)
    hols = hols if hols is not None else holidays(d.year)
    while d.weekday() >= 5 or d in hols:
        d = add_days(d, 1)
    return d


def due_dates(form: str, year: int) -> list[dict]:
    """[{period_start, period_end, period_label, due}] for every period of the year."""
    rule_id = {"2550Q": "DUE-2550Q", "2551Q": "DUE-2551Q", "0619-E": "DUE-0619E", "1601-EQ": "DUE-1601EQ", "1604-E": "DUE-1604E", "1600-VT": "DUE-1600VT", "1702Q": "DUE-1702Q", "1702-RT": "DUE-1702RT", "1701Q": "DUE-1701Q", "1701": "DUE-1701", "1701A": "DUE-1701"}[form]
    n = _notes(rule_id)
    hols = holidays(year) | holidays(year + 1)
    out = []
    period = n.get("period")
    if period == "quarter":
        quarters = [int(q) for q in n.get("quarters", "1,2,3,4").split(",")]
        fixed = n.get("fixed", "").split(",") if n.get("fixed") else []
        for q in quarters:
            start = getdate(f"{year}-{(q - 1) * 3 + 1:02d}-01")
            end = get_last_day(add_months(start, 2))
            if fixed:
                due = getdate(f"{year}-{fixed[q - 1]}")
            elif n.get("offset") == "eom":
                due = get_last_day(add_months(end, 1))
            elif n.get("offset_days"):
                due = add_days(end, int(n["offset_days"]))
            else:
                due = getdate(f"{add_months(end, 1).year}-{add_months(end, 1).month:02d}-{int(n['offset']):02d}")
            out.append({"period_start": start, "period_end": end, "period_label": f"{year}-Q{q}", "due": next_working_day(due, hols)})
    elif period == "month":
        months = [int(m) for m in n.get("months", "").split(",")] if n.get("months") else None
        for m in range(1, 13):
            if months and ((m - 1) % 3 + 1) not in months:
                continue
            start = getdate(f"{year}-{m:02d}-01")
            end = get_last_day(start)
            nxt = add_months(start, 1)
            due = getdate(f"{nxt.year}-{nxt.month:02d}-{int(n['offset']):02d}")
            out.append({"period_start": start, "period_end": end, "period_label": f"{year}-{m:02d}", "due": next_working_day(due, hols)})
    elif period == "year":
        start, end = getdate(f"{year}-01-01"), getdate(f"{year}-12-31")
        due = getdate(f"{year + 1}-{n['fixed']}")
        out.append({"period_start": start, "period_end": end, "period_label": str(year), "due": next_working_day(due, hols)})
    return out


def applicable_forms(company: str) -> list[str]:
    c = frappe.get_cached_doc("Company", company)
    forms = ["2550Q"] if (c.get("ph_vat_status") or "Non-VAT") == "VAT" else ["2551Q"]
    forms += ["0619-E", "1601-EQ", "1604-E"]
    if frappe.db.exists("Purchase Invoice", {"company": company, "docstatus": 1, "ph_rc_atc": ("!=", "")}):
        forms.append("1600-VT")
    if (c.get("ph_taxpayer_type") or "Non-individual") == "Individual":
        forms += ["1701Q", "1701"]
    else:
        forms += ["1702Q", "1702-RT"]
    return forms


def calendar(company: str, year: int) -> list[dict]:
    rows = []
    for form in applicable_forms(company):
        for d in due_dates(form, year):
            label = d["period_label"]
            fig = frappe.db.get_value("PH Tax Return Figures", {"company": company, "form": form, "period_label": label}, ["name", "filed", "computed_on"], as_dict=True)
            if fig and fig.filed:
                status = "Filed"
            elif fig:
                status = "Computed, not filed"
            elif getdate(frappe.utils.nowdate()) > d["due"]:
                status = "OVERDUE, nothing computed"
            elif getdate(frappe.utils.nowdate()) > d["period_end"]:
                status = "Due, not computed"
            else:
                status = "Period open"
            rows.append({"form": form, **d, "status": status, "figures": fig.name if fig else None})
    rows.sort(key=lambda r: (r["due"], r["form"]))
    return rows


def setup():
    """Seed the regular holidays of the current and next year (dates that do not move)."""
    from frappe.utils import nowdate

    y = getdate(nowdate()).year
    fixed = {"01-01": "New Year's Day", "04-09": "Araw ng Kagitingan", "05-01": "Labor Day", "06-12": "Independence Day", "08-21": "Ninoy Aquino Day", "11-01": "All Saints' Day", "11-30": "Bonifacio Day", "12-08": "Feast of the Immaculate Conception", "12-25": "Christmas Day", "12-30": "Rizal Day", "12-31": "Last Day of the Year"}
    for year in (y, y + 1):
        for md, name in fixed.items():
            d = f"{year}-{md}"
            if not frappe.db.exists("PH Holiday", {"holiday_date": d}):
                frappe.get_doc({"doctype": "PH Holiday", "holiday_date": d, "holiday_name": name, "movable": 0}).insert(ignore_permissions=True)
