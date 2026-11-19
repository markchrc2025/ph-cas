"""QA pass 4: every function of Sentire Ledger, end to end, on the staging site.

`run(section)` runs one section as the signed-in user (the QA admin through the connector), with
no ignore_permissions anywhere, so permissions, BIR serials, the posting-date lock, the Annex B
locks and every tax rule apply as they do for a person. Each step runs in its own savepoint: a
failing step is rolled back and reported, and the section carries on. The result is a short
list of steps with ok / FAIL and a one-line detail, so a whole section fits in one reply.

Sections (in the order they build on each other): companies, purchasing, sales, tasks, inventory,
projects, assets, quality, crm, support, industries, forms. The data is idempotent where the app
allows it (masters are reused, documents are added again on a rerun).

Staging only (require_staging); the test suite runs it under frappe.flags.in_test.
"""

from __future__ import annotations

import json
import traceback

import frappe
from frappe.utils import add_days, flt, getdate, nowdate, today

from ph_cas.qa.api import is_staging

# ---- the four taxpayer types --------------------------------------------------------------------
COMPANIES = {
    # name: (abbr, vat, individual, fields)
    "QA4 Reyes Hardware": ("Q4RH", "VAT", True, {
        "tax_id": "000-905-001", "ph_registered_name": "JOSE DELA PAZ REYES", "ph_business_style": "REYES HARDWARE",
        "ph_last_name": "Reyes", "ph_first_name": "Jose", "ph_middle_name": "Dela Paz", "ph_birthdate": "1980-06-02",
        "ph_civil_status": "Married", "ph_individual_type": "Single Proprietorship", "ph_citizenship": "Filipino",
        "ph_registered_address": "88 Rizal Avenue\nBarangay San Roque, Marikina City", "ph_zip": "1800",
        "ph_contact_number": "09181234567", "ph_email": "qa.reyes@example.com", "ph_line_of_business": "Retail of hardware",
        "ph_income_tax_option": "Graduated (individual)", "ph_deduction_method": "Itemized", "ph_taxpayer_class": "Small",
        "ph_primary_business": "Goods",
    }),
    "QA4 Cruz Bakeshop": ("Q4CB", "Non-VAT", True, {
        "tax_id": "000-905-002", "ph_registered_name": "ANA SANTOS CRUZ", "ph_business_style": "CRUZ BAKESHOP",
        "ph_last_name": "Cruz", "ph_first_name": "Ana", "ph_middle_name": "Santos", "ph_birthdate": "1990-01-20",
        "ph_civil_status": "Single", "ph_individual_type": "Single Proprietorship", "ph_citizenship": "Filipino",
        "ph_registered_address": "3 Bonifacio Street\nBarangay 4, Pasig City", "ph_zip": "1600",
        "ph_contact_number": "09191234567", "ph_email": "qa.cruz@example.com", "ph_line_of_business": "Bakery",
        "ph_income_tax_option": "8% option (individual)", "ph_deduction_method": "Itemized", "ph_taxpayer_class": "Micro",
        "ph_primary_business": "Goods",
    }),
    "QA4 Bayani Builders Corp.": ("Q4BB", "VAT", False, {
        "tax_id": "000-905-003", "ph_registered_name": "BAYANI BUILDERS CORP.", "ph_business_style": "BAYANI BUILDERS",
        "ph_registered_address": "20 Ortigas Avenue\nBarangay Ugong, Pasig City", "ph_zip": "1604", "ph_incorporation_date": "2019-05-02",
        "ph_contact_number": "0286001234", "ph_email": "qa.bayani@example.com", "ph_line_of_business": "General construction",
        "ph_income_tax_option": "Corporate", "ph_deduction_method": "Itemized", "ph_taxpayer_class": "Medium",
        "ph_primary_business": "Services", "ph_operations_start_year": 2019,
    }),
    "QA4 Lakbay Travel Services Inc.": ("Q4LT", "Non-VAT", False, {
        "tax_id": "000-905-004", "ph_registered_name": "LAKBAY TRAVEL SERVICES INC.", "ph_business_style": "LAKBAY TRAVEL",
        "ph_registered_address": "7 Taft Avenue\nBarangay 700, Manila", "ph_zip": "1004", "ph_incorporation_date": "2023-02-14",
        "ph_contact_number": "0285551234", "ph_email": "qa.lakbay@example.com", "ph_line_of_business": "Travel agency",
        "ph_income_tax_option": "Corporate", "ph_deduction_method": "OSD (40%)", "ph_taxpayer_class": "Micro",
        "ph_primary_business": "Services", "ph_operations_start_year": 2023,
    }),
}
VAT_CO, NONVAT_IND, VAT_CORP, NONVAT_CORP = list(COMPANIES)


class Step(Exception):
    pass


class Runner:
    def __init__(self):
        self.steps: list[dict] = []
        self.made: dict = {}

    def step(self, name: str, fn, *args, **kwargs):
        sp = "qa4_" + frappe.generate_hash(length=8)
        frappe.db.savepoint(sp)
        try:
            detail = fn(*args, **kwargs)
            self.steps.append({"step": name, "ok": True, "detail": _short(detail)})
            return detail
        except Exception as e:
            frappe.db.rollback(save_point=sp)
            frappe.local.message_log = []
            tb = traceback.extract_tb(e.__traceback__)
            where = next((f"{f.filename.split('/apps/')[-1]}:{f.lineno}" for f in reversed(tb) if "/apps/" in f.filename), "")
            self.steps.append({"step": name, "ok": False, "detail": f"{type(e).__name__}: {_short(_msg(e))} [{where}]"})
            return None

    def expect(self, cond, msg):
        if not cond:
            raise Step(msg)

    def result(self, section):
        fails = [s for s in self.steps if not s["ok"]]
        return {"section": section, "passed": len(self.steps) - len(fails), "failed": len(fails), "steps": self.steps}


def _msg(e) -> str:
    s = str(e) or repr(e)
    return frappe.utils.strip_html(s)


def _short(v, n=220) -> str:
    if v is None:
        return ""
    s = v if isinstance(v, str) else json.dumps(v, default=str)
    return s if len(s) <= n else s[: n - 3] + "..."


def refused(fn, *args, **kwargs) -> str:
    """The app must refuse this; returns the refusal message."""
    sp = "qa4r_" + frappe.generate_hash(length=8)
    frappe.db.savepoint(sp)
    try:
        fn(*args, **kwargs)
    except Exception as e:
        frappe.db.rollback(save_point=sp)
        frappe.local.message_log = []
        return _short(_msg(e), 140)
    frappe.db.rollback(save_point=sp)
    raise Step("was allowed but must be refused")


# ---- small builders (no ignore_permissions) -----------------------------------------------------
def abbr(company):
    return frappe.get_cached_value("Company", company, "abbr")


def acc(company, name):
    return f"{name} - {abbr(company)}"


def ensure(doctype, name, values: dict, key="name"):
    if frappe.db.exists(doctype, name):
        return name
    doc = frappe.get_doc({"doctype": doctype, **values})
    doc.insert()
    return doc.name


def item(code, vat_class="VATable", stock=0, group=None, **extra):
    group = group or ("Products" if stock else "Services")
    if not frappe.db.exists("Item Group", group):
        group = "All Item Groups"
    return ensure("Item", code, {"item_code": code, "item_name": extra.pop("item_name", code), "item_group": group, "stock_uom": "Nos",
                                 "is_stock_item": stock, "ph_vat_class": vat_class, **extra})


def customer(name, **f):
    return ensure("Customer", name, {"customer_name": name, "customer_type": f.pop("customer_type", "Company"), "customer_group": "Commercial" if frappe.db.exists("Customer Group", "Commercial") else "Individual",
                                     "territory": "All Territories", **f})


def supplier(name, **f):
    return ensure("Supplier", name, {"supplier_name": name, "supplier_type": f.pop("supplier_type", "Company"), "supplier_group": "All Supplier Groups", **f})


def sales_invoice(company, cust, lines, submit=True, **f):
    si = frappe.get_doc({
        "doctype": "Sales Invoice", "company": company, "customer": cust, "posting_date": today(), "due_date": add_days(today(), 30),
        "debit_to": acc(company, "Debtors"), "ph_manual_invoice_no": f.pop("manual", None) or "QA4-" + frappe.generate_hash(length=6).upper(),
        "items": [{"item_code": c, "qty": q, "rate": r, "income_account": acc(company, "Sales"), "cost_center": acc(company, "Main"), **(x[0] if x else {})} for c, q, r, *x in lines],
        **f,
    })
    si.insert()
    if submit:
        si.submit()
    return si


def purchase_invoice(company, sup, lines, submit=True, **f):
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": company, "supplier": sup, "posting_date": today(), "due_date": add_days(today(), 30),
        "bill_no": f.pop("bill_no", None) or "QA4B-" + frappe.generate_hash(length=6).upper(), "bill_date": today(), "credit_to": acc(company, "Creditors"),
        "items": [{"item_code": c, "qty": q, "rate": r, "expense_account": acc(company, "Administrative Expenses"), "cost_center": acc(company, "Main"), **(x[0] if x else {})} for c, q, r, *x in lines],
        **f,
    })
    pi.insert()
    if submit:
        pi.submit()
    return pi


def tax_rows(doc) -> dict:
    """account (without the company suffix) -> amount, from the document's tax table."""
    out = {}
    for t in doc.get("taxes") or []:
        name = t.account_head.rsplit(" - ", 1)[0]
        out[name] = flt(out.get(name)) + flt(t.tax_amount)
    return out


def gl_balance(company, account, from_date=None, to_date=None) -> float:
    cond, args = "company = %s and account = %s and is_cancelled = 0", [company, account]
    if from_date:
        cond += " and posting_date >= %s"
        args.append(from_date)
    if to_date:
        cond += " and posting_date <= %s"
        args.append(to_date)
    return flt(frappe.db.sql(f"select sum(debit) - sum(credit) from `tabGL Entry` where {cond}", args)[0][0], 2)


def gl(voucher_type, voucher_no) -> dict:
    out = {}
    for r in frappe.get_all("GL Entry", filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0}, fields=["account", "debit", "credit"]):
        name = r.account.rsplit(" - ", 1)[0]
        out[name] = flt(out.get(name)) + flt(r.debit) - flt(r.credit)
    return {k: round(v, 2) for k, v in out.items() if round(v, 2)}


def submit_mapped(doc, **set_values):
    for k, v in set_values.items():
        doc.set(k, v)
    if doc.doctype in ("Purchase Invoice", "Sales Invoice") and not doc.get("bill_no") and doc.doctype == "Purchase Invoice":
        doc.bill_no, doc.bill_date = "QA4B-" + frappe.generate_hash(length=6).upper(), today()
    if doc.doctype == "Sales Invoice" and not doc.get("ph_manual_invoice_no"):
        doc.ph_manual_invoice_no = "QA4-" + frappe.generate_hash(length=6).upper()
    doc.insert()
    doc.submit()
    return doc


# ---- section: companies -------------------------------------------------------------------------
def s_companies(r: Runner):
    from ph_cas.setup.chart import setup_philippine_company

    for name, (ab, vat, individual, fields) in COMPANIES.items():
        def make(name=name, ab=ab, vat=vat, individual=individual, fields=fields):
            if not frappe.db.exists("Company", name):
                frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": ab, "default_currency": "PHP", "country": "Philippines",
                                "chart_of_accounts": "Standard", "ph_branch_code": "00000", "ph_rdo": "045", "ph_vat_status": vat,
                                "ph_taxpayer_type": "Individual" if individual else "Non-individual", **fields}).insert()
            out = setup_philippine_company(name)
            c = frappe.get_doc("Company", name)
            r.expect(c.ph_vat_status == vat, f"VAT status {c.ph_vat_status}")
            series = frappe.get_all("BIR Series", filters={"company": name}, pluck="document_type")
            r.expect({"Sales Invoice", "Credit Note", "Debit Note"} <= set(series), f"series {series}")
            if vat == "VAT":
                r.expect(frappe.db.exists("Account", acc(name, "Output VAT")), "no Output VAT account")
            return f"{len(out.get('accounts') or [])} accounts, series {sorted(series)}"
        r.step(f"set up {name} ({vat}, {'individual' if individual else 'corporation'})", make)

    def header():
        from ph_cas.audit.header import ph_header_lines as header_lines

        lines = header_lines(VAT_CORP)
        text = " ".join(lines) if isinstance(lines, (list, tuple)) else str(lines)
        r.expect("BAYANI BUILDERS CORP." in text and "000-905-003" in text, text[:160])
        return text[:160]
    r.step("Annex B header names the company and TIN", header)

    def tin_check():
        return refused(frappe.get_doc({"doctype": "Customer", "customer_name": "QA4 Bad TIN", "customer_group": "Commercial", "territory": "All Territories", "ph_tin": "12-34"}).insert)
    r.step("a malformed TIN is refused", tin_check)


# ---- section: purchasing ------------------------------------------------------------------------
def _parties():
    s_goods = supplier("QA4 Tools Wholesale Corp.", ph_tin="000-907-001", ph_branch_code="00000", ph_vat_status="VAT", ph_payee_type="Non-individual",
                       ph_ewt_category="goods", ph_registered_name="QA4 TOOLS WHOLESALE CORP.", ph_address_line1="5 Quirino Avenue, Paranaque City", ph_zip="1700")
    s_prof = supplier("QA4 Dizon Law Office", supplier_type="Individual", ph_tin="000-907-002", ph_branch_code="00000", ph_vat_status="VAT", ph_payee_type="Individual",
                      ph_ewt_category="professional", ph_registered_name="", ph_last_name="DIZON", ph_first_name="RAMON", ph_middle_name="CRUZ",
                      ph_address_line1="9 Ayala Avenue, Makati City", ph_zip="1226")
    s_rent = supplier("QA4 Pasig Realty Inc.", ph_tin="000-907-003", ph_branch_code="00000", ph_vat_status="VAT", ph_payee_type="Non-individual",
                      ph_ewt_category="rent", ph_registered_name="QA4 PASIG REALTY INC.", ph_address_line1="1 Capitol Commons, Pasig City", ph_zip="1603")
    c_vat = customer("QA4 Marikina Builders Inc.", ph_tin="000-906-001", ph_branch_code="00000", ph_vat_status="VAT", ph_registered_name="QA4 MARIKINA BUILDERS INC.",
                     ph_address_line1="10 Shoe Avenue, Marikina City", ph_zip="1800", ph_top_withholding_agent=1)
    c_walkin = customer("QA4 Walk-in", customer_type="Individual", ph_vat_status="Non-VAT")
    c_gov = customer("QA4 City Government of Pasig", ph_tin="000-906-002", ph_branch_code="00000", ph_vat_status="Non-VAT", ph_registered_name="CITY GOVERNMENT OF PASIG",
                     ph_is_government=1, ph_address_line1="Caruncho Avenue, Pasig City", ph_zip="1600")
    return s_goods, s_prof, s_rent, c_vat, c_walkin, c_gov


