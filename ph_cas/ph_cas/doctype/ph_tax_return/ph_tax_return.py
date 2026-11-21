"""PH Tax Return: one BIR return (or certificate run) of a company for a period.

Draft -> Ready (needs empty) -> Filed (submitted: read-only, the seal) -> Amended
(superseded by an amendment). Three kinds of figure: books (fed from posted
records, kept in `data` with a `_source`), typed (the user's, also in `data`)
and derived (the compute, shown in `lines`, never stored as truth).

Filing requires: needs empty, the BIR confirmation e-mail (or a System Manager
override with a reason), a contact number, and a built engine. At that moment
the Company's taxpayer block is snapshotted, the clear copy is rendered from the
stored export, and the figures are published to PH Tax Return Figures.
"""

import hashlib
import json
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime

from ph_cas.birpdf import BirPdfError, parse_ebir_export, render_return
from ph_cas.forms import confirmation as conf
from ph_cas.forms import engine, period as period_mod
from ph_cas.forms.export import ExportRefusal, manila_date, write_lined, write_tabbed
from ph_cas.forms.money import text as money_text
from ph_cas.forms.registry import BUILT, spec

MANAGER_ROLES = ("Accounts Manager", "Accounting Manager", "System Manager")
PREVIEWS_PER_MINUTE = 40
TOO_MANY_PREVIEWS = "Too many previews; wait a moment."
SEALED = "This return has been filed and is sealed: a filed return is never changed. Ask a manager to open an amendment."


