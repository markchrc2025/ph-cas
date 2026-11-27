"""B73: Philippine import templates and batch edit (after ECOUNT's Excel upload and Change Selected).

Four templates, each a CSV that opens in Excel:

- parties       customers and suppliers with their BIR details: TIN and branch code, payee type and
                the individual's names, VAT status, government / top withholding agent, and for a
                supplier the withholding category the tax engine reads.
- items         what is sold or bought: VAT class, stock or not, capital good, price, and the
                income and expense accounts for the company.
- balances      the old books' account balances at the cut-over day. A receivable or payable
                account's total is booked against Temporary Opening; the open items template then
                replaces it with one row per customer or supplier, and the Go-live checklist shows
                Temporary Opening back at zero when the two agree.
- open_items    what each customer still owes and each supplier is still owed, one row per old
                invoice or bill, as party rows in an opening Journal Entry (never as invoices: an
                old invoice is not a new BIR invoice, see ph_cas.golive).

check_import() reads a file (or rows) and reports every row's problems without saving anything;
run_import() saves only when every row passes, and all rows or none. batch_update() changes one
or more BIR fields on many customers, suppliers or items at once, each saved through its own
validation, so a wrong value is refused per record.
"""

from __future__ import annotations

import csv
import io
import re

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from ph_cas.setup.master_data import VAT_CLASS, VAT_STATUS, normalize_tin

YES = {"1", "y", "yes", "true", "x", "oo"}
VAT_STATUSES = VAT_STATUS.split("\n")
VAT_CLASSES = VAT_CLASS.split("\n")
PAYEE_TYPES = ["Individual", "Non-individual"]


def _ewt_categories():
    from ph_cas.tax.purchase import CATEGORIES

    return [c for c in CATEGORIES.split("\n") if c]


# key, label, required, help, example
TEMPLATES = {
    "parties": [
        ("party_type", "Customer or Supplier", 1, "Customer or Supplier", "Customer"),
        ("name", "Name", 1, "As it should appear in lists", "Marikina Builders Inc."),
        ("payee_type", "Payee type", 1, "Individual or Non-individual", "Non-individual"),
        ("tin", "TIN", 0, "9 digits, 000-000-000; the branch code goes in its own column", "000-123-456"),
        ("branch_code", "Branch code", 0, "5 digits; 00000 for the head office", "00000"),
        ("registered_name", "Registered name", 0, "Non-individual: the name on its COR (defaults to Name)", "MARIKINA BUILDERS INC."),
        ("last_name", "Last name", 0, "Individual: required", ""),
        ("first_name", "First name", 0, "Individual: required", ""),
        ("middle_name", "Middle name", 0, "Individual", ""),
        ("vat_status", "VAT status", 1, "VAT, Non-VAT or VAT-exempt", "VAT"),
        ("government", "Government agency or GOCC", 0, "yes or blank", ""),
        ("top_withholding_agent", "Top withholding agent", 0, "yes or blank", ""),
        ("ewt_category", "Withholding category", 0, "Supplier: professional, rent, contractor, goods, services, reduced_wholesale, or blank", ""),
        ("over_threshold", "Over the threshold or VAT-registered", 0, "Supplier, professionals: yes for the higher rate", ""),
        ("address_line1", "Address line 1", 0, "Registered address", "12 J.P. Rizal Street, Concepcion Uno"),
        ("address_line2", "Address line 2", 0, "City or municipality", "Marikina City"),
        ("zip", "ZIP code", 0, "4 digits", "1807"),
    ],
    "items": [
        ("item_code", "Item code", 1, "Unique code", "TILE-6060"),
        ("item_name", "Item name", 1, "", "Floor tile 60x60 (box)"),
        ("item_group", "Item group", 0, "An existing item group (defaults to Products or Services)", "Products"),
        ("uom", "Unit", 0, "An existing unit (defaults to Nos)", "Box"),
        ("stock_item", "Stock item", 0, "yes for goods counted in inventory", "yes"),
        ("vat_class", "VAT class", 1, "VATable, VAT-exempt, Zero-rated or Government", "VATable"),
        ("capital_good", "Capital good", 0, "yes for a depreciable asset", ""),
        ("selling_price", "Selling price", 0, "Standard selling price", "320"),
        ("cost", "Cost", 0, "Valuation rate for a stock item", "250"),
        ("income_account", "Income account", 0, "Account name for the company (defaults to the company's)", ""),
        ("expense_account", "Expense account", 0, "Account name for the company (defaults to the company's)", ""),
    ],
    "balances": [
        ("account", "Account", 1, "Account name as in the chart, with or without the company abbreviation", "Cash"),
        ("debit", "Debit", 0, "Debit balance at the cut-over day", "100000"),
        ("credit", "Credit", 0, "Credit balance at the cut-over day", ""),
    ],
    "open_items": [
        ("party_type", "Customer or Supplier", 1, "Customer or Supplier", "Customer"),
        ("party", "Name", 1, "An existing customer or supplier (import them first)", "Marikina Builders Inc."),
        ("reference_no", "Old invoice or bill no.", 1, "The number in the old books", "SI 001234"),
        ("reference_date", "Date", 1, "Its date, on or before the cut-over day", "2026-10-15"),
        ("amount", "Amount still owed", 1, "Positive; a negative amount is an advance or credit balance", "56000"),
    ],
}


