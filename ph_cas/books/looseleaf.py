"""B50: the books of accounts in the loose-leaf format (Excel and PDF).

A taxpayer that keeps loose-leaf books registers a sample format with its RDO
(BIR Form 1900, Permit to Use Loose-Leaf Books), prints the books on that
format, has them hardbound and submits them within 15 days after the taxable
year (through ORUS since RMC 4-2026), with a sworn statement giving the number
of volumes and pages of each book. So the format must not drift.

The layout follows the sample books the owner supplied (JuanTax exports,
January 2020): the book title; a header block (owner's name, owner's address,
TIN, period, name of user; run date, page, application software, permit to use
number); upper-case column names; one row per entry; a TOTAL row. What it does
not copy: amounts and dates stored as text, references that lose their leading
zeros, a gross purchase net of withholding in one book and gross in another,
"customer" headings on supplier books, and a ledger balance with the sign
reversed. Amounts are numbers with two decimals, dates are dates, references
are text, balances are debit-positive.

Every page carries the full header and "Page x of y", in the PDF and in the
Excel file alike (the Excel file is cut into the same pages with page breaks),
so both give the same page count for the sworn statement.
"""

import io
import math
import zipfile
from dataclasses import dataclass, field

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, now_datetime

from ph_cas.audit.header import company_facts, software_name, software_version
from ph_cas.books.common import cash_accounts, party_name, party_tin

ROWS_PER_PAGE = 20  # data rows per page (each up to two lines), the same in the PDF and the Excel file


@dataclass
class Col:
    label: str
    kind: str = "text"  # text, money, date_long (January 1, 2026), date (01/01/2026)
    width: float = 12  # relative width (Excel characters)


@dataclass
class Book:
    code: str
    title: str
    columns: list
    rows: list = field(default_factory=list)  # lists of values, one per column
    styles: list = field(default_factory=list)  # per row: "", "bold" (totals and ledger subtotals)
    extra_header: list = field(default_factory=list)  # [(label, value)] added to the right block

    def add(self, values, style=""):
        self.rows.append(values)
        self.styles.append(style)

    @property
    def pages(self) -> int:
        return max(1, math.ceil(len(self.rows) / ROWS_PER_PAGE))


# ---------------------------------------------------------------- the header

def _tin(company) -> tuple[str, str]:
    f = company_facts(company)
    label = "VAT Reg. TIN" if f["vat_status"] == "VAT" else "Non-VAT Reg. TIN" if f["vat_status"] else "TIN"
    return label, (f"{f['tin']}-{f['branch']}" if f["tin"] else "")


def _period(start, end) -> str:
    s, e = getdate(start), getdate(end)
    if (s.year, s.month) == (e.year, e.month) and s.day == 1 and add_days(e, 1).month != e.month:
        return s.strftime("%B %Y")
    if s.day == 1 and add_days(e, 1).month != e.month:
        return f"{s.strftime('%B %Y')} to {e.strftime('%B %Y')}"
    return f"{s.strftime('%B %d, %Y')} to {e.strftime('%B %d, %Y')}"


def header(company, start, end, user=None) -> dict:
    """The facts every page of every book carries."""
    c = frappe.get_cached_doc("Company", company)
    f = company_facts(company)
    address = f["address"] or ", ".join(x.strip() for x in (c.get("ph_registered_address") or "").splitlines() if x.strip())
    if c.get("ph_zip") and c.get("ph_zip") not in address:
        address = f"{address} {c.get('ph_zip')}".strip()
    tin_label, tin = _tin(company)
    user = user or frappe.session.user
    permit = c.get("ph_looseleaf_permit_no") or c.get("ph_accn") or ""
    permit_date = c.get("ph_looseleaf_permit_date") or (c.get("ph_accn_date") if not c.get("ph_looseleaf_permit_no") else None)
    return {
        "owner": f["name"], "address": address, "tin_label": tin_label, "tin": tin, "period": _period(start, end),
        "user": frappe.utils.get_fullname(user) or user, "run_date": now_datetime().strftime("%m-%d-%Y"),
        "software": f"{software_name()} {software_version()}", "permit": permit,
        "permit_date": getdate(permit_date).strftime("%m-%d-%Y") if permit_date else "",
    }


# ---------------------------------------------------------------- the books