class PHTaxReturn(Document):
    # ---- lifecycle ---------------------------------------------------------------
    def autoname(self):
        self.company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        self.period_key = self._period().key
        self.name = f"{self.form}-{self.period_key}-{self.company_abbr}" + ("-A" + str(self._amendment_no()) if self.amends else "")

    def _amendment_no(self) -> int:
        return frappe.db.count("PH Tax Return", {"amends": self.amends}) + 1

    def _spec(self):
        return spec(self.form)

    def onload(self):
        # only the forms the BIR's eBIRForms package can open get an export file; the rest are
        # printed on the BIR form and keyed into eBIRForms or eFPS from that print
        self.set_onload("ebir_export", bool(self.form) and self._spec().output == "export")

    def _company(self) -> dict:
        if self.docstatus == 1 and self.filed_snapshot:
            snap = self.filed_snapshot if isinstance(self.filed_snapshot, dict) else json.loads(self.filed_snapshot)
            return snap.get("company") or snap
        return engine.taxpayer_block(frappe.get_cached_doc("Company", self.company))

    def _period(self):
        s = self._spec()
        fy = frappe.get_cached_value("Company", self.company, "ph_fiscal_year_start") if s.fiscal else None
        try:
            return period_mod.parse(self.period_key, s.period, fy)
        except ValueError as e:
            frappe.throw(_("{0} for the {1}.").format(str(e), self.form))

    def _data(self) -> dict:
        d = self.data
        if isinstance(d, str):
            d = json.loads(d) if d.strip() else {}
        return d or {}

    def _ctx(self) -> engine.Context:
        return engine.Context(
            spec=self._spec(),
            period=self._period(),
            company=self._company(),
            is_amended=bool(self.is_amended),
            contact_number=self.contact_number or "",
            date_filed=self.filed_on.strftime("%Y/%m/%d") if self.docstatus == 1 and self.filed_on else manila_date(),
            final=self.docstatus == 1,
            return_name=self.name or "",
            extra={"amends": self.amends},
        )

    def validate(self):
        s = self._spec()
        self.form_version = s.version
        self.company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
        p = self._period()
        self.period_key, self.period_label = p.key, p.label
        self.period_start, self.period_end, self.fiscal = p.start, p.end, int(p.fiscal)
        if not self.contact_number:
            self.contact_number = frappe.get_cached_value("Company", self.company, "ph_contact_number") or ""
        if self.docstatus == 0:
            self.refresh_figures()
            self.status = "Ready" if not self._needs() else "Draft"
        if self.amends and not self.is_amended:
            self.is_amended = 1

    def refresh_figures(self):
        """lines, needs and warnings from the draft's data; derived figures are never stored elsewhere."""
        data = self._data()
        out = engine.refresh(data, self._ctx())
        self.set("lines", [])
        for ln in out["lines"]:
            if str(ln["item"]).startswith("_"):
                continue
            self.append("lines", {"item": ln["item"], "label": ln["label"], "amount": float(ln["amount"]), "source": ln.get("kind", "derived"), "reason": ln.get("source") or ""})
        self.needs = json.dumps(out["needs"])
        warnings = list(out["warnings"])
        if self.form == "2550Q" and self.alphalist_file and not self.is_new():
            warnings += self._slsp_tie_out()
        self.warnings = "\n".join(warnings)
        self.data = json.dumps(data, default=str)

    def _needs(self) -> list:
        n = self.needs
        if isinstance(n, str):
            n = json.loads(n) if n.strip() else []
        return n or []

    def on_trash(self):
        if self.docstatus == 1:
            frappe.throw(_(SEALED))
        if self.amends and frappe.db.get_value("PH Tax Return", self.amends, "amended_by") == self.name:
            # a deleted draft amendment frees the original for a new one
            frappe.db.set_value("PH Tax Return", self.amends, "amended_by", None, update_modified=False)

    # ---- the seal ------------------------------------------------------------------
    def before_submit(self):
        s = self._spec()
        if s.code not in BUILT:
            frappe.throw(_("The {0} engine is not built yet; it cannot be filed from here.").format(s.code))
        if s.output != "certificate" and not set(frappe.get_roles()) & set(MANAGER_ROLES):
            # B79: an Accountant prepares the return; the Accounting Manager or the Owner files it
            frappe.throw(_("Only an Accounting Manager or the Owner marks a return as filed. The Accountant prepares it; ask a manager to submit it."), frappe.PermissionError)
        needs = self._needs()
        if needs:
            frappe.throw(_("The return still needs: {0}").format("; ".join(n["question"] for n in needs[:5])))
        if not (self.contact_number or "").strip():
            frappe.throw(_("A contact number is needed before a return is submitted."))
        basis = {"filed_on": getdate(), "reference": "issued"} if s.output == "certificate" else self._confirmation_basis()
        self.filed_on = basis["filed_on"]
        self.filed_reference = basis["reference"]
        snapshot = {"snapshot_version": 1, "taken_at": now_datetime().isoformat(), "company": engine.taxpayer_block(frappe.get_cached_doc("Company", self.company)), "contact_number": self.contact_number}
        mod = engine.module(s)
        if hasattr(mod, "filed_snapshot_extra"):
            snapshot.update(mod.filed_snapshot_extra(self._data(), self._ctx()))
        self.filed_snapshot = json.dumps(snapshot, default=str)
        self.status = "Filed"
        if s.output == "export":
            self._write_export(final=True)

    def _confirmation_basis(self) -> dict:
        if self.override_reason and (self.override_reason or "").strip():
            if "System Manager" not in frappe.get_roles():
                frappe.throw(_("Only a System Manager may file without the BIR confirmation e-mail."))
            return {"filed_on": getdate(), "reference": "override"}
        if not self.confirmation:
            frappe.throw(_("Attach the BIR Tax Return Receipt Confirmation e-mail to mark this return as filed (a System Manager may override with a reason)."))
        c = frappe.get_doc("PH BIR Confirmation", self.confirmation)
        if c.tax_return and c.tax_return != self.name:
            frappe.throw(_("Confirmation {0} is already attached to {1}.").format(c.name, c.tax_return))
        errors = self._check_confirmation(c)
        if errors:
            frappe.throw(_("The confirmation does not match this return: {0}").format(" ".join(errors)))
        c.db_set("tax_return", self.name)
        received = get_datetime(c.received_at) if c.received_at else None
        return {"filed_on": received.date() if received else getdate(), "reference": c.reference or c.name}

    def _check_confirmation(self, c) -> list[str]:
        if c.kind == "Override":
            return []
        comp = self._company()
        p = self._period()
        facts = conf.ConfirmationFacts(True, c.reference, get_datetime(c.received_at).replace(tzinfo=conf.MANILA) if c.received_at else None, c.sha256 or "")
        return conf.check_against(facts, self._spec().key, comp.get("tax_id") or "", comp.get("ph_branch_code") or "0", p.kind, p.year, p.n)

    def on_submit(self):
        self._render(clear=True)
        mod = engine.module(self._spec())
        if hasattr(mod, "on_filed"):
            mod.on_filed(self)
        if self._spec().output != "certificate":
            self._publish_figures()
        if self.amends:
            frappe.db.set_value("PH Tax Return", self.amends, {"status": "Amended", "amended_by": self.name})
        frappe.db.set_value("PH Tax Return", self.name, "status", "Filed")

    def on_cancel(self):
        frappe.throw(_(SEALED))

    def _publish_figures(self):
        """The filed figures feed the dashboard, the calendar and the reconciliation through
        PH Tax Return Figures, as before F0."""
        from ph_cas.tax.returns import get_or_create

        fig = get_or_create(self.company, self.form, self.period_start, self.period_end, compute=False)
        frappe.flags.ph_recompute_filed = True
        try:
            fig.set("lines", [])
            for r in self.lines:
                fig.append("lines", {"item": r.item, "label": r.label, "amount": r.amount, "source": f"PH Tax Return {self.name}"})
            fig.filed, fig.filed_reference, fig.filed_on = 1, self.filed_reference, self.filed_on
            fig.computed_on, fig.computed_by = now_datetime(), frappe.session.user
            fig.save(ignore_permissions=True)
        finally:
            frappe.flags.ph_recompute_filed = False

    # ---- books, export, print -------------------------------------------------------
    @frappe.whitelist()
    def refresh_from_books(self):
        if self.docstatus != 0:
            frappe.throw(_(SEALED))
        mod = engine.module(self._spec())
        if mod is None:
            frappe.throw(_("The {0} engine is not built yet.").format(self.form))
        data = self._data()
        fed = mod.feed(self._ctx())
        overridden = []
        src = data.get("_source") or {}
        prior = src.get("books") or {}
        for k, v in fed["figures"].items():
            v = money_text(v) if not isinstance(v, (list, dict, str)) else v
            if k in data and k in prior and data[k] != prior[k]:
                overridden.append(k)  # the user changed a books figure: keep theirs, say so
                continue
            data[k] = v
        data["_source"] = {"kind": "books", "as_of": now_datetime().isoformat(), "books": {k: (money_text(v) if not isinstance(v, (list, dict, str)) else v) for k, v in fed["figures"].items()}, "lines": fed["lines"], "warnings": fed["warnings"] + [f"{k} was changed by hand and kept; the books say {prior[k]}." for k in overridden]}
        self.data = json.dumps(data, default=str)
        self.books_as_of = now_datetime()
        self.save()
        return {"figures": len(fed["figures"]), "warnings": self.warnings}

    def _rows(self) -> tuple[list, str | None]:
        s = self._spec()
        mod = engine.module(s)
        if mod is None:
            frappe.throw(_("The {0} engine is not built yet.").format(self.form))
        data, ctx = self._data(), self._ctx()
        comp = mod.compute(data, ctx)
        try:
            if s.output == "export":
                rows, name = mod.export_rows(data, comp, ctx)
                return rows, name
            return mod.print_rows(data, comp, ctx), None
        except ExportRefusal as e:
            frappe.throw(str(e))

    def _export_text(self, rows: list) -> str:
        """The eBIRForms file in the form's own layout: the engine's writer when it has one
        (the income-tax returns), else the tabbed 2551Q layout or the lined one."""
        s = self._spec()
        writer = getattr(engine.module(s), "write_export", None)
        if writer:
            return writer(rows)
        return write_tabbed(rows) if s.key == "2551Q" else write_lined(rows)

    def _write_export(self, final: bool = False) -> str:
        s = self._spec()
        rows, file_name = self._rows()
        if final:
            rows = [(k, "1" if k == "txtFinalFlag" else v) for k, v in rows]
        text = self._export_text(rows)
        f = self._attach(file_name, text.encode("utf-8"), "export_file")
        self.export_file, self.export_file_name = f.file_url, file_name
        return f.file_url

    def _attach(self, file_name: str, content: bytes, fieldname: str):
        for old in frappe.get_all("File", {"attached_to_doctype": self.doctype, "attached_to_name": self.name, "attached_to_field": fieldname}, pluck="name"):
            frappe.delete_doc("File", old, ignore_permissions=True, force=True)
        f = frappe.get_doc({"doctype": "File", "file_name": file_name, "attached_to_doctype": self.doctype, "attached_to_name": self.name, "attached_to_field": fieldname, "is_private": 1, "content": content})
        f.flags.ignore_permissions = True
        f.insert()
        return f

    @frappe.whitelist()
    def export_for_ebirforms(self):
        if self.docstatus != 0:
            frappe.throw(_("This return is filed. Download its eBIRForms file from the attachments."))
        if self._spec().output != "export":
            frappe.throw(_("The {0} has no eBIRForms import file. Use Preview to print it on the BIR's form, then key the same figures into eBIRForms or eFPS.").format(self.form))
        url = self._write_export()
        self.db_set({"export_file": self.export_file, "export_file_name": self.export_file_name})
        return url

    def _print_rows_for_pdf(self) -> list:
        s = self._spec()
        if s.output == "export":
            if self.docstatus == 1 and self.export_file:
                content = frappe.get_doc("File", {"file_url": self.export_file}).get_content()
                return parse_ebir_export(content.decode("utf-8") if isinstance(content, bytes) else content)
            rows, _n = self._rows()
            return parse_ebir_export(self._export_text(rows))
        rows, _n = self._rows()
        return rows

    def _render(self, clear: bool = False) -> str:
        s = self._spec()
        try:
            if s.output == "certificate":
                mod = engine.module(s)
                pdf = mod.print_all(self._data(), self._ctx(), None if clear else "DRAFT", None if clear else datetime.now(conf.MANILA))
            else:
                rows = self._print_rows_for_pdf()
                pdf = render_return(s.key, s.version, rows) if clear else render_return(s.key, s.version, rows, "DRAFT", datetime.now(conf.MANILA))
            name = f"{self.name} as filed.pdf" if clear else f"{self.name} DRAFT.pdf"
            field = "clear_copy" if clear else "preview_pdf"
        except (BirPdfError, ExportRefusal) as e:
            frappe.throw(_("The {0} could not be printed: {1}").format(self.form, str(e)))
        f = self._attach(name, pdf, field)
        if clear:
            self.db_set("clear_copy", f.file_url)
        else:
            self.db_set("preview_pdf", f.file_url)
        return f.file_url

    @frappe.whitelist()
    def preview(self):
        """The DRAFT preview; live, so limited per user to 40 a minute."""
        if self.docstatus == 1:
            return self.clear_copy
        if not take_preview_slot(frappe.session.user):
            frappe.throw(_(TOO_MANY_PREVIEWS))
        return self._render(clear=False)

    # ---- after filing: a change is an amendment, opened by a manager -----------------
    @frappe.whitelist()
    def open_amendment(self, reason: str):
        """A manager opens an amendment of a filed return: a new draft with the same data,
        linked back; the original stays filed and readable. With an approval chain on PH
        Tax Return (M5.3) the approved change request opens it; without one, the manager's
        role is the gate."""
        if self.docstatus != 1:
            frappe.throw(_("Only a filed return is amended."))
        if not (reason or "").strip():
            frappe.throw(_("Give the reason for the amendment."))
        approved = frappe.flags.get("ph_approval_amend") == self.name
        if not approved and not set(frappe.get_roles()) & set(MANAGER_ROLES):
            frappe.throw(_("Only an accounts manager may open an amendment of a filed return; ask for one with Request change."))
        if self.amended_by:
            frappe.throw(_("{0} already amends this return.").format(self.amended_by))
        # B82 (LDG-216): one amendment at a time; an open draft amendment blocks a second
        draft = frappe.db.get_value("PH Tax Return", {"amends": self.name, "docstatus": 0}, "name")
        if draft:
            frappe.throw(_("{0} already amends this return. Finish or delete that draft first.").format(draft))
        doc = frappe.copy_doc(self)
        doc.docstatus = 0
        doc.amends = self.name
        doc.is_amended = 1
        doc.status = "Draft"
        doc.confirmation = doc.override_reason = None
        doc.filed_on = doc.filed_reference = doc.filed_snapshot = None
        doc.export_file = doc.export_file_name = doc.preview_pdf = doc.clear_copy = None
        doc.notes = f"Amendment opened by {frappe.session.user}: {reason.strip()}"
        doc.insert()
        from ph_cas.audit.events import record

        record("tax_return.amendment_opened", "PH Tax Return", self.name, 1, {"amendment": doc.name, "reason": reason.strip()})
        # the original shows its amendment at once; it turns Amended when the amendment is filed
        frappe.db.set_value("PH Tax Return", self.name, "amended_by", doc.name, update_modified=False)
        return doc.name


    @frappe.whitelist()
    def form_spec(self):
        """What the inputs editor shows: the form's typed inputs and schedules (from the
        engine's INPUTS and SCHEDULES), the books keys with their values, and the data."""
        mod = engine.module(self._spec())
        data = self._data()
        src = data.get("_source") or {}
        books = src.get("books") or {}
        labels = {ln["key"]: ln["label"] for ln in (src.get("lines") or []) if ln.get("key")}
        for entry in (getattr(mod, "LABELS", []) or []):
            # (key, label) on the VAT return; (key, item, label[, books key]) on the income-tax returns
            key = entry[0]
            labels.setdefault(key, f"{key[1:].upper()} {entry[1]}" if len(entry) == 2 else f"{entry[1]} {entry[2]}")
        return {
            "built": mod is not None,
            "labels": labels,
            "inputs": list(getattr(mod, "INPUTS", []) or []),
            "schedules": {k: {"label": v[0], "columns": v[1], "keys": v[2] if len(v) > 2 else [f"c{i}" for i in range(len(v[1]))]} for k, v in (getattr(mod, "SCHEDULES", {}) or {}).items()},
            "books": books,
            "data": data,
            "money": self._spec().money,
        }

    @frappe.whitelist()
    def set_inputs(self, values):
        """Write typed values (a dict of key: value) into the draft's data and recompute."""
        if self.docstatus != 0:
            frappe.throw(_(SEALED))
        values = json.loads(values) if isinstance(values, str) else (values or {})
        data = self._data()
        for k, v in values.items():
            if k.startswith("_"):
                continue
            if v in (None, ""):
                data.pop(k, None)
            else:
                data[k] = v
        self.data = json.dumps(data, default=str)
        self.save()
        return {"status": self.status, "needs": self._needs(), "warnings": self.warnings}

    @frappe.whitelist()
    def generate_slsp(self):
        """2550Q only: write the RELIEF sales, purchases and importations files, one per
        month of the quarter (PH Alphalist File records), and tie their totals out
        against the return."""
        if self.form != "2550Q":
            frappe.throw(_("The SLSP goes with the 2550Q."))
        from ph_cas.dat.relief import generate

        from ph_cas.dat.relief import has_importations, months

        made = []
        for first, last in months(self.period_start, self.period_end):  # one file per month (RDO answer 11)
            for kind in ("S", "P", "I"):
                if kind == "I" and not has_importations(self.company, str(first), str(last)):
                    made.append(_("I {0}: no importations this month, so no file").format(f"{first:%m/%Y}"))
                    continue
                try:
                    made.append(generate(self.company, kind, str(first), str(last)))
                except Exception as e:
                    made.append(f"{kind} {first:%m/%Y}: not written ({e})")
        self.db_set("alphalist_file", next((m for m in made if not m.endswith(")")), None))
        tie = self._slsp_tie_out()
        return {"files": made, "tie_out": tie}

    @frappe.whitelist()
    def generate_sawt(self):
        """The SAWT (summary alphalist of withholding taxes) that goes with a return
        claiming credits from the 2307s received: 2550Q (VAT), 2551Q (percentage tax),
        1701Q, 1702Q, 1701 and 1702-RT (income tax). Written from the PH 2307 Received
        of the period."""
        from ph_cas.dat.sawt import KIND_BY_FORM, _code, generate

        if _code(self.form) not in KIND_BY_FORM:
            frappe.throw(_("The {0} has no SAWT.").format(self.form))
        self.check_permission("read")
        return generate(self.company, self.form, str(self.period_start), str(self.period_end))

    @frappe.whitelist()
    def generate_attachment(self):
        """The form's attachment file (the QAP of a 1601-EQ, the annual alphalist of a 1604-E),
        written by the engine as a PH Alphalist File and linked to the return."""
        mod = engine.module(self._spec())
        if mod is None or not hasattr(mod, "write_attachment"):
            frappe.throw(_("The {0} has no attachment file.").format(self.form))
        return mod.write_attachment(self)

    def _slsp_tie_out(self) -> list[str]:
        mod = engine.module(self._spec())
        if mod is None or not hasattr(mod, "slsp_tie_out"):
            return []
        return mod.slsp_tie_out(self._data(), self._ctx())


