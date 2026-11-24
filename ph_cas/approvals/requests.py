"""The life of an approval request: opened by the maker, walked step by step by the
recipients, closed by a rejection, a withdrawal, or the last approval, which
posts the document (submit) or, on a filed PH Tax Return, opens its amendment.

A request keeps the chain's steps as they were (snapshot) and a fingerprint of
the document; a change to the document after the request voids it, and an
approved request is consumed exactly once by the submit it allows.
"""

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import cint, get_url_to_form, now_datetime

from ph_cas.approvals import chains
from ph_cas.audit.events import record

# B87: the dates a later-day submit moves (see carry_on_submit) are not part of what was approved
VOLATILE = {"posting_date", "posting_time", "due_date", "discount_date", "modified", "modified_by", "creation", "owner", "docstatus", "idx", "name", "parent", "parentfield", "parenttype", "doctype", "__islocal", "__unsaved", "__last_sync_on", "__onload", "_user_tags", "_comments", "_assign", "_liked_by", "amended_from", "workflow_state"}
OPEN = ("Pending", "Approved")


def fingerprint(doc) -> str:
    def strip(d):
        out = {}
        for k, v in d.items():
            if k in VOLATILE or k.startswith("__"):
                continue
            if isinstance(v, list):
                out[k] = [strip(r if isinstance(r, dict) else r.as_dict()) for r in v]
            else:
                out[k] = v
        return out

    payload = strip(doc.as_dict())
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def latest(doctype: str, name: str, statuses=OPEN):
    rows = frappe.get_all("PH Approval Request", {"document_type": doctype, "document_name": name, "status": ["in", list(statuses)]}, ["name"], order_by="creation desc", limit=1)
    return frappe.get_doc("PH Approval Request", rows[0].name) if rows else None


def _step(req, n: int) -> dict | None:
    for s in json.loads(req.snapshot or "[]"):
        if cint(s["step"]) == n:
            return s
    return None


def _steps(req, doc) -> list[dict]:
    return [s for s in json.loads(req.snapshot or "[]") if chains.evaluate(s.get("condition"), doc)]


def _link(doc) -> str:
    return get_url_to_form(doc.doctype, doc.name)


def _mail(recipients: list[str], subject: str, message: str):
    if not recipients:
        return
    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message, delayed=True)
    except Exception:
        frappe.clear_last_message()  # no outgoing account yet: the panel and the home card still carry the request
        frappe.log_error(title="Approval mail not sent")


def _label(doc) -> str:
    return f"{doc.doctype} {doc.name}"


def open_request(doctype: str, name: str, reason: str = "") -> str:
    doc = frappe.get_doc(doctype, name)
    change = doc.docstatus == 1
    cancel = change and doctype != "PH Tax Return"  # B84: a cancellation request
    if not frappe.has_permission(doctype, "cancel" if cancel else "write", doc):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    chain = chains.chain_for(doc)
    if chain is None:
        if cancel:
            frappe.throw(_("No approval chain applies to cancelling {0}; cancel it as usual.").format(_label(doc)))
        frappe.throw(_("No approval chain applies to {0}; submit it as usual.").format(_label(doc)))
    if doctype == "PH Tax Return" and not change:
        frappe.throw(_("A draft return is filed with its BIR confirmation; the chain gates changes to a filed return."))
    if cancel and not (reason or "").strip():
        frappe.throw(_("Give the reason for the cancellation."))
    if change and not (reason or "").strip():
        frappe.throw(_("Give the reason for the change."))
    if latest(doctype, name):
        frappe.throw(_("{0} already has an open approval request.").format(_label(doc)))
    req = frappe.get_doc(
        {
            "doctype": "PH Approval Request",
            "document_type": doctype,
            "document_name": name,
            "company": doc.get("company"),
            "chain": chain.name,
            "status": "Pending",
            "current_step": 0,
            "requested_by": frappe.session.user,
            "requested_at": now_datetime(),
            "reason": (reason or "").strip(),
            "fingerprint": fingerprint(doc),
            "snapshot": json.dumps(chains.snapshot(chain)),
        }
    )
    req.flags.ignore_permissions = True
    req.insert()
    record("approval_requested", doctype, name, doc.docstatus, {"request": req.name, "chain": chain.name, "reason": req.reason})
    _advance(req, doc, after=0)
    return req.name