def s_purchasing(r: Runner):
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

    parties = r.step("suppliers and customers with TIN, VAT status and EWT category", lambda: list(_parties()))
    if not parties:
        return
    s_goods, s_prof, s_rent = parties[:3]
    hammer = item("QA4-HAMMER", stock=1, item_name="Claw Hammer 16oz", valuation_rate=250)
    service = item("QA4 Legal Retainer")
    rent = item("QA4 Office Rent")

    for co in (VAT_CO, VAT_CORP, NONVAT_IND, NONVAT_CORP):
        vat = frappe.get_cached_value("Company", co, "ph_vat_status") == "VAT"
        state = {}

        def po_cycle(co=co, vat=vat, state=state):
            wh = acc(co, "Stores")
            po = frappe.get_doc({"doctype": "Purchase Order", "company": co, "supplier": s_goods, "transaction_date": today(), "schedule_date": add_days(today(), 3),
                                 "set_warehouse": wh, "items": [{"item_code": hammer, "qty": 100, "rate": 250, "schedule_date": add_days(today(), 3), "warehouse": wh}]})
            po.insert()
            po.submit()
            pr = submit_mapped(make_purchase_receipt(po.name))
            pi = submit_mapped(make_purchase_invoice(pr.name))
            t = tax_rows(pi)
            state["pi"] = pi.name
            if vat:
                r.expect(abs(t.get("Input VAT - Goods", 0) - 3000) < 0.01 or abs(flt(sum(v for k, v in t.items() if k.startswith("Input VAT"))) - 3000) < 0.01, f"input VAT {t}")
            else:
                r.expect(not any(k.startswith("Input VAT") for k in t), f"non-VAT buyer claimed input VAT {t}")
            stock = frappe.db.get_value("Bin", {"item_code": hammer, "warehouse": wh}, "actual_qty")
            r.expect(flt(stock) >= 100, f"stock {stock}")
            return f"{po.name} -> {pr.name} -> {pi.name}; taxes {t}; stock {stock}"
        r.step(f"[{co}] PO -> receipt -> bill (goods)", po_cycle)

        def professional(co=co, vat=vat, state=state):
            pi = purchase_invoice(co, s_prof, [(service, 1, 50000)])
            t = tax_rows(pi)
            ewt = abs(t.get("Withholding Tax Payable - Expanded", 0))
            r.expect(ewt == 2500.0, f"EWT 5% on an individual professional under the 3M threshold {t}")
            if vat:
                r.expect(t.get("Input VAT - Services") == 6000.0, f"input VAT on services {t}")
            else:
                r.expect(not any(k.startswith("Input VAT") for k in t), f"non-VAT buyer claimed input VAT {t}")
            state["prof"] = pi.name
            return f"{pi.name}: {t}"
        r.step(f"[{co}] professional fee bill with EWT", professional)

        def rental(co=co):
            pi = purchase_invoice(co, s_rent, [(rent, 1, 30000)])
            t = tax_rows(pi)
            r.expect(abs(t.get("Withholding Tax Payable - Expanded", 0)) == 1500, f"EWT 5% on rent {t}")
            return f"{pi.name}: {t}"
        r.step(f"[{co}] rent bill with 5% EWT", rental)

        def pay(co=co, state=state):
            if not state.get("prof"):
                raise Step("no bill to pay")
            pe = get_payment_entry("Purchase Invoice", state["prof"])
            pe.reference_no, pe.reference_date = "QA4-CHK-001", today()
            pe.insert()
            pe.submit()
            out = frappe.db.get_value("Purchase Invoice", state["prof"], "outstanding_amount")
            r.expect(flt(out) == 0, f"outstanding {out}")
            return f"{pe.name} paid {pe.paid_amount}"
        r.step(f"[{co}] pay the professional fee", pay)

    def certs():
        from ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued import generate_quarter
        from ph_cas.tax.returns import quarter_bounds

        qs, _qe = quarter_bounds(today())
        names = generate_quarter(VAT_CORP, str(qs))
        r.expect(names, "no 2307 generated or refreshed")
        doc = frappe.get_doc("PH 2307 Issued", names[0])
        r.expect(flt(doc.total_tax) > 0, f"2307 total tax {doc.total_tax}")
        return f"{len(names)} certificates; first {doc.name}: income {doc.total_income}, tax {doc.total_tax}"
    r.step(f"[{VAT_CORP}] 2307s issued for the quarter", certs)

    def back_dated():
        return refused(purchase_invoice, VAT_CORP, s_prof, [(service, 1, 1000)], posting_date=add_days(today(), -40), set_posting_time=1)
    r.step("a back-dated bill without a reason is refused", back_dated)


# ---- section: sales -----------------------------------------------------------------------------
def s_sales(r: Runner):
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

    _s_goods, _s_prof, _s_rent, c_vat, c_walkin, c_gov = _parties()
    vatable, exempt, zero = item("QA4 Repair Service"), item("QA4 Books", "VAT-exempt", group="Products"), item("QA4 Export Service", "Zero-rated")

    for co in (VAT_CO, VAT_CORP, NONVAT_IND, NONVAT_CORP):
        vat = frappe.get_cached_value("Company", co, "ph_vat_status") == "VAT"
        state = {}

        def invoice(co=co, vat=vat, state=state):
            lines = [(vatable, 2, 5600), (exempt, 3, 500)] + ([(zero, 1, 10000)] if vat else [])
            si = sales_invoice(co, c_vat, lines)
            t = tax_rows(si)
            serial = si.get("bir_serial") or ""
            r.expect(len(serial) == 8 and serial.isdigit(), f"BIR serial {serial!r}")
            if vat:
                r.expect(abs(t.get("Output VAT", 0) - 1344) < 0.01 or abs(t.get("Output VAT", 0) - 1200) < 0.01, f"output VAT {t}")
            else:
                r.expect("Output VAT" not in t, f"non-VAT seller charged VAT {t}")
            state["si"] = si.name
            return f"{si.name} serial {serial} total {si.grand_total} taxes {t}"
        r.step(f"[{co}] sales invoice (VATable, exempt{', zero-rated' if vat else ''})", invoice)

        def serial_continues(co=co, state=state):
            a = frappe.db.get_value("Sales Invoice", state["si"], "bir_serial")
            b = sales_invoice(co, c_walkin, [(vatable, 1, 1120)]).bir_serial
            r.expect(int(b) == int(a) + 1, f"{a} then {b}")
            return f"{a} -> {b}"
        r.step(f"[{co}] the next invoice takes the next serial", serial_continues)

        def manual_no_unique(co=co, state=state):
            used = frappe.db.get_value("Sales Invoice", state["si"], "ph_manual_invoice_no")
            return refused(sales_invoice, co, c_walkin, [(vatable, 1, 100)], manual=used)
        r.step(f"[{co}] a manual invoice number cannot be used twice", manual_no_unique)

        def no_cancel(co=co, state=state):
            return refused(frappe.get_doc("Sales Invoice", state["si"]).cancel)
        r.step(f"[{co}] an issued invoice cannot be cancelled", no_cancel)

        def no_edit(co=co, state=state):
            doc = frappe.get_doc("Sales Invoice", state["si"])
            doc.posting_date = add_days(doc.posting_date, -1)
            return refused(doc.save)
        r.step(f"[{co}] a posted invoice's date cannot be changed", no_edit)

        def credit_note(co=co, state=state):
            cn = make_sales_return(state["si"])
            cn.items = cn.items[:1]
            cn.items[0].qty = -1
            cn.ph_manual_invoice_no = "QA4-CN-" + frappe.generate_hash(length=5).upper()
            cn.insert()
            cn.submit()
            r.expect(cn.is_return and cn.get("bir_serial"), "no credit note serial")
            return f"{cn.name} serial {cn.bir_serial} total {cn.grand_total}"
        r.step(f"[{co}] credit note for one line", credit_note)

        def debit_note(co=co, state=state):
            dn = sales_invoice(co, c_vat, [(vatable, 1, 560)], is_debit_note=1, return_against=state["si"], submit=False)
            dn.submit()
            r.expect(dn.get("bir_serial"), "no debit note serial")
            return f"{dn.name} serial {dn.bir_serial}"
        r.step(f"[{co}] debit note", debit_note)

        def collect(co=co, state=state):
            pe = get_payment_entry("Sales Invoice", state["si"])
            pe.reference_no, pe.reference_date = "QA4-OR-001", today()
            pe.insert()
            pe.submit()
            return f"{pe.name} received {pe.paid_amount}; receipt serial {pe.get('bir_serial') or '-'}"
        r.step(f"[{co}] collection (payment entry / collection receipt)", collect)

        if co in (VAT_CO, VAT_CORP):
            def sc_pwd(co=co):
                si = sales_invoice(co, c_walkin, [(vatable, 1, 1120)], ph_sc_pwd_applied=1, ph_sc_pwd_type="Senior Citizen", ph_sc_pwd_name="Lola Basyang", ph_sc_pwd_id="OSCA-12345")
                t = tax_rows(si)
                r.expect("Output VAT" not in t and flt(si.ph_sc_pwd_discount) > 0, f"SC sale {t}, discount {si.ph_sc_pwd_discount}")
                return f"{si.name}: gross {si.ph_sc_pwd_gross}, discount {si.ph_sc_pwd_discount}, total {si.grand_total}"
            r.step(f"[{co}] senior citizen sale (VAT-exempt, 20%)", sc_pwd)

        def back_dated(co=co):
            return refused(sales_invoice, co, c_walkin, [(vatable, 1, 100)], posting_date=add_days(today(), -3), set_posting_time=1)
        r.step(f"[{co}] a back-dated invoice is refused", back_dated)

    def gov_sale():
        si = sales_invoice(VAT_CORP, c_gov, [(vatable, 1, 112000)])
        return f"{si.name}: taxes {tax_rows(si)}"
    r.step(f"[{VAT_CORP}] sale to a government office", gov_sale)

    def received_2307():
        from ph_cas.tax.returns import quarter_bounds

        qs, qe = quarter_bounds(today())
        d = frappe.get_doc({"doctype": "PH 2307 Received", "company": VAT_CORP, "customer": c_vat, "period_from": qs, "period_to": qe,
                            "lines": [{"atc": "WC160", "kind": "Income tax", "month_1": 10000, "tax_withheld": 200}]})
        d.insert()
        d.submit()
        return f"{d.name} tax {d.total_tax}"
    r.step(f"[{VAT_CORP}] 2307 received from a customer", received_2307)

    def books():
        out = []
        for rep in ("PH Sales Journal", "PH Purchase Journal", "PH Cash Receipts Book", "PH Cash Disbursements Book", "PH General Journal", "PH General Ledger Book"):
            from frappe.desk.query_report import run

            res = run(rep, filters={"company": VAT_CORP, "from_date": f"{getdate(today()).year}-01-01", "to_date": today()})
            out.append(f"{rep.replace('PH ', '')}: {len(res.get('result') or [])}")
        return "; ".join(out)
    r.step(f"[{VAT_CORP}] the six books run", books)

    def audit_trail():
        from frappe.desk.query_report import run

        res = run("BIR Audit Trail", filters={"from_date": today(), "to_date": today()})
        n = len(res.get("result") or [])
        r.expect(n > 0, "empty audit trail")
        return f"{n} rows today"
    r.step("audit trail report", audit_trail)


# ---- section: tasks -----------------------------------------------------------------------------
def s_tasks(r: Runner):
    from frappe.desk.form.assign_to import add as assign

    def todo_assign():
        user = frappe.session.user
        si = frappe.get_all("Sales Invoice", filters={"company": VAT_CORP, "docstatus": 1}, pluck="name", limit=1)
        r.expect(si, "no invoice to assign")
        assign({"assign_to": [user], "doctype": "Sales Invoice", "name": si[0], "description": "QA4: follow up the collection", "date": add_days(today(), 2)})
        todo = frappe.get_all("ToDo", filters={"reference_type": "Sales Invoice", "reference_name": si[0], "allocated_to": user, "status": "Open"}, pluck="name")
        r.expect(todo, "no ToDo made")
        return f"ToDo {todo[0]} on {si[0]}"
    r.step("assign a document to a user (ToDo)", todo_assign)

    def project_task():
        p = ensure("Project", "QA4 Office Fit-out", {"project_name": "QA4 Office Fit-out", "company": VAT_CORP, "expected_start_date": today(), "expected_end_date": add_days(today(), 60)}) \
            if not frappe.db.exists("Project", {"project_name": "QA4 Office Fit-out"}) else frappe.db.get_value("Project", {"project_name": "QA4 Office Fit-out"}, "name")
        t = frappe.get_doc({"doctype": "Task", "subject": "QA4 Prepare the bill of quantities", "project": p, "exp_start_date": today(), "exp_end_date": add_days(today(), 5), "priority": "High"})
        t.insert()
        assign({"assign_to": [frappe.session.user], "doctype": "Task", "name": t.name, "description": t.subject})
        t.reload()
        r.expect(frappe.session.user in (t.get("_assign") or ""), f"assigned {t.get('_assign')}")
        t.status = "Completed"
        t.completed_on = today()
        t.save()
        return f"{t.name} in {p}, assigned and completed"
    r.step("project task: create, assign, complete", project_task)

    def standalone_task():
        t = frappe.get_doc({"doctype": "Task", "subject": "QA4 File the 2550Q", "exp_end_date": add_days(today(), 7), "priority": "Urgent"})
        t.insert()
        assign({"assign_to": [frappe.session.user], "doctype": "Task", "name": t.name, "description": t.subject})
        return t.name
    r.step("standalone task with assignment", standalone_task)


# ---- section: inventory -------------------------------------------------------------------------
def s_inventory(r: Runner):
    co = VAT_CO
    hammer = item("QA4-HAMMER", stock=1, item_name="Claw Hammer 16oz", valuation_rate=250)
    nails = item("QA4-NAILS", stock=1, item_name="Common Nails 2in (kg)", valuation_rate=80)
    wh, wh2 = acc(co, "Stores"), None

    def second_wh():
        name = acc(co, "Showroom")
        if not frappe.db.exists("Warehouse", name):
            frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Showroom", "company": co, "parent_warehouse": acc(co, "All Warehouses")}).insert()
        return name
    wh2 = r.step("second warehouse", second_wh) or wh

    def receipt():
        se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": co,
                             "items": [{"item_code": nails, "qty": 50, "basic_rate": 80, "t_warehouse": wh}, {"item_code": hammer, "qty": 20, "basic_rate": 250, "t_warehouse": wh}]})
        se.insert()
        se.submit()
        return se.name
    r.step("material receipt", receipt)

    def transfer():
        se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Transfer", "company": co,
                             "items": [{"item_code": hammer, "qty": 5, "s_warehouse": wh, "t_warehouse": wh2}]})
        se.insert()
        se.submit()
        q = frappe.db.get_value("Bin", {"item_code": hammer, "warehouse": wh2}, "actual_qty")
        r.expect(flt(q) >= 5, f"showroom {q}")
        return f"{se.name}; showroom {q}"
    r.step("transfer between warehouses", transfer)

    def sell_from_stock():
        _p = _parties()
        si = sales_invoice(co, _p[4], [(hammer, 2, 450, {"warehouse": wh2})], update_stock=1)
        sle = frappe.get_all("Stock Ledger Entry", filters={"voucher_no": si.name, "is_cancelled": 0}, fields=["actual_qty"])
        r.expect(sle and flt(sle[0].actual_qty) == -2, f"stock ledger {sle}")
        g = gl("Sales Invoice", si.name)
        return f"{si.name} stock -2; GL {g}"
    r.step("invoice that ships from stock (update stock)", sell_from_stock)

    def delivery_note():
        from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

        _p = _parties()
        dn = frappe.get_doc({"doctype": "Delivery Note", "company": co, "customer": _p[3], "set_warehouse": wh, "items": [{"item_code": nails, "qty": 10, "rate": 120, "warehouse": wh}]})
        dn.insert()
        dn.submit()
        si = submit_mapped(make_sales_invoice(dn.name))
        return f"{dn.name} -> {si.name} serial {si.bir_serial}"
    r.step("delivery note then invoice", delivery_note)

    def reconcile():
        sr = frappe.get_doc({"doctype": "Stock Reconciliation", "company": co, "purpose": "Stock Reconciliation",
                             "items": [{"item_code": nails, "warehouse": wh, "qty": 38, "valuation_rate": 80}]})
        sr.insert()
        sr.submit()
        return sr.name
    r.step("stock count (reconciliation)", reconcile)


    def method_locked():
        c = frappe.get_doc("Company", co)
        c.ph_inventory_method = "Perpetual"
        return refused(c.save)
    r.step("D7: the inventory method cannot change after stock moved", method_locked)

    def no_backdate():
        se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": co, "posting_date": add_days(today(), -5), "set_posting_time": 1,
                             "items": [{"item_code": nails, "qty": 1, "basic_rate": 80, "t_warehouse": wh}]})
        return refused(lambda: (se.insert(), se.submit()))
    r.step("D7: a back-dated stock entry is refused", no_backdate)

    def perpetual_off():
        r.expect(not frappe.get_cached_value("Company", co, "enable_perpetual_inventory"), "perpetual inventory is on for a periodic company")
        se = frappe.get_all("Stock Entry", filters={"company": co, "docstatus": 1}, pluck="name", limit=1)
        g = gl("Stock Entry", se[0]) if se else {}
        r.expect(not g, f"stock entry posted to the ledger {g}")
        return "no GL rows for stock entries"
    r.step("periodic: stock entries post nothing to the ledger", perpetual_off)

    def reports():
        from frappe.desk.query_report import run

        led = run("Stock Ledger", filters={"company": co, "from_date": f"{getdate(today()).year}-01-01", "to_date": today(), "valuation_field_type": "Currency"})
        inv = run("PH Inventory Book", filters={"company": co, "from_date": f"{getdate(today()).year}-01-01", "to_date": today()})
        n_led, n_inv = len(led.get("result") or []), len(inv.get("result") or [])
        r.expect(n_led and n_inv, f"stock ledger {n_led}, inventory book {n_inv}")
        return f"stock ledger {n_led} rows; inventory book {n_inv} rows"
    r.step("stock ledger and inventory book", reports)