def _invoice_no(si) -> str:
    return si.get("ph_manual_invoice_no") or si.get("bir_serial") or si.name


def _items(doctype, name) -> str:
    items = frappe.get_all(f"{doctype} Item", filters={"parent": name}, fields=["item_name"], order_by="idx", limit=3)
    return ", ".join(i.item_name for i in items)[:120]


def _address(party_type, party, display=None) -> str:
    l1, l2, z = frappe.db.get_value(party_type, party, ["ph_address_line1", "ph_address_line2", "ph_zip"]) or (None, None, None)
    a = " ".join(p.strip() for p in [l1, l2] if p and p.strip())
    if z and z not in a:
        a = f"{a} {z}".strip()
    return a or frappe.utils.strip_html(display or "").replace("\n", " ").strip()


def _purchase_rate(end) -> float:
    from ph_cas.tax.rules import resolve

    return flt(resolve("vat", end, side="purchase").rate) or 12


def _sales_split(si) -> dict:
    """VATable (or percentage-tax base for a Non-VAT seller), exempt, zero-rated and VAT of one invoice."""
    vatable = flt(si.ph_vatable_sales) or flt(si.get("ph_pt_base"))
    return {"vatable": vatable, "exempt": flt(si.ph_exempt_sales), "zero": flt(si.ph_zero_rated_sales), "vat": flt(si.ph_vat_amount)}


def _purchase_split(pi, rate) -> dict:
    vat = flt(pi.ph_input_vat_goods) + flt(pi.ph_input_vat_services) + flt(pi.ph_input_vat_capital)
    vatable = vat * 100 / rate + (flt(pi.ph_vat_cost) * 100 / rate if flt(pi.get("ph_vat_cost")) else 0)
    exempt = flt(pi.ph_exempt_purchases) + (flt(pi.ph_rc_base) if flt(pi.get("ph_rc_vat")) else 0)
    return {"vatable": flt(vatable, 2), "exempt": flt(exempt, 2), "vat": flt(vat, 2)}


SI_FIELDS = ["name", "posting_date", "bir_serial", "ph_manual_invoice_no", "customer", "customer_name", "is_return", "is_debit_note", "address_display",
             "ph_vatable_sales", "ph_exempt_sales", "ph_zero_rated_sales", "ph_vat_amount", "ph_pt_base", "discount_amount", "grand_total"]
PI_FIELDS = ["name", "posting_date", "bill_no", "supplier", "supplier_name", "is_return", "ph_input_vat_goods", "ph_input_vat_services", "ph_input_vat_capital",
             "ph_exempt_purchases", "ph_rc_vat", "ph_rc_base", "ph_vat_cost", "discount_amount", "grand_total"]

SALES_COLS = [Col("GL DATE", "date_long", 16), Col("TIN", "text", 17), Col("CUSTOMER NAME", "text", 24), Col("CUSTOMER ADDRESS", "text", 26),
              Col("DESCRIPTION", "text", 22), Col("DOCUMENT TYPE", "text", 13), Col("INVOICE NO.", "text", 13), Col("VATABLE SALES / AMOUNT", "money", 15),
              Col("VAT EXEMPT SALES", "money", 14), Col("ZERO RATED SALES", "money", 14), Col("VAT AMT", "money", 13), Col("DEFERRED VAT AMT", "money", 13),
              Col("DISCOUNT", "money", 12), Col("GROSS SALES", "money", 15)]
PURCHASE_COLS = [Col("GL DATE", "date_long", 16), Col("TIN", "text", 17), Col("SUPPLIER NAME", "text", 24), Col("SUPPLIER ADDRESS", "text", 26),
                 Col("DESCRIPTION", "text", 22), Col("DOCUMENT TYPE", "text", 13), Col("REFERENCE NO.", "text", 14), Col("VATABLE PURCHASE / AMOUNT", "money", 16),
                 Col("VAT EXEMPT PURCHASE", "money", 15), Col("VAT AMT", "money", 13), Col("DEFERRED VAT AMT", "money", 13), Col("DISCOUNT", "money", 12),
                 Col("GROSS PURCHASE", "money", 15)]


def _total_row(book, first_money: int, sums: list):
    row = [None] * len(book.columns)
    row[first_money - 1] = "TOTAL"
    for i, v in enumerate(sums):
        row[first_money + i] = flt(v, 2)
    book.add(row, "bold")


