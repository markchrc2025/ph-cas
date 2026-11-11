"""B38: product branding. Everything a user can see says Sentire Ledger (or whatever
PRODUCT_NAME is), never Frappe or ERPNext: logo, favicon, splash, login page, desk
title, app rail, help menu, website footer, email sender, email header and footer,
About dialog, first page after sign-in.

Licence notices are not branding: the About dialog keeps a licences section naming the
open-source components (GPL v3 for ERPNext and ph_cas, MIT for Frappe) and the source
keeps every copyright header. Trademarks are removed from the interface only.

`apply(product, provider)` is idempotent and runs on every container start from
`ph_cas.deploy_config` (primary site and every client site). `boot_session` patches the
desk boot payload, which is where the app rail reads its icon and title.
"""

from __future__ import annotations

import os

import frappe
from frappe.utils import get_url

ASSETS = {
    "logo": "/assets/ph_cas/images/logo.svg",
    "wordmark": "/assets/ph_cas/images/wordmark.svg",
    "wordmark_png": "/assets/ph_cas/images/wordmark.png",
    "favicon": "/assets/ph_cas/images/favicon.ico",
    "icon_180": "/assets/ph_cas/images/icon-180.png",
    "icon_512": "/assets/ph_cas/images/icon-512.png",
}
DEFAULT_PRODUCT = "Sentire Ledger"
DEFAULT_PROVIDER = "MCRC Tax and Accounting Services"
HIDDEN_HELP_ITEMS = ("Frappe Support", "Documentation", "User Forum", "Report an Issue", "Keyboard Shortcuts")
WORKSPACE = "Sentire Ledger"


def product_name() -> str:
    name = None
    if frappe.db.exists("DocType", "PH CAS Settings"):
        name = frappe.db.get_single_value("PH CAS Settings", "product_name")
    return (name or os.environ.get("PRODUCT_NAME") or DEFAULT_PRODUCT).strip()


def provider_name() -> str:
    name = None
    if frappe.db.exists("DocType", "PH CAS Settings"):
        name = frappe.db.get_single_value("PH CAS Settings", "provider_name")
    return (name or os.environ.get("PROVIDER_NAME") or DEFAULT_PROVIDER).strip()


def support_email() -> str:
    return (os.environ.get("SUPPORT_EMAIL") or os.environ.get("ADMIN_EMAIL") or "").strip()


def apply(product: str | None = None, provider: str | None = None) -> str:
    """Write the product identity into every setting Frappe reads it from."""
    product = (product or product_name()).strip()
    provider = (provider or provider_name()).strip()
    _ph_cas_settings(product, provider)
    _website_settings(product, provider)
    _navbar_settings(product)
    _system_settings(product, provider)
    _email_accounts(product)
    _default_workspace()
    _dock_first(product)
    _scrub_framework_names(product)
    frappe.clear_cache()
    return f"branding: {product} by {provider}"


def _ph_cas_settings(product: str, provider: str):
    """PH CAS Settings is the single source the BIR header and every other reader use."""
    if not frappe.db.exists("DocType", "PH CAS Settings"):
        return
    s = frappe.get_single("PH CAS Settings")
    changed = False
    if s.get("product_name") != product:
        s.product_name = product
        changed = True
    if s.get("provider_name") != provider:
        s.provider_name = provider
        changed = True
    if changed:
        s.flags.ignore_permissions = True
        s.save()


def _website_settings(product: str, provider: str):
    ws = frappe.get_single("Website Settings")
    values = {
        "app_name": product,
        "app_logo": ASSETS["logo"],
        "favicon": ASSETS["favicon"],
        "splash_image": ASSETS["logo"],
        "brand_html": f'<img src="{ASSETS["wordmark"]}" alt="{product}" style="height:28px">',
        "footer_powered": f"{product} is operated by {provider}.",
        "copyright": provider,
        "hide_footer_signup": 1,
        "disable_signup": 1,
    }
    changed = False
    for k, v in values.items():
        if ws.meta.has_field(k) and ws.get(k) != v:
            ws.set(k, v)
            changed = True
    if changed:
        ws.flags.ignore_permissions = True
        ws.flags.ignore_mandatory = True
        ws.save()


