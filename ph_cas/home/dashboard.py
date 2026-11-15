"""B39: the home page's data, in one call.

Everything the home page shows comes from `get()`: the company's figures for the chosen
period, the open balances, the tax position from the mapped accounts, the next due dates
from the compliance calendar, a 12-month series, the counts of drafts, and the onboarding
checklist. One request instead of one per card, which is what made the workspace feel slow.

Figures are read from posted documents and the General Ledger only; nothing here computes a
return. The VAT and withholding cards are the balances of the accounts the tax engine posts
to, which is what will be remitted, not an estimate.
"""

from __future__ import annotations

from datetime import date

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate, nowdate

from ph_cas.setup.onboarding import ONBOARDING

PERIODS = ("month", "last_month", "quarter", "year", "all")

TILES = [
    {"label": "Sales", "route": "/app/sales-invoice", "icon": "receipt-text"},
    {"label": "Purchases", "route": "/app/purchase-invoice", "icon": "shopping-cart"},
    {"label": "Payments", "route": "/app/payment-entry", "icon": "banknote"},
    {"label": "BIR", "route": "/app/ph-tax-return-figures", "icon": "landmark"},
    {"label": "Books", "route": "/app/query-report/PH General Ledger Book", "icon": "notebook"},
    {"label": "Reports", "route": "/app/query-report/BIR Audit Trail", "icon": "chart-column"},
]

CREATE_ACTIONS = [
    {"label": "New sales invoice", "route": "/app/sales-invoice/new"},
    {"label": "New purchase invoice", "route": "/app/purchase-invoice/new"},
    {"label": "Record a payment", "route": "/app/payment-entry/new"},
    {"label": "Journal entry", "route": "/app/journal-entry/new"},
    {"label": "Issue a 2307", "route": "/app/ph-2307-issued/new"},
    {"label": "Compute a return", "route": "/app/ph-tax-return/new"},
]


def period_bounds(period: str, today: date | None = None) -> tuple[date | None, date | None, str]:
    today = today or getdate(nowdate())
    if period == "last_month":
        start = get_first_day(add_months(today, -1))
        return start, get_last_day(start), start.strftime("%B %Y")
    if period == "quarter":
        q = (today.month - 1) // 3
        start = date(today.year, q * 3 + 1, 1)
        return start, get_last_day(add_months(start, 2)), f"Q{q + 1} {today.year}"
    if period == "year":
        return date(today.year, 1, 1), date(today.year, 12, 31), str(today.year)
    if period == "all":
        return None, None, _("All time")
    start = get_first_day(today)
    return start, get_last_day(today), today.strftime("%B %Y")


def _companies() -> list[str]:
    return frappe.get_list("Company", pluck="name", order_by="creation asc")


def _sum(doctype: str, field: str, company: str, start, end, extra: str = "", **extra_params) -> float:
    cond = "docstatus = 1 and company = %(company)s"
    params = {"company": company, **extra_params}
    if start:
        cond += " and posting_date between %(start)s and %(end)s"
        params.update(start=start, end=end)
    return flt(frappe.db.sql(f"select sum(`{field}`) from `tab{doctype}` where {cond} {extra}", params)[0][0])


def _count(doctype: str, company: str, start, end, docstatus: int = 1) -> int:
    cond = "docstatus = %(ds)s and company = %(company)s"
    params = {"company": company, "ds": docstatus}
    if start:
        cond += " and posting_date between %(start)s and %(end)s"
        params.update(start=start, end=end)
    return int(frappe.db.sql(f"select count(*) from `tab{doctype}` where {cond}", params)[0][0])


def _gl_balance(company: str, accounts: list[str], credit_side: bool = False) -> float:
    if not accounts:
        return 0.0
    rows = frappe.db.sql(
        """select sum(debit) - sum(credit) from `tabGL Entry`
           where company = %s and is_cancelled = 0 and account in %s""",
        (company, tuple(accounts)),
    )
    bal = flt(rows[0][0])
    return -bal if credit_side else bal


def _mapped(company: str, purposes: list[str]) -> list[str]:
    if not frappe.db.exists("DocType", "PH Account Mapping"):
        return []
    return frappe.get_all(
        "PH Account Mapping", filters={"company": company, "purpose": ["in", purposes]}, pluck="account"
    )


def _cash_accounts(company: str) -> list[str]:
    return frappe.get_all(
        "Account", filters={"company": company, "is_group": 0, "account_type": ["in", ["Cash", "Bank"]]}, pluck="name"
    )


def _monthly(company: str, months: int = 12) -> list[dict]:
    today = getdate(nowdate())
    out = []
    for i in range(months - 1, -1, -1):
        start = get_first_day(add_months(today, -i))
        end = get_last_day(start)
        out.append(
            {
                "label": start.strftime("%b %y"),
                "sales": _sum("Sales Invoice", "base_net_total", company, start, end),
                "purchases": _sum("Purchase Invoice", "base_net_total", company, start, end),
            }
        )
    return out


def _due_dates(company: str, limit: int = 5) -> list[dict]:
    try:
        from ph_cas.tax.calendar import calendar
    except Exception:
        return []
    today = getdate(nowdate())
    rows = []
    for year in (today.year, today.year + 1):
        try:
            rows.extend(calendar(company, year))
        except Exception:
            frappe.log_error("home dashboard: compliance calendar")
            break
    rows = [r for r in rows if getdate(r["due"]) >= today or "OVERDUE" in (r.get("status") or "")]
    rows.sort(key=lambda r: (getdate(r["due"]), r["form"]))
    return [
        {
            "form": r["form"],
            "period": r.get("period_label"),
            "due": str(r["due"]),
            "days": (getdate(r["due"]) - today).days,
            "status": r.get("status"),
            "route": f"/app/ph-tax-return-figures/{r['figures']}" if r.get("figures") else "/app/ph-tax-return-figures/new",
        }
        for r in rows[:limit]
    ]


