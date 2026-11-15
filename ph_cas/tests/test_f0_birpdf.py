"""F0: the overlay engine prints onto the BIR's own blanks, deterministically, and
refuses anything that does not fit. No database needed."""

import hashlib
import json
import os
import unittest
from datetime import datetime

from pypdf import PdfReader

from ph_cas.birpdf import (
    TEMPLATES,
    BirPdfError,
    layout_return,
    load_map,
    parse_ebir_export,
    render_proof,
    render_return,
    template_path,
)
from ph_cas.birpdf.render import metrics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "birpdf", "fixtures")

# The blanks, byte for byte as the owner committed them. Never change a template.
BLANKS = {
    "0619-E Jan 2018 rev final.pdf": "0418160d63d4e6f68c34f2bad553273a5d148c3686d8562d338d35fcdd0c5215",
    "1600-VT January 2018 ENCS final.pdf": "6314f5797fd3663bdfd2eac6d7923f18a1c48efcea9af83ab0464b11cc58128a",
    "1601-EQ January 2019 ENCS final.pdf": "5277addc6778c96a53fde99b8664b1a5213fcea638dea06033c9acf22ee73c25",
    "1601C final Jan 2018 with DPA.pdf": "c8faaa71015337a73b4ceb96bfb265c539589ab5e10eb27899bb81f87f417397",
    "1604-C Jan 2018 Final.pdf": "5239dd7f94bfc9d8a1b2e330e2da955bd5a0223762f41e95112d6b3822325dfd",
    "1604E Jan 2018 ENCS Final2.pdf": "1db203442630c74ff4c95b509e204f542c5ba8fb1bd812440793e314ce709876",
    "1701 Jan 2018 final with rates.pdf": "19be91d78258eb7c255f2615610db2739f10c378f8ac97adc0887c1bf40d1b2e",
    "1701A Jan 2018 v5 with rates.pdf": "8d492eabc6da2088cf9a55084488b192def5cc415048f607142c8bce1b72bfb8",
    "1701Q Jan 2018 final rev2_copy.pdf": "c731d3f12556e6f19ab81f6113ca7c4a23f7ed099675c03451ac0074d96b85ed",
    "1702-RT Jan 2018 ENCS Final v3.pdf": "d9a6a8a13e0114934261151c4eb269a1573042e7ce670eaf12b15f169d308d2d",
    "1702Q 2018ENCS final2.pdf": "589e22190b9211571cb8a0ba14c97c17dff250f3b8ee9f9e8f6cc3b37b1b1be4",
    "2306 Jan 2018 ENCS v4.pdf": "f7c0391b0a622b82a275d44720bc3bf8325cc7dd1393856361055f94dde75fe3",
    "2307 Jan 2018 ENCS v3.pdf": "eca9476c5f6346939b973e693d35d635f6dd82519b87092c717c21965b0b90f9",
    "2316 Sep 2021 ENCS_Final_corrected.pdf": "8e927e65b096d7a786ba7d36c55c28ee3de3546278880d9de8c11a91d1b48d60",
    "2550Q  April 2024 ENCS_Final.pdf": "18eb16925010fdda820cef958221ba2c0d073066efa93a898113e39b31135a25",
    "2551Q Jan 2018 ENCS final rev 3_copy.pdf": "1f270ecf66d778836a14697863e420ff65d5ed0a5576a6cf58b97c9a8e8c9b24",
}
MAPPED = {
    "0619E": "2018-01",
    "1601C": "2018-01",
    "1601EQ": "2019-01",
    "1600VT": "2018-01",
    "1604E": "2018-01",
    "1701": "2018-01",
    "1701A": "2018-01",
    "1701Q": "2018-01",
    "1702Q": "2018-01",
    "1702RT": "2018-01",
    "2307": "2018-01",
    "2550Q": "2024-04",
    "2551Q": "2018-01",
}


def fixture_rows(name: str) -> list[tuple[str, str]]:
    path = os.path.join(FIXTURES, name)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if name.endswith(".xml"):
        return parse_ebir_export(text)
    return [tuple(r) for r in json.loads(text)]


