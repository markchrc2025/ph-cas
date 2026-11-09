"""/demo_login?token=...: one-click sign-in for open-demo users (B33)."""

import frappe
from frappe import _

no_cache = 1


def get_context(context):
    from ph_cas.hosting.demo_access import consume_token, is_demo_site

    token = frappe.form_dict.get("token")
    context.no_header = 1
    if not is_demo_site() or not token:
        context.error = _("This link is not valid.")
        return context
    user = consume_token(token)
    if not user:
        context.error = _("This demo link has expired. Request a new one from the demo page.")
        return context
    frappe.local.login_manager.login_as(user)
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/app"
    raise frappe.Redirect
