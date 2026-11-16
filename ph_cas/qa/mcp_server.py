"""Sentire Ledger QA connector: an MCP server for the STAGING site only (docs/STAGING.md).

Runs inside the staging container on QA_MCP_PORT (8010). It signs in to the staging site as the
QA admin and calls the site's own HTTP API, so validation, permissions and the Annex B locks apply
exactly as for a person; it has no database access of its own.

Safety, as the Payroll QA connector:
- the URL is the key: /mcp/<QA_MCP_SECRET>; a wrong key or any other path is a 404. The secret is
  generated in Dokploy and must be at least 32 characters, or the server does not start;
- it refuses to start unless PH_STAGING=1 and the site is a staging site (site config
  ph_staging_site 1, ph_cas_production not 1);
- 120 calls a minute; one JSON audit line per call in the container log.

MCP over HTTP (streamable HTTP, JSON responses): POST JSON-RPC 2.0 to the URL. Standard library
plus requests (present in the bench environment).

Run: /home/frappe/bench/env/bin/python -m ph_cas.qa.mcp_server
"""

import json
import re
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

import requests

PROTOCOL = "2025-06-18"
SITE_URL = os.environ.get("QA_SITE_URL") or "http://127.0.0.1:8001"  # gunicorn inside the container
QA_USER = "qa.admin@sentire.solutions"
RATE_PER_MIN = 120
BLOCKED_PATHS = ("/api/method/login", "/api/method/logout", "/api/v2/method/login", "/api/v2/method/logout", "/api/method/frappe.core.doctype.user.user.")