def sales_journal(company, start, end) -> Book:
    """One line per invoice, credit note (negative) and debit note."""
    b = Book("SJ", "SALES JOURNAL", SALES_COLS)
    tot = [0.0] * 7
    pcache = {}
    for si in frappe.get_all("Sales Invoice", filters={"company": company, "docstatus": 1, "posting_date": ("between", [start, end])},
                             fields=SI_FIELDS, order_by="posting_date, bir_serial, name"):
        s = _sales_split(si)
        disc = flt(si.discount_amount)
        gross = s["vatable"] + s["exempt"] + s["zero"] + s["vat"]
        kind = "Credit Note" if si.is_return else "Debit Note" if si.is_debit_note else "Invoice"
        vals = [s["vatable"], s["exempt"], s["zero"], s["vat"], 0.0, disc, gross]
        b.add([si.posting_date, party_tin("Customer", si.customer, pcache), si.customer_name, _address("Customer", si.customer, si.address_display),
               _items("Sales Invoice", si.name), kind, _invoice_no(si), *[flt(v, 2) for v in vals]])
        tot = [a + v for a, v in zip(tot, vals)]
    _total_row(b, 7, tot)
    return b


def purchase_journal(company, start, end) -> Book:
    """One line per supplier bill; gross purchase is before withholding."""
    b = Book("PJ", "PURCHASE JOURNAL", PURCHASE_COLS)
    rate, tot, pcache = _purchase_rate(end), [0.0] * 6, {}
    for pi in frappe.get_all("Purchase Invoice", filters={"company": company, "docstatus": 1, "posting_date": ("between", [start, end])},
                             fields=PI_FIELDS, order_by="posting_date, name"):
        s = _purchase_split(pi, rate)
        disc = flt(pi.discount_amount)
        vals = [s["vatable"], s["exempt"], s["vat"], 0.0, disc, s["vatable"] + s["exempt"] + s["vat"]]
        b.add([pi.posting_date, party_tin("Supplier", pi.supplier, pcache), pi.supplier_name, _address("Supplier", pi.supplier),
               _items("Purchase Invoice", pi.name), "Debit Memo" if pi.is_return else "Invoice", pi.bill_no or pi.name, *[flt(v, 2) for v in vals]])
        tot = [a + v for a, v in zip(tot, vals)]
    _total_row(b, 7, tot)
    return b


def _cash_vouchers(company, start, end, side: str):
    """Vouchers with a cash or bank debit (receipts) or credit (disbursements) in the period, with that cash amount."""
    cash = cash_accounts(company)
    if not cash:
        return []
    col = "debit" if side == "in" else "credit"
    return frappe.db.sql(
        f"""select voucher_type, voucher_no, posting_date, sum({col}) as cash
            from `tabGL Entry` where company = %(c)s and is_cancelled = 0 and posting_date between %(s)s and %(e)s
              and account in %(cash)s and {col} > 0
            group by voucher_type, voucher_no, posting_date order by posting_date, voucher_no""",
        {"c": company, "s": start, "e": end, "cash": tuple(cash)}, as_dict=True)