# ---- section: projects --------------------------------------------------------------------------
def s_projects(r: Runner):
    co = VAT_CORP
    _p = _parties()
    svc = item("QA4 Construction Services")

    def project():
        name = frappe.db.get_value("Project", {"project_name": "QA4 Warehouse Build"}, "name")
        if not name:
            p = frappe.get_doc({"doctype": "Project", "project_name": "QA4 Warehouse Build", "company": co, "customer": _p[3], "expected_start_date": today(),
                                "expected_end_date": add_days(today(), 120), "estimated_costing": 2000000})
            p.insert()
            name = p.name
        for i, subj in enumerate(("Site preparation", "Foundation", "Roofing")):
            if not frappe.db.exists("Task", {"project": name, "subject": f"QA4 {subj}"}):
                frappe.get_doc({"doctype": "Task", "project": name, "subject": f"QA4 {subj}", "exp_start_date": add_days(today(), i * 30), "exp_end_date": add_days(today(), i * 30 + 25)}).insert()
        return name
    proj = r.step("project with three tasks", project)

    def timesheet():
        act = ensure("Activity Type", "QA4 Site Work", {"activity_type": "QA4 Site Work", "billing_rate": 1500, "costing_rate": 800})
        ts = frappe.get_doc({"doctype": "Timesheet", "company": co, "customer": _p[3], "parent_project": proj,
                             "time_logs": [{"activity_type": act, "from_time": f"{today()} 08:00:00", "to_time": f"{today()} 16:00:00", "hours": 8, "project": proj,
                                            "is_billable": 1, "billing_hours": 8, "billing_rate": 1500, "costing_rate": 800}]})
        ts.insert()
        ts.submit()
        return f"{ts.name}: billable {ts.total_billable_amount}"
    ts = r.step("timesheet with billable hours", timesheet)

    def bill_timesheet():
        from erpnext.projects.doctype.timesheet.timesheet import make_sales_invoice

        name = frappe.get_all("Timesheet", filters={"parent_project": proj, "docstatus": 1, "status": ("!=", "Billed")}, pluck="name", limit=1)
        r.expect(name, "no timesheet to bill")
        si = make_sales_invoice(name[0], item_code=svc, customer=_p[3])
        si.company = co
        si.debit_to = acc(co, "Debtors")
        for row in si.items:
            row.income_account, row.cost_center = acc(co, "Sales"), acc(co, "Main")
        si = submit_mapped(si)
        return f"{si.name} total {si.grand_total} taxes {tax_rows(si)}"
    r.step("bill the timesheet", bill_timesheet)

    def progress_billing():
        si = sales_invoice(co, _p[3], [(svc, 1, 500000)], project=proj)
        return f"{si.name} 25% progress billing, taxes {tax_rows(si)}"
    r.step("progress billing on the project", progress_billing)

    def costing():
        pi = purchase_invoice(co, _p[0], [(item("QA4 Cement (bags)", group="Products"), 100, 280, {"project": proj})], )
        p = frappe.get_doc("Project", proj)
        p.update_costing() if hasattr(p, "update_costing") else None
        return f"{pi.name}; project billed {frappe.db.get_value('Project', proj, 'total_billed_amount')}, purchase cost {frappe.db.get_value('Project', proj, 'total_purchase_cost')}"
    r.step("project purchase cost and billing totals", costing)


# ---- section: assets ----------------------------------------------------------------------------
def s_assets(r: Runner):
    co = VAT_CORP
    _p = _parties()

    def category():
        if not frappe.db.exists("Asset Category", "QA4 Construction Equipment"):
            frappe.get_doc({"doctype": "Asset Category", "asset_category_name": "QA4 Construction Equipment",
                            "finance_books": [{"depreciation_method": "Straight Line", "total_number_of_depreciations": 60, "frequency_of_depreciation": 1}],
                            "accounts": [{"company_name": co, "fixed_asset_account": _fixed_asset_account(co), "accumulated_depreciation_account": acc(co, "Accumulated Depreciation"),
                                          "depreciation_expense_account": acc(co, "Depreciation")}]}).insert()
        return "QA4 Construction Equipment"
    cat = r.step("asset category with accounts and straight-line depreciation", category)

    def buy_asset():
        code = item("QA4 Concrete Mixer", group="Products", is_fixed_asset=1, asset_category=cat, ph_is_capital_good=1, auto_create_assets=1, asset_naming_series="ACC-ASS-.YYYY.-", is_stock_item=0)
        it = frappe.get_doc("Item", code)
        if not it.auto_create_assets or not it.get("asset_naming_series"):
            it.auto_create_assets = 1
            it.asset_naming_series = "ACC-ASS-.YYYY.-"
            it.save()
        pi = purchase_invoice(co, _p[0], [(code, 1, 1200000, {"asset_location": _location(), "expense_account": _fixed_asset_account(co)})], update_stock=1)
        t = tax_rows(pi)
        r.expect(abs(t.get("Input VAT - Capital Goods", 0) - 144000) < 0.01, f"input VAT on capital goods {t}")
        assets = frappe.get_all("Asset", filters={"purchase_invoice": pi.name}, pluck="name")
        r.expect(assets, "the bill made no asset")
        return {"pi": pi.name, "taxes": t, "assets": assets}
    bought = r.step("buy a capital good (input VAT on capital goods)", buy_asset)

    def submit_asset():
        names = (bought or {}).get("assets") or []
        r.expect(names, "no asset from the purchase")
        a = frappe.get_doc("Asset", names[0])
        a.location = a.location or _location()
        a.available_for_use_date = today()
        a.calculate_depreciation = 1
        if not a.get("finance_books"):
            a.append("finance_books", {"depreciation_method": "Straight Line", "total_number_of_depreciations": 60, "frequency_of_depreciation": 1,
                                       "depreciation_start_date": frappe.utils.get_last_day(today())})
        a.save()
        a.submit()
        sched = frappe.get_all("Asset Depreciation Schedule", filters={"asset": a.name, "docstatus": 1}, pluck="name")
        r.expect(sched, "no depreciation schedule")
        return f"{a.name} submitted; schedule {sched[0]}"
    r.step("submit the asset with a depreciation schedule", submit_asset)

    def opening_asset():
        a = frappe.get_doc({"doctype": "Asset", "company": co, "item_code": item("QA4 Service Vehicle", group="Products", is_fixed_asset=1, asset_category=cat),
                            "asset_name": "QA4 Service Vehicle", "location": _location(), "is_existing_asset": 1, "gross_purchase_amount": 900000, "net_purchase_amount": 900000,
                            "purchase_date": "2024-01-15", "available_for_use_date": "2024-01-15", "calculate_depreciation": 0})
        a.insert()
        a.submit()
        return a.name
    r.step("existing (opening) asset", opening_asset)

    def reports():
        from frappe.desk.query_report import run

        res = run("Fixed Asset Register", filters={"company": co, "status": "In Location", "filter_based_on": "Date Range", "from_date": f"{getdate(today()).year}-01-01", "to_date": today()})
        return f"register {len(res.get('result') or [])} rows"
    r.step("fixed asset register", reports)


def _fixed_asset_account(co):
    name = frappe.db.get_value("Account", {"company": co, "account_type": "Fixed Asset", "is_group": 0}, "name")
    return name or acc(co, "Plants and Machineries")


def _location():
    return ensure("Location", "QA4 Main Yard", {"location_name": "QA4 Main Yard"})


# ---- section: quality ---------------------------------------------------------------------------
def s_quality(r: Runner):
    def goal_and_procedure():
        proc = ensure("Quality Procedure", "QA4 Receiving Inspection", {"quality_procedure_name": "QA4 Receiving Inspection", "processes": [{"process_description": "Check quantity and damage on every delivery"}]})
        goal = ensure("Quality Goal", "QA4 Zero damaged deliveries", {"goal": "QA4 Zero damaged deliveries", "procedure": proc, "frequency": "Monthly",
                                                                        "objectives": [{"objective": "Damaged items per delivery", "target": "0", "uom": "Nos"}]})
        return f"{proc} / {goal}"
    r.step("quality procedure and goal", goal_and_procedure)

    def inspection():
        param = ensure("Quality Inspection Parameter", "QA4 Visual", {"parameter": "QA4 Visual"})
        tmpl = ensure("Quality Inspection Template", "QA4 Hardware Check", {"quality_inspection_template_name": "QA4 Hardware Check",
                                                                           "item_quality_inspection_parameter": [{"specification": param, "numeric": 0, "value": "No damage"}]})
        code = item("QA4-HELMET", stock=1, item_name="Safety Helmet", valuation_rate=300, inspection_required_before_purchase=1, quality_inspection_template=tmpl)
        co = VAT_CORP
        prd = frappe.get_doc({"doctype": "Purchase Receipt", "company": co, "supplier": _parties()[0], "set_warehouse": acc(co, "Stores"),
                              "items": [{"item_code": code, "qty": 20, "rate": 300, "warehouse": acc(co, "Stores")}]})
        prd.insert()
        r.expect(refused(prd.submit), "receipt went in without the inspection")
        qi = frappe.get_doc({"doctype": "Quality Inspection", "inspection_type": "Incoming", "reference_type": "Purchase Receipt", "reference_name": prd.name,
                             "item_code": prd.items[0].item_code, "sample_size": 5, "inspected_by": frappe.session.user, "quality_inspection_template": tmpl,
                             "readings": [{"specification": param, "numeric": 0, "value": "No damage", "status": "Accepted"}], "status": "Accepted", "manual_inspection": 1})
        qi.insert()
        qi.submit()
        prd.reload()
        prd.items[0].quality_inspection = qi.name
        prd.save()
        prd.submit()
        return f"{qi.name} {qi.status}; {prd.name} received after inspection"
    r.step("incoming quality inspection on a receipt", inspection)

    def non_conformance():
        proc = "QA4 Receiving Inspection"
        nc = frappe.get_doc({"doctype": "Non Conformance", "subject": "QA4 Bent hammers in delivery", "procedure": proc, "status": "Open", "details": "3 of 100 bent", "corrective_action": "Return to supplier", "preventive_action": "Inspect at receiving"})
        nc.insert()
        action = frappe.get_doc({"doctype": "Quality Action", "corrective_preventive": "Corrective", "procedure": proc, "status": "Open",
                                 "resolutions": [{"problem": "Bent hammers", "resolution": "Debit memo to supplier", "status": "Completed"}]})
        action.insert()
        meeting = frappe.get_doc({"doctype": "Quality Meeting", "status": "Open", "minutes": [{"document_type": "Quality Action", "document_name": action.name, "minute": "Agreed to inspect every delivery"}]})
        meeting.insert()
        return f"{nc.name}, {action.name}, {meeting.name}"
    r.step("non-conformance, corrective action and meeting", non_conformance)

    def review():
        rv = frappe.get_doc({"doctype": "Quality Review", "goal": "QA4 Zero damaged deliveries", "date": today(), "reviews": [{"objective": "Damaged items per delivery", "target": "0", "achieved": "3", "status": "Failed"}]})
        rv.insert()
        return f"{rv.name} {rv.status}"
    r.step("quality review", review)


# ---- section: crm -------------------------------------------------------------------------------
def s_crm(r: Runner):
    co = VAT_CORP
    state = {}

    def lead():
        name = frappe.db.get_value("Lead", {"email_id": "qa4.lead@example.com"}, "name")
        if not name:
            ld = frappe.get_doc({"doctype": "Lead", "first_name": "Carmen", "last_name": "Villanueva", "company_name": "QA4 Villanueva Foods Inc.", "email_id": "qa4.lead@example.com",
                                 "mobile_no": "09170000001", "source": "Advertisement", "company": co})
            ld.insert()
            name = ld.name
        state["lead"] = name
        return name
    r.step("lead", lead)

    def opportunity():
        from erpnext.crm.doctype.lead.lead import make_opportunity

        op = make_opportunity(state["lead"])
        op.company = co
        op.opportunity_amount = 350000
        op.append("items", {"item_code": item("QA4 Repair Service"), "qty": 1, "rate": 350000})
        op.insert()
        state["opp"] = op.name
        return op.name
    r.step("opportunity from the lead", opportunity)

    def quotation():
        from erpnext.crm.doctype.opportunity.opportunity import make_quotation

        q = make_quotation(state["opp"])
        q.company = co
        q.valid_till = add_days(today(), 30)
        q.insert()
        q.submit()
        state["quote"] = q.name
        return f"{q.name} {q.grand_total}"
    r.step("quotation from the opportunity", quotation)

    def won():
        from erpnext.selling.doctype.quotation.quotation import make_sales_order

        so = make_sales_order(state["quote"])
        so.delivery_date = add_days(today(), 14)
        so.insert()
        so.submit()
        state["so"] = so.name
        cust = so.customer
        r.expect(frappe.db.exists("Customer", cust), "no customer")
        c = frappe.get_doc("Customer", cust)
        c.update({"ph_tin": "000-906-010", "ph_branch_code": "00000", "ph_vat_status": "VAT", "ph_registered_name": "QA4 VILLANUEVA FOODS INC.",
                  "ph_address_line1": "45 Commonwealth Avenue, Quezon City", "ph_zip": "1121"})
        c.save()
        return f"{so.name} for {cust}"
    r.step("sales order from the quotation (lead becomes a customer)", won)

    def bill_order():
        from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

        si = make_sales_invoice(state["so"])
        si = submit_mapped(si)
        return f"{si.name} serial {si.bir_serial} taxes {tax_rows(si)}"
    r.step("invoice the sales order", bill_order)

    def campaign():
        return ensure("Campaign", "QA4 Year-end Promo", {"campaign_name": "QA4 Year-end Promo"})
    r.step("campaign", campaign)


# ---- section: support ---------------------------------------------------------------------------
def s_support(r: Runner):
    _p = _parties()

    def issue():
        iss = frappe.get_doc({"doctype": "Issue", "subject": "QA4 Invoice printed without the ATP", "raised_by": "qa4.customer@example.com", "customer": _p[3], "company": VAT_CORP,
                              "priority": "High" if frappe.db.exists("Issue Priority", "High") else None, "description": "The duplicate copy had no ATP line."})
        iss.insert()
        iss.status = "Replied"
        iss.save()
        iss.status = "Resolved"
        iss.resolution_details = "Collection receipt ATP added on the Company."
        iss.save()
        iss.status = "Closed"
        iss.save()
        return f"{iss.name} closed"
    r.step("issue: open, reply, resolve, close", issue)

    def warranty():
        wc = frappe.get_doc({"doctype": "Warranty Claim", "customer": _p[3], "complaint_date": today(), "item_code": "QA4-HAMMER", "complaint": "Handle cracked", "status": "Open", "company": VAT_CO})
        wc.insert()
        return wc.name
    r.step("warranty claim", warranty)

    def maintenance():
        ms = frappe.get_doc({"doctype": "Maintenance Visit", "customer": _p[3], "company": VAT_CO, "mntc_date": today(), "maintenance_type": "Breakdown", "completion_status": "Fully Completed",
                             "purposes": [{"item_code": "QA4-HAMMER", "service_person": _sales_person(), "description": "Replaced handle", "work_done": "Replaced handle"}]})
        ms.insert()
        ms.submit()
        return ms.name
    r.step("maintenance visit", maintenance)


def _sales_person():
    return ensure("Sales Person", "QA4 Technician", {"sales_person_name": "QA4 Technician", "parent_sales_person": "Sales Team" if frappe.db.exists("Sales Person", "Sales Team") else ""})


