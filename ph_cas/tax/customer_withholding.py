"""B13: withholding by customers and the 2307s received.

When a customer withholds (government, top withholding agent, online platform,
or on request), the invoice shows the creditable tax (ATC, rate, base, amount)
and the amount due net of it (RR 6-2026 "Less: Withholding Tax" from
16 Oct 2026). The receivable stays gross on the books; when the customer pays
the net amount, the Payment Entry books the difference to the creditable tax
account as a deduction, automatically. The 2307 the customer later issues is
recorded as PH 2307 Received and reconciled against those deductions.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ph_cas.setup.chart import account_for
from ph_cas.tax.rules import PHNoRuleError, resolve

WHT_FIELDS = [
    {"fieldname": "ph_wht_section", "fieldtype": "Section Break", "label": "Tax withheld by the customer", "insert_after": "ph_vat_rule", "collapsible": 1},
    {"fieldname": "ph_wht_applicable", "fieldtype": "Check", "label": "Customer withholds tax", "insert_after": "ph_wht_section", "description": "Set from the customer's profile (government, top withholding agent, platform). Tick to apply on request."},
    {"fieldname": "ph_wht_atc", "fieldtype": "Data", "label": "ATC (income tax)", "insert_after": "ph_wht_applicable", "depends_on": "ph_wht_applicable"},
    {"fieldname": "ph_wht_rate", "fieldtype": "Percent", "label": "Rate (%)", "insert_after": "ph_wht_atc", "depends_on": "ph_wht_applicable"},
    {"fieldname": "ph_wht_base", "fieldtype": "Currency", "label": "Base (net of VAT)", "read_only": 1, "insert_after": "ph_wht_rate", "depends_on": "ph_wht_applicable"},
    {"fieldname": "ph_wht_amount", "fieldtype": "Currency", "label": "Less: Withholding Tax (income)", "read_only": 1, "insert_after": "ph_wht_base", "depends_on": "ph_wht_applicable"},
    {"fieldname": "ph_wht_col", "fieldtype": "Column Break", "insert_after": "ph_wht_amount"},
    {"fieldname": "ph_wvat_atc", "fieldtype": "Data", "label": "ATC (VAT withheld)", "read_only": 1, "insert_after": "ph_wht_col", "depends_on": "ph_wht_applicable"},
    {"fieldname": "ph_wvat_amount", "fieldtype": "Currency", "label": "Less: VAT withheld (5%)", "read_only": 1, "insert_after": "ph_wvat_atc", "depends_on": "ph_wht_applicable"},
    {"fieldname": "ph_wpt_atc", "fieldtype": "Data", "label": "ATC (percentage tax withheld)", "read_only": 1, "insert_after": "ph_wvat_amount", "depends_on": "ph_wht_applicable"},
    {"fieldname": "ph_wpt_amount", "fieldtype": "Currency", "label": "Less: Percentage tax withheld", "read_only": 1, "insert_after": "ph_wpt_atc", "depends_on": "ph_wht_applicable"},
    {"fieldname": "ph_wht_total", "fieldtype": "Currency", "label": "Total withheld by the customer", "read_only": 1, "insert_after": "ph_wpt_amount", "bold": 1},
    {"fieldname": "ph_net_due", "fieldtype": "Currency", "label": "Amount due net of withholding", "read_only": 1, "insert_after": "ph_wht_total", "bold": 1},
    {"fieldname": "ph_wht_rules", "fieldtype": "Data", "label": "Rules applied", "read_only": 1, "insert_after": "ph_net_due"},
]

PE_FIELDS = [
    {"fieldname": "ph_wht_deducted", "fieldtype": "Currency", "label": "Tax withheld by the customer (booked as deductions)", "read_only": 1, "insert_after": "deductions"},
]


def setup():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Sales Invoice": WHT_FIELDS, "Payment Entry": PE_FIELDS}, ignore_validate=True, update=True)


def _payee_type(company: str) -> str:
    return frappe.get_cached_value("Company", company, "ph_taxpayer_type") or "Non-individual"


def _line_category(row) -> str:
    is_stock = frappe.get_cached_value("Item", row.item_code, "is_stock_item") if row.get("item_code") else 0
    return "goods" if is_stock else "services"


def _split_by_category(doc) -> dict:
    out = {"goods": 0.0, "services": 0.0}
    for row in doc.get("items") or []:
        if row.get("ph_vat_class") == "VAT-exempt" and doc.get("ph_tax_regime") == "VAT":
            pass  # exempt sales are still income payments; withholding applies to them too
        out[_line_category(row)] += flt(row.net_amount if row.get("net_amount") is not None else row.amount)
    return out


def compute(doc):
    """Fill the withholding block from the customer's profile and the rules."""
    customer = frappe.get_cached_doc("Customer", doc.customer) if doc.get("customer") else None
    manual = bool(doc.get("ph_wht_applicable")) and not (customer and (customer.get("ph_is_government") or customer.get("ph_top_withholding_agent") or customer.get("ph_is_platform")))
    applies = manual or (customer and (customer.get("ph_is_government") or customer.get("ph_top_withholding_agent") or customer.get("ph_is_platform")))
    manual_atc, manual_rate = doc.get("ph_wht_atc"), flt(doc.get("ph_wht_rate"))
    _clear(doc)
    if not applies:
        return
    doc.ph_wht_applicable = 1
    date = getdate(doc.posting_date)
    payee_type = _payee_type(doc.company)
    rules = []
    cats = _split_by_category(doc)
    base_total = flt(cats["goods"] + cats["services"], 2)
    doc.ph_wht_base = base_total

    if manual:
        if not manual_atc or not manual_rate:
            frappe.throw(_("Withholding on request needs the ATC and the rate the customer will apply."))
        doc.ph_wht_atc, doc.ph_wht_rate = manual_atc, manual_rate
        doc.ph_wht_amount = flt(base_total * manual_rate / 100, 2)
    elif customer.get("ph_is_government"):
        amt, atcs = 0.0, []
        for cat, base in cats.items():
            if not base:
                continue
            r = resolve("ewt", date, payor="government", category=cat, payee_type=payee_type)
            amt += flt(base * flt(r.rate) / 100, 2)
            atcs.append(r.atc)
            rules.append(r.rule_id)
        doc.ph_wht_atc = ",".join(atcs)
        doc.ph_wht_rate = _blended_rate(amt, base_total)
        doc.ph_wht_amount = flt(amt, 2)
        if doc.get("ph_tax_regime") == "VAT":
            vamt, vatcs = 0.0, []
            for cat, base in cats.items():
                if not base:
                    continue
                r = resolve("vat_withholding", date, payor="government", **{"class": cat})
                vamt += flt(base * flt(r.rate) / 100, 2)
                vatcs.append(r.atc)
                rules.append(r.rule_id)
            doc.ph_wvat_atc = ",".join(vatcs)
            doc.ph_wvat_amount = flt(vamt, 2)
        else:
            r = resolve("percentage", date, payor="government", vat="0")
            doc.ph_wpt_atc = r.atc
            doc.ph_wpt_amount = flt(flt(doc.get("ph_pt_base")) * flt(r.rate) / 100, 2)
            rules.append(r.rule_id)
    elif customer.get("ph_top_withholding_agent"):
        amt, atcs = 0.0, []
        for cat, base in cats.items():
            if not base:
                continue
            r = resolve("ewt", date, category=f"twa_{cat}", payee_type=payee_type)
            amt += flt(base * flt(r.rate) / 100, 2)
            atcs.append(r.atc)
            rules.append(r.rule_id)
        doc.ph_wht_atc = ",".join(atcs)
        doc.ph_wht_rate = _blended_rate(amt, base_total)
        doc.ph_wht_amount = flt(amt, 2)
    elif customer.get("ph_is_platform"):
        try:
            r = resolve("ewt", date, payor="platform", payee_type=payee_type)
        except PHNoRuleError:
            r = None
        if r:
            doc.ph_wht_atc = r.atc
            doc.ph_wht_rate = flt(r.rate)
            doc.ph_wht_amount = flt(flt(doc.grand_total or base_total) * flt(r.rate) / 100, 2)
            doc.ph_wht_base = flt(doc.grand_total or base_total, 2)
            rules.append(r.rule_id)
    doc.ph_wht_total = flt(flt(doc.ph_wht_amount) + flt(doc.ph_wvat_amount) + flt(doc.ph_wpt_amount), 2)
    doc.ph_net_due = flt(flt(doc.grand_total) - flt(doc.ph_wht_total), 2)
    doc.ph_wht_rules = ",".join(rules)