# ---- reading -------------------------------------------------------------------------------------
def _columns(kind):
    if kind not in TEMPLATES:
        frappe.throw(_("Unknown template {0}. Choose one of: {1}").format(kind, ", ".join(TEMPLATES)))
    return TEMPLATES[kind]


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def _table_from_file(file_url: str) -> list[list]:
    f = frappe.get_doc("File", {"file_url": file_url})
    content = f.get_content()
    if (f.file_name or file_url).lower().endswith((".xlsx", ".xls")):
        from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

        return read_xlsx_file_from_attached_file(fcontent=content)
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(content)))


def _rows(kind, rows=None, csv_text=None, file_url=None) -> list[tuple[int, dict]]:
    """[(line number in the file, {key: text})]; lines starting with # and blank lines are skipped."""
    cols = _columns(kind)
    if isinstance(rows, str):
        rows = frappe.parse_json(rows)
    if rows:
        return [(i + 2, {k: str(r.get(k) if r.get(k) is not None else "").strip() for k, *_x in cols}) for i, r in enumerate(rows)]
    table = list(csv.reader(io.StringIO(csv_text))) if csv_text else _table_from_file(file_url) if file_url else []
    if not table:
        frappe.throw(_("The file is empty."))
    lookup = {}
    for k, label, *_x in cols:
        lookup[_norm(k)] = k
        lookup[_norm(label)] = k
    header = [lookup.get(_norm(h)) for h in table[0]]
    missing = [label for k, label, req, *_x in cols if req and k not in header]
    if missing:
        frappe.throw(_("The file is missing these columns: {0}. Start from the template.").format(", ".join(missing)))
    out = []
    for n, line in enumerate(table[1:], start=2):
        cells = ["" if c is None else str(c).strip() for c in line]
        if not any(cells) or cells[0].startswith("#") or _is_sample(kind, cells):
            continue
        out.append((n, {k: (cells[i] if i < len(cells) else "") for i, k in enumerate(header) if k}))
    return out


def _yes(v) -> int:
    return 1 if str(v or "").strip().lower() in YES else 0


def _num(v):
    s = re.sub(r"[,\s₱]|PHP", "", str(v or ""))
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return None


def _pick(v, choices):
    for c in choices:
        if _norm(c) == _norm(v):
            return c
    return None


def _account(company, name):
    if not name:
        return None
    abbr = frappe.get_cached_value("Company", company, "abbr")
    for cand in (name, f"{name} - {abbr}"):
        acc = frappe.db.get_value("Account", {"name": cand, "company": company}, ["name", "is_group", "account_type"], as_dict=True)
        if acc:
            return acc
    acc = frappe.db.get_value("Account", {"account_name": name, "company": company}, ["name", "is_group", "account_type"], as_dict=True)
    return acc