# ---- section: industries ------------------------------------------------------------------------
def s_industries(r: Runner):
    from ph_cas.modules import api as modules

    before = modules.modules_on()
    for industry, mods in modules.presets().items():
        def preset(industry=industry, mods=mods):
            got = modules.apply_preset(industry)
            on = sorted(k for k, v in got.items() if v)
            r.expect(set(mods) <= set(on), f"{industry}: on {on}, expected {mods}")
            return f"on: {', '.join(on)}"
        r.step(f"preset: {industry}", preset)
    r.step("all modules back on", lambda: sorted(k for k, v in modules.set_modules(before or [m["key"] for m in modules.catalogue()]).items() if v))

    _p = _parties()

    def restaurant():
        food = item("QA4 Chicken Adobo Meal", group="Products")
        si = sales_invoice(VAT_CO, _p[4], [(food, 4, 168)])
        sc = sales_invoice(VAT_CO, _p[4], [(food, 2, 168)], ph_sc_pwd_applied=1, ph_sc_pwd_type="PWD", ph_sc_pwd_name="Juan Dela Cruz", ph_sc_pwd_id="PWD-0001")
        return f"dine-in {si.name} {si.grand_total}; PWD {sc.name} {sc.grand_total}"
    r.step("restaurant: meals, with a PWD discount", restaurant)

    def end_of_day():
        from ph_cas.invoicing.rules import make_end_of_day_invoice

        c = frappe.get_doc("Company", VAT_CO)
        if not c.get("ph_walkin_customer"):
            c.ph_walkin_customer = _p[4]
            c.save()
        out = make_end_of_day_invoice(VAT_CO, today(), vatable=1500, exempt=200)
        return str(out)
    r.step("retail: end-of-day invoice for sales below the threshold", end_of_day)

    def manufacturing():
        from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

        co = VAT_CO
        flour = item("QA4 Flour (kg)", stock=1, group="Products", valuation_rate=50)
        bread = item("QA4 Pandesal (pack)", stock=1, group="Products", valuation_rate=0)
        se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": co, "items": [{"item_code": flour, "qty": 100, "basic_rate": 50, "t_warehouse": acc(co, "Stores")}]})
        se.insert()
        se.submit()
        bom = frappe.db.get_value("BOM", {"item": bread, "is_active": 1, "is_default": 1, "docstatus": 1}, "name")
        if not bom:
            b = frappe.get_doc({"doctype": "BOM", "item": bread, "company": co, "quantity": 10, "items": [{"item_code": flour, "qty": 2, "rate": 50}]})
            b.insert()
            b.submit()
            bom = b.name
        wo = frappe.get_doc({"doctype": "Work Order", "production_item": bread, "bom_no": bom, "qty": 10, "company": co, "wip_warehouse": acc(co, "Work In Progress"),
                             "fg_warehouse": acc(co, "Finished Goods"), "source_warehouse": acc(co, "Stores"), "planned_start_date": f"{today()} 08:00:00", "skip_transfer": 1})
        wo.insert()
        wo.submit()
        m = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 10))
        m.insert()
        m.submit()
        q = frappe.db.get_value("Bin", {"item_code": bread, "warehouse": acc(co, "Finished Goods")}, "actual_qty")
        r.expect(flt(q) >= 10, f"finished goods {q}")
        return f"BOM {bom}, {wo.name}, manufacture {m.name}, finished {q}"
    r.step("manufacturing: BOM, work order, manufacture", manufacturing)

    def professional():
        fee = item("QA4 Audit Engagement Fee")
        si = sales_invoice(VAT_CORP, _p[3], [(fee, 1, 150000)])
        return f"{si.name} {si.grand_total} taxes {tax_rows(si)}"
    r.step("professional practice: fee to a top withholding agent", professional)

    def services_export():
        exp = item("QA4 Export Service", "Zero-rated")
        foreign = customer("QA4 Pacific Holdings Pte Ltd", ph_vat_status="Non-VAT", ph_registered_name="QA4 PACIFIC HOLDINGS PTE LTD")
        si = sales_invoice(VAT_CORP, foreign, [(exp, 1, 300000)])
        r.expect("Output VAT" not in tax_rows(si), f"export charged VAT {tax_rows(si)}")
        return f"{si.name} zero-rated {si.grand_total}"
    r.step("services: zero-rated export", services_export)

    def travel_nonvat():
        tour = item("QA4 Tour Package")
        si = sales_invoice(NONVAT_CORP, _p[4], [(tour, 2, 18000)])
        r.expect("Output VAT" not in tax_rows(si), "non-VAT charged VAT")
        return f"{si.name} {si.grand_total} (percentage tax seller)"
    r.step("travel agency (non-VAT corporation)", travel_nonvat)


# ---- section: forms -----------------------------------------------------------------------------
def s_forms(r: Runner):
    from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import new_return
    from ph_cas.tax.returns import quarter_bounds

    y = getdate(today()).year
    qs, _qe = quarter_bounds(today())
    q_now = (getdate(qs).month - 1) // 3 + 1
    m_now = getdate(today()).month
    last_q = q_now - 1 if q_now > 1 else 1
    plan = []
    corp_vat = "Tala Trading Corporation" if frappe.db.exists("Company", "Tala Trading Corporation") else VAT_CORP
    for co in [corp_vat, VAT_CORP, VAT_CO]:
        plan += [(co, "2550Q", f"{y}-Q{q_now}"), (co, "0619-E", f"{y}-{m_now - 1:02d}" if m_now > 1 else f"{y}-01"), (co, "1601-EQ", f"{y}-Q{q_now}"),
                 (co, "1600-VT", f"{y}-{m_now:02d}"), (co, "1604-E", f"{y}"), (co, "2307", f"{y}-Q{q_now}")]
    for co in [n for n in ("QA Corner Store", NONVAT_CORP, NONVAT_IND) if frappe.db.exists("Company", n)]:
        plan += [(co, "2551Q", f"{y}-Q{q_now}")]
    for co in [n for n in (corp_vat, VAT_CORP, NONVAT_CORP) if frappe.db.exists("Company", n)]:
        plan += [(co, "1702Q", f"{y}-Q{last_q}"), (co, "1702-RT", f"{y}")]
    for co in [n for n in ("QA Sole Proprietor", VAT_CO, NONVAT_IND) if frappe.db.exists("Company", n)]:
        plan += [(co, "1701Q", f"{y}-Q{last_q}"), (co, "1701", f"{y}"), (co, "1701A", f"{y}")]

    for co, form, key in plan:
        def build(co=co, form=form, key=key):
            name = new_return(co, form, key)
            doc = frappe.get_doc("PH Tax Return", name)
            doc.refresh_from_books()
            doc.reload()
            lines = frappe.get_all("PH Tax Return Line", filters={"parenttype": "PH Tax Return", "parent": name}, fields=["item", "amount"], order_by="idx")
            top = [f"{l.item}={flt(l.amount):,.2f}" for l in lines if flt(l.amount)][:5]
            needs = (doc.needs or "").strip()
            out = f"{name} [{doc.status}] {'; '.join(top)}"
            if needs and needs != "[]":
                out += f" | needs: {needs[:80]}"
            if (doc.warnings or "").strip():
                out += f" | warnings: {doc.warnings.strip()[:120]}"
            if form in ("1601-EQ", "1604-E"):
                try:
                    out += f" | attachment {doc.generate_attachment()}"
                except Exception as e:
                    out += f" | attachment: {_short(_msg(e), 80)}"
            if form in ("2550Q",):
                try:
                    s = doc.generate_slsp()
                    out += f" | SLSP {len(s.get('files') or [])} files, tie-out {s.get('tie_out')}"
                except Exception as e:
                    out += f" | SLSP: {_short(_msg(e), 80)}"
            if form in ("2550Q", "2551Q", "1702Q", "1701Q", "1702-RT", "1701"):
                try:
                    out += f" | SAWT {doc.generate_sawt()}"
                except Exception as e:
                    out += f" | SAWT: {_short(_msg(e), 60)}"
            if frappe.get_cached_doc("PH Tax Return", name) and form not in ("2307",):
                try:
                    exp = doc.export_for_ebirforms() if hasattr(doc, "export_for_ebirforms") else None
                    if exp:
                        out += " | export ok"
                except Exception as e:
                    out += f" | export: {_short(_msg(e), 60)}"
            return out
        r.step(f"{form} {key} {co}", build)


# ---- section: inventory tracking (periodic year-end, and perpetual) ------------------------------
PERIODIC_CO = "QA4 Dagat Trading Corp."
PERPETUAL_CO = "QA4 Mabuhay Trading Corp."


def _trading_company(name, ab, method, tin):
    from ph_cas.setup.chart import setup_philippine_company

    if not frappe.db.exists("Company", name):
        frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": ab, "default_currency": "PHP", "country": "Philippines", "chart_of_accounts": "Standard",
                        "ph_branch_code": "00000", "ph_rdo": "045", "ph_vat_status": "VAT", "ph_taxpayer_type": "Non-individual", "ph_inventory_method": method,
                        "tax_id": tin, "ph_registered_name": name.upper(), "ph_registered_address": "3 Ilaya Street\nBarangay San Nicolas, Manila",
                        "ph_zip": "1010", "ph_incorporation_date": "2021-03-01", "ph_contact_number": "0282001234", "ph_email": "qa.trading@example.com",
                        "ph_income_tax_option": "Corporate", "ph_deduction_method": "Itemized", "ph_taxpayer_class": "Small", "ph_primary_business": "Goods",
                        "ph_operations_start_year": 2021}).insert()
    setup_philippine_company(name)
    return frappe.get_doc("Company", name)


def s_inventory_tracking(r: Runner):
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
    from ph_cas.setup.chart import setup_philippine_company

    _p0 = _parties()
    tile = item("QA4-TILE", stock=1, item_name="Floor tile 60x60 (box)", valuation_rate=250)

    def periodic_year():
        from ph_cas.stock.periodic import book_value, counted_value, inventory_account, post_adjustment

        if frappe.db.exists("Company", PERIODIC_CO) and frappe.db.exists("Stock Ledger Entry", {"company": PERIODIC_CO, "is_cancelled": 0}):
            return "already run on this site (the hand figures hold for a fresh company only)"
        c = _trading_company(PERIODIC_CO, "Q4DT", "Periodic", "000-905-006")
        r.expect(not c.enable_perpetual_inventory, "periodic company has perpetual on")
        co, wh = PERIODIC_CO, acc(PERIODIC_CO, "Stores")
        cogs_acc = c.default_expense_account
        po = frappe.get_doc({"doctype": "Purchase Order", "company": co, "supplier": _p0[0], "transaction_date": today(), "schedule_date": today(), "set_warehouse": wh,
                             "items": [{"item_code": tile, "qty": 100, "rate": 250, "schedule_date": today(), "warehouse": wh}]})
        po.insert()
        po.submit()
        submit_mapped(make_purchase_invoice(submit_mapped(make_purchase_receipt(po.name)).name))
        r.expect(gl_balance(co, cogs_acc) == 25000, f"purchases to cost of sales {gl_balance(co, cogs_acc)}")
        sales_invoice(co, _p0[3], [(tile, 30, 400, {"warehouse": wh})], update_stock=1)
        # the year-end count: 68 boxes (2 broken)
        sr = frappe.get_doc({"doctype": "Stock Reconciliation", "company": co, "purpose": "Stock Reconciliation", "items": [{"item_code": tile, "warehouse": wh, "qty": 68, "valuation_rate": 250}]})
        sr.insert()
        sr.submit()
        out = post_adjustment(co, today())
        r.expect(out["counted"] == 17000 and out["adjustment"] == 17000 and out["journal_entry"], f"adjustment {out}")
        r.expect(book_value(co, inventory_account(co), today()) == 17000, "inventory account is not the count")
        cogs = gl_balance(co, cogs_acc)
        r.expect(cogs == 8000, f"cost of sales {cogs}, expected 0 + 25,000 - 17,000 = 8,000")
        r.expect(post_adjustment(co, today())["journal_entry"] is None, "a second run posted again")
        from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import new_return

        name = new_return(co, "1702-RT", str(getdate(today()).year))
        frappe.get_doc("PH Tax Return", name).refresh_from_books()
        rt = frappe.db.get_value("PH Tax Return Line", {"parenttype": "PH Tax Return", "parent": name, "item": "30"}, "amount")
        r.expect(flt(rt) == 8000, f"1702-RT item 30 cost of sales {rt}")
        return f"bought 100 x 250, sold 30, counted 68: {out['journal_entry']} Dr inventory 17,000 / Cr cost of sales; cost of sales 8,000 = 1702-RT item 30"
    r.step("periodic: year-end count, inventory adjustment, cost of sales on the 1702-RT", periodic_year)

    co = PERPETUAL_CO
    _p = _parties()
    rice = item("QA4-RICE25", stock=1, item_name="Rice 25kg sack", valuation_rate=1200)

    def company():
        if not frappe.db.exists("Company", co):
            frappe.get_doc({"doctype": "Company", "company_name": co, "abbr": "Q4MT", "default_currency": "PHP", "country": "Philippines", "chart_of_accounts": "Standard",
                            "ph_branch_code": "00000", "ph_rdo": "045", "ph_vat_status": "VAT", "ph_taxpayer_type": "Non-individual", "ph_inventory_method": "Perpetual",
                            "tax_id": "000-905-005", "ph_registered_name": "QA4 MABUHAY TRADING CORP.", "ph_registered_address": "3 Ilaya Street\nBarangay San Nicolas, Manila",
                            "ph_zip": "1010", "ph_incorporation_date": "2021-03-01", "ph_contact_number": "0282001234", "ph_email": "qa.mabuhay@example.com",
                            "ph_income_tax_option": "Corporate", "ph_deduction_method": "Itemized", "ph_taxpayer_class": "Small", "ph_primary_business": "Goods",
                            "ph_operations_start_year": 2021}).insert()
        setup_philippine_company(co)
        c = frappe.get_doc("Company", co)
        r.expect(c.enable_perpetual_inventory and c.ph_inventory_method == "Perpetual", "perpetual not on")
        r.expect(c.default_inventory_account and c.stock_received_but_not_billed and c.stock_adjustment_account,
                 f"accounts: inventory {c.default_inventory_account}, SRBNB {c.stock_received_but_not_billed}, adjustment {c.stock_adjustment_account}")
        return f"perpetual; inventory {c.default_inventory_account}"
    if not r.step("company with perpetual inventory (tracked)", company):
        return
    wh = acc(co, "Stores")
    inv_acc = frappe.get_cached_value("Company", co, "default_inventory_account")

    def receive_and_bill():
        po = frappe.get_doc({"doctype": "Purchase Order", "company": co, "supplier": _p[0], "transaction_date": today(), "schedule_date": today(), "set_warehouse": wh,
                             "items": [{"item_code": rice, "qty": 50, "rate": 1200, "schedule_date": today(), "warehouse": wh}]})
        po.insert()
        po.submit()
        pr = submit_mapped(make_purchase_receipt(po.name))
        g = gl("Purchase Receipt", pr.name)
        r.expect(g.get(inv_acc.rsplit(" - ", 1)[0]) == 60000, f"receipt GL {g}")
        pi = submit_mapped(make_purchase_invoice(pr.name))
        gp = gl("Purchase Invoice", pi.name)
        return f"{pr.name} GL {g}; {pi.name} GL {gp}"
    r.step("receipt posts stock in hand; the bill clears stock received not billed", receive_and_bill)

    def sell():
        si = sales_invoice(co, _p[3], [(rice, 10, 1500, {"warehouse": wh})], update_stock=1)
        g = gl("Sales Invoice", si.name)
        r.expect(g.get("Cost of Goods Sold") == 12000 and g.get(inv_acc.rsplit(" - ", 1)[0]) == -12000, f"sale GL {g}")
        return f"{si.name} GL {g}"
    r.step("a sale from stock posts cost of sales at valuation", sell)

    def year_end_count():
        q = flt(frappe.db.get_value("Bin", {"item_code": rice, "warehouse": wh}, "actual_qty"))
        sr = frappe.get_doc({"doctype": "Stock Reconciliation", "company": co, "purpose": "Stock Reconciliation",
                             "items": [{"item_code": rice, "warehouse": wh, "qty": q - 2, "valuation_rate": 1200}]})
        sr.insert()
        sr.submit()
        g = gl("Stock Reconciliation", sr.name)
        r.expect(g.get("Stock Adjustment") == 2400 and g.get(inv_acc.rsplit(" - ", 1)[0]) == -2400, f"count GL {g}")
        return f"{sr.name}: 2 sacks short, GL {g}"
    r.step("year-end count posts the shortage to stock adjustment", year_end_count)

    def ties():
        from ph_cas.stock.periodic import counted_value

        books, stock = gl_balance(co, inv_acc), counted_value(co, today())
        r.expect(abs(books - stock) < 0.01, f"stock in hand {books} vs stock value {stock}")
        from frappe.desk.query_report import run

        res = run("Stock and Account Value Comparison", filters={"company": co, "as_on_date": today()})
        rows = [x for x in (res.get("result") or []) if isinstance(x, dict) and abs(flt(x.get("difference_value"))) > 0.01]
        r.expect(not rows, f"value comparison differences {rows[:2]}")
        return f"stock in hand {books:,.2f} = stock value {stock:,.2f}"
    r.step("stock in hand equals the stock ledger value", ties)

    def periodic_tool_refuses():
        from ph_cas.stock.periodic import post_adjustment

        return refused(post_adjustment, co, today())
    r.step("the periodic year-end tool refuses a perpetual company", periodic_tool_refuses)

    def locked():
        c = frappe.get_doc("Company", co)
        c.ph_inventory_method = "Periodic"
        return refused(c.save)
    r.step("D7: perpetual cannot switch back after stock moved", locked)