def _blended_rate(amount, base):
    return flt(amount / base * 100, 4) if base else 0


def _clear(doc):
    for f in ("ph_wht_atc", "ph_wvat_atc", "ph_wpt_atc", "ph_wht_rules"):
        doc.set(f, None)
    for f in ("ph_wht_rate", "ph_wht_base", "ph_wht_amount", "ph_wvat_amount", "ph_wpt_amount", "ph_wht_total"):
        doc.set(f, 0)
    doc.ph_net_due = flt(doc.get("grand_total"))


def validate(doc, method=None):
    """doc_events['Sales Invoice'].validate, after ph_cas.tax.vat.validate."""
    compute(doc)


def shows_less_withholding_line(doc) -> bool:
    """RR 6-2026: the printed invoice carries the line from 16 Oct 2026."""
    if not doc.get("ph_wht_applicable") or not flt(doc.get("ph_wht_total")):
        return False
    try:
        resolve("calendar", doc.posting_date, base=None, **{})
    except Exception:
        pass
    rule = frappe.db.get_value("PH Tax Rule", "INV-LESS-WHT-LINE", ["effective_from", "effective_to"], as_dict=True)
    if not rule:
        return False
    d = getdate(doc.posting_date)
    return getdate(rule.effective_from) <= d and (not rule.effective_to or d <= getdate(rule.effective_to))