# ---- checking ------------------------------------------------------------------------------------
def _split_tin(r, e):
    """B94 (owner, IM-001): a TIN is read with or without dashes. 9 digits is the TIN; 12 digits is
    the TIN and a 3-digit branch; 14 digits is the TIN and a 5-digit branch. Anything else is refused
    (a TIN missing digits is never accepted). The branch code gets back the leading zeros Excel drops."""
    br = str(r.get("branch_code") or "").strip()
    if br.isdigit() and len(br) < 5:
        br = br.zfill(5)
    tin = str(r.get("tin") or "").strip()
    if tin:
        digits = re.sub(r"\D", "", tin)
        if len(digits) in (12, 14):
            own = digits[9:].zfill(5)
            if br and br != own:
                e.append(_("TIN {0} carries branch {1}, but the Branch code column says {2}").format(tin, own, br))
            br = br or own
            digits = digits[:9]
        if len(digits) == 9:
            r["tin"] = normalize_tin(digits)
        else:
            e.append(_("TIN {0} has {1} digits; it needs 9 (000-123-456), or 12 or 14 with the branch code. If Excel dropped leading zeros, format the TIN column as Text.").format(tin, len(digits)))
    r["branch_code"] = br


def _check_party(company, r, seen):
    e = []
    pt = _pick(r.get("party_type"), ["Customer", "Supplier"])
    if not pt:
        e.append(_("Customer or Supplier: write Customer or Supplier"))
    elif not _may_create(pt):
        # B96 (UAT LDG-247): a role that may not add suppliers (Staff) cannot add them by import either
        e.append(_("You may not add a {0}: this line needs a user who can.").format(_(pt).lower()))
    name = r.get("name")
    if not name:
        e.append(_("Name is required"))
    payee = _pick(r.get("payee_type") or "Non-individual", PAYEE_TYPES)
    if not payee:
        e.append(_("Payee type: Individual or Non-individual"))
    elif payee == "Individual" and not (r.get("last_name") and r.get("first_name")):
        e.append(_("An individual needs a last name and a first name (the alphalists report them separately)"))
    _split_tin(r, e)
    tin = r.get("tin")
    if tin:
        digits = re.sub(r"\D", "", tin)
        if len(digits) == 9:
            t = normalize_tin(digits)
            key = (pt, t, r.get("branch_code") or "00000")
            if key in seen and t != "000-111-222":
                e.append(_("TIN {0} branch {1} appears twice in the file (line {2})").format(t, key[2], seen[key]))
            seen.setdefault(key, r["_line"])
    br = r.get("branch_code")
    if br and not (br.isdigit() and len(br) == 5):
        e.append(_("Branch code must be 5 digits (00000 for the head office)"))
    if not _pick(r.get("vat_status"), VAT_STATUSES):
        e.append(_("VAT status: VAT, Non-VAT or VAT-exempt"))
    cat = r.get("ewt_category")
    if cat:
        if pt == "Customer":
            e.append(_("Withholding category is for suppliers (what the company withholds when it pays them)"))
        elif not _pick(cat, _ewt_categories()):
            e.append(_("Withholding category: one of {0}").format(", ".join(_ewt_categories())))
    z = r.get("zip")
    if z and z.isdigit() and len(z) < 4:
        z = r["zip"] = z.zfill(4)  # B94: Excel drops leading zeros
    if z and not (z.isdigit() and len(z) == 4):
        e.append(_("ZIP code must be 4 digits"))
    w = []
    if pt and name and frappe.db.exists(pt, name):
        w.append(_("{0} {1} already exists: its BIR details will be updated").format(_(pt), name))
    elif pt and tin and len(re.sub(r"\D", "", tin)) == 9:
        other = frappe.db.get_value(pt, {"ph_tin": normalize_tin(re.sub(r"\D", "", tin)), "ph_branch_code": br or "00000"}, "name")
        if other and normalize_tin(re.sub(r"\D", "", tin)) != "000-111-222":
            w.append(_("{0} {1} already has this TIN and branch").format(_(pt), other))
    if not tin and pt == "Supplier" and cat:
        w.append(_("No TIN: the 2307 and the alphalist need the supplier's TIN"))
    return e, w