def _onboarding() -> dict | None:
    if not frappe.db.exists("Module Onboarding", ONBOARDING):
        return None
    if frappe.db.get_default("ph_home_hide_onboarding", frappe.session.user):
        return None
    doc = frappe.get_doc("Module Onboarding", ONBOARDING)
    from ph_cas.tutorials.api import step_map, uploaded

    videos, on_server = step_map(), uploaded()
    steps = []
    for row in doc.steps:
        s = frappe.db.get_value(
            "Onboarding Step",
            row.step,
            ["name", "title", "description", "action", "action_label", "path", "reference_document", "is_complete", "is_skipped"],
            as_dict=True,
        )
        if not s:
            continue
        route = s.path
        if not route and s.reference_document:
            route = f"/app/{frappe.scrub(s.reference_document).replace('_', '-')}"
            if s.action == "Create Entry":
                route += "/new"
        steps.append(
            {
                "name": s.name,
                "title": s.title,
                "description": s.description,
                "action_label": s.action_label,
                "route": route,
                "done": bool(s.is_complete or s.is_skipped),
                "video": videos.get(s.name) if videos.get(s.name) in on_server else None,
                "video_length": on_server.get(videos.get(s.name)),
            }
        )
    if steps and all(s["done"] for s in steps):
        return None
    return {"title": doc.title, "steps": steps, "done": sum(1 for s in steps if s["done"]), "total": len(steps)}


def _greeting(now=None) -> str:
    hour = (now or frappe.utils.now_datetime()).hour
    if hour < 12:
        return _("Good morning")
    if hour < 18:
        return _("Good afternoon")
    return _("Good evening")


def _approvals() -> list:
    try:
        from ph_cas.approvals.requests import pending_for

        return pending_for()
    except Exception:
        return []


@frappe.whitelist()
def get(company: str | None = None, period: str = "month") -> dict:
    """Everything the home page shows, for one company and one period."""
    if period not in PERIODS:
        period = "month"
    companies = _companies()
    company = company if company in companies else (frappe.defaults.get_user_default("Company") or (companies[0] if companies else None))
    if company and not frappe.has_permission("Company", doc=company):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    start, end, period_label = period_bounds(period)
    user = frappe.get_cached_value("User", frappe.session.user, ["first_name", "full_name"], as_dict=True)
    out = {
        "greeting": _greeting(),
        "first_name": (user.first_name or user.full_name or frappe.session.user).strip(),
        "date": frappe.utils.formatdate(nowdate(), "EEEE, d MMMM yyyy"),
        "company": company,
        "companies": companies,
        "period": period,
        "period_label": period_label,
        "currency": frappe.get_cached_value("Company", company, "default_currency") if company else "PHP",
        "tiles": TILES,
        "create_actions": CREATE_ACTIONS,
        "figures": {},
        "monthly": [],
        "due": [],
        "onboarding": _onboarding(),
        "approvals": _approvals(),
    }
    if not company:
        return out
    f = out["figures"]
    f["sales"] = _sum("Sales Invoice", "base_net_total", company, start, end)
    f["purchases"] = _sum("Purchase Invoice", "base_net_total", company, start, end)
    f["invoices_issued"] = _count("Sales Invoice", company, start, end)
    f["bills_recorded"] = _count("Purchase Invoice", company, start, end)
    f["receivable"] = _sum("Sales Invoice", "outstanding_amount", company, None, None, "and outstanding_amount > 0")
    f["payable"] = _sum("Purchase Invoice", "outstanding_amount", company, None, None, "and outstanding_amount > 0")
    f["overdue_receivable"] = _sum(
        "Sales Invoice", "outstanding_amount", company, None, None, "and outstanding_amount > 0 and due_date < %(today)s", today=nowdate()
    )
    f["cash"] = _gl_balance(company, _cash_accounts(company))
    f["output_vat"] = _gl_balance(company, _mapped(company, ["output_vat", "vat_payable"]), credit_side=True)
    f["input_vat"] = _gl_balance(
        company, _mapped(company, ["input_vat_goods", "input_vat_services", "input_vat_capital", "input_vat_import", "input_vat_reverse_charge"])
    )
    f["vat_position"] = flt(f["output_vat"] - f["input_vat"], 2)
    f["withholding_to_remit"] = _gl_balance(
        company, _mapped(company, ["ewt_payable", "wt_compensation_payable", "final_wt_payable", "wt_vat_payable"]), credit_side=True
    )
    f["percentage_tax_payable"] = _gl_balance(company, _mapped(company, ["percentage_tax_payable"]), credit_side=True)
    f["drafts"] = {
        "sales_invoice": _count("Sales Invoice", company, None, None, docstatus=0),
        "purchase_invoice": _count("Purchase Invoice", company, None, None, docstatus=0),
        "payment_entry": _count("Payment Entry", company, None, None, docstatus=0),
        "journal_entry": _count("Journal Entry", company, None, None, docstatus=0),
    }
    out["monthly"] = _monthly(company)
    out["due"] = _due_dates(company)
    return out


@frappe.whitelist()
def hide_onboarding():
    frappe.defaults.set_user_default("ph_home_hide_onboarding", 1)
    return True