def _navbar_settings(product: str):
    nb = frappe.get_single("Navbar Settings")
    changed = False
    if nb.get("app_logo") != ASSETS["logo"]:
        nb.app_logo = ASSETS["logo"]
        changed = True
    mail = support_email()
    wanted_label = f"Contact {provider_name()}"
    seen_contact = False
    for row in nb.get("help_dropdown") or []:
        if row.item_label in HIDDEN_HELP_ITEMS and not row.hidden:
            row.hidden = 1
            changed = True
        if row.item_label == wanted_label:
            seen_contact = True
            if mail and row.route != f"mailto:{mail}":
                row.route = f"mailto:{mail}"
                changed = True
    if mail and not seen_contact:
        nb.append("help_dropdown", {"item_label": wanted_label, "item_type": "Route", "route": f"mailto:{mail}", "is_standard": 0})
        changed = True
    if changed:
        nb.flags.ignore_permissions = True
        nb.save()


def _system_settings(product: str, provider: str):
    ss = frappe.get_single("System Settings")
    values = {
        "app_name": product,
        "disable_standard_email_footer": 1,
        "email_footer_address": f"{product} is operated by {provider}.",
    }
    for k, v in values.items():
        if ss.meta.has_field(k) and ss.get(k) != v:
            frappe.db.set_single_value("System Settings", k, v)
    # frappe.db.get_default reads __default, which System Settings also writes on save
    frappe.db.set_default("disable_standard_email_footer", 1)
    frappe.db.set_default("email_footer_address", values["email_footer_address"])


def _email_accounts(product: str):
    """Every outgoing account sends as the product: sender name, header wordmark, no
    'Sent via' footer. The account created by deploy_config is renamed to the product so
    the From header reads '<product> <noreply@...>'."""
    logo = get_url(ASSETS["wordmark_png"])
    for name in frappe.get_all("Email Account", filters={"enable_outgoing": 1}, pluck="name"):
        doc = frappe.get_doc("Email Account", name)
        changed = False
        if doc.meta.has_field("brand_logo") and doc.get("brand_logo") != logo:
            doc.brand_logo = logo
            changed = True
        if doc.get("footer"):
            doc.footer = ""
            changed = True
        if not doc.get("always_use_account_name_as_sender_name"):
            doc.always_use_account_name_as_sender_name = 1
            changed = True
        if changed:
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.db_update()
            for child in doc.get_all_children():
                child.db_update()
        if doc.get("default_outgoing") and name != product and not frappe.db.exists("Email Account", product):
            from frappe.model.rename_doc import rename_doc

            rename_doc("Email Account", name, product, force=True, ignore_permissions=True, show_alert=False)
            frappe.db.set_value("Email Account", product, "email_account_name", product, update_modified=False)


def _default_workspace():
    if not frappe.db.exists("Workspace", WORKSPACE):
        return
    frappe.db.sql(
        """update `tabUser` set default_workspace=%s
           where enabled=1 and user_type='System User' and ifnull(default_workspace,'')=''""",
        (WORKSPACE,),
    )


SIDEBAR = "Sentire Ledger"
FRAMEWORK_NAMES = ("ERPNext", "Frappe")
# records the framework ships whose user-facing text names the framework
SCRUB = {
    "Module Onboarding": ("title", "subtitle", "success_message"),
    "Onboarding Step": ("title", "description", "intro_video_url"),
    "Workspace": ("title",),
}