def _check_item(company, r, seen):
    e, w = [], []
    code = r.get("item_code")
    if not code:
        e.append(_("Item code is required"))
    elif code in seen:
        e.append(_("Item code {0} appears twice in the file (line {1})").format(code, seen[code]))
    else:
        seen[code] = r["_line"]
    if not r.get("item_name"):
        e.append(_("Item name is required"))
    if not _pick(r.get("vat_class"), VAT_CLASSES):
        e.append(_("VAT class: VATable, VAT-exempt, Zero-rated or Government"))
    if r.get("item_group") and not frappe.db.exists("Item Group", r["item_group"]):
        e.append(_("Item group {0} does not exist").format(r["item_group"]))
    if r.get("uom") and not frappe.db.exists("UOM", r["uom"]):
        e.append(_("Unit {0} does not exist").format(r["uom"]))
    for f in ("selling_price", "cost"):
        v = _num(r.get(f))
        if v is None or v < 0:
            e.append(_("{0} must be a number, zero or more").format(dict((k, l) for k, l, *_x in TEMPLATES["items"])[f]))
    for f, want in (("income_account", "Income"), ("expense_account", "Expense")):
        if r.get(f):
            a = _account(company, r[f])
            if not a or a.is_group:
                e.append(_("{0} is not a posting account of {1}").format(r[f], company))
    if code and frappe.db.exists("Item", code):
        w.append(_("Item {0} already exists: its BIR details will be updated").format(code))
    return e, w


def _check_balance(company, r, seen):
    e, w = [], []
    a = _account(company, r.get("account"))
    if not a:
        e.append(_("Account {0} is not in {1}'s chart").format(r.get("account"), company))
    elif a.is_group:
        e.append(_("{0} is a group; use the account under it").format(a.name))
    dr, cr = _num(r.get("debit")), _num(r.get("credit"))
    if dr is None or cr is None or dr < 0 or cr < 0:
        e.append(_("Debit and credit must be numbers, zero or more"))
    elif bool(dr) == bool(cr):
        e.append(_("Fill in the debit or the credit, not both and not neither"))
    if a and a.account_type in ("Receivable", "Payable"):
        w.append(_("{0}: booked against Temporary Opening; the open items template then lists it by customer or supplier").format(a.name))
    if a and a.account_type == "Stock":
        w.append(_("{0}: also post the opening stock count (Stock Reconciliation, Opening Stock) with the same value").format(a.name))
    return e, w


def _check_open_item(company, r, seen):
    e, w = [], []
    pt = _pick(r.get("party_type"), ["Customer", "Supplier"])
    if not pt:
        e.append(_("Customer or Supplier: write Customer or Supplier"))
    elif not frappe.db.exists(pt, r.get("party")):
        e.append(_("{0} {1} does not exist: import the customers and suppliers first").format(_(pt), r.get("party")))
    if not r.get("reference_no"):
        e.append(_("The old invoice or bill number is required"))
    try:
        d = getdate(r.get("reference_date")) if r.get("reference_date") else None
    except Exception:
        d = None
    from ph_cas.golive import cutover

    day = cutover(company)
    if not d:
        e.append(_("Date must be a date (YYYY-MM-DD)"))
    elif day and d > getdate(day):
        e.append(_("Date {0} is after the cut-over day {1}: it belongs in the new books").format(d, day))
    amt = _num(r.get("amount"))
    if amt is None or not amt:
        e.append(_("Amount must be a number other than zero"))
    key = (pt, r.get("party"), r.get("reference_no"))
    if key in seen:
        e.append(_("This invoice appears twice in the file (line {0})").format(seen[key]))
    seen.setdefault(key, r["_line"])
    return e, w


CHECKS = {"parties": _check_party, "items": _check_item, "balances": _check_balance, "open_items": _check_open_item}


def _may_create(dt: str) -> bool:
    from ph_cas.setup.roles import COUNTER_LIMITED, cashier_limit

    return bool(frappe.has_permission(dt, "create")) and (dt not in COUNTER_LIMITED or cashier_limit(dt, "create"))


KIND_DOCTYPES = {"parties": ("Customer", "Supplier"), "items": ("Item",), "balances": ("Journal Entry",), "open_items": ("Journal Entry",)}


