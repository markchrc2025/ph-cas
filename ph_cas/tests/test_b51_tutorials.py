"""B51: tutorial videos played inside Sentire Ledger from our own server, not YouTube."""

import datetime
from io import BytesIO
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.tutorials import api, storage
from ph_cas.tutorials.storage import S3


class FakeS3:
    """Stands in for the bucket: keeps objects and multipart pieces in memory."""

    def __init__(self):
        self.objects, self.parts, self.n = {}, {}, 0
        self.real = S3("https://s3.example.test", "us-east-1", "videos", "AK", "SK")

    def head(self, key):
        return {"size": len(self.objects[key]), "etag": "x"} if key in self.objects else None

    def get(self, key):
        return self.objects[key]

    def put(self, key, data, content_type):
        self.objects[key] = data

    def start_multipart(self, key, content_type):
        self.n += 1
        self.parts[f"u{self.n}"] = {}
        return f"u{self.n}"

    def upload_part(self, key, upload_id, number, data):
        self.parts[upload_id][number] = data
        return f"etag{number}"

    def complete_multipart(self, key, upload_id, etags):
        pieces = self.parts.pop(upload_id)
        assert etags == [f"etag{i}" for i in sorted(pieces)]
        self.objects[key] = b"".join(pieces[i] for i in sorted(pieces))

    def abort_multipart(self, key, upload_id):
        self.parts.pop(upload_id, None)

    def presign(self, key, expires=21600):
        return self.real.presign(key, expires)