TOOLS = [
    {
        "name": "staging_status",
        "description": "What the staging site holds: versions, companies, modules on, counts of posted documents, tax rules (confirmed/draft), BIR returns, and the scenarios seed_scenario can add. Call this first.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_documents",
        "description": "List records of a DocType (Frappe get_list as the QA admin). filters: a dict ({\"docstatus\": 1}) or a list of [field, operator, value]. fields default to name and modified.",
        "inputSchema": {"type": "object", "required": ["doctype"], "properties": {
            "doctype": {"type": "string"}, "filters": {}, "fields": {"type": "array", "items": {"type": "string"}},
            "order_by": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 500}}},
    },
    {
        "name": "get_document",
        "description": "One record, with its child tables.",
        "inputSchema": {"type": "object", "required": ["doctype", "name"], "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}}},
    },
    {
        "name": "create_document",
        "description": "Insert a record (saved as a draft for submittable DocTypes). values are the fields, child tables as lists of dicts. Returns the saved record or the app's validation message.",
        "inputSchema": {"type": "object", "required": ["doctype", "values"], "properties": {"doctype": {"type": "string"}, "values": {"type": "object"}}},
    },
    {
        "name": "update_document",
        "description": "Change fields of a record (the app refuses changes to posted accounting fields, as it should).",
        "inputSchema": {"type": "object", "required": ["doctype", "name", "values"], "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}, "values": {"type": "object"}}},
    },
    {
        "name": "submit_document",
        "description": "Submit (post) a draft. BIR serials, approval chains and every Annex B control apply.",
        "inputSchema": {"type": "object", "required": ["doctype", "name"], "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}}},
    },
    {
        "name": "cancel_document",
        "description": "Cancel a submitted record (the app refuses it for issued invoices; corrections go through credit or debit notes).",
        "inputSchema": {"type": "object", "required": ["doctype", "name"], "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}}},
    },
    {
        "name": "call_method",
        "description": "Call a whitelisted server method, e.g. ph_cas.tutorials.api.play or a document method through run_doc_method. http_method GET or POST (default POST).",
        "inputSchema": {"type": "object", "required": ["method"], "properties": {"method": {"type": "string"}, "args": {"type": "object"}, "http_method": {"type": "string", "enum": ["GET", "POST"]}}},
    },
    {
        "name": "run_report",
        "description": "Run a report (script or query report) with filters and return its columns and rows, e.g. PH Sales Journal, BIR Audit Trail, General Ledger.",
        "inputSchema": {"type": "object", "required": ["report"], "properties": {"report": {"type": "string"}, "filters": {"type": "object"}}},
    },
    {
        "name": "get_print",
        "description": "The HTML of a print (e.g. Sales Invoice with print format PH Sales Invoice), through the same print page as the Print button, so it is recorded as on the real site (REPRINT counting). preview: true renders the desk's on-screen preview instead, which records nothing.",
        "inputSchema": {"type": "object", "required": ["doctype", "name"], "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}, "print_format": {"type": "string"}, "preview": {"type": "boolean"}}},
    },
    {
        "name": "seed_scenario",
        "description": "Add test data: vat_quarter (three months of VATable, zero-rated and exempt sales and EWT bills in the current quarter) or non_vat_company (a second, non-VAT company with sales for the 2551Q).",
        "inputSchema": {"type": "object", "required": ["scenario"], "properties": {"scenario": {"type": "string", "enum": ["vat_quarter", "non_vat_company"]}, "company": {"type": "string"}}},
    },
    {
        "name": "api_request",
        "description": "Any call to the site's /api (resource or method), for what the other tools do not cover. Sign-in, sign-out and user password endpoints are refused. To reset the staging data, restart the 'Ledger Staging' app in Dokploy.",
        "inputSchema": {"type": "object", "required": ["method", "path"], "properties": {
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]}, "path": {"type": "string", "description": "Starts with /api/"},
            "params": {"type": "object"}, "body": {"type": "object"}}},
    },
]


class Site:
    """A signed-in session on the staging site."""

    def __init__(self, host: str, password: str):
        self.host, self.password = host, password
        self.s = requests.Session()
        self.s.headers.update({"Host": host, "Accept": "application/json"})
        self.lock = threading.Lock()
        self.signed_in = False

    def login(self):
        r = self.s.post(f"{SITE_URL}/api/method/login", data={"usr": QA_USER, "pwd": self.password}, timeout=60)
        if r.status_code != 200 or "verification" in r.text:
            raise RuntimeError(f"QA admin sign-in failed ({r.status_code}): {r.text[:200]}")
        self.signed_in = True

    def call(self, method: str, path: str, params=None, json_body=None, data=None):
        with self.lock:
            if not self.signed_in:
                self.login()
            for attempt in (1, 2):
                r = self.s.request(method, f"{SITE_URL}{path}", params=params, json=json_body, data=data, timeout=300)
                if r.status_code in (401, 403) and attempt == 1 and "session" in r.text.lower():
                    self.login()
                    continue
                return r
        return r


def _message(r) -> dict:
    """The app's answer: the result, or its error in plain words."""
    try:
        body = r.json()
    except ValueError:
        return {"status": r.status_code, "text": r.text[:4000]}
    if r.status_code >= 400:
        msgs = []
        try:
            for m in json.loads(body.get("_server_messages") or "[]"):
                msgs.append(json.loads(m).get("message"))
        except Exception:
            pass
        return {"status": r.status_code, "error": body.get("exc_type") or "Error", "messages": msgs or [body.get("exception") or body.get("message")]}
    return body.get("message", body.get("data", body))


def _print_body(page: str) -> str:
    """The printed content of a /printview page: the body, without styles and scripts."""
    body = re.search(r"<body[^>]*>(.*)</body>", page, re.S)
    text = body.group(1) if body else page
    text = re.sub(r"<(script|style)\b.*?</\1>", "", text, flags=re.S)
    return text.strip()


def _q(name: str) -> str:
    return quote(name, safe="")


def run_tool(site: Site, name: str, a: dict):
    if name == "staging_status":
        return _message(site.call("GET", "/api/method/ph_cas.qa.api.status"))
    if name == "list_documents":
        params = {"fields": json.dumps(a.get("fields") or ["name", "modified"]), "limit_page_length": a.get("limit") or 20}
        if a.get("filters") is not None:
            params["filters"] = json.dumps(a["filters"])
        if a.get("order_by"):
            params["order_by"] = a["order_by"]
        return _message(site.call("GET", f"/api/resource/{_q(a['doctype'])}", params=params))
    if name == "get_document":
        return _message(site.call("GET", f"/api/resource/{_q(a['doctype'])}/{_q(a['name'])}"))
    if name == "create_document":
        return _message(site.call("POST", f"/api/resource/{_q(a['doctype'])}", json_body=a["values"]))
    if name == "update_document":
        return _message(site.call("PUT", f"/api/resource/{_q(a['doctype'])}/{_q(a['name'])}", json_body=a["values"]))
    if name == "submit_document":
        doc = _message(site.call("GET", f"/api/resource/{_q(a['doctype'])}/{_q(a['name'])}"))
        if not isinstance(doc, dict) or "doctype" not in doc:
            return doc
        return _message(site.call("POST", "/api/method/frappe.client.submit", json_body={"doc": doc}))
    if name == "cancel_document":
        return _message(site.call("POST", "/api/method/frappe.client.cancel", json_body={"doctype": a["doctype"], "name": a["name"]}))
    if name == "call_method":
        m = a["method"]
        if any(f"/api/method/{m}".startswith(b) for b in BLOCKED_PATHS):
            return {"error": "Refused: sign-in, sign-out and password methods are not available to the connector."}
        if (a.get("http_method") or "POST") == "GET":
            return _message(site.call("GET", f"/api/method/{m}", params=a.get("args") or {}))
        return _message(site.call("POST", f"/api/method/{m}", json_body=a.get("args") or {}))
    if name == "run_report":
        out = _message(site.call("POST", "/api/method/frappe.desk.query_report.run", json_body={"report_name": a["report"], "filters": a.get("filters") or {}}))
        if isinstance(out, dict) and "result" in out:
            cols = [c.get("fieldname") or c.get("label") if isinstance(c, dict) else str(c) for c in out.get("columns") or []]
            rows = out.get("result") or []
            return {"columns": cols, "row_count": len(rows), "rows": rows[:200], "truncated": len(rows) > 200}
        return out
    if name == "get_print":
        if a.get("preview"):
            params = {"doc": a["doctype"], "name": a["name"]}
            if a.get("print_format"):
                params["print_format"] = a["print_format"]
            out = _message(site.call("POST", "/api/method/frappe.www.printview.get_html_and_style", json_body=params))
            html = out.get("html") if isinstance(out, dict) else None
            if html is None:
                return out
        else:
            params = {"doctype": a["doctype"], "name": a["name"], "no_letterhead": 0}
            if a.get("print_format"):
                params["format"] = a["print_format"]
            r = site.call("GET", "/printview", params=params)
            if r.status_code >= 400:
                return {"status": r.status_code, "text": _print_body(r.text)[:4000]}
            html = _print_body(r.text)
        return {"html": html[:60000], "truncated": len(html) > 60000}
    if name == "seed_scenario":
        return _message(site.call("POST", "/api/method/ph_cas.qa.api.seed_scenario", json_body={"scenario": a["scenario"], "company": a.get("company")}))
    if name == "api_request":
        path = a["path"]
        if not path.startswith("/api/") or any(path.startswith(b) for b in BLOCKED_PATHS):
            return {"error": "Refused: only /api/ paths, and not sign-in, sign-out or password endpoints."}
        return _message(site.call(a["method"], path, params=a.get("params"), json_body=a.get("body")))
    raise KeyError(name)


class Limiter:
    def __init__(self, per_min):
        self.per_min, self.calls, self.lock = per_min, [], threading.Lock()

    def ok(self) -> bool:
        with self.lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < 60]
            if len(self.calls) >= self.per_min:
                return False
            self.calls.append(now)
            return True


def make_handler(secret: str, site: Site, limiter: Limiter):
    path_ok = f"/mcp/{secret}"

    class Handler(BaseHTTPRequestHandler):
        server_version = "SentireLedgerQA/1"

        def log_message(self, *args):  # the audit line below is the log
            pass

        def _send(self, code, body=None, headers=None):
            data = b"" if body is None else json.dumps(body).encode()
            self.send_response(code)
            if body is not None:
                self.send_header("Content-Type", "application/json")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.split("?")[0].rstrip("/") != path_ok:
                return self._send(404, {"error": "not found"})
            self._send(405, {"error": "POST JSON-RPC to this URL"}, {"Allow": "POST"})

        def do_DELETE(self):
            self._send(404 if self.path.split("?")[0].rstrip("/") != path_ok else 200)

        def do_POST(self):
            if self.path.split("?")[0].rstrip("/") != path_ok:
                return self._send(404, {"error": "not found"})
            try:
                req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            except ValueError:
                return self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            if isinstance(req, list):
                out = [r for r in (self.rpc(x) for x in req) if r is not None]
                return self._send(200, out) if out else self._send(202)
            out = self.rpc(req)
            return self._send(200, out) if out is not None else self._send(202)

        def rpc(self, req):
            rid, method, params = req.get("id"), req.get("method"), req.get("params") or {}
            if rid is None:  # a notification, such as notifications/initialized
                return None
            if method == "initialize":
                return {"jsonrpc": "2.0", "id": rid, "result": {
                    "protocolVersion": params.get("protocolVersion") or PROTOCOL,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "sentire-ledger-staging-qa", "version": "1.0.0"},
                    "instructions": "Sentire Ledger QA connector: drives the STAGING site (never production) as the QA admin. Call staging_status first. Everything goes through the app's own API, so a refusal is the app's own validation or permission check: report it, do not work around it. Money is in pesos. Reset: restart the 'Ledger Staging' app in Dokploy.",
                }}
            if method == "ping":
                return {"jsonrpc": "2.0", "id": rid, "result": {}}
            if method == "tools/list":
                return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
            if method == "tools/call":
                name, args = params.get("name"), params.get("arguments") or {}
                started = time.time()
                if not limiter.ok():
                    result, is_error = {"error": "Rate limit: 120 calls a minute."}, True
                else:
                    try:
                        result = run_tool(site, name, args)
                        is_error = isinstance(result, dict) and "error" in result
                    except KeyError:
                        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": f"Unknown tool {name}"}}
                    except Exception as e:  # connection or sign-in trouble
                        result, is_error = {"error": str(e)[:500]}, True
                print(json.dumps({"qa_mcp": name, "args": {k: (v if k != "values" else "...") for k, v in args.items()}, "ok": not is_error, "ms": int((time.time() - started) * 1000)}), flush=True)
                return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": json.dumps(result, default=str, indent=1)[:200000]}], "isError": bool(is_error)}}
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Method not found: {method}"}}

    return Handler