# ---- section: roles ------------------------------------------------------------------------------
def s_roles(r: Runner):
    from ph_cas.setup import roles as R

    me = frappe.session.user
    users = {}
    for profile in (R.OWNER, R.BOOKKEEPER, R.CASHIER):
        def make_user(profile=profile):
            email = f"qa4.{profile.lower()}@example.com"
            if not frappe.db.exists("User", email):
                u = frappe.get_doc({"doctype": "User", "email": email, "first_name": f"QA4 {profile}", "send_welcome_email": 0, "user_type": "System User",
                                    "role_profiles": [{"role_profile": profile}]})
                u.insert()
            u = frappe.get_doc("User", email)
            have = {x.role for x in u.roles}
            want = set(R.PROFILES[profile]) & set(frappe.get_all("Role", pluck="name"))
            r.expect(want <= have, f"missing {sorted(want - have)}")
            users[profile] = email
            return f"{email}: {len(have)} roles"
        r.step(f"user with the {profile} profile", make_user)

    _p = _parties()

    def as_user(profile, fn):
        def run():
            frappe.set_user(users[profile])
            try:
                return fn()
            finally:
                frappe.set_user(me)
        return run

    def owner_masters():
        s = supplier(f"QA4 Owner Supplier {frappe.generate_hash(length=4)}", ph_tin="000-908-001", ph_branch_code="00000", ph_vat_status="VAT", ph_payee_type="Non-individual",
                     ph_ewt_category="services", ph_registered_name="QA4 OWNER SUPPLIER", ph_address_line1="1 Owner St, Pasig City", ph_zip="1600")
        ip = frappe.get_doc({"doctype": "Item Price", "item_code": item(f"QA4 Owner Item {frappe.generate_hash(length=4)}"), "price_list": "Standard Selling", "price_list_rate": 5600})
        ip.insert()
        return f"{s}, {ip.name}"
    r.step("Owner: adds a supplier and an item price", as_user(R.OWNER, owner_masters))

    def bookkeeper_work():
        s = supplier(f"QA4 Bookkeeper Supplier {frappe.generate_hash(length=4)}", ph_tin="000-908-002", ph_branch_code="00000", ph_vat_status="VAT", ph_payee_type="Non-individual",
                     ph_ewt_category="services", ph_registered_name="QA4 BOOKKEEPER SUPPLIER", ph_address_line1="2 Book St, Pasig City", ph_zip="1600")
        pi = purchase_invoice(VAT_CORP, s, [(item("QA4 Janitorial Services"), 1, 20000)])
        from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import new_return
        from ph_cas.tax.returns import quarter_bounds

        qs, _ = quarter_bounds(today())
        name = new_return(VAT_CORP, "2550Q", f"{qs.year}-Q{(qs.month - 1) // 3 + 1}")
        frappe.get_doc("PH Tax Return", name).refresh_from_books()
        return f"{s}; bill {pi.name}; {name} refreshed"
    r.step("Bookkeeper: supplier, bill with EWT, 2550Q from the books", as_user(R.BOOKKEEPER, bookkeeper_work))

    def bookkeeper_no_users():
        return refused(frappe.get_doc({"doctype": "User", "email": "qa4.nope@example.com", "first_name": "Nope", "send_welcome_email": 0}).insert)
    r.step("Bookkeeper: cannot add users", as_user(R.BOOKKEEPER, bookkeeper_no_users))

    def cashier_sale():
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        si = sales_invoice(VAT_CO, _p[4], [("QA4-HAMMER", 1, 450, {"warehouse": acc(VAT_CO, "Stores")})], update_stock=1)
        pe = get_payment_entry("Sales Invoice", si.name)
        pe.reference_no, pe.reference_date = "QA4-CASH", today()
        pe.insert()
        pe.submit()
        return f"{si.name} serial {si.bir_serial}; collected {pe.name}"
    r.step("Cashier: invoices and collects at the counter", as_user(R.CASHIER, cashier_sale))

    def cashier_limits():
        a = refused(supplier, f"QA4 Cashier Supplier {frappe.generate_hash(length=4)}")
        b = refused(purchase_invoice, VAT_CO, _p[0], [("QA4 Repair Service", 1, 100)])
        c = refused(lambda: frappe.get_doc({"doctype": "Journal Entry", "company": VAT_CO, "posting_date": today(), "accounts": [
            {"account": acc(VAT_CO, "Cash"), "debit_in_account_currency": 100, "cost_center": acc(VAT_CO, "Main")},
            {"account": acc(VAT_CO, "Sales"), "credit_in_account_currency": 100, "cost_center": acc(VAT_CO, "Main")}]}).insert())
        return f"supplier: {a} | bill: {b} | journal: {c}"
    r.step("Cashier: cannot add suppliers, post bills or journal entries", as_user(R.CASHIER, cashier_limits))


# ---- section: reports ----------------------------------------------------------------------------
def _report(name, filters):
    from frappe.desk.query_report import run

    res = run(name, filters=filters)
    cols = [(c.get("fieldname") if isinstance(c, dict) else str(c).split(":")[0].lower().replace(" ", "_")) for c in (res.get("columns") or [])]
    rows = []
    for x in res.get("result") or []:
        rows.append(x if isinstance(x, dict) else dict(zip(cols, x)))
    return rows


def _is_summary(x) -> bool:
    """A report's own total, tie-out or closing row (they repeat the detail, so a sum skips them)."""
    if x.get("is_tie_row") or x.get("is_closing") or x.get("is_total_row"):
        return True
    texts = [v for v in x.values() if isinstance(v, str)]
    if any(v.strip().strip("'").upper() == "TOTAL" for v in texts):
        return True
    has_date = any(hasattr(v, "year") for v in x.values())
    return not has_date and not any(v.strip() for v in texts)  # an unlabelled sum row


def _col(rows, field):
    return flt(sum(flt(x.get(field)) for x in rows if not _is_summary(x)), 2)


_REFRESHED: set = set()


def _ret_line(company, form, key, item):
    from ph_cas.ph_cas.doctype.ph_tax_return.ph_tax_return import new_return

    name = new_return(company, form, key)
    if (company, form, key) not in _REFRESHED:
        doc = frappe.get_doc("PH Tax Return", name)
        if doc.docstatus == 0:
            doc.refresh_from_books()
        _REFRESHED.add((company, form, key))
    v = frappe.db.get_value("PH Tax Return Line", {"parenttype": "PH Tax Return", "parent": name, "item": item}, "amount")
    return None if v is None else flt(v, 2)


def s_reports(r: Runner):
    _REFRESHED.clear()
    co = VAT_CORP
    y = getdate(today()).year
    ys, ye = f"{y}-01-01", f"{y}-12-31"
    from ph_cas.tax.returns import quarter_bounds

    qs, qe = quarter_bounds(today())
    qkey = f"{qs.year}-Q{(qs.month - 1) // 3 + 1}"
    base = {"company": co, "from_date": ys, "to_date": ye}
    fy = frappe.db.get_value("Fiscal Year", {"year_start_date": ("<=", today()), "year_end_date": (">=", today())}, "name")
    si_f = {"company": co, "docstatus": 1, "posting_date": ("between", [ys, ye])}

    def books_tie():
        out = []
        for rep in ("PH Sales Journal", "PH Purchase Journal", "PH Cash Receipts Book", "PH Cash Disbursements Book", "PH General Journal", "PH General Ledger Book"):
            rows = _report(rep, base)
            ties = [x for x in rows if x.get("is_tie_row") or x.get("is_closing")]
            bad = [x.get("particulars") for x in ties if "TIES" not in str(x.get("particulars") or "").upper() and "(ties)" not in str(x.get("particulars") or "")]
            r.expect(not bad, f"{rep}: {bad}")
            out.append(f"{rep.replace('PH ', '')} {len(rows)} rows, {len(ties)} ties")
        return "; ".join(out)
    r.step("the six books tie to the ledger", books_tie)

    def sales_journal_vs_invoices():
        rows = _report("PH Sales Journal", base)
        sj = _col(rows, "ph_vatable_sales") + _col(rows, "ph_exempt_sales") + _col(rows, "ph_zero_rated_sales")
        db = flt(sum(frappe.get_all("Sales Invoice", filters=si_f, pluck="base_net_total")), 2)
        vat = _col(rows, "ph_vat_amount")
        led = -gl_balance(co, acc(co, "Output VAT"), ys, ye)
        r.expect(abs(sj - db) < 0.01, f"journal sales {sj:,.2f} vs invoices {db:,.2f}")
        r.expect(abs(vat - led) < 0.01, f"journal VAT {vat:,.2f} vs ledger {led:,.2f}")
        reg = _report("Sales Register", base)
        reg_net = _col(reg, "net_total")
        r.expect(abs(reg_net - db) < 0.01, f"sales register net {reg_net:,.2f} vs invoices {db:,.2f}")
        return f"sales {sj:,.2f} = invoices = register; output VAT {vat:,.2f} = ledger"
    r.step("Sales Journal and Sales Register = the invoices; VAT = the ledger", sales_journal_vs_invoices)

    def purchase_journal_vs_bills():
        rows = _report("PH Purchase Journal", base)
        ewt = _col(rows, "ph_ewt_amount")
        led = -gl_balance(co, acc(co, "Withholding Tax Payable - Expanded"), ys, ye)
        db = flt(sum(frappe.get_all("Purchase Invoice", filters=si_f, pluck="base_net_total")), 2)
        reg = _col(_report("Purchase Register", base), "net_total")
        r.expect(abs(ewt - led) < 0.01, f"journal EWT {ewt:,.2f} vs ledger {led:,.2f}")
        r.expect(abs(reg - db) < 0.01, f"purchase register {reg:,.2f} vs bills {db:,.2f}")
        return f"EWT {ewt:,.2f} = ledger; purchases {db:,.2f} = register"
    r.step("Purchase Journal and Purchase Register = the bills; EWT = the ledger", purchase_journal_vs_bills)

    def receivables():
        rows = _report("Accounts Receivable", {"company": co, "report_date": ye, "ageing_based_on": "Due Date", "range": "30, 60, 90, 120"})
        rep = _col([x for x in rows if x.get("voucher_no")], "outstanding")
        db = flt(sum(frappe.get_all("Sales Invoice", filters={"company": co, "docstatus": 1}, pluck="outstanding_amount")), 2)
        led = gl_balance(co, acc(co, "Debtors"), None, ye)
        r.expect(abs(rep - db) < 0.01 and abs(rep - led) < 0.01, f"AR report {rep:,.2f}, invoices {db:,.2f}, ledger {led:,.2f}")
        return f"AR {rep:,.2f} = invoices' outstanding = Debtors"
    r.step("Accounts Receivable = open invoices = the Debtors account", receivables)

    def payables():
        rows = _report("Accounts Payable", {"company": co, "report_date": ye, "ageing_based_on": "Due Date", "range": "30, 60, 90, 120"})
        rep = _col([x for x in rows if x.get("voucher_no")], "outstanding")
        db = flt(sum(frappe.get_all("Purchase Invoice", filters={"company": co, "docstatus": 1}, pluck="outstanding_amount")), 2)
        led = -gl_balance(co, acc(co, "Creditors"), None, ye)
        r.expect(abs(rep - db) < 0.01 and abs(rep - led) < 0.01, f"AP report {rep:,.2f}, bills {db:,.2f}, ledger {led:,.2f}")
        return f"AP {rep:,.2f} = open bills = Creditors"
    r.step("Accounts Payable = open bills = the Creditors account", payables)

    def statements():
        tb = _report("Trial Balance", {"company": co, "fiscal_year": fy, "from_date": ys, "to_date": ye})
        tot = next(x for x in tb if "Total" in str(x.get("account")))
        r.expect(abs(flt(tot.get("closing_debit")) - flt(tot.get("closing_credit"))) < 0.01, f"trial balance {tot}")
        flt_ = {"company": co, "filter_based_on": "Date Range", "period_start_date": ys, "period_end_date": ye, "periodicity": "Yearly", "from_fiscal_year": fy, "to_fiscal_year": fy}
        pl = _report("Profit and Loss Statement", flt_)
        profit = flt(next(x for x in pl if "Profit for the year" in str(x.get("account"))).get("total"), 2)
        led = -flt(frappe.db.sql("""select sum(g.debit) - sum(g.credit) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
            where g.company = %s and g.is_cancelled = 0 and a.report_type = 'Profit and Loss' and g.posting_date between %s and %s""", (co, ys, ye))[0][0], 2)
        r.expect(abs(profit - led) < 0.01, f"P&L profit {profit:,.2f} vs ledger {led:,.2f}")
        bs = _report("Balance Sheet", flt_)
        assets = flt(next(x for x in bs if "Total Asset" in str(x.get("account"))).get("total"), 2)
        other = flt(next(x for x in bs if str(x.get("account")).strip("'") == "Total (Credit)").get("total"), 2)
        r.expect(abs(assets - other) < 0.01, f"assets {assets:,.2f} vs liabilities, equity and profit {other:,.2f}")
        return f"trial balance {flt(tot.get('closing_debit')):,.2f} both sides; profit {profit:,.2f} = ledger; assets {assets:,.2f} = liabilities + equity + profit"
    r.step("Trial Balance, Profit and Loss, Balance Sheet", statements)

    def vat_return_vs_books():
        rows = _report("PH Sales Journal", {"company": co, "from_date": str(qs), "to_date": str(qe)})
        checks = {"31A": _col(rows, "ph_vatable_sales"), "32A": _col(rows, "ph_zero_rated_sales"), "33A": _col(rows, "ph_exempt_sales"),
                  "31B": -gl_balance(co, acc(co, "Output VAT"), str(qs), str(qe))}
        bad = {k: (v, _ret_line(co, "2550Q", qkey, k)) for k, v in checks.items() if _ret_line(co, "2550Q", qkey, k) is None or abs(v - _ret_line(co, "2550Q", qkey, k)) > 0.01}
        r.expect(not bad, f"2550Q vs books (books, return): {bad}")
        return "; ".join(f"{k} {v:,.2f}" for k, v in checks.items())
    r.step(f"2550Q {qkey} = the Sales Journal and the Output VAT account", vat_return_vs_books)

    def ewt_return_vs_books():
        rows = _report("PH Purchase Journal", {"company": co, "from_date": str(qs), "to_date": str(qe)})
        ewt = _col(rows, "ph_ewt_amount")
        ret = _ret_line(co, "1601-EQ", qkey, "19")
        r.expect(ret is not None and abs(ewt - ret) < 0.01, f"1601-EQ item 19 {ret} vs journal {ewt:,.2f}")
        return f"EWT {ewt:,.2f} = 1601-EQ item 19"
    r.step(f"1601-EQ {qkey} = the Purchase Journal", ewt_return_vs_books)

    def income_return_vs_books():
        sales = -gl_balance(co, acc(co, "Sales"), ys, ye)
        ret = _ret_line(co, "1702-RT", str(y), "27")
        r.expect(ret is not None and abs(sales - ret) < 1, f"1702-RT item 27 {ret} vs Sales account {sales:,.2f}")
        rec = _report("PH Book to Tax Reconciliation", base)
        unexplained = next((flt(x.get("amount")) for x in rec if "Unexplained" in str(x.get("line"))), None)
        r.expect(unexplained is not None and abs(unexplained) < 0.01, f"book-to-tax unexplained {unexplained}")
        return f"1702-RT sales {ret:,.2f} = Sales account; book-to-tax unexplained 0"
    r.step("1702-RT = the ledger; book-to-tax reconciliation explains everything", income_return_vs_books)

    def sc_pwd_and_2307():
        sc = _col(_report("PH SC PWD Sales", base), "ph_sc_pwd_discount")
        db = flt(sum(frappe.get_all("Sales Invoice", filters=si_f, pluck="ph_sc_pwd_discount")), 2)
        r.expect(abs(sc - db) < 0.01, f"SC/PWD report {sc} vs invoices {db}")
        rec = _report("PH 2307 Received Reconciliation", base)
        cert = _col(rec, "certified")
        db2 = flt(sum(frappe.get_all("PH 2307 Received", filters={"company": co, "docstatus": 1}, pluck="total_tax")), 2)
        r.expect(abs(cert - db2) < 0.01, f"2307 report {cert} vs certificates {db2}")
        return f"SC/PWD discounts {sc:,.2f}; 2307 certified {cert:,.2f}"
    r.step("SC/PWD Sales and 2307 Received reports = the documents", sc_pwd_and_2307)

    def calendar():
        rows = _report("PH Compliance Calendar", {"company": co, "year": y})
        row = next((x for x in rows if x.get("form") == "2550Q" and x.get("period_label") == qkey), None)
        r.expect(row and row.get("figures"), f"2550Q {qkey} row {row}")
        return f"{len(rows)} rows; 2550Q {qkey}: {row['status']}"
    r.step("compliance calendar shows the returns in progress", calendar)

    def modules():
        out = []
        far = _report("Fixed Asset Register", {"company": co, "status": "In Location", "filter_based_on": "Date Range", "from_date": "2000-01-01", "to_date": ye})
        fa = _col([x for x in far if x.get("asset_id") and x.get("asset_id") != "Total"], "net_purchase_amount")
        db = flt(sum(frappe.get_all("Asset", filters={"company": co, "docstatus": 1}, pluck="net_purchase_amount")), 2)
        r.expect(abs(fa - db) < 0.01, f"asset register {fa} vs assets {db}")
        out.append(f"assets {fa:,.0f}")
        ps = _report("Project Summary", {"company": co})
        r.expect(any(x.get("project_name") == "QA4 Warehouse Build" and x.get("total_tasks") == 3 for x in ps), "project missing from Project Summary")
        out.append(f"projects {len(ps)}")
        ld = _report("Lead Details", base)
        r.expect(any(x.get("email_id") == "qa4.lead@example.com" for x in ld), "lead missing from Lead Details")
        iss = _report("Issue Summary", {**base, "based_on": "Customer"})
        r.expect(sum(flt(x.get("total_issues")) for x in iss) >= 1, "issue missing from Issue Summary")
        out.append(f"leads {len(ld)}, issue rows {len(iss)}")
        gp = _report("Gross Profit", {"company": VAT_CO, "from_date": ys, "to_date": ye, "group_by": "Invoice"})
        out.append(f"gross profit rows {len(gp)}")
        for rep, f in (("Item-wise Sales Register", base), ("Cash Flow", {"company": co, "filter_based_on": "Date Range", "period_start_date": ys, "period_end_date": ye, "periodicity": "Yearly", "from_fiscal_year": fy, "to_fiscal_year": fy}),
                       ("Stock Ledger", {"company": VAT_CO, "from_date": ys, "to_date": ye}), ("Stock Projected Qty", {"company": VAT_CO}),
                       ("Work Order Summary", {"company": VAT_CO, "from_date": ys, "to_date": ye, "age": 0, "charts_based_on": "Status"}),
                       ("Quality Inspection Summary", {"company": co, "from_date": ys, "to_date": ye}),
                       ("Asset Depreciations and Balances", {"company": co, "from_date": ys, "to_date": ye, "group_by": "Asset Category"}),
                       ("Daily Timesheet Summary", {"from_date": ys, "to_date": ye}), ("Delayed Tasks Summary", {}),
                       ("Opportunity Summary by Sales Stage", {"company": co, "from_date": ys, "to_date": ye, "based_on": "Opportunity Owner", "data_based_on": "Number", "opportunity_source": ""})):
            out.append(f"{rep} {len(_report(rep, f))}")
        return "; ".join(out)
    r.step("module reports carry the module's documents", modules)

    def slsp_walk_in():
        from frappe.utils import get_first_day, get_last_day

        from ph_cas.dat.relief import GENERIC_NAME, GENERIC_TIN, build_sales

        first, last = str(get_first_day(today())), str(get_last_day(today()))
        _name, content, n = build_sales(VAT_CO, first, last)
        text = content.decode("utf-8", "replace") if isinstance(content, bytes) else content
        lines = [ln for ln in text.splitlines() if GENERIC_TIN in ln]
        r.expect(len(lines) == 1 and GENERIC_NAME in lines[0] and "MARIKINA CITY" in lines[0], f"generic rows {lines}")
        walk_in = flt(frappe.db.sql("""select sum(si.ph_vatable_sales) from `tabSales Invoice` si join `tabCustomer` c on c.name = si.customer
            where si.company = %s and si.docstatus = 1 and si.posting_date between %s and %s and ifnull(c.ph_tin, '') = '' and ifnull(c.tax_id, '') = ''""", (VAT_CO, first, last))[0][0], 2)
        r.expect(f"{walk_in:.2f}" in lines[0], f"walk-in VATable {walk_in:.2f} not on the row: {lines[0]}")
        return f"{n} rows; {lines[0][:150]}"
    r.step("SLSP: walk-in sales on one Generic Customer row", slsp_walk_in)

    def audit_by_document():
        si = frappe.get_all("Sales Invoice", filters={"company": co, "docstatus": 1}, pluck="name", limit=1)[0]
        rows = _report("BIR Audit Trail", {"from_date": ys, "to_date": ye, "ref_doctype": "Sales Invoice", "ref_name": si})
        r.expect(rows, f"no audit rows for {si}")
        return f"{si}: {len(rows)} audit rows"
    r.step("audit trail finds a document's history", audit_by_document)


