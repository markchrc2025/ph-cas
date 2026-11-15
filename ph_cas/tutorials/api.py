"""Tutorial videos, played inside Sentire Ledger from our own server.

Each video has three files in the private bucket, under tutorials/<code>/:
video.mp4, captions.vtt and poster.jpg. Every site shares them; the records here (seeded from
data/tutorials.json) say where each video plays: the onboarding cards in `steps`, and the forms
in `help_for`, which offer it under Help.

Playback: `play` returns links signed for a few hours. The captions come through this site
(`captions`), so the player needs nothing from the bucket but the video and its thumbnail.

Upload (System Manager): the browser sends a file in 8 MB pieces to `upload_part`, which passes
each piece to the bucket as one part of a multipart upload. Nothing is kept on this server.
"""

import json
import os
import re

import frappe
from frappe import _
from frappe.utils import now_datetime

from ph_cas.tutorials import storage

DOCTYPE = "PH Tutorial Video"
PART_SIZE = 8 * 1024 * 1024
KINDS = {
    "video": ("video.mp4", "video/mp4"),
    "captions": ("captions.vtt", "text/vtt; charset=utf-8"),
    "poster": ("poster.jpg", "image/jpeg"),
}


def key(code: str, kind: str) -> str:
    return f"tutorials/{code}/{KINDS[kind][0]}"


# ---- the catalogue -----------------------------------------------------------------------------
def catalogue() -> list[dict]:
    with open(os.path.join(os.path.dirname(__file__), "data", "tutorials.json"), encoding="utf-8") as f:
        return json.load(f)["videos"]


def seed() -> dict:
    """Create or refresh the records from data/tutorials.json. Upload state is left alone."""
    made, updated = [], []
    for row in catalogue():
        steps = [s for s in row["steps"] if frappe.db.exists("Onboarding Step", s)]
        values = {
            "title": row["title"],
            "length": row["length"],
            "summary": row["summary"],
            "help_for": "\n".join(row["help_for"]),
        }
        if frappe.db.exists(DOCTYPE, row["code"]):
            doc = frappe.get_doc(DOCTYPE, row["code"])
            changed = any((doc.get(k) or "") != v for k, v in values.items()) or [s.step for s in doc.steps] != steps
            if not changed:
                continue
            doc.update(values)
            doc.set("steps", [{"step": s} for s in steps])
            doc.save(ignore_permissions=True)
            updated.append(row["code"])
        else:
            doc = frappe.get_doc({"doctype": DOCTYPE, "code": row["code"], **values, "steps": [{"step": s} for s in steps]})
            doc.insert(ignore_permissions=True)
            made.append(row["code"])
    return {"made": made, "updated": updated}


def step_map() -> dict:
    """Onboarding step name -> video code, for the onboarding card (sent in boot)."""
    rows = frappe.get_all("PH Tutorial Video Step", filters={"parenttype": DOCTYPE}, fields=["parent", "step"])
    return {r.step: r.parent for r in rows}


def help_map() -> dict:
    """DocType -> [(code, title)], for the Help menu on forms (sent in boot)."""
    out = {}
    for r in frappe.get_all(DOCTYPE, fields=["name", "title", "help_for"], order_by="name asc"):
        for dt in (r.help_for or "").splitlines():
            if dt.strip():
                out.setdefault(dt.strip(), []).append([r.name, r.title])
    return out


def extend_bootinfo(bootinfo):
    if frappe.session.user == "Guest":
        return
    try:
        # only what this site knows is on the server, so no card or menu offers a missing video
        on_server = uploaded()
        steps = {step: code for step, code in step_map().items() if code in on_server}
        helps = {dt: [v for v in vids if v[0] in on_server] for dt, vids in help_map().items()}
        bootinfo.ph_tutorials = {"steps": steps, "help": {dt: v for dt, v in helps.items() if v}, "storage": storage.is_configured()}
    except Exception:
        # a missing table during the first migrate must not break the desk
        bootinfo.ph_tutorials = {"steps": {}, "help": {}, "storage": False}


# ---- playback ----------------------------------------------------------------------------------
def _require_desk_user():
    user = frappe.session.user
    if user == "Guest" or frappe.get_cached_value("User", user, "user_type") != "System User":
        frappe.throw(_("Sign in to watch the tutorials."), frappe.PermissionError)