def preflight(site_name: str) -> str:
    """Refuse to start anywhere but on a staging site."""
    if os.environ.get("PH_STAGING") != "1":
        sys.exit("PH_STAGING is not 1: the QA connector runs only in the staging container")
    if os.environ.get("PH_PRODUCTION") == "1":
        sys.exit("PH_PRODUCTION is 1: refusing to start")
    secret = os.environ.get("QA_MCP_SECRET") or ""
    if len(secret) < 32:
        sys.exit("QA_MCP_SECRET must be at least 32 characters")
    if not os.environ.get("STAGING_ADMIN_PASSWORD"):
        sys.exit("STAGING_ADMIN_PASSWORD is not set")
    conf_path = os.path.join(os.environ.get("QA_SITES_PATH") or "/home/frappe/bench/sites", site_name, "site_config.json")
    try:
        conf = json.load(open(conf_path))
    except OSError:
        sys.exit(f"no site config at {conf_path}")
    if not conf.get("ph_staging_site") or conf.get("ph_cas_production"):
        sys.exit("the site is not a staging site (ph_staging_site 1, ph_cas_production not 1)")
    return secret


def main():
    site_name = os.environ.get("SITE_NAME") or sys.exit("SITE_NAME is required")
    secret = preflight(site_name)
    port = int(os.environ.get("QA_MCP_PORT") or 8010)
    site = Site(site_name, os.environ["STAGING_ADMIN_PASSWORD"])
    httpd = ThreadingHTTPServer(("0.0.0.0", port), make_handler(secret, site, Limiter(RATE_PER_MIN)))
    print(f"== QA connector listening on {port} for {site_name}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