# ---- section: go-live and opening balances (B71) ----------------------------------------------
GO_LIVE_CO = "QA4 Bagong Simula Trading Corp."


def s_go_live(r: Runner):
    from frappe.utils import add_days

    from ph_cas.golive import go_live_checklist

    _p = _parties()
    tile = item("QA4-TILE", stock=1, item_name="Floor tile 60x60 (box)", valuation_rate=250)
    # a company that has not gone live yet: the first free one of QA4 Bagong Simula Trading Corp., ... 2, ... 3
    n = 1
    while frappe.db.exists("Journal Entry", {"company": GO_LIVE_CO + (f" {n}" if n > 1 else ""), "is_opening": "Yes", "docstatus": 1}):
        n += 1
    co = GO_LIVE_CO + (f" {n}" if n > 1 else "")
    state = {}

    def company():
        c = _trading_company(co, f"Q4BS{n if n > 1 else ''}", "Periodic", "000-905-007")
        return c.name
    if not r.step("a fresh company that is about to go live", company):
        return
    cutover = add_days(today(), -1)

    def je(posting_date, rows, opening=True):
        return frappe.get_doc({"doctype": "Journal Entry", "company": co, "posting_date": posting_date, "voucher_type": "Opening Entry" if opening else "Journal Entry",
                               "is_opening": "Yes" if opening else "No", "user_remark": "QA4 opening balances from the old books",
                               "accounts": [{"cost_center": acc(co, "Main"), **x} for x in rows]})

    rows = [
        {"account": acc(co, "Cash"), "debit_in_account_currency": 100000},
        {"account": acc(co, "Stock In Hand"), "debit_in_account_currency": 25000},
        {"account": acc(co, "Debtors"), "party_type": "Customer", "party": _p[3], "debit_in_account_currency": 56000, "user_remark": "Old SI 001234 of 2026-10-15"},
        {"account": acc(co, "Creditors"), "party_type": "Supplier", "party": _p[0], "credit_in_account_currency": 33600, "user_remark": "Old bill TW-889"},
        {"account": acc(co, "Capital Stock"), "credit_in_account_currency": 147400},
    ]

    def no_date_yet():
        frappe.db.set_value("Company", co, "ph_go_live_date", None)
        frappe.clear_document_cache("Company", co)
        return refused(je(cutover, rows).insert)
    r.step("an opening entry is refused until the go-live date is set", no_date_yet)

    def set_date():
        c = frappe.get_doc("Company", co)
        c.ph_go_live_date = today()
        c.save()
        frappe.clear_document_cache("Company", co)
        before = {i["key"]: i["status"] for i in go_live_checklist(co)}
        r.expect(before["go_live"] == "done" and before["balances"] == "missing", f"checklist {before}")
        return f"go live {today()}, cut-over {cutover}; checklist before: {before}"
    r.step("set the go-live date; the checklist shows balances missing", set_date)

    def wrong_day():
        return refused(je(add_days(cutover, -3), rows).insert)
    r.step("an opening entry on another day is refused", wrong_day)

    def opening_invoice_refused():
        si = frappe.get_doc({"doctype": "Sales Invoice", "company": co, "customer": _p[3], "is_opening": "Yes", "posting_date": cutover, "set_posting_time": 1,
                             "debit_to": acc(co, "Debtors"), "items": [{"item_code": item("QA4 Repair Service"), "qty": 1, "rate": 56000, "income_account": acc(co, "Temporary Opening")}]})
        return refused(si.insert)
    r.step("an opening invoice is refused (no BIR serial or VAT for old invoices)", opening_invoice_refused)

    def opening_entry():
        d = je(cutover, rows)
        d.insert()
        d.submit()
        state["je"] = d.name
        r.expect(not d.get("ph_backdate_reason"), "needed a back-date reason")
        return f"{d.name} dated {d.posting_date}: cash 100,000, inventory 25,000, Marikina Builders owes 56,000, owe Tools Wholesale 33,600, capital 147,400"
    r.step("opening Journal Entry on the cut-over day, no reason needed", opening_entry)

    def opening_stock():
        sr = frappe.get_doc({"doctype": "Stock Reconciliation", "company": co, "purpose": "Opening Stock", "posting_date": cutover, "set_posting_time": 1,
                             "expense_account": acc(co, "Temporary Opening"),
                             "items": [{"item_code": tile, "warehouse": acc(co, "Stores"), "qty": 100, "valuation_rate": 250}]})
        sr.insert()
        sr.submit()
        from ph_cas.stock.periodic import book_value, counted_value, inventory_account

        r.expect(counted_value(co, cutover) == 25000 and book_value(co, inventory_account(co), cutover) == 25000, "stock count and inventory account differ")
        return f"{sr.name}: 100 boxes x 250 = 25,000 = inventory account"
    r.step("opening stock count on the cut-over day", opening_stock)

    def receivable_shows():
        rows_ = _report("Accounts Receivable", {"company": co, "report_date": today(), "ageing_based_on": "Posting Date", "range": "30, 60, 90, 120"})
        mine = [x for x in rows_ if x.get("voucher_no") == state["je"]]
        r.expect(mine and flt(mine[0].get("outstanding")) == 56000, f"AR rows {mine}")
        ap = _report("Accounts Payable", {"company": co, "report_date": today(), "ageing_based_on": "Posting Date", "range": "30, 60, 90, 120"})
        r.expect(any(x.get("voucher_no") == state["je"] and flt(x.get("outstanding")) == 33600 for x in ap), "AP row missing")
        return "AR 56,000 and AP 33,600 from the opening entry"
    r.step("the old balances show in Accounts Receivable and Payable", receivable_shows)

    def collect_old():
        pe = frappe.get_doc({"doctype": "Payment Entry", "payment_type": "Receive", "company": co, "posting_date": today(), "party_type": "Customer", "party": _p[3],
                             "paid_from": acc(co, "Debtors"), "paid_to": acc(co, "Cash"), "paid_amount": 56000, "received_amount": 56000,
                             "reference_no": "QA4-OLD-OR", "reference_date": today(),
                             "references": [{"reference_doctype": "Journal Entry", "reference_name": state["je"], "allocated_amount": 56000}]})
        pe.insert()
        pe.submit()
        rows_ = _report("Accounts Receivable", {"company": co, "report_date": today(), "ageing_based_on": "Posting Date", "range": "30, 60, 90, 120"})
        r.expect(not [x for x in rows_ if x.get("voucher_no") == state["je"]], "still open after collection")
        return f"{pe.name} collected 56,000 against the opening balance; receipt serial {pe.get('bir_serial') or '-'}"
    r.step("collect an old balance against the opening entry", collect_old)

    def checklist_after():
        items = {i["key"]: (i["status"], i["detail"]) for i in go_live_checklist(co)}
        bad = {k: v for k, v in items.items() if v[0] == "missing"}
        r.expect(not bad, f"still missing {bad}")
        return "; ".join(f"{k}: {v[0]}" for k, v in items.items())
    r.step("the go-live checklist is complete", checklist_after)

    def tb():
        f = frappe.db.get_value("Fiscal Year", {"year_start_date": ("<=", today()), "year_end_date": (">=", today())}, "name")
        rows_ = _report("Trial Balance", {"company": co, "fiscal_year": f, "from_date": f"{getdate(today()).year}-01-01", "to_date": cutover})
        tot = next(x for x in rows_ if "Total" in str(x.get("account")))
        r.expect(abs(flt(tot.get("closing_debit")) - flt(tot.get("closing_credit"))) < 0.01, f"TB {tot}")
        return f"trial balance at cut-over {flt(tot.get('closing_debit')):,.2f} both sides"
    r.step("trial balance on the cut-over day balances", tb)


# ---- section: record an expense (B72) --------------------------------------------------------
def s_expense(r: Runner):
    from ph_cas.expense import preview_expense, record_expense

    co = VAT_CORP
    _p = _parties()
    rno = "OR-" + frappe.generate_hash(length=6).upper()
    jeepney = supplier("QA4 Mang Jose Tricycle", supplier_type="Individual", ph_vat_status="Non-VAT", ph_payee_type="Individual", ph_last_name="SANTOS", ph_first_name="JOSE", ph_middle_name="")
    state = {}

    def preview():
        f = preview_expense(company=co, supplier=_p[1], amount=11200, description="Notarial and legal advice", receipt_no=rno, expense_account=acc(co, "Legal Expenses"))
        r.expect((f["net"], f["vat"], f["ewt"], f["paid"]) == (10000, 1200, 500, 10700), f"preview {f}")
        r.expect(not frappe.db.exists("Purchase Invoice", {"bill_no": rno}), "the preview posted")
        return f"receipt 11,200 -> net 10,000, input VAT 1,200, EWT {f['ewt_atc']} 500, cash paid 10,700 (nothing posted)"
    r.step("preview: VAT worked back from the receipt, EWT on the net", preview)

    def post():
        out = record_expense(company=co, supplier=_p[1], amount=11200, description="Notarial and legal advice", receipt_no=rno, expense_account=acc(co, "Legal Expenses"))
        g = gl("Purchase Invoice", out["purchase_invoice"])
        want = {"Legal Expenses": 10000, "Input VAT - Services": 1200, "Withholding Tax Payable - Expanded": -500, "Cash": -10700}
        bad = {k: (g.get(k), v) for k, v in want.items() if g.get(k) != v}
        r.expect(not bad, f"GL {g}")
        r.expect(frappe.db.get_value("Purchase Invoice", out["purchase_invoice"], "outstanding_amount") == 0, "not paid")
        state["pi"] = out["purchase_invoice"]
        return f"{out['purchase_invoice']} paid; GL {g}"
    r.step("post: one paid bill, cash out net of EWT", post)

    def small_cash():
        out = record_expense(company=co, supplier=jeepney, amount=150, description="Tricycle fare to the BIR office", expense_account=acc(co, "Travel Expenses"))
        r.expect((out["net"], out["vat"], out["ewt"], out["paid"]) == (150, 0, 0, 150), f"non-VAT {out}")
        return f"{out['purchase_invoice']}: 150, no VAT, no EWT"
    r.step("a small cash expense from a non-VAT supplier", small_cash)

    def in_the_books():
        from ph_cas.ph_cas.doctype.ph_2307_issued.ph_2307_issued import generate_quarter
        from ph_cas.tax.returns import quarter_bounds

        y = getdate(today()).year
        pj = _report("PH Purchase Journal", {"company": co, "from_date": f"{y}-01-01", "to_date": f"{y}-12-31"})
        r.expect(any(x.get("name") == state["pi"] for x in pj), "not in the Purchase Journal")
        cd = _report("PH Cash Disbursements Book", {"company": co, "from_date": f"{y}-01-01", "to_date": f"{y}-12-31"})
        r.expect(any(state["pi"] in str(x.values()) for x in cd), "not in the Cash Disbursements Book")
        qs, _qe = quarter_bounds(today())
        names = generate_quarter(co, str(qs))
        cert = next((n for n in names if frappe.db.get_value("PH 2307 Issued", n, "supplier") == _p[1]), None)
        r.expect(cert and flt(frappe.db.get_value("PH 2307 Issued", cert, "total_tax")) >= 500, f"2307 {cert}")
        return f"in the Purchase Journal and the Cash Disbursements Book; 2307 {cert} carries the 500"
    r.step("the expense reaches the books and the quarter's 2307", in_the_books)

    def cashier_refused():
        from ph_cas.setup import roles as R

        email = "qa4.cashier@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "QA4 Cashier", "send_welcome_email": 0, "role_profiles": [{"role_profile": R.CASHIER}]}).insert()
        me = frappe.session.user
        frappe.set_user(email)
        try:
            return refused(record_expense, company=co, supplier=jeepney, amount=50, description="Snacks", expense_account=acc(co, "Miscellaneous Expenses"))
        finally:
            frappe.set_user(me)
    r.step("a Cashier cannot record an expense", cashier_refused)

    def needs_account():
        return refused(record_expense, company=co, supplier=jeepney, amount=80, description="Load for the office phone")
    r.step("no expense account and no item: refused (never cost of goods sold by default)", needs_account)