class TestF0BirPdf(unittest.TestCase):
    def test_every_blank_is_pinned_and_unchanged(self):
        for template, filename in TEMPLATES.items():
            path = template_path(template)
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            self.assertEqual(digest, BLANKS[filename], f"{template}: the blank changed")

    def test_every_map_loads_and_matches_its_blank(self):
        for form, version in MAPPED.items():
            m = load_map(form, version)
            reader = PdfReader(template_path(m["template"]))
            self.assertEqual(len(reader.pages), len(m["pages"]), form)
            for page, mp in zip(reader.pages, m["pages"]):
                self.assertAlmostEqual(float(page.mediabox.width), mp["width"], delta=0.5)
                self.assertAlmostEqual(float(page.mediabox.height), mp["height"], delta=0.5)

    def test_every_fixture_renders_and_is_deterministic(self):
        for name in sorted(os.listdir(FIXTURES)):
            form = name.split("-")[0]
            rows = fixture_rows(name)
            a = render_return(form, MAPPED[form], rows)
            b = render_return(form, MAPPED[form], rows)
            self.assertEqual(a, b, f"{name}: two renders differ")
            self.assertTrue(a.startswith(b"%PDF"), name)
            reader = PdfReader(__import__("io").BytesIO(a))
            self.assertEqual(reader.metadata.title, load_map(form, MAPPED[form])["title"])
            self.assertIsNone(reader.metadata.creation_date)

    def test_the_2307_prints_page_one_only(self):
        pdf = render_return("2307", "2018-01", fixture_rows("2307-sample.json"))
        self.assertEqual(len(PdfReader(__import__("io").BytesIO(pdf)).pages), 1)

    def test_a_long_2307_description_wraps_inside_its_row(self):
        """LDG-97: a 68-character ATC description used to fail the whole print."""
        m = load_map("2307", "2018-01")
        rows = dict(fixture_rows("2307-sample.json"))
        desc = "Professional fees, individual, gross up to 3M and not VAT-registered"
        rows["c2307:a1Desc"] = desc
        f = next(x for x in m["fields"] if x["key"] == "c2307:a1Desc")
        met = metrics()
        ops = [o for o in layout_return(m, list(rows.items()), met) if o.y > f["y"] - 8 and o.y < f["y"] + 8 and o.x < f["x1"]]
        self.assertEqual(len(ops), 2)
        self.assertEqual(" ".join(o.text for o in ops), desc.upper())
        for o in ops:
            self.assertGreaterEqual(o.size, f["minSize"])
            self.assertLessEqual(met.width(o.text, o.size), f["x1"] - f["x0"])
        # the block stays inside the row: top cap to bottom baseline within rowHeight
        top = max(o.y for o in ops) + met.cap_height(ops[0].size)
        self.assertLessEqual(top - min(o.y for o in ops), f["rowHeight"])
        # a short description is untouched: one line at the full size
        rows["c2307:a1Desc"] = "Rentals"
        one = [o for o in layout_return(m, list(rows.items()), met) if o.text == "RENTALS"]
        self.assertEqual([(o.y, o.size) for o in one], [(f["y"], f["size"])])
        render_return("2307", "2018-01", list(rows.items()))

    def test_a_draft_preview_is_stamped_and_needs_the_time(self):
        rows = fixture_rows("2551Q-sample.xml")
        with self.assertRaises(BirPdfError):
            render_return("2551Q", "2018-01", rows, "DRAFT")
        at = datetime(2026, 11, 12, 1, 30)
        d1 = render_return("2551Q", "2018-01", rows, "DRAFT", at)
        d2 = render_return("2551Q", "2018-01", rows, "DRAFT", at)
        clean = render_return("2551Q", "2018-01", rows)
        self.assertEqual(d1, d2)
        self.assertNotEqual(d1, clean)
        text = "".join(p.extract_text() for p in PdfReader(__import__("io").BytesIO(d1)).pages)
        self.assertIn("NOT FILED", text)
        self.assertIn("12 Nov 2026, 1:30 AM", text)

    def test_errors_name_the_field_and_nothing_is_cut_off(self):
        m = load_map("2551Q", "2018-01")
        met = metrics()
        base = dict(fixture_rows("2551Q-sample.xml"))

        def with_(key, value):
            d = dict(base)
            d[key] = value
            return list(d.items())

        # a digit comb that does not fit
        with self.assertRaises(BirPdfError) as cm:
            layout_return(m, with_("frm2551Qv2018:txtTIN1", "1234"), met)
        self.assertIn("txtTIN1", str(cm.exception))
        # a checkbox takes true or false only
        with self.assertRaises(BirPdfError):
            layout_return(m, with_("frm2551Qv2018:qtr_1", "yes"), met)
        # an unknown key
        with self.assertRaises(BirPdfError) as cm:
            layout_return(m, list(base.items()) + [("frm2551Qv2018:nosuchkey", "1")], met)
        self.assertIn("no entry in the field map", str(cm.exception))
        # a name too long for its boxes squeezes instead of failing (names only)
        long_name = "A VERY LONG REGISTERED NAME OF AN INVENTED TAXPAYER COMPANY INCORPORATED"
        ops = layout_return(m, with_("frm2551Qv2018:registeredName", long_name), met)
        squeezed = [o for o in ops if o.text == long_name or len(o.text) > 1 and long_name.startswith(o.text)]
        self.assertTrue(squeezed, "a long name prints whole on one line")
        self.assertLessEqual(squeezed[0].size, m["size"])

    def test_a_spaced_contact_number_prints_digits_only(self):
        # the contact boxes on every form take the digits; spaces, dashes and brackets drop
        for key, ver in MAPPED.items():
            m = load_map(key, ver)
            for f in m["fields"]:
                k = f["key"].lower()
                if f.get("kind") == "comb" and ("contact" in k or "telnum" in k or k.endswith(":telno")):
                    self.assertEqual(f.get("drop"), " -()+.", f["key"])
        m = load_map("1702RT", "2018-01")
        base = dict(fixture_rows("1702RT-sample.xml"))
        base["frm1702RT:txtPg1Pt1I11Contact"] = "02 8123 4567"
        ops = layout_return(m, list(base.items()), metrics())
        self.assertTrue(ops)

    def test_whole_peso_forms_refuse_centavos(self):
        m = load_map("1701Q", "2018-01")
        base = dict(fixture_rows("1701Q-sample.xml"))
        money = next(f for f in m["fields"] if f["kind"] == "money" and not f.get("cents") and f["key"] in base)
        base[money["key"]] = "1234.50"
        with self.assertRaises(BirPdfError) as cm:
            layout_return(m, list(base.items()), metrics())
        self.assertIn("centavos", str(cm.exception))

    def test_parse_refuses_a_malformed_export(self):
        with self.assertRaises(BirPdfError):
            parse_ebir_export("<?xml version='1.0'?>")
        with self.assertRaises(BirPdfError):
            parse_ebir_export("<div>frmUnknown:a=1frmUnknown:a=</div>")
        rows = parse_ebir_export("<div>frm2551Qv2018:registeredName=A%20Bfrm2551Qv2018:registeredName=</div>")
        self.assertEqual(rows, [("frm2551Qv2018:registeredName", "A B")])

    def test_proofs_render_for_every_map(self):
        for form, version in MAPPED.items():
            self.assertTrue(render_proof(form, version).startswith(b"%PDF"), form)
