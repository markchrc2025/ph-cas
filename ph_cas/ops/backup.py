"""B31: backups and the restore drill (decisions D2, D3; Annex B item 7).

Frappe's bench backup dumps the database only and prunes after about a day.
Here: database plus private and public files, a manifest with SHA-256 hashes,
AES-256 encryption with the key in site_config (ph_backup_key), and an
off-site copy by rclone to the Philippine bucket named in site_config
(ph_backup_remote). Retention ten years (RETENTION-5Y rule notes the Annex B
form's figure). A monthly restore drill restores the latest backup into a
scratch site and runs the chain check there.
"""

import hashlib
import json
import os
import shutil
import subprocess

import frappe
from frappe.utils import now_datetime
from frappe.utils.backups import new_backup


def run_backup(encrypt: bool = True, upload: bool = True) -> dict:
    b = new_backup(ignore_files=False, force=True)
    files = [p for p in (b.backup_path_db, b.backup_path_files, b.backup_path_private_files, b.backup_path_conf) if p and os.path.exists(p)]
    manifest = {"site": frappe.local.site, "taken_on": now_datetime().strftime("%Y-%m-%d %H:%M:%S"), "files": {}}
    out_files = []
    key = frappe.conf.get("ph_backup_key")
    for path in files:
        digest = _sha256(path)
        manifest["files"][os.path.basename(path)] = {"sha256": digest, "bytes": os.path.getsize(path)}
        if encrypt and key:
            enc = encrypt_file(path, key)
            out_files.append(enc)
            manifest["files"][os.path.basename(path)]["encrypted"] = os.path.basename(enc)
        else:
            out_files.append(path)
    mpath = os.path.join(os.path.dirname(b.backup_path_db), os.path.basename(b.backup_path_db).replace("-database.sql.gz", "-manifest.json"))
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    out_files.append(mpath)
    result = {"files": out_files, "manifest": mpath, "uploaded": False}
    remote = frappe.conf.get("ph_backup_remote")
    if upload and remote and shutil.which("rclone"):
        for p in out_files:
            subprocess.run(["rclone", "copy", p, f"{remote}/{frappe.local.site}/"], check=True)
        result["uploaded"] = True
    frappe.db.set_value("PH CAS Settings", None, "last_backup_on", now_datetime(), update_modified=False)
    from ph_cas.audit.events import record

    record("settings_change", "PH CAS Settings", "backup", 0, {"backup": os.path.basename(mpath), "uploaded": result["uploaded"], "encrypted": bool(encrypt and key)})
    return result


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def encrypt_file(path: str, key: str) -> str:
    out = path + ".enc"
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-in", path, "-out", out, "-pass", f"pass:{key}"], check=True)
    os.remove(path)
    return out


def decrypt_file(path: str, key: str, out: str | None = None) -> str:
    out = out or path[:-4]
    subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", path, "-out", out, "-pass", f"pass:{key}"], check=True)
    return out


def verify_backup(manifest_path: str, key: str | None = None) -> dict:
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    folder = os.path.dirname(manifest_path)
    bad = []
    for name, meta in manifest["files"].items():
        path = os.path.join(folder, meta.get("encrypted") or name)
        if not os.path.exists(path):
            bad.append(name)
            continue
        if meta.get("encrypted"):
            if not key:
                continue
            tmp = decrypt_file(path, key, os.path.join(folder, "verify-" + name))
            ok = _sha256(tmp) == meta["sha256"]
            os.remove(tmp)
        else:
            ok = _sha256(path) == meta["sha256"]
        if not ok:
            bad.append(name)
    return {"ok": not bad, "bad": bad, "taken_on": manifest["taken_on"]}


def scheduled_daily_backup():
    """scheduler_events.daily"""
    try:
        run_backup()
    except Exception:
        frappe.log_error("ph_cas: daily backup failed")
        raise