# ---- section: Philippine import templates and batch edit (B73) ----------------------------------
IMPORT_CO = "QA4 Bagong Bukas Trading Corp."


def _csv(rows):
    import csv as _c
    import io as _io

    b = _io.StringIO()
    _c.writer(b).writerows(rows)
    return b.getvalue()


def s_imports(r: Runner):
    from frappe.utils import add_days

    from ph_cas import imports as I
    from ph_cas.golive import go_live_checklist

    n = 1
    while frappe.db.exists("Journal Entry", {"company": IMPORT_CO + (f" {n}" if n > 1 else ""), "is_opening": "Yes", "docstatus": 1}):
        n += 1
    co = IMPORT_CO + (f" {n}" if n > 1 else "")
    state = {}
    P_HEAD = ["Customer or Supplier", "Name", "Payee type", "TIN", "Branch code", "Registered name", "Last name", "First name", "Middle name", "VAT status",
              "Government agency or GOCC", "Top withholding agent", "Withholding category", "Over the threshold or VAT-registered", "Address line 1", "Address line 2", "ZIP code"]

    def template():
        t = I.template_csv("parties")
        lines = t.splitlines()
        r.expect(lines[0].startswith("Customer or Supplier,Name,Payee type,TIN") and lines[1].startswith("# required") and lines[2].startswith("# e.g."), t[:200])
        for k in I.TEMPLATES:
            I.template_csv(k)
        return f"4 templates; parties header: {lines[0][:90]}..."
    r.step("templates: header, a help row and an example row, both skipped on import", template)

    def bad_file():
        bad = _csv([P_HEAD,
                    ["Customer", "QA4 Imp Bad TIN", "Non-individual", "000123456000", "", "", "", "", "", "VAT"],
                    ["Supplier", "QA4 Imp No Names", "Individual", "000-777-001", "00000", "", "", "", "", "Non-VAT", "", "", "professional"],
                    ["Customer", "QA4 Imp Bad VAT", "Non-individual", "000-777-002", "00000", "", "", "", "", "VAT registered"],
                    ["Customer", "QA4 Imp Cust EWT", "Non-individual", "000-777-003", "00000", "", "", "", "", "VAT", "", "", "rent"],
                    ["Customer", "QA4 Imp Dup", "Non-individual", "000-777-003", "00000", "", "", "", "", "VAT", "", "", ""],
                    ["Supplier", "QA4 Imp Bad Branch", "Non-individual", "000-777-004", "0001", "", "", "", "", "VAT", "", "", "", "", "", "", "18070"]])
        res = I.check_import("parties", csv_text=bad)
        lines = {e["line"]: " ".join(e["errors"]) for e in res["errors"]}
        want = {2: "branch code", 3: "last name", 4: "VAT status", 5: "for suppliers", 6: "twice", 7: "5 digits"}
        miss = {k: v for k, v in want.items() if v not in lines.get(k, "")}
        r.expect(not res["ok"] and not miss, f"missing {miss}; got {lines}")
        r.expect("Line 2" in refused(I.run_import, "parties", csv_text=bad), "imported")
        r.expect(not frappe.db.exists("Customer", "QA4 Imp Bad VAT"), "a bad file saved a record")
        return f"{len(lines)} lines refused with reasons: " + "; ".join(f"{k}: {v[:50]}" for k, v in sorted(lines.items()))
    r.step("a bad customer/supplier file is checked line by line and nothing is saved", bad_file)

    good = _csv([P_HEAD,
                 ["# e.g. Customer", "example row, skipped"],
                 ["Customer", "QA4 Imp Pasig Hardware Inc.", "Non-individual", "000-777-101", "00000", "PASIG HARDWARE INC.", "", "", "", "VAT", "", "yes", "", "", "8 Caruncho Ave", "Pasig City", "1600"],
                 ["Customer", "QA4 Imp Generic Customer", "Non-individual", "000111222", "00000", "", "", "", "", "Non-VAT", "", "", "", "", "", "Makati City", ""],
                 ["Supplier", "QA4 Imp Atty. Reyes", "Individual", "000-777-102", "00000", "", "REYES", "MARIA", "CRUZ", "VAT", "", "", "professional", "yes", "2 Shaw Blvd", "Mandaluyong City", "1550"],
                 ["Supplier", "QA4 Imp Cebu Tiles Corp.", "Non-individual", "000-777-103", "00000", "", "", "", "", "VAT", "", "", "", "", "", "Cebu City", "6000"]])

    def parties():
        res = I.check_import("parties", csv_text=good)
        r.expect(res["ok"] and res["rows"] == 4, f"check {res}")
        out = I.run_import("parties", csv_text=good)
        s_ = frappe.get_doc("Supplier", "QA4 Imp Atty. Reyes")
        r.expect((s_.ph_tin, s_.ph_payee_type, s_.ph_ewt_category, s_.ph_over_threshold, s_.ph_last_name) == ("000-777-102", "Individual", "professional", 1, "REYES"), f"supplier {s_.as_dict()}")
        c = frappe.get_doc("Customer", "QA4 Imp Pasig Hardware Inc.")
        r.expect((c.ph_tin, c.ph_vat_status, c.ph_top_withholding_agent) == ("000-777-101", "VAT", 1), "customer fields")
        r.expect(frappe.db.get_value("Customer", "QA4 Imp Generic Customer", "ph_tin") == "000-111-222", "walk-in TIN")
        return f"created {len(out['created'])}, updated {len(out['updated'])}: TINs formatted, the lawyer is an individual professional over the threshold"
    r.step("import customers and suppliers with their BIR details", parties)

    def reimport():
        before = frappe.db.count("Supplier", {"supplier_name": ("like", "QA4 Imp%")})
        out = I.run_import("parties", csv_text=good)
        r.expect(len(out["updated"]) == 4 and not out["created"] and frappe.db.count("Supplier", {"supplier_name": ("like", "QA4 Imp%")}) == before, f"{out}")
        return "the same file again updates the 4 records; no duplicates"
    r.step("importing the same file again updates, never duplicates", reimport)

    def company():
        c = _trading_company(co, f"Q4BK{n if n > 1 else ''}", "Periodic", "000-905-008")
        c.ph_go_live_date = today()
        c.save()
        frappe.clear_document_cache("Company", co)
        return f"{co}: live {today()}"
    if not r.step("a fresh company going live today", company):
        return

    def items():
        csv_ = _csv([["Item code", "Item name", "Item group", "Unit", "Stock item", "VAT class", "Capital good", "Selling price", "Cost", "Income account", "Expense account"],
                     ["QA4-IMP-TILE", "Imported tile 30x30 (box)", "", "Nos", "yes", "VATable", "", "320", "250", "Sales", ""],
                     ["QA4-IMP-RICE", "Rice, regular milled (sack)", "", "Nos", "yes", "VAT-exempt", "", "1,950.00", "1700", "", ""],
                     ["QA4-IMP-BAD", "Bad item", "", "", "", "VAT", "", "abc", "", "No Such Account", ""]])
        res = I.check_import("items", company=co, csv_text=csv_)
        r.expect(not res["ok"] and [e["line"] for e in res["errors"]] == [4], f"{res}")
        out = I.run_import("items", company=co, csv_text="\n".join(csv_.splitlines()[:3]))
        it = frappe.get_doc("Item", "QA4-IMP-RICE")
        r.expect(it.ph_vat_class == "VAT-exempt" and it.is_stock_item == 1, "rice")
        d = next((x for x in frappe.get_doc("Item", "QA4-IMP-TILE").item_defaults if x.company == co), None)
        r.expect(d and d.income_account == acc(co, "Sales"), "tile income account")
        return f"bad row refused (VAT class, price, account); {len(out['created']) + len(out['updated'])} items saved; rice VAT-exempt; tile sells to {d.income_account}"
    r.step("import items with VAT class, price and the company's accounts", items)

    B_HEAD = ["Account", "Debit", "Credit"]
    bal = [B_HEAD, ["Cash", "100,000.00", ""], ["Stock In Hand", "25000", ""], ["Debtors", "56000", ""], ["Creditors", "", "33600"], ["Capital Stock", "", "147400"]]

    def unbalanced():
        b = [list(x) for x in bal]
        b[1][1] = "100,500.00"
        res = I.check_import("balances", company=co, csv_text=_csv(b))
        r.expect(not res["ok"] and any("differ by 500" in x for x in res["summary"]), f"{res}")
        return refused(I.run_import, "balances", company=co, csv_text=_csv(b))
    r.step("an old trial balance that does not balance is refused", unbalanced)

    def balances():
        out = I.run_import("balances", company=co, csv_text=_csv(bal))
        je = frappe.get_doc("Journal Entry", out["posted"][0])
        r.expect(str(je.posting_date) == str(add_days(today(), -1)) and je.is_opening == "Yes", f"{je.posting_date} {je.is_opening}")
        temp = next(a.debit for a in je.accounts if frappe.db.get_value("Account", a.account, "account_type") == "Temporary")
        r.expect(flt(temp) == 22400, f"temporary opening {temp}")
        state["bal_je"] = je.name
        return f"{je.name} dated the cut-over day; receivables less payables (22,400) wait on Temporary Opening"
    r.step("import the opening account balances", balances)

    def open_items():
        O_HEAD = ["Customer or Supplier", "Name", "Old invoice or bill no.", "Date", "Amount still owed"]
        late = _csv([O_HEAD, ["Customer", "QA4 Imp Pasig Hardware Inc.", "SI 9999", str(today()), "1000"]])
        msg = refused(I.run_import, "open_items", company=co, csv_text=late)
        r.expect("after the cut-over day" in msg, msg)
        ok = _csv([O_HEAD,
                   ["Customer", "QA4 Imp Pasig Hardware Inc.", "SI 001201", "2026-09-30", "30000"],
                   ["Customer", "QA4 Imp Pasig Hardware Inc.", "SI 001234", "2026-10-15", "26,000"],
                   ["Supplier", "QA4 Imp Cebu Tiles Corp.", "CT-0457", "2026-10-20", "33600"]])
        out = I.run_import("open_items", company=co, csv_text=ok)
        state["oi_je"] = out["posted"][0]
        rows_ = _report("Accounts Receivable", {"company": co, "report_date": today(), "ageing_based_on": "Posting Date", "range": "30, 60, 90, 120"})
        ar = sum(flt(x.get("outstanding")) for x in rows_ if x.get("voucher_no") == state["oi_je"])
        r.expect(ar == 56000, f"AR {ar}")
        from ph_cas.golive import _temporary_opening_balance

        t = _temporary_opening_balance(co, add_days(today(), -1))
        r.expect(abs(t) < 0.01, f"temporary opening still {t}")
        return f"refused a date after cut-over; {out['posted'][0]}: Pasig Hardware owes 56,000 on two old invoices, owe Cebu Tiles 33,600; Temporary Opening back to zero"
    r.step("import the open invoices and bills; Temporary Opening clears", open_items)

    def checklist():
        st = {i["key"]: i["status"] for i in go_live_checklist(co)}
        r.expect(st["balances"] == "done" and st["open_items"] == "done", f"{st}")
        return f"balances: {st['balances']}, open items: {st['open_items']}"
    r.step("the go-live checklist shows balances and open items done", checklist)

    def batch():
        out = I.batch_update("Supplier", ["QA4 Imp Atty. Reyes", "QA4 Imp Cebu Tiles Corp."], {"ph_payee_type": "Individual"})
        r.expect(out["changed"] == ["QA4 Imp Atty. Reyes"] and [x["name"] for x in out["refused"]] == ["QA4 Imp Cebu Tiles Corp."], f"{out}")
        out2 = I.batch_update("Supplier", ["QA4 Imp Atty. Reyes", "QA4 Imp Cebu Tiles Corp."], {"ph_vat_status": "VAT"})
        r.expect(len(out2["changed"]) == 2, f"{out2}")
        r.expect(refused(I.batch_update, "Supplier", ["QA4 Imp Cebu Tiles Corp."], {"ph_tin": "000-000-000"}), "a TIN was batch edited")
        return f"2 changed; a corporation cannot become an individual without names: {out['refused'][0]['reason'][:80]}"
    r.step("batch edit: each record through its own validation; the TIN is not batch editable", batch)

    def cashier():
        from ph_cas.setup import roles as R

        email = "qa4.cashier@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "QA4 Cashier", "send_welcome_email": 0, "role_profiles": [{"role_profile": R.CASHIER}]}).insert()
        me = frappe.session.user
        frappe.set_user(email)
        try:
            return refused(I.run_import, "parties", csv_text=_csv([P_HEAD, ["Supplier", "QA4 Imp Cashier Supplier", "Non-individual", "000-777-199", "00000", "", "", "", "", "VAT"]]))
        finally:
            frappe.set_user(me)
    r.step("a Cashier cannot import suppliers", cashier)


