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

    def no_backdate():
        se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": co, "posting_date": add_days(today(), -5), "set_posting_time": 1,
                             "items": [{"item_code": nails, "qty": 1, "basic_rate": 80, "t_warehouse": wh}]})
        return refused(lambda: (se.insert(), se.submit()))
    r.step("D7: a back-dated stock entry is refused", no_backdate)

    def perpetual_off():
        r.expect(not frappe.get_cached_value("Company", co, "enable_perpetual_inventory"), "perpetual inventory is on")
        se = frappe.get_all("Stock Entry", filters={"company": co, "docstatus": 1}, pluck="name", limit=1)
        g = gl("Stock Entry", se[0]) if se else {}
        r.expect(not g, f"stock entry posted to the ledger {g}")
        return "no GL rows for stock entries"
    r.step("D7: perpetual inventory off (no stock GL)", perpetual_off)

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
        iss = frappe.get_doc({"doctype": "Issue", "subject": "QA4 Invoice printed without the ATP", "raised_by": "qa4.customer@example.com", "customer": _p[3],
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
            lines = frappe.get_all("PH Tax Return Line", filters={"parent": name}, fields=["item", "amount"], order_by="idx")
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


SECTIONS = {
    "companies": s_companies, "purchasing": s_purchasing, "sales": s_sales, "tasks": s_tasks, "inventory": s_inventory,
    "projects": s_projects, "assets": s_assets, "quality": s_quality, "crm": s_crm, "support": s_support,
    "industries": s_industries, "forms": s_forms,
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