def _dock_first(product: str):
    """The Sentire Ledger shell (ph_cas/ph_cas/sidebar) is the first rail entry of the app the
    users see, so the desk opens on it. Written as the site layer of the dock. The desk keeps
    only the entries a layer names (keep_unnamed is False in resolve_app_dock), so the layer
    lists the app's own entries after ours, in their shipped order, or they would vanish."""
    if not frappe.db.exists("Sidebar", SIDEBAR):
        return
    try:
        from frappe.desk.doctype.dock.dock import get_app_base, get_site_dock_layer, save_site_dock
    except ImportError:
        return
    user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        base = get_app_base("erpnext") or []
        try:
            current = get_site_dock_layer("erpnext") or []
        except Exception:
            current = []
        ours = {"link_type": "Sidebar", "link_to": SIDEBAR, "title": product, "icon": "calculator-soft"}
        key = lambda r: (r.get("link_type") or "", r.get("link_to") or "", r.get("url") or "")  # noqa: E731
        rest = [
            {k: r.get(k) for k in ("link_type", "link_to", "url") if r.get(k)}
            for r in base
            if key(r) != key(ours)
        ]
        wanted = [key(ours), *[key(r) for r in rest]]
        if [key(r) for r in current] == wanted and (current[0].get("title") or "") == product:
            return
        save_site_dock("erpnext", [ours, *rest])
    except Exception:
        frappe.log_error("ph_cas branding: could not place the shell first on the dock")
    finally:
        frappe.set_user(user)


def _scrub_framework_names(product: str):
    """Text the framework ships that names itself ("Get to know ERPNext") says the product."""
    for doctype, fields in SCRUB.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        meta = frappe.get_meta(doctype)
        fields = [f for f in fields if meta.has_field(f)]
        if not fields:
            continue
        for row in frappe.get_all(doctype, fields=["name", *fields]):
            for f in fields:
                old = row.get(f) or ""
                if not isinstance(old, str):
                    continue
                new = old
                for fw in FRAMEWORK_NAMES:
                    if fw in new and "http" not in new:
                        new = new.replace(fw, product)
                if new != old:
                    frappe.db.set_value(doctype, row.name, f, new, update_modified=False)


def set_user_workspace(doc, method=None):
    """User.validate: a new system user lands on the product workspace."""
    if not doc.get("default_workspace") and frappe.db.exists("Workspace", WORKSPACE):
        doc.default_workspace = WORKSPACE


def boot_session(bootinfo):
    """Desk boot: the app rail and the browser tab read these."""
    product = product_name()
    bootinfo.app_logo_url = ASSETS["logo"]
    if bootinfo.get("sysdefaults"):
        bootinfo.sysdefaults["app_name"] = product
    for app in bootinfo.get("app_data") or []:
        if app.get("app_name") in ("erpnext", "frappe", "ph_cas"):
            app["app_logo_url"] = ASSETS["logo"]
            if app.get("app_name") in ("erpnext", "ph_cas"):
                app["app_title"] = product
            elif app.get("app_name") == "frappe":
                app["app_title"] = "System tools"
    bootinfo.ph_cas_branding = {
        "product": product,
        "provider": provider_name(),
        "support_email": support_email(),
        "version": frappe.get_attr("ph_cas.__version__"),
        "wordmark": ASSETS["wordmark"],
        "licences": licence_text(),
        "home": {"workspace_path": "/desk/" + frappe.scrub(WORKSPACE).replace("_", "-"), "page": "sentire-home"}
        if frappe.db.exists("Page", "sentire-home")
        else None,
    }


def licence_text() -> str:
    try:
        erp = frappe.get_attr("erpnext.__version__")
    except Exception:
        erp = "?"
    return (
        f"Built on open-source software. ERPNext {erp} (GNU GPL v3) and Frappe Framework "
        f"{frappe.__version__} (MIT). The ph_cas application is licensed under the GNU GPL v3. "
        "Copyright notices are kept in the source code as the licences require."
    )


def email_wrapper(title: str, body_html: str) -> dict:
    """kwargs for frappe.sendmail so the message carries the wordmark header, the product
    footer and no framework footer."""
    return {"header": [title, "blue"], "with_container": True, "message": body_html}


def website_context(context):
    """Web pages (login, /demo, /pilot, error pages) outside the desk."""
    product = product_name()
    context["favicon"] = ASSETS["favicon"]
    context["splash_image"] = ASSETS["logo"]
    context["app_name"] = product
    context["title"] = context.get("title") or product
    return context
