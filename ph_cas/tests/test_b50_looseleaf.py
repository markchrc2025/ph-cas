"""B50: the loose-leaf books in the registered format (Excel and PDF)."""

import io
import zipfile

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from ph_cas.books.looseleaf import BOOKS, ROWS_PER_PAGE, build, header, pack, to_pdf, to_xlsx
from ph_cas.setup.chart import setup_philippine_company
from ph_cas.tests.fixtures import make_sales_invoice
from ph_cas.tests.setup import TEST_COMPANY

SALES_HEAD = ["GL DATE", "TIN", "CUSTOMER NAME", "CUSTOMER ADDRESS", "DESCRIPTION", "DOCUMENT TYPE", "INVOICE NO.", "VATABLE SALES / AMOUNT",
              "VAT EXEMPT SALES", "ZERO RATED SALES", "VAT AMT", "DEFERRED VAT AMT", "DISCOUNT", "GROSS SALES"]


class TestB50LooseLeaf(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup_philippine_company(TEST_COMPANY)
        make_sales_invoice()
        self.start, self.end = getdate(today()).replace(day=1), getdate(today())

    def test_six_books_with_the_registered_columns_and_totals(self):
        books = build(TEST_COMPANY, self.start, self.end)
        self.assertEqual([b.code for b in books], [c for c, _t, _f in BOOKS])
        sj = books[0]
        self.assertEqual([c.label for c in sj.columns], SALES_HEAD)
        self.assertEqual(sj.rows[-1][6], "TOTAL")
        self.assertGreaterEqual(len(sj.rows), 2)
        self.assertEqual(round(sum(r[13] for r in sj.rows[:-1]), 2), sj.rows[-1][13])
        gl = books[-1]
        self.assertEqual(gl.rows[-1][2], "TOTAL")
        self.assertEqual(gl.rows[-1][4], gl.rows[-1][5])  # debits equal credits
        self.assertEqual(books[1].columns[2].label, "SUPPLIER NAME")

    def test_excel_keeps_numbers_dates_and_the_header_on_every_page(self):
        from openpyxl import load_workbook

        sj = build(TEST_COMPANY, self.start, self.end, ["SJ"])[0]
        while len(sj.rows) <= ROWS_PER_PAGE:  # force a second page
            sj.add(list(sj.rows[0]))
        h = header(TEST_COMPANY, self.start, self.end)
        ws = load_workbook(io.BytesIO(to_xlsx(sj, h))).active
        cells = [(c.coordinate, c.value) for row in ws.iter_rows() for c in row if c.value is not None]
        values = [v for _k, v in cells]
        self.assertIn("SALES JOURNAL", values)
        self.assertEqual(values.count("OWNER'S NAME"), sj.pages)
        self.assertIn(f": Page 2 of {sj.pages}", values)
        self.assertEqual(len(ws.row_breaks.brk), sj.pages - 1)
        head_row = next(c.row for row in ws.iter_rows() for c in row if c.value == "GL DATE")
        first = [c.value for c in ws[head_row + 1]]
        self.assertIsInstance(first[0], __import__("datetime").datetime)
        self.assertIsInstance(first[13], (int, float))  # a number, not text
        self.assertEqual(ws.cell(head_row + 1, 1).number_format, "mmmm d, yyyy")

    def test_pdf_page_count_and_the_pack(self):
        from pypdf import PdfReader

        gl = build(TEST_COMPANY, self.start, self.end, ["GL"])[0]
        pdf = to_pdf(gl, header(TEST_COMPANY, self.start, self.end))
        self.assertEqual(len(PdfReader(io.BytesIO(pdf)).pages), gl.pages)
        text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
        self.assertIn("GENERAL LEDGER", text)
        self.assertIn(f"Page 1 of {gl.pages}", text)
        self.assertIn("PERMIT TO USE NO.", text)
        name, data, pages = pack(TEST_COMPANY, self.start, self.end, "pdf")
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        self.assertEqual(len(names), 7)
        self.assertIn("PAGES.txt", names)
        self.assertEqual(pages["GENERAL LEDGER"], gl.pages)

    def test_excel_header_never_shares_a_cell(self):
        """Every header label and value sits in its own cell or merged range, on wide and narrow books."""
        from openpyxl import load_workbook

        h = header(TEST_COMPANY, self.start, self.end)
        for book in build(TEST_COMPANY, self.start, self.end, ["SJ", "GJ", "GL"]):
            ws = load_workbook(io.BytesIO(to_xlsx(book, h))).active
            values = [c.value for row in ws.iter_rows(max_row=14) for c in row if c.value]
            for label in ("OWNER'S NAME", "OWNER'S ADDRESS", "PERIOD", "RUN DATE", "PAGE", "APPLICATION SOFTWARE", "PERMIT TO USE NO."):
                self.assertIn(label, values, book.code)
            self.assertIn(f": {h['owner']}", values, book.code)
            self.assertIn(f": {h['software']}", values, book.code)
            starts = [(m.min_row, m.min_col, m.max_col) for m in ws.merged_cells.ranges]
            for r in {s[0] for s in starts}:
                spans = sorted((a, b) for row, a, b in starts if row == r)
                for (a1, b1), (a2, _b2) in zip(spans, spans[1:]):
                    self.assertLess(b1, a2, f"{book.code} row {r} overlaps")