def _present(code: str) -> dict:
    """What the bucket holds for a video. Cached for ten minutes per site."""
    cache_key = f"ph_tutorial_present:{code}"
    hit = frappe.cache.get_value(cache_key)
    if hit is not None:
        return hit
    s3 = storage.client()
    out = {kind: bool(s3.head(key(code, kind))) for kind in KINDS}
    frappe.cache.set_value(cache_key, out, expires_in_sec=600)
    return out


@frappe.whitelist()
def play(code: str) -> dict:
    """Signed links for the player. `available` is false until the video is uploaded."""
    _require_desk_user()
    code = _clean_code(code)
    title = frappe.db.get_value(DOCTYPE, code, "title")
    if not title:
        frappe.throw(_("There is no tutorial {0}.").format(code))
    if not storage.is_configured():
        return {"code": code, "title": title, "available": False, "reason": "not_configured"}
    present = _present(code)
    if not present["video"]:
        return {"code": code, "title": title, "available": False, "reason": "not_uploaded"}
    s3 = storage.client()
    return {
        "code": code,
        "title": title,
        "available": True,
        "video": s3.presign(key(code, "video")),
        "poster": s3.presign(key(code, "poster")) if present["poster"] else None,
        "captions": f"/api/method/ph_cas.tutorials.api.captions?code={code}" if present["captions"] else None,
    }


@frappe.whitelist()
def captions(code: str):
    """The captions file, served by this site so the player's <track> stays same-origin."""
    _require_desk_user()
    code = _clean_code(code)
    cache_key = f"ph_tutorial_vtt:{code}"
    text = frappe.cache.get_value(cache_key)
    if text is None:
        text = storage.client().get(key(code, "captions")).decode("utf-8")
        frappe.cache.set_value(cache_key, text, expires_in_sec=3600)
    from werkzeug.wrappers import Response

    return Response(text, mimetype="text/vtt", headers={"Cache-Control": "private, max-age=3600"})


# ---- upload (System Manager) --------------------------------------------------------------------
def _require_uploader():
    frappe.only_for("System Manager")


def _clean_code(code: str) -> str:
    code = (code or "").strip().upper()
    if not re.fullmatch(r"V\d{2}", code):
        frappe.throw(_("{0} is not a tutorial code (V01, V02, ...).").format(code or "''"))
    return code


def code_from_filename(filename: str) -> str | None:
    """SL-V35-file-your-withholding-tax-returns.mp4 -> V35."""
    m = re.search(r"(?:^|[^A-Za-z0-9])V(\d{2})(?:[^0-9]|$)", filename or "", re.I)
    return f"V{m.group(1)}" if m else None


def srt_to_vtt(text: str) -> str:
    text = text.replace("\r\n", "\n").lstrip("﻿").strip()
    if text.startswith("WEBVTT"):
        return text + "\n"
    text = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", text)
    return "WEBVTT\n\n" + text + "\n"


def _mark(code: str, **values):
    values.update({"uploaded_on": now_datetime(), "uploaded_by": frappe.session.user, "checked_on": now_datetime()})
    frappe.db.set_value(DOCTYPE, code, values)
    frappe.cache.delete_value(f"ph_tutorial_present:{code}")
    frappe.cache.delete_value(f"ph_tutorial_vtt:{code}")