def _row_for(req, step_no: int, recipient: str, role_type: str, decision: str, title: str):
    req.append("decisions", {"step": step_no, "step_title": title, "recipient": recipient, "role_type": role_type, "decision": decision})


def _advance(req, doc, after: int):
    """Start the first applicable step after `after`; finish when there is none."""
    steps = _steps(req, doc)
    for s in steps:
        n = cint(s["step"])
        if n <= after:
            continue
        users = chains.recipients(frappe._dict(s), doc)
        if not s.get("allow_self_approval"):
            users = [u for u in users if u != req.requested_by]
        if not users:
            _row_for(req, n, None, s["role_type"], "Skipped", s["title"])
            continue
        req.current_step = n
        if s["role_type"] == "Notify":
            for u in users:
                _row_for(req, n, u, "Notify", "Notified", s["title"])
            _mail(users, _("{0} for your information").format(_label(doc)), _notify_message(req, doc, s))
            continue
        order = s.get("receiving_order") or "Any one"
        for i, u in enumerate(users):
            _row_for(req, n, u, "Approver", "Pending" if (order != "Sequential" or i == 0) else "Waiting", s["title"])
        req.save(ignore_permissions=True)
        _mail(users if order != "Sequential" else users[:1], _("{0} awaits your approval").format(_label(doc)), _ask_message(req, doc, s))
        return
    _finish(req, doc)


def _ask_message(req, doc, s) -> str:
    note = f"<p><i>{frappe.utils.escape_html(s.get('private_note') or '')}</i></p>" if s.get("private_note") else ""
    return f"<p>{_label(doc)} was sent for approval by {req.requested_by} (step {s['step']}, {frappe.utils.escape_html(s['title'])}).</p>{note}<p><a href=\"{_link(doc)}\">Open the document</a> to approve or reject it.</p>"


def _notify_message(req, doc, s) -> str:
    return f"<p>{_label(doc)} is going through approval (step {s['step']}, {frappe.utils.escape_html(s['title'])}); this is for your information.</p><p><a href=\"{_link(doc)}\">Open the document</a>.</p>"


def _pending_row(req, user: str):
    for d in req.decisions:
        if cint(d.step) == cint(req.current_step) and d.recipient == user and d.decision == "Pending":
            return d
    return None


def decide(request: str, decision: str, comment: str = "") -> dict:
    if decision not in ("Approved", "Rejected"):
        frappe.throw(_("A decision is Approved or Rejected."))
    req = frappe.get_doc("PH Approval Request", request)
    if req.status != "Pending":
        frappe.throw(_("This request is {0}.").format(req.status))
    user = frappe.session.user
    row = _pending_row(req, user)
    if row is None:
        frappe.throw(_("This step is not waiting for your decision."))
    if decision == "Rejected" and not (comment or "").strip():
        frappe.throw(_("Give the reason for the rejection."))
    doc = frappe.get_doc(req.document_type, req.document_name)
    if fingerprint(doc) != req.fingerprint:
        _void(req, doc, "The document changed after the request was made.")
        frappe.throw(_("{0} changed after the request was made; the request is void. Ask the maker to request approval again.").format(_label(doc)))
    row.decision = decision
    row.decided_at = now_datetime()
    row.comment = (comment or "").strip()
    record(f"approval_{decision.lower()}", req.document_type, req.document_name, doc.docstatus, {"request": req.name, "step": req.current_step, "by": user, "comment": row.comment})
    if decision == "Rejected":
        for d in req.decisions:
            if d.decision in ("Pending", "Waiting"):
                d.decision = "Skipped"
        req.status = "Rejected"
        req.decided_at = now_datetime()
        req.save(ignore_permissions=True)
        _mail([req.requested_by], _("{0} was rejected").format(_label(doc)), f"<p>{user} rejected {_label(doc)} at step {req.current_step}: {frappe.utils.escape_html(row.comment)}</p><p><a href=\"{_link(doc)}\">Open the document</a>, change it and request approval again.</p>")
        return {"status": req.status}
    s = _step(req, cint(req.current_step)) or {}
    order = s.get("receiving_order") or "Any one"
    step_rows = [d for d in req.decisions if cint(d.step) == cint(req.current_step) and d.role_type == "Approver"]
    done = False
    if order == "Any one":
        for d in step_rows:
            if d.decision in ("Pending", "Waiting"):
                d.decision = "Skipped"
        done = True
    elif order == "Everyone":
        done = all(d.decision == "Approved" for d in step_rows)
    else:
        nxt = next((d for d in step_rows if d.decision == "Waiting"), None)
        if nxt:
            nxt.decision = "Pending"
            req.save(ignore_permissions=True)
            _mail([nxt.recipient], _("{0} awaits your approval").format(_label(doc)), _ask_message(req, doc, s))
        else:
            done = True
    if done:
        req.save(ignore_permissions=True)
        _advance(req, doc, after=cint(req.current_step))
    else:
        req.save(ignore_permissions=True)
    req.reload()
    return {"status": req.status}


