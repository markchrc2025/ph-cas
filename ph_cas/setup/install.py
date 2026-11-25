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
    from ph_cas.controls.security import force_system_settings

    force_system_settings()  # B05
    from ph_cas.controls import serial

    serial.setup()  # B06
    from ph_cas.audit import header

    header.setup()  # B08
    from ph_cas.setup import master_data

    master_data.setup()  # B09
    from ph_cas.tax import rules

    rules.seed()  # B11
    rules.apply_acceptance()  # LDG-47: the owner accepted the rules
    from ph_cas.tax import vat

    vat.setup()  # B12
    from ph_cas.tax import customer_withholding

    customer_withholding.setup()  # B13
    from ph_cas.tax import purchase

    purchase.setup()  # B14
    from ph_cas.tax import reverse_charge

    reverse_charge.setup()  # B15
    from ph_cas.tax import ovc

    ovc.setup()  # B16
    from ph_cas.tax import calendar

    calendar.setup()  # B17
    from ph_cas.tax import income_tax

    income_tax.setup()  # B18
    from ph_cas.invoicing import setup as invoicing_setup

    invoicing_setup.setup()  # B20
    from ph_cas.invoicing import rules as invoicing_rules

    invoicing_rules.setup()  # B21
    from ph_cas.tax import sc_pwd

    sc_pwd.setup()  # B22
    from ph_cas.dat import relief

    relief.setup()  # B29
    from ph_cas.hosting import tiers

    tiers.setup()  # B32
    from ph_cas.hosting import demo_access

    demo_access.setup()  # B33
    from ph_cas.setup import onboarding

    onboarding.setup()  # B34
    from ph_cas import branding

    branding.apply()  # B38
    from ph_cas.setup import roles

    roles.setup()  # B69
    from ph_cas import golive

    golive.setup()  # B71
    from ph_cas.invoicing import paid_now

    paid_now.setup()  # B76
    from ph_cas.setup import ui

    ui.setup()  # B82
    from ph_cas.cloud import sso

    sso.setup()  # B88
    frappe.db.commit()