class TestB51Tutorials(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        api.seed()
        self.fake = FakeS3()
        for code in ("V09", "V35"):
            for kind in api.KINDS:
                frappe.cache.delete_value(f"ph_tutorial_present:{code}")

    # signing -----------------------------------------------------------------------------------
    def test_signing_matches_the_aws_test_vectors(self):
        s3 = S3("https://examplebucket.s3.amazonaws.com", "us-east-1", "", "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        now = datetime.datetime(2013, 5, 24, tzinfo=datetime.UTC)
        url = s3.presign("test.txt", 86400, now=now)
        self.assertTrue(url.endswith("X-Amz-Signature=aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"), url)
        headers = s3.signed_headers("GET", "test.txt", {}, None, {"Range": "bytes=0-9"}, now=now)
        self.assertIn("Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41", headers["authorization"])

    def test_path_style_puts_the_bucket_in_the_path(self):
        s3 = S3("https://s3.sentire.solutions", "us-east-1", "sentire-ledger-videos", "AK", "SK")
        self.assertTrue(s3.presign("tutorials/V01/video.mp4").startswith("https://s3.sentire.solutions/sentire-ledger-videos/tutorials/V01/video.mp4?"))
        # the server may reach the bucket inside the network; links are signed for the browser's address
        inner = S3("http://rustfs:9000", "us-east-1", "sentire-ledger-videos", "AK", "SK", public_endpoint="https://s3.sentire.solutions")
        now = datetime.datetime(2026, 11, 15, tzinfo=datetime.UTC)
        self.assertEqual(inner.presign("k", now=now), s3.presign("k", now=now))

    # the catalogue -----------------------------------------------------------------------------
    def test_the_catalogue_has_the_57_videos_and_where_they_play(self):
        # B70: 57 videos in learning order, each with its section, on-screen menu path and the report it ends on
        self.assertEqual(frappe.db.count("PH Tutorial Video"), 57)
        self.assertEqual(api.seed(), {"made": [], "updated": []})  # idempotent
        steps = api.step_map()
        self.assertEqual(steps["Create Customer"], "V09")
        self.assertEqual(steps["PH Set Up Company"], "V03")
        for s in ("Create Selling Item", "Create Item"):
            self.assertEqual(steps[s], "V11")
        for s in ("Create Buying Item", "Create Raw Materials"):
            self.assertEqual(steps[s], "V12")
        help_codes = [c for c, _ in api.help_map()["PH Tax Return"]]
        self.assertEqual(help_codes, ["V48", "V49", "V50", "V51", "V52", "V53", "V54"])
        self.assertEqual(frappe.db.get_value("PH Tutorial Video", "V50", "title"), "File your withholding tax returns")
        v11 = frappe.get_doc("PH Tutorial Video", "V11")
        self.assertEqual((v11.title, v11.section), ("Add an item you sell", "Your records"))
        self.assertTrue(v11.menu_path and v11.ends_on)

    def test_catalogue_rules(self):
        rows = api.catalogue()
        self.assertEqual([r["code"] for r in rows], [f"V{i:02d}" for i in range(1, len(rows) + 1)])
        for r in rows:
            m, s = r["length"].split(":")
            self.assertLessEqual(int(m) * 60 + int(s), 90, r["code"])  # 60 to 90 s, long topics split
            self.assertTrue(r["section"] and r["menu_path"] and r["ends_on"], r["code"])
        steps = [s for r in rows for s in r["steps"]]
        self.assertEqual(len(steps), len(set(steps)))  # one video per onboarding card

    def test_retired_codes_go_unless_a_video_was_uploaded(self):
        for code, size in (("V98", 0), ("V99", 1000)):
            if not frappe.db.exists("PH Tutorial Video", code):
                frappe.get_doc({"doctype": "PH Tutorial Video", "code": code, "title": "Old", "length": "1:00", "summary": "x", "video_size": size}).insert(ignore_permissions=True)
        out = api.seed()
        self.assertEqual(out.get("removed"), ["V98"])
        self.assertEqual(out.get("kept_with_video"), ["V99"])
        self.assertFalse(frappe.db.exists("PH Tutorial Video", "V98"))
        frappe.delete_doc("PH Tutorial Video", "V99", force=True)

    def test_file_names_and_captions(self):
        self.assertEqual(api.code_from_filename("SL-V50-file-your-withholding-tax-returns.mp4"), "V50")
        self.assertEqual(api.code_from_filename("V01.srt"), "V01")
        self.assertIsNone(api.code_from_filename("SL-V350.mp4"))
        vtt = api.srt_to_vtt("﻿1\r\n00:00:01,500 --> 00:00:03,000\r\nHello\r\n")
        self.assertEqual(vtt, "WEBVTT\n\n1\n00:00:01.500 --> 00:00:03.000\nHello\n")

    # playback ----------------------------------------------------------------------------------
    def test_play_says_why_when_there_is_nothing_to_play(self):
        with patch.object(storage, "is_configured", return_value=False):
            self.assertEqual(api.play("V09")["reason"], "not_configured")
        with patch.object(storage, "is_configured", return_value=True), patch.object(storage, "client", return_value=self.fake):
            self.assertEqual(api.play("V09")["reason"], "not_uploaded")

    # upload, then play -------------------------------------------------------------------------
    def test_upload_in_pieces_then_play_with_signed_links(self):
        video = b"\x00\x00\x00\x24ftypisom" + b"x" * (api.PART_SIZE + 1000)
        srt = "1\n00:00:00,000 --> 00:00:02,000\nTax you withhold\n".encode()
        png = BytesIO()
        from PIL import Image

        Image.new("RGB", (1920, 1080), (12, 34, 56)).save(png, "PNG")
        with patch.object(storage, "is_configured", return_value=True), patch.object(storage, "client", return_value=self.fake):
            plan = api.start_upload("V35", "video", len(video))
            self.assertEqual(plan["parts"], 2)
            for i in range(plan["parts"]):
                piece = video[i * plan["part_size"] : (i + 1) * plan["part_size"]]
                with patch.object(api, "_body", return_value=piece):
                    api.upload_part("V35", "video", i + 1, plan["upload_id"])
            api.finish_upload("V35", plan["upload_id"])
            with patch.object(api, "_body", return_value=srt):
                api.upload_part("V35", "captions")
            with patch.object(api, "_body", return_value=png.getvalue()):
                api.upload_part("V35", "poster")

            self.assertEqual(self.fake.objects["tutorials/V35/video.mp4"], video)
            self.assertTrue(self.fake.objects["tutorials/V35/captions.vtt"].startswith(b"WEBVTT\n\n1\n00:00:00.000"))
            self.assertEqual(self.fake.objects["tutorials/V35/poster.jpg"][:2], b"\xff\xd8")  # a JPEG
            doc = frappe.get_doc("PH Tutorial Video", "V35")
            self.assertEqual((doc.video_size, doc.has_captions, doc.has_poster), (len(video), 1, 1))

            out = api.play("V35")
            self.assertTrue(out["available"])
            self.assertIn("/videos/tutorials/V35/video.mp4?", out["video"])
            self.assertIn("X-Amz-Signature=", out["video"])
            self.assertNotIn("SK", out["video"].split("?")[1].split("X-Amz-Signature")[0])
            self.assertEqual(out["captions"], "/api/method/ph_cas.tutorials.api.captions?code=V35")
            resp = api.captions("V35")
            self.assertEqual(resp.mimetype, "text/vtt")
            self.assertIn(b"Tax you withhold", resp.get_data())

    def test_a_missing_piece_stops_the_upload(self):
        with patch.object(storage, "client", return_value=self.fake):
            plan = api.start_upload("V09", "video", api.PART_SIZE * 2)
            with patch.object(api, "_body", return_value=b"a" * 10):
                api.upload_part("V09", "video", 1, plan["upload_id"])
            with self.assertRaises(frappe.ValidationError):
                api.finish_upload("V09", plan["upload_id"])

    def test_only_a_system_manager_uploads(self):
        user = "ph.tutorial.viewer@example.com"
        if not frappe.db.exists("User", user):
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "Viewer", "roles": [{"role": "Accounts User"}]}).insert(ignore_permissions=True)
        frappe.set_user(user)
        try:
            with self.assertRaises(frappe.PermissionError):
                api.start_upload("V09", "video", 10)
        finally:
            frappe.set_user("Administrator")