def _carry_to_today(doc):
    """B87 (LDG-244): a draft approved on a later day posts today (ERPNext moves a document's
    posting date to today when Edit Posting Date is not ticked). Its due dates move by the same
    number of days, so the terms the maker set are kept and no due date falls before the posting
    date ("Due Date cannot be before ..."). A date the manager set on purpose is left alone."""
    from frappe.utils import add_days, date_diff, getdate, nowdate

    if not doc.meta.has_field("posting_date") or not doc.get("posting_date") or doc.get("set_posting_time"):
        return
    days = date_diff(nowdate(), doc.posting_date)
    if days <= 0:
        return
    doc.posting_date = nowdate()
    if doc.meta.has_field("posting_time"):
        doc.posting_time = frappe.utils.nowtime()
    if doc.get("due_date"):
        doc.due_date = add_days(doc.due_date, days)
    for row in doc.get("payment_schedule") or []:
        if row.get("due_date"):
            row.due_date = add_days(row.due_date, days)
        if row.get("discount_date"):
            row.discount_date = add_days(row.discount_date, days)
    if doc.get("bill_date") and doc.get("due_date") and getdate(doc.due_date) < getdate(doc.bill_date):
        doc.due_date = doc.bill_date


def carry_on_submit(doc, method=None):
    """doc_events before_validate (Sales and Purchase Invoice): a draft from an earlier day that
    is submitted today, by its maker or by an approval, carries today with its due dates."""
    if doc.docstatus == 1 and getattr(doc, "_action", None) == "submit":
        _carry_to_today(doc)


def _finish(req, doc):
    req.status = "Approved"
    req.decided_at = now_datetime()
    req.save(ignore_permissions=True)
    record("approval_completed", req.document_type, req.document_name, doc.docstatus, {"request": req.name, "approvers": [d.recipient for d in req.decisions if d.decision == "Approved"]})
    try:
        if doc.docstatus == 0:
            frappe.flags.ph_approval_submit = req.name
            doc.flags.ignore_permissions = True
            _carry_to_today(doc)
            doc.submit()
        elif req.document_type == "PH Tax Return":
            frappe.flags.ph_approval_amend = doc.name
            doc.open_amendment(req.reason or "Approved change request")
            consume(req.name)
        else:
            # B84: an approved cancellation request
            frappe.flags.ph_approval_cancel = req.name
            doc.flags.ignore_permissions = True
            doc.cancel()
    except Exception:
        # the approval stands; the maker fixes the document and submits (the gate
        # consumes the approved request when the document is unchanged)
        if frappe.flags.in_test:
            raise
        req.reload()
        _mail([req.requested_by], _("{0} is approved but could not be posted").format(_label(doc)), f"<p>Every approver approved {_label(doc)}, but posting it failed. <a href=\"{_link(doc)}\">Open the document</a>, read the error, and submit it.</p>")
        frappe.log_error(title=f"Approved {_label(doc)} did not post")
        frappe.flags.ph_approval_submit = None
        frappe.flags.ph_approval_amend = None
        frappe.flags.ph_approval_cancel = None
        return
    finally:
        frappe.flags.ph_approval_submit = None
        frappe.flags.ph_approval_amend = None
        frappe.flags.ph_approval_cancel = None
    done = _("cancelled") if doc.docstatus == 2 else _("posted")
    _mail([req.requested_by], _("{0} is approved and {1}").format(_label(doc), done), f"<p>{_label(doc)} went through every step and is {done}.</p><p><a href=\"{_link(doc)}\">Open the document</a>.</p>")