def take_preview_slot(user: str, now: float | None = None) -> bool:
    """Count one preview for the user; False when the limit is reached (nothing is counted then)."""
    import time

    now = now or time.time()
    key = f"ph_preview:{user}"
    cache = frappe.cache()
    hits = [t for t in (cache.get_value(key) or []) if now - t < 60]
    if len(hits) >= PREVIEWS_PER_MINUTE:
        cache.set_value(key, hits, expires_in_sec=60)
        return False
    hits.append(now)
    cache.set_value(key, hits, expires_in_sec=60)
    return True


@frappe.whitelist()
def attach_confirmation(tax_return: str, file_url: str):
    """Read an uploaded confirmation (.eml, .pdf or .txt), make the PH BIR Confirmation
    record, check it against the return, and link it."""
    doc = frappe.get_doc("PH Tax Return", tax_return)
    doc.check_permission("write")
    f = frappe.get_doc("File", {"file_url": file_url})
    content = f.get_content()
    if isinstance(content, str):
        content = content.encode("utf-8")
    facts = conf.read_confirmation(content, f.file_name)
    dup = frappe.db.get_value("PH BIR Confirmation", {"sha256": facts.sha256}, ["name", "tax_return"], as_dict=True)
    if dup and dup.tax_return and dup.tax_return != tax_return:
        frappe.throw(_("This confirmation is already attached to {0}.").format(dup.tax_return))
    comp = doc._company()
    p = doc._period()
    errors = conf.check_against(facts, doc._spec().key, comp.get("tax_id") or "", comp.get("ph_branch_code") or "0", p.kind, p.year, p.n)
    c = frappe.get_doc(
        {
            "doctype": "PH BIR Confirmation",
            "form": doc.form,
            "tin": comp.get("tax_id"),
            "period_key": doc.period_key,
            "kind": "BIR e-mail",
            "reference": facts.file_name,
            "received_at": facts.received_at.replace(tzinfo=None) if facts.received_at else None,
            "file": file_url,
            "sha256": facts.sha256,
            "attached_by": frappe.session.user,
        }
    )
    c.insert()
    f.db_set({"attached_to_doctype": "PH BIR Confirmation", "attached_to_name": c.name, "attached_to_field": "file"})
    doc.db_set("confirmation", c.name)
    return {"confirmation": c.name, "errors": errors, "received_at": c.received_at, "file_name": facts.file_name}


@frappe.whitelist()
def new_return(company: str, form: str, period_key: str):
    """Open (or make) the return of a company for a form and period."""
    abbr = frappe.get_cached_value("Company", company, "abbr")
    name = f"{form}-{period_key.strip().upper()}-{abbr}"
    if frappe.db.exists("PH Tax Return", name):
        return name
    doc = frappe.get_doc({"doctype": "PH Tax Return", "company": company, "form": form, "period_key": period_key})
    doc.insert()
    return doc.name


def sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