def _cash_book(company, start, end, side: str) -> Book:
    """Collections (side in) or payments (side out) in the columns of the sales or
    purchase journal: each payment is split by the VAT buckets of the invoices it
    settles, in proportion to the amount applied; anything not applied to an
    invoice (advances, other receipts or payments) is in the AMOUNT column.
    DISCOUNT holds deductions taken on the payment (such as tax withheld), so
    GROSS less DISCOUNT is the cash received or paid."""
    sales = side == "in"
    b = Book("CRJ" if sales else "CDJ", "CASH RECEIPT JOURNAL" if sales else "DISBURSEMENT JOURNAL", SALES_COLS if sales else PURCHASE_COLS)
    if sales:
        b.columns = SALES_COLS[:6] + [Col("REFERENCE NO.", "text", 14)] + SALES_COLS[7:]
    keys = ["vatable", "exempt", "zero", "vat"] if sales else ["vatable", "exempt", "vat"]
    rate, pcache = _purchase_rate(end), {}
    tot = [0.0] * (len(keys) + 3)
    for v in _cash_vouchers(company, start, end, side):
        split = {k: 0.0 for k in keys}
        deductions, party_type, party, ref, desc, kind = 0.0, None, None, v.voucher_no, "", v.voucher_type
        if v.voucher_type == "Payment Entry":
            pe = frappe.get_doc("Payment Entry", v.voucher_no)
            party_type, party, kind = pe.party_type, pe.party, "Collection Receipt" if sales else "Payment"
            ref = pe.get("bir_serial") or pe.reference_no or pe.name
            # ERPNext writes "Amount PHP ... received from ..." when the user typed no
            # remark (custom_remarks off): the book says which invoices were paid instead.
            desc = (pe.remarks or "").replace("\n", " ")[:120] if pe.get("custom_remarks") else ""
            paid, invoice_withheld = [], 0.0
            deductions = sum(flt(d.amount) for d in pe.get("deductions") or [])
            applied = 0.0
            for r in pe.references:
                if r.reference_doctype not in ("Sales Invoice", "Purchase Invoice"):
                    continue
                d = frappe.db.get_value(r.reference_doctype, r.reference_name, SI_FIELDS if sales else PI_FIELDS, as_dict=True)
                total = flt(d.grand_total)
                if not total:
                    continue
                parts = _sales_split(d) if sales else _purchase_split(d, rate)
                share = flt(r.allocated_amount) / total
                for k in keys:
                    split[k] += parts[k] * share
                if not sales:
                    # Tax withheld on the supplier invoice: the book shows the purchase
                    # before withholding, so the withheld part goes in DISCOUNT and
                    # GROSS less DISCOUNT stays the cash paid.
                    withheld = sum(parts.values()) - total
                    if withheld >= 0.005:
                        invoice_withheld += withheld * share
                applied += flt(r.allocated_amount)
                nos = frappe.db.get_value(r.reference_doctype, r.reference_name, ["ph_manual_invoice_no", "bir_serial"] if sales else ["bill_no", "name"])
                paid.append(nos[0] or nos[1] or r.reference_name)
            if not desc:
                what = ("Collection of invoice " if sales else "Payment of supplier invoice ") if len(paid) == 1 else ("Collection of invoices " if sales else "Payment of supplier invoices ")
                desc = (what + ", ".join(paid)) if paid else ("Advance from customer" if sales else "Advance to supplier")
            rest = flt(v.cash) + deductions - applied
            if abs(rest) >= 0.005:
                split["vatable"] += rest  # the AMOUNT part of the first money column
            deductions += invoice_withheld
        else:
            first = frappe.db.get_value("GL Entry", {"voucher_no": v.voucher_no, "voucher_type": v.voucher_type, "is_cancelled": 0, "party": ("is", "set")}, ["party_type", "party"], as_dict=True)
            if first:
                party_type, party = first.party_type, first.party
            desc = (frappe.db.get_value(v.voucher_type, v.voucher_no, "user_remark") if v.voucher_type == "Journal Entry" else "") or v.voucher_type
            desc = str(desc).replace("\n", " ")[:120]
            split["vatable"] = flt(v.cash)
        gross = sum(split.values())
        vals = [*(split[k] for k in keys), 0.0, deductions, gross]
        b.add([v.posting_date, party_tin(party_type, party, pcache), party_name(party_type, party, pcache), _address(party_type, party) if party_type in ("Customer", "Supplier") else "",
               desc, kind, ref, *[flt(x, 2) for x in vals]])
        tot = [a + x for a, x in zip(tot, vals)]
    _total_row(b, 7, tot)
    return b


def cash_receipt_journal(company, start, end) -> Book:
    return _cash_book(company, start, end, "in")


def disbursement_journal(company, start, end) -> Book:
    return _cash_book(company, start, end, "out")


GJ_TYPES_SKIPPED = ("Sales Invoice", "Purchase Invoice", "Payment Entry")


def _account_title(account, cache) -> str:
    if account not in cache:
        name, number = frappe.db.get_value("Account", account, ["account_name", "account_number"]) or (account, None)
        cache[account] = f"{name} ({number})" if number else name
    return cache[account]