def consume(request: str):
    frappe.db.set_value("PH Approval Request", request, {"status": "Consumed"}, update_modified=True)


def _void(req, doc, why: str):
    req.status = "Void"
    req.reason = ((req.reason + " | ") if req.reason else "") + why
    req.decided_at = now_datetime()
    for d in req.decisions:
        if d.decision in ("Pending", "Waiting"):
            d.decision = "Skipped"
    req.save(ignore_permissions=True)
    record("approval_void", req.document_type, req.document_name, doc.docstatus, {"request": req.name, "why": why})


def withdraw(request: str) -> dict:
    req = frappe.get_doc("PH Approval Request", request)
    if req.status != "Pending":
        frappe.throw(_("This request is {0}.").format(req.status))
    if frappe.session.user != req.requested_by and not frappe.has_permission("PH Approval Chain", "write"):
        frappe.throw(_("Only the requestor or a manager withdraws a request."))
    req.status = "Withdrawn"
    req.decided_at = now_datetime()
    for d in req.decisions:
        if d.decision in ("Pending", "Waiting"):
            d.decision = "Skipped"
    req.save(ignore_permissions=True)
    record("approval_withdrawn", req.document_type, req.document_name, 0, {"request": req.name, "by": frappe.session.user})
    return {"status": req.status}


def void_if_changed(doc):
    """on_update of any document: a change after the request voids it."""
    req = latest(doc.doctype, doc.name)
    if req is None:
        return
    if fingerprint(doc) != req.fingerprint:
        _void(req, doc, "The document changed after the request was made.")


def pending_for(user: str | None = None) -> list[dict]:
    user = user or frappe.session.user
    rows = frappe.db.sql(
        """select r.name as request, r.document_type, r.document_name, r.requested_by, r.requested_at, r.current_step, d.step_title
           from `tabPH Approval Decision` d join `tabPH Approval Request` r on r.name = d.parent
           where d.recipient = %s and d.decision = 'Pending' and r.status = 'Pending' and d.step = r.current_step
           order by r.requested_at""",
        (user,),
        as_dict=True,
    )
    for r in rows:
        r["title"] = frappe.db.get_value(r.document_type, r.document_name, "title") if frappe.get_meta(r.document_type).get_field("title") else None
        r["url"] = f"/app/{frappe.scrub(r.document_type).replace('_', '-')}/{r.document_name}"
    return rows


def status_for(doctype: str, name: str) -> dict:
    """What the form's panel shows: whether a chain applies, the open or last request
    with its steps, and what the current user may do."""
    doc = frappe.get_doc(doctype, name)
    chain = chains.chain_for(doc)
    if doctype == "PH Tax Return" and doc.docstatus == 0:
        chain = None
    out = {"applies": chain is not None, "action": chains.action_for(doc), "chain": chain.name if chain else None, "chain_title": chain.title if chain else None, "single_user": chains.single_user_site(), "request": None}
    req = latest(doctype, name) or latest(doctype, name, ("Rejected", "Withdrawn", "Void", "Consumed"))
    if req is None:
        return out
    user = frappe.session.user
    steps = []
    for s in json.loads(req.snapshot or "[]"):
        rows = [d for d in req.decisions if cint(d.step) == cint(s["step"])]
        steps.append({"step": s["step"], "title": s["title"], "role_type": s["role_type"], "receiving_order": s["receiving_order"], "current": cint(req.current_step) == cint(s["step"]) and req.status == "Pending", "decisions": [{"recipient": d.recipient, "decision": d.decision, "decided_at": str(d.decided_at or ""), "comment": d.comment or ""} for d in rows], "private_note": s.get("private_note") if any(d.recipient == user for d in rows) else ""})
    out["request"] = {"name": req.name, "status": req.status, "requested_by": req.requested_by, "requested_at": str(req.requested_at or ""), "decided_at": str(req.decided_at or ""), "reason": req.reason or "", "current_step": req.current_step, "steps": steps, "can_decide": req.status == "Pending" and _pending_row(req, user) is not None, "can_withdraw": req.status == "Pending" and (user == req.requested_by or frappe.has_permission("PH Approval Chain", "write"))}
    return out
