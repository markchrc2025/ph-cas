"""B03: series counters of accounting documents cannot be reset or moved."""

import frappe
from frappe import _
from frappe.core.doctype.document_naming_settings.document_naming_settings import (
    DocumentNamingSettings,
)

from ph_cas.controls.locks import POSTED_VOUCHER_TYPES, PHLockError, locks_active


def _accounting_prefixes() -> set[str]:
    prefixes = set()
    for doctype in POSTED_VOUCHER_TYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        meta = frappe.get_meta(doctype)
        df = meta.get_field("naming_series")
        if df and df.options:
            for opt in str(df.options).split("\n"):
                opt = opt.strip()
                if opt:
                    prefixes.add(opt)
    return prefixes


class PHDocumentNamingSettings(DocumentNamingSettings):
    @frappe.whitelist()
    def update_series_start(self):
        if locks_active():
            transaction_type = self.get("transaction_type")
            prefix = self.get("prefix") or ""
            if (
                transaction_type in POSTED_VOUCHER_TYPES
                or not transaction_type
                or prefix in _accounting_prefixes()
            ):
                frappe.throw(
                    _("The series counter of an accounting document cannot be changed in this system."),
                    PHLockError,
                )
        return super().update_series_start()
