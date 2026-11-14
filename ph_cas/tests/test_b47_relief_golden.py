"""B47: the RELIEF writer reproduces the BIR RELIEF 2.3 module's own files byte for byte."""

import os
import unittest

from ph_cas.dat.relief import importations_file, purchases_file, sales_file

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden", "relief")
END = "2026-11-30"
OWNER = {"tin": "474079835", "names": ["SAMPLE TAXPAYER CORP", "", "", ""], "trade": "SAMPLE STORE",
         "a1": "UNIT 1 123 RIZAL AVE BRGY POBLACION", "a2": "MAKATI METRO MANILA 1200", "rdo": "047", "fiscal_month": 12}


def golden(name):
    with open(os.path.join(GOLDEN, name), "rb") as f:
        return f.read()


def company(name, a1, a2, **amounts):
    return {"names": [name, "", "", ""], "a1": a1, "a2": a2, **amounts}


def person(last, first, middle, a1, a2, **amounts):
    return {"names": ["", last, first, middle], "a1": a1, "a2": a2, **amounts}


class TestB47ReliefGolden(unittest.TestCase):
    def test_sales_file_matches_relief(self):
        merged = {
            # two sales to Bayani (100,000 + 10,000 taxable), merged per TIN as RELIEF does
            "123456789": company("BAYANI RETAIL STORES INC", "45 MABINI ST BRGY 1", "PASIG CITY 1600", exempt=5000, zero=3000, taxable=110000, vat=13200),
            "234567890": person("DELA CRUZ", "JUAN", "SANTOS", "7 ACACIA ST BRGY SAN ROQUE", "QUEZON CITY 1100", exempt=0, zero=0, taxable=50000, vat=6000),
        }
        self.assertEqual(sales_file(OWNER, merged, END), golden("474079835S112026.DAT"))

    def test_purchases_file_matches_relief(self):
        merged = {
            "111111112": company("ZETA SUPPLY CORP", "9 KALAW ST", "MANILA 1000", exempt=0, zero=0, services=20000, capital=0, goods=0, vat=2400),
            "999999998": company("ALPHA PARTS INC", "88 SHAW BLVD", "MANDALUYONG 1550", exempt=1500, zero=0, services=0, capital=10000, goods=20000, vat=3600),
            "555555556": person("REYES", "DIWA", "MARQUEZ", "3 ILANG-ILANG ST", "CEBU CITY 6000", exempt=0, zero=2000, services=0, capital=0, goods=5000, vat=600),
        }
        self.assertEqual(purchases_file(OWNER, merged, END, noncreditable=600), golden("474079835P112026.DAT"))

    def test_importations_file_matches_relief(self):
        rows = [{"entry_no": "C12345", "assessed": "2026-11-05", "seller": "SHENZHEN PARTS CO LTD", "imported": "2026-11-03", "country": "CHINA",
                 "dutiable": 100000, "charges": 15000, "exempt": 0, "taxable": 115000, "vat": 13800, "or_no": "OR998877", "paid": "2026-11-06"}]
        self.assertEqual(importations_file(OWNER, rows, END), golden("474079835I112026.DAT"))
        self.assertEqual(importations_file(OWNER, [], END), b"")

    def test_individual_owner_header_matches_relief(self):
        """An individual owner: registered name blank, the person's names quoted, header zeros as 0.00."""
        o = {"tin": "474079835", "names": ["", "SANTOS", "MARIA", "LOPEZ"], "trade": "MARIAS BAKESHOP",
             "a1": "LOT 3 5 MABINI ST BRGY 2", "a2": "SAN JUAN METRO MANILA 1500", "rdo": "046", "fiscal_month": 12}
        merged = {"123456789": company("BAYANI RETAIL STORES INC", "45 MABINI ST BRGY 1", "PASIG CITY 1600", exempt=0, zero=0, taxable=10000, vat=1200)}
        self.assertEqual(sales_file(o, merged, END), golden("individual-owner-474079835S112026.DAT"))