# ---- section: subsidiary ledgers and the cash position (B74) ------------------------------------
def s_ledgers(r: Runner):
    from ph_cas.books import looseleaf as L
    from ph_cas.books.cash import cash_position

    co = VAT_CORP
    y = getdate(today()).year
    start, end = f"{y}-01-01", today()

    def gl_party_balance(atype, ptype, before=None):
        cond, args = ("and g.posting_date < %s", (co, atype, ptype, before)) if before else ("and g.posting_date <= %s", (co, atype, ptype, end))
        return flt(frappe.db.sql(f"""select coalesce(sum(g.debit) - sum(g.credit), 0) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
                                    where g.company = %s and g.is_cancelled = 0 and a.account_type = %s and g.party_type = %s {cond}""", args)[0][0], 2)

    def ar():
        b = L.ar_ledger(co, start, end)
        tot = b.rows[-1]
        want = gl_party_balance("Receivable", "Customer")
        r.expect(flt(tot[5], 2) == want, f"AR ledger total {tot[5]} vs GL {want}")
        blocks = [x for x in b.rows if x[2] and "balance forwarded" in str(x[2])]
        r.expect(blocks and any("TIN " in str(x[2]) for x in blocks), "no customer block with a TIN")
        r.expect(any(str(x[2]).startswith("SALES INVOICE") for x in b.rows), "no sales invoice entry")
        return f"{len(blocks)} customers; balance {want:,.2f} ties to the receivable accounts"
    r.step("customers' subsidiary ledger ties to Accounts Receivable", ar)

    def ap():
        b = L.ap_ledger(co, start, end)
        want = -gl_party_balance("Payable", "Supplier")
        r.expect(flt(b.rows[-1][5], 2) == want, f"AP ledger total {b.rows[-1][5]} vs GL {want}")
        r.expect(any(str(x[2]).startswith("PURCHASE INVOICE") for x in b.rows), "no bill entry")
        return f"{len([x for x in b.rows if 'balance forwarded' in str(x[2])])} suppliers; owed {want:,.2f} ties to the payable accounts (credit-positive)"
    r.step("suppliers' subsidiary ledger ties to Accounts Payable", ap)

    def forwarded():
        b = L.ar_ledger(co, today(), today())
        fwd = sum(flt(x[5]) for x in b.rows if "balance forwarded" in str(x[2]))
        want = gl_party_balance("Receivable", "Customer", before=today())
        r.expect(flt(fwd, 2) == want, f"forwarded {fwd} vs {want}")
        return f"balances forwarded into today: {fwd:,.2f}"
    r.step("a ledger that starts mid-year brings the balances forward", forwarded)

    def pack():
        import io as _io
        import zipfile as _z

        _n, data, pages = L.pack(co, start, end, "xlsx", subsidiary=True)
        names = _z.ZipFile(_io.BytesIO(data)).namelist()
        r.expect(any(n.startswith("ARL_") for n in names) and any(n.startswith("APL_") for n in names), f"{names}")
        txt = _z.ZipFile(_io.BytesIO(data)).read("PAGES.txt").decode()
        r.expect("Accounts Receivable Subsidiary Ledger" in txt, txt)
        _n2, data2, pages2 = L.pack(co, start, end, "xlsx")
        r.expect(len(pages2) == 6 and len(pages) == 8, f"{len(pages2)} {len(pages)}")
        wb = __import__("openpyxl").load_workbook(_io.BytesIO(_z.ZipFile(_io.BytesIO(data)).read(next(n for n in names if n.startswith("ARL_")))))
        vals = [c.value for row in wb.active.iter_rows(max_row=12) for c in row if c.value]
        r.expect("OWNER'S NAME" in vals and any("Page 1 of" in str(v) for v in vals), "no BIR header")
        return f"8 books with the subsidiary ledgers (6 without); BIR header on each page; pages {pages.get('ACCOUNTS RECEIVABLE SUBSIDIARY LEDGER')} AR, {pages.get('ACCOUNTS PAYABLE SUBSIDIARY LEDGER')} AP"
    r.step("the loose-leaf pack adds both ledgers when asked, with the BIR header", pack)

    def cash():
        from ph_cas.expense import record_expense

        before = cash_position(co)
        sup = supplier("QA4 Mang Jose Tricycle", supplier_type="Individual", ph_vat_status="Non-VAT", ph_payee_type="Individual", ph_last_name="SANTOS", ph_first_name="JOSE")
        record_expense(company=co, supplier=sup, amount=120, description="Tricycle fare (cash position check)", expense_account=acc(co, "Travel Expenses"))
        p = cash_position(co)
        cash_acc = frappe.get_cached_value("Company", co, "default_cash_account")
        row = next(x for x in p["accounts"] if x["account"] == cash_acc)
        b0 = next(x for x in before["accounts"] if x["account"] == cash_acc)
        r.expect(flt(row["paid"] - b0["paid"], 2) == 120, f"paid moved {row['paid'] - b0['paid']}")
        r.expect(all(flt(x["opening"] + x["received"] - x["paid"], 2) == x["closing"] for x in p["accounts"]), "a row does not add up")
        gl_cash = flt(frappe.db.sql("""select coalesce(sum(debit) - sum(credit), 0) from `tabGL Entry` where company = %s and is_cancelled = 0
                                       and posting_date <= %s and account in %s""", (co, today(), [x["account"] for x in p["accounts"]]))[0][0], 2)
        r.expect(p["total"]["closing"] == gl_cash, f"closing {p['total']['closing']} vs GL {gl_cash}")
        from ph_cas.ph_cas.report.ph_cash_position.ph_cash_position import execute

        _c, rows, *_x = execute({"company": co, "day": today()})
        r.expect(rows[-1]["closing"] == gl_cash, "report total")
        return f"{len(p['accounts'])} cash and bank accounts; today in {p['total']['received']:,.2f}, out {p['total']['paid']:,.2f}; ending {gl_cash:,.2f} = the ledger"
    r.step("the cash position: beginning + in - out = ending, and it ties to the ledger", cash)


# ---- section: a home per role set, Your plan, Get help (B75) -------------------------------------
def s_role_homes(r: Runner):
    from ph_cas.home import dashboard
    from ph_cas.hosting.tiers import my_plan
    from ph_cas.setup import roles as R

    co = VAT_CORP
    email = "qa4.cashier@example.com"
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "QA4 Cashier", "send_welcome_email": 0, "role_profiles": [{"role_profile": R.CASHIER}]}).insert()

    def cashier_home():
        me = frappe.session.user
        frappe.set_user(email)
        try:
            d = dashboard.get(company=co)
        finally:
            frappe.set_user(me)
        r.expect(d["role_set"] == "Cashier", d["role_set"])
        r.expect(set(d["figures"]) <= {"sales_today", "invoices_today", "cash", "receivable", "overdue_receivable", "drafts_mine"}, f"leaks {sorted(d['figures'])}")
        r.expect("chart" not in d["sections"] and not d["monthly"] and not d["due"], "cashier sees the chart or the tax calendar")
        r.expect([a["label"] for a in d["create_actions"]] == ["New sales invoice", "Record a collection"], f"{d['create_actions']}")
        return f"cards {d['cards']}; no payables, VAT or withholding figures sent"
    r.step("a Cashier's home: today's counter only", cashier_home)

    def owner_home():
        d = dashboard.get(company=co)
        r.expect(d["role_set"] == "Owner" and "vat" in d["cards"] and "vat_position" in d["figures"], f"{d['role_set']} {d['cards']}")
        r.expect(any(a.get("action") == "record_expense" for a in d["create_actions"]), "no Record an expense")
        return f"{d['role_set']}: {len(d['cards'])} cards, sections {d['sections']}"
    r.step("the owner's home: the whole business, with Record an expense and Import", owner_home)

    def plan():
        p = my_plan()
        r.expect(p["tier"] and {x["label"] for x in p["rows"]} >= {"Users", "Invoices this month"}, f"{p}")
        return f"{p['tier']}: " + ", ".join(f"{x['label']} {x['used']}/{x['limit'] or 'no limit'}" for x in p["rows"])
    r.step("Help > Your plan: the tier, its limits and the use", plan)

    def help_menu():
        from ph_cas import branding

        branding._navbar_settings(branding.product_name())
        items = {x.item_label: x.action for x in frappe.get_single("Navbar Settings").help_dropdown if not x.hidden}
        r.expect(items.get("Get help") == "ph_cas.get_help()" and items.get("Your plan") == "ph_cas.show_plan()", f"{items}")
        r.expect(not [k for k in items if "Frappe" in k], f"framework items still shown: {items}")
        return "Help menu: " + ", ".join(items)
    r.step("the Help menu carries Get help and Your plan", help_menu)


# ---- section: counter and cash (B76) -------------------------------------------------------------
def s_counter(r: Runner):
    from ph_cas.books.cash import cash_position
    from ph_cas.controls.serial import series_name
    from ph_cas.expense import record_expense
    from ph_cas.setup.chart import CARD_ACCOUNT, setup_philippine_company

    co = VAT_CORP
    _sg, _sp, _sr, c_twa, c_walkin, _cg = _parties()
    svc = item("QA4 Repair Service")
    cash = frappe.get_cached_value("Company", co, "default_cash_account")
    cr_series = series_name(co, "00000", "Collection Receipt")
    state = {}

    def cr_next():
        return frappe.db.get_value("BIR Series", cr_series, "next_number") if frappe.db.exists("BIR Series", cr_series) else None

    def paid_now():
        state["cr0"], state["cash0"] = cr_next(), cash_position(co)
        si = sales_invoice(co, c_walkin, [(svc, 1, 1000)], ph_paid_now=1, ph_paid_mode="Cash")
        si.reload()
        r.expect(si.status == "Paid" and flt(si.outstanding_amount) == 0 and flt(si.paid_amount) == 1120, f"{si.status} {si.outstanding_amount} {si.paid_amount}")
        r.expect(si.bir_serial and si.is_pos == 1, f"serial {si.bir_serial}")
        r.expect(cr_next() == state["cr0"], f"collection receipt series moved {state['cr0']} -> {cr_next()}")
        r.expect(not frappe.get_all("Payment Entry Reference", filters={"reference_name": si.name, "docstatus": 1}), "a Payment Entry was made")
        state["si"] = si
        gl = {}
        for g in frappe.get_all("GL Entry", filters={"voucher_no": si.name, "is_cancelled": 0}, fields=["account", "debit", "credit"]):
            gl[g.account] = flt(gl.get(g.account, 0) + flt(g.debit) - flt(g.credit), 2)
        r.expect(gl.get(cash) == 1120 and gl.get(acc(co, "Sales")) == -1000 and gl.get(acc(co, "Output VAT")) == -120 and not gl.get(acc(co, "Debtors")), f"{gl}")
        return f"{si.name} serial {si.bir_serial}: Paid, 1,120.00 in cash (1,000 + 12% VAT); no Payment Entry, collection receipt series unchanged ({state['cr0']})"
    if not r.step("paid in full now: one invoice, paid, no collection receipt used", paid_now):
        return

    def books():
        si = state["si"]
        _c, rows = __import__("ph_cas.ph_cas.report.ph_cash_receipts_book.ph_cash_receipts_book", fromlist=["execute"]).execute(
            {"company": co, "from_date": today(), "to_date": today()})
        row = next((x for x in rows if x.get("reference") and si.bir_serial in str(x.get("reference")) and flt(x.get("cash_debit")) == 1120), None)
        r.expect(row, "no Cash Receipts Book row under the invoice serial")
        tie = rows[-1]
        r.expect("TIES TO THE LEDGER" in str(tie.get("particulars")), f"tie row {tie}")
        p = cash_position(co)
        moved = next(x["received"] for x in p["accounts"] if x["account"] == cash) - next(x["received"] for x in state["cash0"]["accounts"] if x["account"] == cash)
        r.expect(flt(moved, 2) == 1120, f"cash position received moved {moved}")
        return f"Cash Receipts Book row under {row['reference']} for 1,120.00; cash position received +1,120.00"
    r.step("the cash sale reaches the Cash Receipts Book and the cash position", books)

    def refusals():
        a = refused(sales_invoice, co, c_twa, [(svc, 1, 1000)], ph_paid_now=1, ph_paid_mode="Cash")
        r.expect("withholds tax" in a, a)
        if not frappe.db.exists("Mode of Payment", "QA4 E-wallet"):
            frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": "QA4 E-wallet", "type": "Bank", "enabled": 1}).insert()
        b = refused(sales_invoice, co, c_walkin, [(svc, 1, 1000)], ph_paid_now=1, ph_paid_mode="QA4 E-wallet")
        r.expect("has no account" in b, b)
        from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

        def credit_note():
            cn = make_sales_return(state["si"].name)
            cn.ph_paid_now = 1
            cn.ph_manual_invoice_no = "QA4-CN-" + frappe.generate_hash(length=6).upper()
            cn.insert()
        c = refused(credit_note)
        r.expect("credit or debit note" in c, c)
        return f"withholding customer: {a[:60]}...; mode without account: {b[:60]}...; credit note: {c[:50]}..."
    r.step("refused: a customer who withholds, a mode with no account, a credit note", refusals)

    def card():
        setup_philippine_company(co)
        card_acc = acc(co, CARD_ACCOUNT)
        r.expect(frappe.db.get_value("Account", card_acc, ["root_type", "account_type"]) == ("Liability", "Bank"), "card account")
        r.expect(frappe.db.get_value("Mode of Payment Account", {"parent": "Credit Card", "company": co}, "default_account") == card_acc, "mode account")
        before = cash_position(co)
        sup = supplier("QA4 Mang Jose Tricycle", supplier_type="Individual", ph_vat_status="Non-VAT", ph_payee_type="Individual", ph_last_name="SANTOS", ph_first_name="JOSE")
        out = record_expense(company=co, supplier=sup, amount=300, description="Fuel on the company card", expense_account=acc(co, "Travel Expenses"), mode_of_payment="Credit Card")
        gl = {g.account: flt(g.credit) for g in frappe.get_all("GL Entry", filters={"voucher_no": out["purchase_invoice"], "is_cancelled": 0}, fields=["account", "credit"]) if flt(g.credit)}
        r.expect(gl.get(card_acc) == 300, f"{gl}")
        after = cash_position(co)
        r.expect(card_acc not in [x["account"] for x in after["accounts"]] and after["total"]["paid"] == before["total"]["paid"], "the card shows as cash")
        from ph_cas.golive import go_live_checklist

        st = {i["key"]: i["status"] for i in go_live_checklist(co)}
        r.expect(st.get("card") == "done", f"{st}")
        return f"{card_acc} (liability, Bank type) with Mode of Payment Credit Card; a 300.00 card expense raises the card balance and leaves cash untouched"
    r.step("the company credit card: set up, used for an expense, kept out of cash", card)

    def cashier_sale():
        from ph_cas.setup import roles as R

        email = "qa4.cashier@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "QA4 Cashier", "send_welcome_email": 0, "role_profiles": [{"role_profile": R.CASHIER}]}).insert()
        me = frappe.session.user
        frappe.set_user(email)
        try:
            si = sales_invoice(co, c_walkin, [(svc, 2, 500)], ph_paid_now=1, ph_paid_mode="Cash")
        finally:
            frappe.set_user(me)
        r.expect(frappe.db.get_value("Sales Invoice", si.name, "status") == "Paid", "not paid")
        return f"{si.name}: the Cashier rang up a paid sale of {si.grand_total:,.2f}"
    r.step("the Cashier makes a paid sale at the counter", cashier_sale)


# ---- section: the print pack for the paper check (B78) -------------------------------------------
def s_paper_check(r: Runner):
    import io as _io

    from pypdf import PdfReader

    from ph_cas.invoicing import paper_check

    co = VAT_CORP

    def pack():
        si = frappe.get_all("Sales Invoice", filters={"company": co, "docstatus": 1, "is_return": 0, "is_debit_note": 0}, order_by="creation desc", pluck="name", limit=1)[0]
        before = frappe.db.count("PH Print Record", {"ref_name": si})
        data, found = paper_check.build(co)
        names = dict(found)
        r.expect(all(names.values()), f"missing documents: {names}")
        pages = PdfReader(_io.BytesIO(data)).pages
        r.expect(len(pages) >= 5, f"{len(pages)} pages")
        texts = [" ".join((p.extract_text() or "").split()) for p in pages]
        r.expect(all("SPECIMEN" in t for t in texts), "a page without the SPECIMEN mark")
        r.expect("exactly 100 mm" in texts[0] and "Actual size (100%)" in texts[0], "cover text")
        r.expect(frappe.db.count("PH Print Record", {"ref_name": si}) == before, "the pack counted a print")
        return f"{len(pages)} pages: cover with the 100 mm bar and checklist, then " + ", ".join(f"{k} {v}" for k, v in found) + "; no print counted"
    r.step("the print pack: cover, the four documents, SPECIMEN on every page, no print counted", pack)

    def true_size():
        data, _found = paper_check.build(co)
        widths = paper_check.bar_widths_mm(data, 0)
        bar = widths
        r.expect(bar and all(99.0 <= w <= 101.0 for w in bar), f"the 100 mm bar is drawn {bar} mm wide: the PDF engine is not printing at true size")
        return f"the bar is {bar[0]} mm in the PDF (so a print at Actual size gives 100 mm)"
    r.step("the PDF is at true size: the 100 mm bar is 100 mm", true_size)

    def roles_():
        from ph_cas.setup import roles as R

        email = "qa4.cashier@example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "QA4 Cashier", "send_welcome_email": 0, "role_profiles": [{"role_profile": R.CASHIER}]}).insert()
        me = frappe.session.user
        frappe.set_user(email)
        try:
            return refused(paper_check.download, co)
        finally:
            frappe.set_user(me)
    r.step("a Cashier cannot download the pack", roles_)


SECTIONS = {
    "companies": s_companies, "purchasing": s_purchasing, "sales": s_sales, "tasks": s_tasks, "inventory": s_inventory,
    "projects": s_projects, "assets": s_assets, "quality": s_quality, "crm": s_crm, "support": s_support,
    "industries": s_industries, "forms": s_forms, "inventory_tracking": s_inventory_tracking, "roles": s_roles, "reports": s_reports, "go_live": s_go_live, "expense": s_expense, "imports": s_imports, "ledgers": s_ledgers, "role_homes": s_role_homes, "counter": s_counter, "paper_check": s_paper_check,
}


@frappe.whitelist()
def run(section: str) -> dict:
    """One section of QA pass 4, as the signed-in user. Staging only."""
    if not (is_staging() or frappe.flags.in_test):
        frappe.throw("QA pass 4 runs only on the staging site.", frappe.PermissionError)
    if section not in SECTIONS:
        frappe.throw(f"Unknown section {section}. Choose one of: {', '.join(SECTIONS)}")
    r = Runner()
    SECTIONS[section](r)
    if not frappe.flags.in_test:
        frappe.db.commit()
    return r.result(section)