def _checked(kind, company, **src):
    # B96 (UAT LDG-247): only a role that may add these records may import them
    if not any(_may_create(dt) for dt in KIND_DOCTYPES.get(kind, ())):
        frappe.throw(_("You may not import these records."), frappe.PermissionError)
    if kind in ("balances", "open_items") and not company:
        frappe.throw(_("Choose the company."))
    rows = _rows(kind, **src)
    seen, out = {}, []
    for line, r in rows:
        r["_line"] = line
        e, w = CHECKS[kind](company, r, seen)
        out.append({"line": line, "row": r, "errors": e, "warnings": w})
    summary = []
    if kind in ("balances", "open_items"):
        from ph_cas.golive import cutover

        if not cutover(company):
            summary.append(_("Set {0}'s go-live date first (Company > Go-live date): opening entries are dated the day before it.").format(company))
    if kind == "balances" and out:
        dr = sum(_num(x["row"].get("debit")) or 0 for x in out)
        cr = sum(_num(x["row"].get("credit")) or 0 for x in out)
        if abs(dr - cr) >= 0.005:
            summary.append(_("Debits {0:,.2f} and credits {1:,.2f} differ by {2:,.2f}: the old trial balance must balance.").format(dr, cr, dr - cr))
    return out, summary


@frappe.whitelist()
def check_import(kind: str, company: str | None = None, rows=None, csv_text: str | None = None, file_url: str | None = None) -> dict:
    out, summary = _checked(kind, company, rows=rows, csv_text=csv_text, file_url=file_url)
    bad = [x for x in out if x["errors"]]
    return {"kind": kind, "rows": len(out), "ok": not bad and not summary, "summary": summary,
            "errors": [{"line": x["line"], "errors": x["errors"]} for x in bad],
            "warnings": [{"line": x["line"], "warnings": x["warnings"]} for x in out if x["warnings"]]}


# ---- saving --------------------------------------------------------------------------------------
def _save_party(company, r):
    pt = _pick(r["party_type"], ["Customer", "Supplier"])
    payee = _pick(r.get("payee_type") or "Non-individual", PAYEE_TYPES)
    values = {
        "ph_payee_type": payee, "ph_tin": normalize_tin(re.sub(r"\D", "", r["tin"])) if r.get("tin") else None,
        "ph_branch_code": r.get("branch_code") or "00000", "ph_registered_name": r.get("registered_name") or (r["name"].upper() if payee != "Individual" else None),
        "ph_last_name": r.get("last_name"), "ph_first_name": r.get("first_name"), "ph_middle_name": r.get("middle_name"),
        "ph_vat_status": _pick(r["vat_status"], VAT_STATUSES), "ph_is_government": _yes(r.get("government")),
        "ph_top_withholding_agent": _yes(r.get("top_withholding_agent")),
        "ph_address_line1": r.get("address_line1"), "ph_address_line2": r.get("address_line2"), "ph_zip": r.get("zip"),
    }
    if pt == "Supplier":
        values["ph_ewt_category"] = _pick(r["ewt_category"], _ewt_categories()) if r.get("ewt_category") else None
        values["ph_over_threshold"] = _yes(r.get("over_threshold"))
    if frappe.db.exists(pt, r["name"]):
        doc = frappe.get_doc(pt, r["name"])
        doc.update(values)
        doc.save()
        return doc.name, "updated"
    base = {"doctype": pt, **values}
    kind = "Individual" if payee == "Individual" else "Company"
    if pt == "Customer":
        from ph_cas.setup.master_data import leaf_group

        group = leaf_group("Customer Group", frappe.db.get_single_value("Selling Settings", "customer_group") or "Commercial")
        base.update({"customer_name": r["name"], "customer_type": kind, "customer_group": group,
                     "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"})
    else:
        base.update({"supplier_name": r["name"], "supplier_type": kind,
                     "supplier_group": _supplier_group()})
    doc = frappe.get_doc(base)
    doc.insert()
    return doc.name, "created"


