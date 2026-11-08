"""B23/B24: the books of accounts. Shared queries, the tie-out helper and the
columns every book carries (RR 9-2009: date, reference, particulars, account,
debit, credit; every print carries the Annex B header through the default
letter head, every export through ph_cas.audit.export)."""

import frappe
from frappe import _
from frappe.utils import flt


def gl_rows(company, start, end, extra: str = "", params: dict | None = None):
    params = dict(params or {})
    params.update({"company": company, "start": start, "end": end})
    return frappe.db.sql(
        f"""select g.posting_date, g.voucher_type, g.voucher_no, g.account, g.party_type, g.party,
                   g.debit, g.credit, g.remarks, g.against, g.is_opening,
                   a.root_type, a.account_type
            from `tabGL Entry` g join `tabAccount` a on a.name = g.account
            where g.company = %(company)s and g.is_cancelled = 0
              and g.posting_date between %(start)s and %(end)s {extra}
            order by g.posting_date, g.voucher_no, g.creation""",
        params,
        as_dict=True,
    )


def voucher_serial(voucher_type, voucher_no, cache: dict) -> str:
    """The BIR serial where the voucher has one, else the voucher number."""
    key = (voucher_type, voucher_no)
    if key not in cache:
        serial = None
        if voucher_type in ("Sales Invoice", "Payment Entry"):
            serial = frappe.db.get_value(voucher_type, voucher_no, "bir_serial")
        cache[key] = serial or voucher_no
    return cache[key]


def party_name(party_type, party, cache: dict) -> str:
    if not party:
        return ""
    key = (party_type, party)
    if key not in cache:
        field = {"Customer": "customer_name", "Supplier": "supplier_name", "Employee": "employee_name"}.get(party_type)
        cache[key] = frappe.db.get_value(party_type, party, field) if field else party
    return cache[key] or party


def party_tin(party_type, party, cache: dict) -> str:
    if party_type not in ("Customer", "Supplier") or not party:
        return ""
    key = ("tin", party_type, party)
    if key not in cache:
        tin, branch = frappe.db.get_value(party_type, party, ["ph_tin", "ph_branch_code"]) or (None, None)
        cache[key] = f"{tin}-{branch or '00000'}" if tin else ""
    return cache[key]


def cash_accounts(company) -> set:
    return set(frappe.get_all("Account", filters={"company": company, "account_type": ("in", ["Cash", "Bank"]), "is_group": 0}, pluck="name"))


def period_totals(company, start, end) -> dict:
    row = frappe.db.sql(
        """select coalesce(sum(debit), 0), coalesce(sum(credit), 0) from `tabGL Entry`
           where company = %s and is_cancelled = 0 and posting_date between %s and %s""",
        (company, start, end),
    )[0]
    return {"debit": flt(row[0], 2), "credit": flt(row[1], 2)}


def tie_out(book_debit: float, book_credit: float, company, start, end) -> dict:
    """Does the book's total agree with the ledger? Returns the comparison."""
    t = period_totals(company, start, end)
    return {"book_debit": flt(book_debit, 2), "book_credit": flt(book_credit, 2), "ledger_debit": t["debit"], "ledger_credit": t["credit"], "ties": flt(book_debit, 2) == t["debit"] and flt(book_credit, 2) == t["credit"]}


def tie_row(label: str, ties: bool, detail: str = ""):
    return {"posting_date": None, "reference": label, "particulars": (_("TIES TO THE LEDGER") if ties else _("DOES NOT TIE")) + (f" ({detail})" if detail else ""), "is_tie_row": 1}


def standard_filters():
    return [
        {"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company", "default": "__default_company", "reqd": 1},
        {"fieldname": "from_date", "label": "From", "fieldtype": "Date", "reqd": 1},
        {"fieldname": "to_date", "label": "To", "fieldtype": "Date", "reqd": 1},
    ]