def _doc_ref(voucher_type, voucher_no, cache) -> str:
    key = (voucher_type, voucher_no)
    if key not in cache:
        ref = None
        if voucher_type == "Sales Invoice":
            ref = _invoice_no(frappe.db.get_value("Sales Invoice", voucher_no, ["name", "bir_serial", "ph_manual_invoice_no"], as_dict=True))
        elif voucher_type == "Purchase Invoice":
            ref = frappe.db.get_value("Purchase Invoice", voucher_no, "bill_no")
        elif voucher_type == "Payment Entry":
            ref = frappe.db.get_value("Payment Entry", voucher_no, "bir_serial") or frappe.db.get_value("Payment Entry", voucher_no, "reference_no")
        elif voucher_type == "Journal Entry":
            remark = (frappe.db.get_value("Journal Entry", voucher_no, "user_remark") or "").replace("\n", " ").strip()
            ref = f"{remark[:90]} | {voucher_no}" if remark else voucher_no
        cache[key] = ref or voucher_no
    return cache[key]


def general_journal(company, start, end) -> Book:
    """Entries that are not sales, purchases or cash: journal entries without a
    cash or bank line and the other vouchers (stock, depreciation, closing)."""
    b = Book("GJ", "GENERAL JOURNAL", [Col("GL DATE", "date", 12), Col("REFERENCE", "text", 46), Col("ACCOUNT", "text", 36), Col("DEBIT", "money", 16), Col("CREDIT", "money", 16)])
    cash = cash_accounts(company)
    rows = frappe.db.sql(
        """select posting_date, voucher_type, voucher_no, account, debit, credit from `tabGL Entry`
           where company = %s and is_cancelled = 0 and posting_date between %s and %s and voucher_type not in %s
           order by posting_date, voucher_no, creation""", (company, start, end, GJ_TYPES_SKIPPED), as_dict=True)
    touches_cash = {r.voucher_no for r in rows if r.account in cash}
    acache, rcache, td, tc = {}, {}, 0.0, 0.0
    for r in rows:
        if r.voucher_no in touches_cash:
            continue
        b.add([r.posting_date, _doc_ref(r.voucher_type, r.voucher_no, rcache), _account_title(r.account, acache), flt(r.debit), flt(r.credit)])
        td, tc = td + flt(r.debit), tc + flt(r.credit)
    b.add([None, None, "TOTAL", flt(td, 2), flt(tc, 2)], "bold")
    return b


SOURCE = {"Sales Invoice": "SALES", "Purchase Invoice": "PURCHASE", "Journal Entry": "MJ", "Stock Entry": "STOCK", "Purchase Receipt": "STOCK",
          "Delivery Note": "STOCK", "Stock Reconciliation": "STOCK", "Period Closing Voucher": "CLOSING", "Asset": "ASSET"}


def general_ledger(company, start, end) -> Book:
    """Per account: opening balance, the entries with a running balance
    (debit-positive), Total and Net Movement; a TOTAL of all debits and credits."""
    b = Book("GL", "GENERAL LEDGER", [Col("GL DATE", "date", 12), Col("REFERENCE", "text", 11), Col("BRIEF DESCRIPTION / EXPLANATION", "text", 40),
                                       Col("ACCOUNT TITLE", "text", 32), Col("DEBITS", "money", 16), Col("CREDITS", "money", 16), Col("BALANCE", "money", 17)])
    entries = frappe.db.sql(
        """select g.posting_date, g.voucher_type, g.voucher_no, g.account, g.debit, g.credit, a.account_type, a.lft
           from `tabGL Entry` g join `tabAccount` a on a.name = g.account
           where g.company = %s and g.is_cancelled = 0 and g.posting_date between %s and %s
           order by a.lft, g.posting_date, g.creation""", (company, start, end), as_dict=True)
    accounts, seen = [], set()
    for e in entries:
        if e.account not in seen:
            seen.add(e.account)
            accounts.append(e.account)
    acache, rcache, ptype, td, tc = {}, {}, {}, 0.0, 0.0
    for account in accounts:
        title = _account_title(account, acache)
        bal = flt(frappe.db.sql("""select coalesce(sum(debit) - sum(credit), 0) from `tabGL Entry`
                                   where company = %s and account = %s and is_cancelled = 0 and posting_date < %s""", (company, account, start))[0][0], 2)
        b.add([None, None, "Opening Balance", title, None, None, bal], "bold")
        d = c = 0.0
        for e in (x for x in entries if x.account == account):
            source = SOURCE.get(e.voucher_type, e.voucher_type.upper()[:10])
            if e.voucher_type == "Payment Entry":
                if e.voucher_no not in ptype:
                    ptype[e.voucher_no] = frappe.db.get_value("Payment Entry", e.voucher_no, "payment_type")
                source = {"Receive": "RECEIPT", "Pay": "PAY"}.get(ptype[e.voucher_no], "TRANSFER")
            elif e.voucher_type in ("Sales Invoice", "Purchase Invoice") and e.account_type == "Tax":
                source = "TAX"
            bal = flt(bal + flt(e.debit) - flt(e.credit), 2)
            b.add([e.posting_date, source, _doc_ref(e.voucher_type, e.voucher_no, rcache), title, flt(e.debit), flt(e.credit), bal])
            d, c = d + flt(e.debit), c + flt(e.credit)
        b.add([None, None, "Total", title, flt(d, 2), flt(c, 2), bal], "bold")
        net = flt(d - c, 2)
        b.add([None, None, "Net Movement", title, net if net > 0 else 0.0, -net if net < 0 else 0.0, bal], "bold")
        td, tc = td + d, tc + c
    b.add([None, None, "TOTAL", None, flt(td, 2), flt(tc, 2), None], "bold")
    b.extra_header = [("VALIDITY DATE", "permit_date")]
    return b


