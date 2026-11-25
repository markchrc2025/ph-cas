"""B88 (CLD-16, task 4.4): export and deletion asked by Sentire Cloud for this site (UC-12).

Calls are signed with the site's event secret. Site creation stays with deploy/ledger-site.sh (a bench-level
step); staff mark the site ready in Sentire Cloud. Deleting a whole site is also bench-level, so delete
answers "manual" and staff record the deletion certificate (ph_cas.hosting.offboard.deletion_certificate).
"""

import hashlib
import hmac
import os
import shutil
import time

import frappe
from frappe.sentire import verify

from ph_cas.cloud import config


def _verified() -> dict | None:
    body = frappe.request.get_data() or b""
    secret = config.conf().get("event_secret")
    if not config.enabled() or not secret or not verify(body, frappe.get_request_header("X-Sentire-Signature") or "", secret):
        frappe.local.response.http_status_code = 401
        return None
    data = frappe.parse_json(body.decode("utf-8"))
    if data.get("orgId") != config.org_id():
        frappe.local.response.http_status_code = 403
        return None
    return data


def _token(name: str, expires: int) -> str:
    secret = config.conf().get("event_secret", "")
    return hmac.new(secret.encode(), f"{name}:{expires}".encode(), hashlib.sha256).hexdigest()


@frappe.whitelist(allow_guest=True, methods=["POST"])
def export():
    data = _verified()
    if data is None:
        return {"ok": False}
    frappe.enqueue("ph_cas.cloud.provisioning.run_export", queue="long", timeout=3600, job_id=f"sentire-export-{data['jobId']}", deduplicate=True, job_id_value=data["jobId"])
    return {"ok": True, "started": True}


def run_export(job_id_value: str):
    """Build the B35 export, zip it, and tell Sentire Cloud where to download it (signed link, 30 days)."""
    from ph_cas.hosting.offboard import export_site

    frappe.set_user("Administrator")
    target = frappe.get_site_path("private", "sentire-export")
    shutil.rmtree(target, ignore_errors=True)
    export_site(target)
    archive = shutil.make_archive(frappe.get_site_path("private", "files", f"sentire-export-{job_id_value}"), "zip", target)
    sha = hashlib.sha256(open(archive, "rb").read()).hexdigest()
    expires = int(time.time()) + 30 * 86400
    name = os.path.basename(archive)
    url = f"{config.site_url()}/api/method/ph_cas.cloud.provisioning.download?name={name}&expires={expires}&sig={_token(name, expires)}"
    _send("app.export.ready", {"jobId": job_id_value, "fileUrl": url, "sha256": sha})


@frappe.whitelist(allow_guest=True, methods=["GET"])
def download(name: str, expires: str, sig: str):
    """The Owner's export link from Sentire Cloud. Works without signing in (the subscription has ended) until it expires."""
    if int(expires) < time.time() or not hmac.compare_digest(sig, _token(name, int(expires))) or "/" in name or not name.startswith("sentire-export-"):
        frappe.throw("This link has expired.", frappe.PermissionError)
    path = frappe.get_site_path("private", "files", name)
    frappe.local.response.filename = name
    frappe.local.response.filecontent = open(path, "rb").read()
    frappe.local.response.type = "download"


@frappe.whitelist(allow_guest=True, methods=["POST"])
def delete_site_data():
    data = _verified()
    if data is None:
        return {"ok": False}
    return {"ok": True, "manual": True, "note": "Site deletion is done with deploy/ledger-site.sh by the operator; staff record the deletion certificate in Sentire Cloud."}


def _send(event_type: str, data: dict):
    import requests
    from frappe.sentire import build_event, encode_event, sign

    event = build_event(event_type, "ledger", data, config.org_id())
    body = encode_event(event)
    requests.post(f"{config.issuer()}/api/v1/events", data=body, headers={"Content-Type": "application/json", "X-Sentire-Signature": sign(body, config.conf()["event_secret"])}, timeout=15).raise_for_status()