# ---- payments ---------------------------------------------------------------


def payment_before_validate(doc, method=None):
    """Payment Entry: when a customer pays an invoice net of the tax it withheld,
    book the difference to the creditable tax accounts as deductions."""
    if doc.get("payment_type") != "Receive" or doc.get("party_type") != "Customer":
        return
    ours = [d for d in (doc.get("deductions") or []) if (d.get("description") or "").startswith("Withheld by customer")]
    previously = {}
    for d in ours:
        inv = (d.description or "").split(" on ", 1)[-1].split(" (", 1)[0]
        previously[inv] = previously.get(inv, 0.0) + flt(d.amount)
    doc.deductions = [d for d in (doc.get("deductions") or []) if d not in ours]
    total = 0.0
    for ref in doc.get("references") or []:
        if ref.reference_doctype != "Sales Invoice" or not ref.reference_name:
            continue
        if previously.get(ref.reference_name):
            # undo our earlier allocation of the withheld part before recomputing
            ref.allocated_amount = flt(ref.allocated_amount) - previously[ref.reference_name]
        si = frappe.db.get_value(
            "Sales Invoice",
            ref.reference_name,
            ["grand_total", "outstanding_amount", "ph_wht_amount", "ph_wvat_amount", "ph_wpt_amount", "ph_wht_total", "ph_wht_atc", "ph_wvat_atc", "ph_wpt_atc", "cost_center"],
            as_dict=True,
        )
        if not si or not flt(si.ph_wht_total):
            continue
        # Only when the customer actually short-pays by the withheld amount
        short = flt(ref.outstanding_amount if ref.get("outstanding_amount") is not None else si.outstanding_amount) - flt(ref.allocated_amount)
        if short <= 0 or short > flt(si.ph_wht_total) + 0.01:
            continue
        already = frappe.db.sql(
            """select coalesce(sum(d.amount),0) from `tabPayment Entry Deduction` d join `tabPayment Entry` p on p.name = d.parent
               where p.docstatus = 1 and p.name != %s and d.description like %s""",
            (doc.name or "", f"Withheld by customer on {ref.reference_name}%"),
        )[0][0]
        remaining = flt(si.ph_wht_total) - flt(already)
        if remaining <= 0:
            continue
        for purpose, amount, atc in (
            ("cwt_receivable", si.ph_wht_amount, si.ph_wht_atc),
            ("cvat_receivable", si.ph_wvat_amount, si.ph_wvat_atc),
            ("cpt_receivable", si.ph_wpt_amount, si.ph_wpt_atc),
        ):
            amount = min(flt(amount), short)
            if amount <= 0:
                continue
            doc.append(
                "deductions",
                {
                    "account": account_for(doc.company, purpose),
                    "cost_center": si.cost_center or frappe.get_cached_value("Company", doc.company, "cost_center"),
                    "amount": flt(amount, 2),
                    "description": f"Withheld by customer on {ref.reference_name} ({atc})",
                },
            )
            short -= amount
            total += amount
            # allocate the withheld part too, so the invoice closes
            ref.allocated_amount = flt(ref.allocated_amount) + amount
    doc.ph_wht_deducted = flt(total, 2)