BOOKS = [
    ("SJ", "Sales Journal", sales_journal),
    ("PJ", "Purchase Journal", purchase_journal),
    ("CRJ", "Cash Receipt Journal", cash_receipt_journal),
    ("CDJ", "Disbursement Journal", disbursement_journal),
    ("GJ", "General Journal", general_journal),
    ("GL", "General Ledger", general_ledger),
]


# ---------------------------------------------------------------- Excel

def _header_rows(h: dict, book: Book, page: int) -> tuple[list, list]:
    left = [("OWNER'S NAME", h["owner"]), ("OWNER'S ADDRESS", h["address"]), (h["tin_label"], h["tin"]), ("PERIOD", h["period"]), ("NAME OF USER", h["user"])]
    right = [("RUN DATE", h["run_date"]), ("PAGE", f"Page {page} of {book.pages}"), ("APPLICATION SOFTWARE", h["software"]), ("PERMIT TO USE NO.", h["permit"])]
    for label, key in book.extra_header:
        right.append((label, h.get(key, "")))
    return left, right


HEADER_LINES = 9  # title, blank, five header lines, blank, column names


def _span_from_start(widths, start, need):
    """The last 1-based column of a range from column start+1 at least need characters wide."""
    total, i = 0, start
    while i < len(widths) and total < need:
        total += widths[i]
        i += 1
    return max(i, start + 1)


def _span_from_end(widths, end, need):
    """The first 1-based column of a range ending at column end at least need characters wide."""
    total, i = 0, end
    while i > 1 and total < need:
        total += widths[i - 1]
        i -= 1
    return i + 1 if total >= need else max(i, 1)


