"""Install and migrate hooks. Later bundles register their custom fields,
property setters and settings here so that a fresh install and a migrated
site end up identical."""

import frappe


def after_install():
    setup_all()


def after_migrate():
    setup_all()


def setup_all():
    """Idempotent. Each bundle appends one call here."""
    from ph_cas.controls.locks import force_accounts_settings

    force_accounts_settings()  # B02
    frappe.db.commit()