@frappe.whitelist(methods=["POST"])
def start_upload(code: str, kind: str, size: int) -> dict:
    _require_uploader()
    code = _clean_code(code)
    if not frappe.db.exists(DOCTYPE, code):
        frappe.throw(_("There is no tutorial {0}.").format(code))
    if kind not in KINDS:
        frappe.throw(_("Unknown file kind {0}.").format(kind))
    size = int(size)
    if kind == "video":
        upload_id = storage.client().start_multipart(key(code, kind), KINDS[kind][1])
        frappe.cache.set_value(f"ph_tutorial_upload:{upload_id}", {"code": code, "size": size, "etags": {}}, expires_in_sec=6 * 3600)
        return {"upload_id": upload_id, "part_size": PART_SIZE, "parts": max(1, -(-size // PART_SIZE))}
    return {"upload_id": None, "part_size": size, "parts": 1}


@frappe.whitelist(methods=["POST"])
def upload_part(code: str, kind: str, part: int = 1, upload_id: str | None = None) -> dict:
    """The request body is the raw bytes of one piece of the file."""
    _require_uploader()
    code = _clean_code(code)
    data = _body()
    if not data:
        frappe.throw(_("The upload sent no data."))
    s3 = storage.client()
    if kind == "video":
        state = frappe.cache.get_value(f"ph_tutorial_upload:{upload_id}")
        if not state or state["code"] != code:
            frappe.throw(_("This upload has expired. Start it again."))
        etag = s3.upload_part(key(code, kind), upload_id, int(part), data)
        state["etags"][str(int(part))] = etag
        frappe.cache.set_value(f"ph_tutorial_upload:{upload_id}", state, expires_in_sec=6 * 3600)
        return {"part": int(part), "etag": etag}
    if kind == "captions":
        data = srt_to_vtt(data.decode("utf-8-sig", errors="replace")).encode("utf-8")
        s3.put(key(code, kind), data, KINDS[kind][1])
        _mark(code, has_captions=1)
    elif kind == "poster":
        data = _to_jpeg(data)
        s3.put(key(code, kind), data, KINDS[kind][1])
        _mark(code, has_poster=1)
    else:
        frappe.throw(_("Unknown file kind {0}.").format(kind))
    return {"done": True}


@frappe.whitelist(methods=["POST"])
def finish_upload(code: str, upload_id: str) -> dict:
    _require_uploader()
    code = _clean_code(code)
    state = frappe.cache.get_value(f"ph_tutorial_upload:{upload_id}")
    if not state or state["code"] != code:
        frappe.throw(_("This upload has expired. Start it again."))
    n = max(1, -(-state["size"] // PART_SIZE))
    missing = [i for i in range(1, n + 1) if str(i) not in state["etags"]]
    if missing:
        frappe.throw(_("Parts {0} did not arrive. Upload the file again.").format(", ".join(map(str, missing))))
    storage.client().complete_multipart(key(code, "video"), upload_id, [state["etags"][str(i)] for i in range(1, n + 1)])
    frappe.cache.delete_value(f"ph_tutorial_upload:{upload_id}")
    _mark(code, video_size=state["size"])
    return {"done": True, "size": state["size"]}


@frappe.whitelist(methods=["POST"])
def cancel_upload(code: str, upload_id: str) -> dict:
    _require_uploader()
    code = _clean_code(code)
    try:
        storage.client().abort_multipart(key(code, "video"), upload_id)
    finally:
        frappe.cache.delete_value(f"ph_tutorial_upload:{upload_id}")
    return {"done": True}


@frappe.whitelist()
def refresh_status() -> dict:
    """Check every video against the bucket (another site may have uploaded it)."""
    _require_uploader()
    s3 = storage.client()
    out = {}
    for code in frappe.get_all(DOCTYPE, pluck="name"):
        video = s3.head(key(code, "video"))
        values = {
            "video_size": video["size"] if video else 0,
            "has_captions": int(bool(s3.head(key(code, "captions")))),
            "has_poster": int(bool(s3.head(key(code, "poster")))),
            "checked_on": now_datetime(),
        }
        frappe.db.set_value(DOCTYPE, code, values)
        frappe.cache.delete_value(f"ph_tutorial_present:{code}")
        out[code] = bool(video)
    return out


def daily_refresh():
    """Another site may have uploaded a video; keep this site's records in step with the bucket."""
    if not storage.is_configured():
        return
    try:
        frappe.set_user("Administrator")
        refresh_status()
    except Exception:
        frappe.log_error(title="Tutorial videos: could not check the video server")


def uploaded() -> dict:
    """Video code -> length, for the videos this site knows are on the server."""
    return {r.name: r.length for r in frappe.get_all(DOCTYPE, filters={"video_size": [">", 0]}, fields=["name", "length"])}


def _body() -> bytes:
    return frappe.request.get_data()


def _to_jpeg(data: bytes) -> bytes:
    """The thumbnails come as PNG from the edit; the player shows a JPEG of at most 1280 wide."""
    from io import BytesIO

    from PIL import Image

    img = Image.open(BytesIO(data))
    img = img.convert("RGB")
    if img.width > 1280:
        img = img.resize((1280, round(img.height * 1280 / img.width)))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()
