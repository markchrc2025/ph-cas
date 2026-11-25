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
    {"label": "BIR", "route": "/app/ph-tax-return", "icon": "landmark"},
    {"label": "Books", "route": "/app/query-report/PH General Ledger Book", "icon": "notebook"},
    {"label": "Reports", "route": "/app/ph-reports", "icon": "chart-column"},
]

CREATE_ACTIONS = [
    {"label": "New sales invoice", "route": "/app/sales-invoice/new"},
    {"label": "New purchase invoice", "route": "/app/purchase-invoice/new"},
    {"label": "Record a payment", "route": "/app/payment-entry/new"},
    {"label": "Journal entry", "route": "/app/journal-entry/new"},
    {"label": "Issue a 2307", "route": "/app/ph-2307-issued/new"},
    {"label": "Compute a return", "route": "/app/ph-tax-return/new"},
]


# B75 (after ECOUNT's dashboards per user): what each role set's home shows
CASHIER_TILES = [
    {"label": "Sales", "route": "/app/sales-invoice", "icon": "receipt-text"},
    {"label": "Collections", "route": "/app/payment-entry?payment_type=Receive", "icon": "banknote"},
    {"label": "Cash today", "route": "/app/query-report/PH Cash Position", "icon": "wallet"},
    {"label": "Items", "route": "/app/item", "icon": "package"},
    {"label": "Reports", "route": "/app/ph-reports", "icon": "chart-column"},
]
CASHIER_ACTIONS = [
    {"label": "New sales invoice", "route": "/app/sales-invoice/new"},
    {"label": "Record a collection", "route": "/app/payment-entry/new?payment_type=Receive"},
]
BOOKKEEPER_EXTRA_ACTIONS = [
    {"label": "Record an expense", "action": "record_expense"},
    {"label": "Import from a template", "action": "import"},
]
_WHOLE = ["sales", "purchases", "cash", "receivable", "payable", "vat", "withholding", "drafts"]
CARDS = {
    "Owner": _WHOLE,
    "Accounting Manager": _WHOLE,
    "Accountant": _WHOLE,
    "Staff": ["sales_today", "cash", "receivable", "drafts_mine"],
}
SECTIONS = {
    "Owner": ["create", "onboarding", "approvals", "cards", "chart", "due"],
    "Accounting Manager": ["create", "onboarding", "approvals", "cards", "chart", "due"],
    "Accountant": ["create", "onboarding", "approvals", "cards", "chart", "due"],
    "Staff": ["create", "cards"],
}


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
        "Account", filters={"company": company, "is_group": 0, "account_type": ["in", ["Cash", "Bank"]], "root_type": ["!=", "Liability"]}, pluck="name"
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


def _return_route(company: str, r: dict) -> str:
    """The return in BIR Returns (PH Tax Return), or a new one for that form and period."""
    from urllib.parse import urlencode

    name = frappe.db.get_value("PH Tax Return", {"company": company, "form": r["form"], "period_start": r["period_start"], "docstatus": ("<", 2)}, "name")
    if name:
        return f"/app/ph-tax-return/{name}"
    return "/app/ph-tax-return/new?" + urlencode({"company": company, "form": r["form"], "period_key": r.get("period_label") or ""})


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
            "route": _return_route(company, r),
        }
        for r in rows[:limit]
    ]


def _onboarding(company: str | None = None) -> dict | None:
    if not frappe.db.exists("Module Onboarding", ONBOARDING):
        return None
    if frappe.db.get_default("ph_home_hide_onboarding", frappe.session.user):
        return None
    doc = frappe.get_doc("Module Onboarding", ONBOARDING)
    from ph_cas.tutorials.api import step_map, uploaded

    from ph_cas.home.progress import step_done

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
        done = step_done(s.name, company)  # B91: from the work, not the click
        if done is None:
            done = bool(s.is_complete or s.is_skipped)
        steps.append(
            {
                "name": s.name,
                "title": s.title,
                "description": s.description,
                "action_label": s.action_label,
                "route": route,
                "done": done,
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


def _modules_off() -> list[str]:
    """B79: a System Manager is told which modules are switched off, so a missing menu is not
    mistaken for lost access (Settings > Modules turns them back on)."""
    if "System Manager" not in frappe.get_roles():
        return []
    try:
        from ph_cas.modules.api import catalogue, state

        st = state()
        return [m.get("label") or m["key"].title() for m in catalogue() if not st.get(m["key"], True)]
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
    from ph_cas.setup.roles import role_set

    rs = role_set()
    out = {
        "greeting": _greeting(),
        "first_name": (user.first_name or user.full_name or frappe.session.user).strip(),
        "date": frappe.utils.formatdate(nowdate(), "EEEE, d MMMM yyyy"),
        "company": company,
        "companies": companies,
        "period": period,
        "period_label": period_label,
        "currency": frappe.get_cached_value("Company", company, "default_currency") if company else "PHP",
        "role_set": rs,
        "tiles": CASHIER_TILES if rs == "Staff" else TILES,
        "create_actions": CASHIER_ACTIONS if rs == "Staff" else CREATE_ACTIONS + BOOKKEEPER_EXTRA_ACTIONS,
        "cards": CARDS[rs],
        "sections": SECTIONS[rs],
        "figures": {},
        "monthly": [],
        "due": [],
        "onboarding": _onboarding(company) if rs != "Staff" else None,
        "approvals": _approvals(),
        "modules_off": _modules_off(),
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
    today_ = nowdate()
    f["sales_today"] = _sum("Sales Invoice", "base_grand_total", company, today_, today_)
    f["invoices_today"] = _count("Sales Invoice", company, today_, today_)
    f["drafts_mine"] = frappe.db.count("Sales Invoice", {"company": company, "docstatus": 0, "owner": frappe.session.user})
    f["drafts"] = {
        "sales_invoice": _count("Sales Invoice", company, None, None, docstatus=0),
        "purchase_invoice": _count("Purchase Invoice", company, None, None, docstatus=0),
        "payment_entry": _count("Payment Entry", company, None, None, docstatus=0),
        "journal_entry": _count("Journal Entry", company, None, None, docstatus=0),
    }
    if rs == "Staff":
        # the counter sees the counter's figures only, not the payables or the tax position
        out["figures"] = {k: f[k] for k in ("sales_today", "invoices_today", "cash", "receivable", "overdue_receivable", "drafts_mine")}
        out["approvals"] = []
        return out
    out["monthly"] = _monthly(company)
    out["due"] = _due_dates(company)
    return out


@frappe.whitelist()
def hide_onboarding():
    frappe.defaults.set_user_default("ph_home_hide_onboarding", 1)
    return True
