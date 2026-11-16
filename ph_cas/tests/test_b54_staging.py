"""B54: the staging QA site and its connector (docs/STAGING.md)."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from ph_cas.qa import api, mcp_server
from ph_cas.tests.setup import TEST_COMPANY


class TestB54StagingSite(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_nothing_runs_outside_a_staging_site(self):
        self.assertFalse(api.is_staging())
        for fn, args in ((api.status, ()), (api.seed_scenario, ("vat_quarter",)), (api.seed, ()), (api.ensure_qa_user, ())):
            with self.assertRaises(frappe.PermissionError):
                fn(*args)
        with patch.dict(frappe.conf, {"ph_staging_site": 1, "ph_cas_production": 1}):
            self.assertFalse(api.is_staging())  # production wins

    def test_on_a_staging_site_the_qa_admin_status_and_scenarios_work(self):
        # the staging calls commit (they run in their own requests); here that would leak
        # the scenario's invoices into the other tests, so the commit is held back
        with patch.dict(frappe.conf, {"ph_staging_site": 1, "ph_cas_production": 0}), patch.dict("os.environ", {"STAGING_ADMIN_PASSWORD": "Qa-test-Password-2026"}), patch.object(frappe.db, "commit"):
            api.ensure_qa_user()
            roles = frappe.get_roles(api.QA_USER)
            self.assertIn("System Manager", roles)
            self.assertIn("Accounting Manager", roles)
            out = api.status()
            for k in ("site", "versions", "companies", "modules_on", "counts", "tax_rules", "scenarios"):
                self.assertIn(k, out)
            self.assertEqual(out["scenarios"], ["income_year", "individual_year", "non_vat_company", "vat_quarter"])
            made = api.seed_scenario("vat_quarter", TEST_COMPANY)
            self.assertTrue(made["sales_invoices"])
            for name in made["sales_invoices"]:
                self.assertEqual(frappe.db.get_value("Sales Invoice", name, "docstatus"), 1)
            with self.assertRaises(frappe.ValidationError):
                api.seed_scenario("nonsense")


class FakeSite:
    def __init__(self):
        self.calls = []

    def call(self, method, path, params=None, json_body=None, data=None):
        self.calls.append((method, path))

        class R:
            status_code = 200
            text = "{}"

            def json(self_inner):
                return {"message": {"ok": True, "path": path}}

        return R()


class TestB54Connector(IntegrationTestCase):
    SECRET = "s" * 40

    def setUp(self):
        self.site = FakeSite()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), mcp_server.make_handler(self.SECRET, self.site, mcp_server.Limiter(3)))
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()

    def post(self, path, body):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, (json.loads(r.read() or b"null"))
        except urllib.error.HTTPError as e:
            return e.code, None

    def test_the_url_is_the_key(self):
        self.assertEqual(self.post("/mcp/wrong", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0], 404)
        self.assertEqual(self.post("/other", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0], 404)
        self.assertEqual(self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0], 200)

    def test_initialize_list_and_call(self):
        code, init = self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(init["result"]["serverInfo"]["name"], "sentire-ledger-staging-qa")
        self.assertEqual(self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "method": "notifications/initialized"})[0], 202)
        _, tools = self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in tools["result"]["tools"]}
        self.assertTrue({"staging_status", "create_document", "submit_document", "run_report", "get_print", "seed_scenario", "api_request"} <= names)
        _, out = self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "staging_status", "arguments": {}}})
        self.assertFalse(out["result"]["isError"])
        self.assertEqual(self.site.calls[-1], ("GET", "/api/method/ph_cas.qa.api.status"))

    def test_sign_in_endpoints_and_the_rate_limit(self):
        _, out = self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "api_request", "arguments": {"method": "POST", "path": "/api/method/login"}}})
        self.assertTrue(out["result"]["isError"])
        _, out = self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "call_method", "arguments": {"method": "logout"}}})
        self.assertTrue(out["result"]["isError"])
        self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "staging_status", "arguments": {}}})
        _, out = self.post(f"/mcp/{self.SECRET}", {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "staging_status", "arguments": {}}})
        self.assertIn("Rate limit", out["result"]["content"][0]["text"])

    def test_it_refuses_to_start_outside_staging(self):
        env = {"PH_STAGING": "1", "PH_PRODUCTION": "0", "QA_MCP_SECRET": self.SECRET, "STAGING_ADMIN_PASSWORD": "x"}
        for change in ({"PH_STAGING": "0"}, {"PH_PRODUCTION": "1"}, {"QA_MCP_SECRET": "short"}, {"STAGING_ADMIN_PASSWORD": ""}):
            with patch.dict("os.environ", {**env, **change}), self.assertRaises(SystemExit):
                mcp_server.preflight(frappe.local.site)
        # the test site has no ph_staging_site in its config
        with patch.dict("os.environ", {**env, "QA_SITES_PATH": frappe.get_site_path("..")}), self.assertRaises(SystemExit):
            mcp_server.preflight(frappe.local.site)
