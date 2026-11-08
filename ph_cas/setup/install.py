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
    from ph_cas.controls.posted_fields import install_property_setters

    install_property_setters()  # B03
    from ph_cas.controls import dates

    dates.setup()  # B04
    frappe.db.commit()