def _save_item(company, r):
    stock = _yes(r.get("stock_item"))
    group = r.get("item_group") or ("Products" if stock else "Services")
    if not frappe.db.exists("Item Group", group):
        group = "All Item Groups"
    values = {"item_name": r["item_name"], "ph_vat_class": _pick(r["vat_class"], VAT_CLASSES), "ph_is_capital_good": _yes(r.get("capital_good"))}
    defaults = {"company": company}
    for f in ("income_account", "expense_account"):
        if r.get(f):
            defaults[f] = _account(company, r[f]).name
    if frappe.db.exists("Item", r["item_code"]):
        doc = frappe.get_doc("Item", r["item_code"])
        doc.update(values)
        if company and len(defaults) > 1:
            row = next((d for d in doc.item_defaults if d.company == company), None) or doc.append("item_defaults", {"company": company})
            row.update(defaults)
        doc.save()
        return doc.name, "updated"
    doc = frappe.get_doc({"doctype": "Item", "item_code": r["item_code"], "item_group": group, "stock_uom": r.get("uom") or "Nos", "is_stock_item": stock,
                          "include_item_in_manufacturing": 0, "standard_rate": _num(r.get("selling_price")) or 0, "valuation_rate": _num(r.get("cost")) or 0,
                          "item_defaults": [defaults] if company else [], **values})
    doc.insert()
    return doc.name, "created"


def _temporary_opening(company):
    acc = frappe.db.get_value("Account", {"company": company, "account_type": "Temporary", "is_group": 0}, "name")
    if not acc:
        frappe.throw(_("{0} has no Temporary Opening account. Run Set up Philippine company.").format(company))
    return acc


def _opening_je(company, rows, remark):
    from ph_cas.golive import cutover

    cc = frappe.get_cached_value("Company", company, "cost_center")
    je = frappe.get_doc({"doctype": "Journal Entry", "company": company, "posting_date": cutover(company), "voucher_type": "Opening Entry",
                         "is_opening": "Yes", "user_remark": remark, "accounts": [{"cost_center": cc, **x} for x in rows]})
    je.insert()
    je.submit()
    return je.name


def _save_balances(company, rows):
    temp = _temporary_opening(company)
    lines, to_temp = [], 0.0
    for r in rows:
        a = _account(company, r["account"])
        dr, cr = _num(r.get("debit")) or 0, _num(r.get("credit")) or 0
        if a.account_type in ("Receivable", "Payable"):
            to_temp += dr - cr
            continue
        lines.append({"account": a.name, "debit_in_account_currency": dr, "credit_in_account_currency": cr})
    if to_temp:
        lines.append({"account": temp, "debit_in_account_currency": max(to_temp, 0), "credit_in_account_currency": max(-to_temp, 0),
                      "user_remark": _("Receivables and payables, listed by party in the open items import")})
    return _opening_je(company, lines, _("Opening account balances (import)"))


def _save_open_items(company, rows):
    from erpnext.accounts.party import get_party_account

    temp = _temporary_opening(company)
    lines, net = [], 0.0
    for r in rows:
        pt = _pick(r["party_type"], ["Customer", "Supplier"])
        amt = _num(r["amount"])
        account = get_party_account(pt, r["party"], company)
        owed_to_us = amt if pt == "Customer" else -amt
        lines.append({"account": account, "party_type": pt, "party": r["party"],
                      "debit_in_account_currency": max(owed_to_us, 0), "credit_in_account_currency": max(-owed_to_us, 0),
                      "user_remark": _("Old {0} of {1}").format(r["reference_no"], r["reference_date"])})
        net += owed_to_us
    lines.append({"account": temp, "debit_in_account_currency": max(-net, 0), "credit_in_account_currency": max(net, 0)})
    return _opening_je(company, lines, _("Open invoices and bills from the old books (import)"))


@frappe.whitelist()
def run_import(kind: str, company: str | None = None, rows=None, csv_text: str | None = None, file_url: str | None = None) -> dict:
    out, summary = _checked(kind, company, rows=rows, csv_text=csv_text, file_url=file_url)
    bad = [x for x in out if x["errors"]]
    if bad or summary:
        lines = summary + [_("Line {0}: {1}").format(x["line"], "; ".join(x["errors"])) for x in bad[:20]]
        frappe.throw("<br>".join(lines), title=_("Nothing was imported"))
    if not out:
        frappe.throw(_("The file has no rows to import."))
    sp = "ph_import_" + frappe.generate_hash(length=8)
    frappe.db.savepoint(sp)
    try:
        if kind == "parties":
            done = [_save_party(company, x["row"]) for x in out]
        elif kind == "items":
            done = [_save_item(company, x["row"]) for x in out]
        elif kind == "balances":
            done = [(_save_balances(company, [x["row"] for x in out]), "posted")]
        else:
            done = [(_save_open_items(company, [x["row"] for x in out]), "posted")]
    except Exception:
        frappe.db.rollback(save_point=sp)
        raise
    return {"kind": kind, "rows": len(out), "created": [n for n, s in done if s == "created"], "updated": [n for n, s in done if s == "updated"],
            "posted": [n for n, s in done if s == "posted"]}