def to_xlsx(book: Book, h: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.pagebreak import Break

    wb = Workbook()
    ws = wb.active
    ws.title = book.title.title()[:31]
    n = len(book.columns)
    # A long date (November 14, 2026) needs 17 characters or Excel shows ###.
    widths = [max(c.width, 17) if c.kind == "date_long" else c.width for c in book.columns]
    # The header block sits in merged ranges wide enough for the labels, so no
    # label is cut off when a narrow first column (GL DATE) sits under it.
    la = _span_from_start(widths, 0, 21)  # left labels: columns 1..la
    vb = _span_from_end(widths, n, 20)  # right values: columns vb..n
    lb = _span_from_end(widths, vb - 1, 24)  # right labels: columns lb..vb-1
    stacked = sum(widths[la:lb - 1]) < 30  # too few columns: the right block goes under the left one
    if stacked:
        lb, vb = 1, la + 1
    bold, thin = Font(name="Calibri", bold=True), Side(style="thin")
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    small = Font(name="Calibri", size=9)

    def put(row, c1, c2, text):
        cell = ws.cell(row, c1, text)
        cell.font = small
        if c2 > c1:
            ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)

    r = 1
    for page in range(1, book.pages + 1):
        ws.cell(r, 1, book.title).font = Font(name="Calibri", bold=True, size=12)
        left, right = _header_rows(h, book, page)
        if stacked:
            for k, (label, value) in enumerate(left + right):
                put(r + 2 + k, 1, la, label)
                put(r + 2 + k, la + 1, n, f": {value}")
            hr = r + 2 + len(left) + len(right) + 1
        else:
            for k, (label, value) in enumerate(left):
                put(r + 2 + k, 1, la, label)
                put(r + 2 + k, la + 1, lb - 1, f": {value}")
            for k, (label, value) in enumerate(right):
                put(r + 2 + k, lb, vb - 1, label)
                put(r + 2 + k, vb, n, f": {value}")
            hr = r + 2 + max(len(left), len(right)) + 1
        for i, col in enumerate(book.columns, 1):
            cell = ws.cell(hr, i, col.label)
            cell.font = bold
            cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
            cell.border = Border(top=thin, bottom=thin)
        ws.row_dimensions[hr].height = 30
        r = hr + 1
        chunk = slice((page - 1) * ROWS_PER_PAGE, page * ROWS_PER_PAGE)
        for values, style in zip(book.rows[chunk], book.styles[chunk]):
            # Like the PDF, a row shows at most two lines: the cell keeps the full
            # text and the fixed height keeps the page count the same as the PDF's.
            two = any(c.kind == "text" and v and len(str(v)) > widths[i] * 1.1 for i, (c, v) in enumerate(zip(book.columns, values)))
            ws.row_dimensions[r].height = 26 if two else 13.5
            for i, (col, v) in enumerate(zip(book.columns, values), 1):
                if v is None or v == "":
                    continue
                cell = ws.cell(r, i)
                cell.font = Font(name="Calibri", size=10, bold=style == "bold")
                cell.alignment = Alignment(vertical="top")
                if col.kind == "money":
                    cell.value = flt(v, 2)
                    cell.number_format = "#,##0.00;-#,##0.00"
                elif col.kind in ("date", "date_long"):
                    cell.value = getdate(v)
                    cell.number_format = "mmmm d, yyyy" if col.kind == "date_long" else "mm/dd/yyyy"
                    cell.alignment = Alignment(horizontal="left", vertical="top")
                else:
                    cell.value = str(v)
                    cell.data_type = "s"
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                if style == "bold":
                    if "TOTAL" in values:
                        cell.border = Border(top=thin)
            r += 1
        if page < book.pages:
            ws.row_breaks.append(Break(id=r - 1))
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_LEGAL
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5
    wb.properties.title = book.title.title()
    wb.properties.creator = h["software"]
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ---------------------------------------------------------------- PDF

def _fmt(col: Col, v) -> str:
    if v is None or v == "":
        return ""
    if col.kind == "money":
        return f"{flt(v, 2):,.2f}"
    if col.kind == "date_long":
        d = getdate(v)
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    if col.kind == "date":
        return getdate(v).strftime("%m/%d/%Y")
    return str(v)


def to_pdf(book: Book, h: dict) -> bytes:
    """Legal landscape, the header block and "Page x of y" on every page; text
    that does not fit its column wraps to a second line, then is cut with an
    ellipsis (column names take up to three lines)."""
    from reportlab.lib.pagesizes import landscape, legal
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas

    W, H = landscape(legal)
    margin, font, size = 28, "Helvetica", 7
    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=(W, H), invariant=1)
    cv.setTitle(book.title.title())
    cv.setAuthor(h["software"])
    total_w = sum(c.width for c in book.columns)
    widths = [(W - 2 * margin) * c.width / total_w for c in book.columns]
    xs = [margin + sum(widths[:i]) for i in range(len(widths))]
    row_h = 2 * (size + 1.5) + 3

    def lines_for(text, width, most=2):
        words, out, cur = str(text).split(), [], ""
        for w in words:
            t = f"{cur} {w}".strip()
            if stringWidth(t, font, size) <= width - 4:
                cur = t
            else:
                if cur:
                    out.append(cur)
                cur = w
        if cur:
            out.append(cur)
        if len(out) > most:
            out = out[:most]
            while stringWidth(out[-1] + "...", font, size) > width - 4 and out[-1]:
                out[-1] = out[-1][:-1]
            out[-1] += "..."
        return out or [""]

    for page in range(1, book.pages + 1):
        y = H - margin
        cv.setFont("Helvetica-Bold", 11)
        cv.drawString(margin, y, book.title)
        y -= 20
        left, right = _header_rows(h, book, page)
        cv.setFont(font, 8)
        for k in range(max(len(left), len(right))):
            if k < len(left):
                cv.drawString(margin, y, left[k][0])
                cv.drawString(margin + 110, y, f": {left[k][1]}")
            if k < len(right):
                cv.drawString(W - margin - 300, y, right[k][0])
                cv.drawString(W - margin - 190, y, f": {right[k][1]}")
            y -= 11
        y -= 10
        cv.setFont("Helvetica-Bold", size)
        cv.line(margin, y + 8, W - margin, y + 8)
        for x, w, col in zip(xs, widths, book.columns):
            hl = lines_for(col.label, w, 3)  # column names may take three lines
            for j, t in enumerate(hl):
                cv.drawCentredString(x + w / 2, y - j * (size + 1.5), t)
        y -= 3 * (size + 1.5) + 2
        cv.line(margin, y + 6, W - margin, y + 6)
        y -= 4
        chunk = slice((page - 1) * ROWS_PER_PAGE, page * ROWS_PER_PAGE)
        for values, style in zip(book.rows[chunk], book.styles[chunk]):
            f = "Helvetica-Bold" if style == "bold" else font
            cv.setFont(f, size)
            for x, w, col, v in zip(xs, widths, book.columns, values):
                text = _fmt(col, v)
                if col.kind == "money":
                    cv.drawRightString(x + w - 2, y, text)
                else:
                    for j, t in enumerate(lines_for(text, w)):
                        cv.drawString(x + 2, y - j * (size + 1.5), t)
            y -= row_h
        cv.setFont(font, 7)
        cv.drawRightString(W - margin, margin - 12, f"{book.title}  |  Page {page} of {book.pages}")
        cv.showPage()
    cv.save()
    return buf.getvalue()


# ---------------------------------------------------------------- the pack

def build(company: str, start, end, codes: list | None = None) -> list:
    return [fn(company, start, end) for code, _title, fn in BOOKS if not codes or code in codes]


def pack(company: str, start, end, fmt: str = "xlsx", user=None) -> tuple[str, bytes, dict]:
    """A zip of the six books (Excel or PDF) and PAGES.txt, the page count per
    book for the sworn statement that goes with the bound books."""
    if fmt not in ("xlsx", "pdf"):
        frappe.throw(_("Format is xlsx or pdf."))
    h = header(company, start, end, user)
    books = build(company, start, end)
    tin = (company_facts(company)["tin"] or "").replace("-", "")
    stamp = f"{getdate(start):%Y%m%d}-{getdate(end):%Y%m%d}"
    pages, buf = {}, io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for b in books:
            data = to_xlsx(b, h) if fmt == "xlsx" else to_pdf(b, h)
            name = f"{b.code}_{b.title.title().replace(' ', '-')}_{stamp}.{fmt}"
            z.writestr(name, data)
            pages[b.title] = b.pages
        lines = [f"LOOSE-LEAF BOOKS OF ACCOUNTS, {h['owner']}, {h['tin_label']} {h['tin']}", f"Period: {h['period']}",
                 f"Permit to use no.: {h['permit'] or '(not set on the Company)'}", "", "Book, number of pages (one volume each unless bound in more):"]
        lines += [f"  {t.title()}: {n} page{'s' if n != 1 else ''}" for t, n in pages.items()]
        lines += ["", f"Total pages: {sum(pages.values())}", "These counts go into the sworn statement submitted with the bound books."]
        z.writestr("PAGES.txt", "\r\n".join(lines) + "\r\n")
    return f"loose-leaf-books_{tin}_{stamp}_{fmt}.zip", buf.getvalue(), pages


@frappe.whitelist()
def download(company: str, from_date: str, to_date: str, fmt: str = "xlsx"):
    frappe.has_permission("Company", "read", company, throw=True)
    if getdate(from_date) > getdate(to_date):
        frappe.throw(_("The start date is after the end date."))
    name, data, pages = pack(company, from_date, to_date, fmt)
    from ph_cas.audit.events import record

    record("export", "Company", company, 0, {"loose_leaf_books": fmt, "from": str(from_date), "to": str(to_date), "pages": pages})
    frappe.response["type"] = "binary"
    frappe.response["filename"] = name
    frappe.response["filecontent"] = data