@frappe.whitelist()
def template_csv(kind: str) -> str:
    cols = _columns(kind)
    buf = io.StringIO()
    w = csv.writer(buf)
    # B94 (owner, IM-001): required columns carry * in the header; one sample row shows the format.
    # The sample row is skipped on import when it is left as it is.
    w.writerow([label + (" *" if req else "") for _k, label, req, *_x in cols])
    w.writerow([e for *_x, e in cols])
    return buf.getvalue()


def _is_sample(kind, cells: list[str]) -> bool:
    ex = [str(e) for *_x, e in _columns(kind)]
    got = [c for c in cells][: len(ex)] + [""] * max(0, len(ex) - len(cells))
    key = lambda c: _norm(c).lstrip("0")  # Excel drops leading zeros (00000 becomes 0)
    return [key(c) for c in got] == [key(c) for c in ex]


@frappe.whitelist()
def download_template(kind: str):
    frappe.response["type"] = "download"
    frappe.response["filename"] = f"sentire-ledger-{kind.replace('_', '-')}-template.csv"
    frappe.response["filecontent"] = "﻿" + template_csv(kind)


# ---- batch edit ----------------------------------------------------------------------------------
BATCH_FIELDS = {
    "Customer": ["ph_vat_status", "ph_payee_type", "ph_is_government", "ph_top_withholding_agent", "ph_branch_code", "ph_address_line2", "ph_zip", "disabled"],
    "Supplier": ["ph_vat_status", "ph_payee_type", "ph_ewt_category", "ph_over_threshold", "ph_is_government", "ph_top_withholding_agent", "ph_branch_code",
                 "ph_address_line2", "ph_zip", "disabled"],
    "Item": ["ph_vat_class", "ph_is_capital_good", "item_group", "disabled"],
}


@frappe.whitelist()
def batch_fields(doctype: str) -> list[dict]:
    if doctype not in BATCH_FIELDS:
        return []
    meta = frappe.get_meta(doctype)
    out = []
    for f in BATCH_FIELDS[doctype]:
        df = meta.get_field(f)
        if df:
            out.append({"fieldname": f, "label": df.label, "fieldtype": df.fieldtype, "options": df.options})
    return out


@frappe.whitelist()
def batch_update(doctype: str, names, values) -> dict:
    """Set the same BIR values on many records. Each record is saved through its own validation;
    a refused record is reported and the others still change."""
    if doctype not in BATCH_FIELDS:
        frappe.throw(_("Batch edit covers Customer, Supplier and Item."))
    names = frappe.parse_json(names) if isinstance(names, str) else names
    values = frappe.parse_json(values) if isinstance(values, str) else values
    bad = set(values) - set(BATCH_FIELDS[doctype])
    if bad:
        frappe.throw(_("These fields cannot be batch edited: {0}").format(", ".join(sorted(bad))))
    if not values:
        frappe.throw(_("Choose at least one field to change."))
    changed, refused = [], []
    for n in names:
        sp = "ph_batch_" + frappe.generate_hash(length=8)
        frappe.db.savepoint(sp)
        try:
            doc = frappe.get_doc(doctype, n)
            doc.check_permission("write")
            for k, v in values.items():
                doc.set(k, cint(v) if meta_is_check(doctype, k) else v)
            doc.save()
            changed.append(n)
        except Exception as e:
            frappe.db.rollback(save_point=sp)
            frappe.local.message_log = []
            refused.append({"name": n, "reason": frappe.utils.strip_html(str(e))[:200]})
    return {"changed": changed, "refused": refused}


def meta_is_check(doctype, fieldname) -> bool:
    df = frappe.get_meta(doctype).get_field(fieldname)
    return bool(df and df.fieldtype == "Check")


def _supplier_group():
    from ph_cas.setup.master_data import leaf_group

    return leaf_group("Supplier Group", frappe.db.get_single_value("Buying Settings", "supplier_group") or "Services")
