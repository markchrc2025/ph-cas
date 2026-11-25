"""B32: subscription tiers and their limits.

The tier of a site is data in PH CAS Settings, set by the hosting provider with
`ledger-site set-tier` (deploy/ledger-site.sh) or `set_tier()` below. Limits are
enforced where the objects are created: users, companies, branches, and the number
of invoices submitted in a calendar month. A limit of 0 means unlimited. The
Internal tier (MCRC's own and demo sites) has no limits.

Provider staff (User.ph_provider_staff) are not counted against the user limit, so
MCRC's read-only bookkeeper seat never consumes a client's seat.
"""

import frappe
from frappe import _
from frappe.utils import get_first_day, getdate, today

TIERS = {
    "Internal": {"max_users": 0, "max_companies": 0, "max_branches": 0, "monthly_invoice_limit": 0},
    "Solo": {"max_users": 1, "max_companies": 1, "max_branches": 1, "monthly_invoice_limit": 150},
    "Team": {"max_users": 5, "max_companies": 1, "max_branches": 3, "monthly_invoice_limit": 1000},
    "Business": {"max_users": 15, "max_companies": 1, "max_branches": 0, "monthly_invoice_limit": 0},
    "Enterprise": {"max_users": 0, "max_companies": 0, "max_branches": 0, "monthly_invoice_limit": 0},
}

STAFF_FIELD = "ph_provider_staff"
EXEMPT_USERS = ("Administrator", "Guest")


class PHTierError(frappe.ValidationError):
    pass


def setup():
    """Called from setup_all. Idempotent."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(
        {
            "User": [
                {
                    "fieldname": STAFF_FIELD,
                    "label": "Provider staff (not counted against the subscription)",
                    "fieldtype": "Check",
                    "insert_after": "enabled",
                    "default": "0",
                    "description": "Tick for MCRC bookkeepers and support staff. Only System Managers may change it.",
                }
            ]
        },
        ignore_validate=True,
        update=True,
    )


def set_tier(tier: str, subscription_until: str | None = None, pilot_until: str | None = None, **overrides) -> dict:
    """Write a tier and its limits to PH CAS Settings. Overrides replace single limits (add-ons)."""
    if tier not in TIERS:
        frappe.throw(_("Unknown tier {0}. Known: {1}").format(tier, ", ".join(TIERS)), PHTierError)
    limits = dict(TIERS[tier])
    for k, v in overrides.items():
        if k in limits and v is not None:
            limits[k] = int(v)
    s = frappe.get_single("PH CAS Settings")
    s.subscription_tier = tier
    for k, v in limits.items():
        setattr(s, k, v)
    if subscription_until is not None:
        s.subscription_until = subscription_until or None
    if pilot_until is not None:
        s.pilot_until = pilot_until or None
    s.flags.ignore_permissions = True
    s.save()
    frappe.db.commit()
    frappe.clear_cache()
    return {"tier": tier, **limits}


def limits() -> dict:
    s = frappe.get_cached_doc("PH CAS Settings")
    tier = s.get("subscription_tier") or "Internal"
    return {
        "tier": tier,
        "max_users": int(s.get("max_users") or 0),
        "max_companies": int(s.get("max_companies") or 0),
        "max_branches": int(s.get("max_branches") or 0),
        "monthly_invoice_limit": int(s.get("monthly_invoice_limit") or 0),
        "subscription_until": s.get("subscription_until"),
        "pilot_until": s.get("pilot_until"),
    }


def is_provider(user: str | None = None) -> bool:
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return bool(frappe.db.get_value("User", user, STAFF_FIELD)) if frappe.db.has_column("User", STAFF_FIELD) else False


def user_query(user=None, doctype=None):
    """B82 (LDG-170): the client's own people only. The Administrator and the provider's
    staff see every user; everyone else's User list leaves out system and provider accounts."""
    if is_provider(user):
        return ""
    return "(`tabUser`.name not in ('Administrator', 'Guest') and ifnull(`tabUser`.{0}, 0) = 0)".format(STAFF_FIELD)


def _counted_users(exclude: str | None = None) -> int:
    filters = {"enabled": 1, "user_type": "System User", "name": ["not in", EXEMPT_USERS], STAFF_FIELD: 0}
    if exclude:
        filters["name"] = ["not in", (*EXEMPT_USERS, exclude)]
    return frappe.db.count("User", filters)


def usage() -> dict:
    """What the site uses against its limits (for the usage report and the provider)."""
    start = get_first_day(today())
    return {
        **limits(),
        "users": _counted_users(),
        "companies": frappe.db.count("Company"),
        "branches": frappe.db.count("Branch"),
        "invoices_this_month": frappe.db.count(
            "Sales Invoice", {"docstatus": 1, "posting_date": [">=", start], "is_return": 0}
        ),
        "modules_on": _modules_on(),
    }


def _modules_on() -> list[str]:
    from ph_cas.modules.api import modules_on

    return modules_on()


FEATURE_OF = {"users": "users", "company": "companies", "branches": "branches", "invoices per month": "invoices_per_month"}


def _refuse(what: str, limit: int, tier: str):
    from ph_cas.cloud import config

    if config.enabled():
        # B88: on Sentire Cloud the limit comes from the plan; the paywall offers the upgrade (HTTP 402).
        from ph_cas.cloud.entitlements import raise_payment_required

        raise_payment_required(
            FEATURE_OF.get(str(what), "users"),
            _("Your {0} plan allows {1} {2}.").format(tier, limit, what),
        )
    frappe.throw(
        _("Your {0} subscription allows {1} {2}. Ask your provider to add more or move to a higher tier.").format(
            tier, limit, what
        ),
        PHTierError,
        title=_("Subscription limit"),
    )


def validate_user(doc, method=None):
    """doc_events['User'].validate"""
    before = None if doc.is_new() else doc.get_doc_before_save()
    changed = bool(doc.get(STAFF_FIELD)) != bool(before.get(STAFF_FIELD) if before else 0)
    if changed and not (frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_test) and not is_provider():
        # B82 (LDG-170): the provider's box is the provider's; a client's Owner cannot tick or clear it
        frappe.throw(_("Only the provider marks a user as provider staff."), frappe.PermissionError)
    if frappe.flags.in_install or frappe.flags.in_migrate:
        return
    lim = limits()
    if not lim["max_users"]:
        return
    if not doc.enabled or doc.user_type != "System User" or doc.name in EXEMPT_USERS or doc.get(STAFF_FIELD):
        return
    before = None if doc.is_new() else doc.get_doc_before_save()
    was_counted = bool(before and before.enabled and before.user_type == "System User" and not before.get(STAFF_FIELD))
    if was_counted:
        return  # already a seat; editing it does not add one
    if _counted_users(exclude=doc.name) + 1 > lim["max_users"]:
        _refuse(_("users"), lim["max_users"], lim["tier"])


def validate_company(doc, method=None):
    """doc_events['Company'].before_insert"""
    lim = limits()
    if lim["max_companies"] and frappe.db.count("Company") + 1 > lim["max_companies"]:
        _refuse(_("company"), lim["max_companies"], lim["tier"])


def validate_branch(doc, method=None):
    """doc_events['Branch'].before_insert"""
    lim = limits()
    if lim["max_branches"] and frappe.db.count("Branch") + 1 > lim["max_branches"]:
        _refuse(_("branches"), lim["max_branches"], lim["tier"])


def validate_invoice_volume(doc, method=None):
    """doc_events['Sales Invoice'].before_submit"""
    lim = limits()
    if not lim["monthly_invoice_limit"] or doc.get("is_return"):
        return
    start = get_first_day(getdate(doc.posting_date))
    end = frappe.utils.get_last_day(start)
    n = frappe.db.count(
        "Sales Invoice",
        {"docstatus": 1, "posting_date": ["between", [start, end]], "is_return": 0, "name": ["!=", doc.name]},
    )
    if n + 1 > lim["monthly_invoice_limit"]:
        _refuse(_("invoices per month"), lim["monthly_invoice_limit"], lim["tier"])


def check_subscription_status() -> dict:
    """For monitoring: expired subscriptions and pilots past their end."""
    lim = limits()
    out = {"tier": lim["tier"], "expired": False, "pilot_ended": False}
    if lim["subscription_until"] and getdate(lim["subscription_until"]) < getdate(today()):
        out["expired"] = True
    if lim["pilot_until"] and getdate(lim["pilot_until"]) < getdate(today()):
        out["pilot_ended"] = True
    return out


TIER_NOTES = {
    "Internal": "The provider's own site: no limits.",
    "Solo": "One user, one company, up to 150 invoices a month.",
    "Team": "Up to 5 users, one company with up to 3 branches, up to 1,000 invoices a month.",
    "Business": "Up to 15 users, one company, any number of branches and invoices.",
    "Enterprise": "No limits on users, companies, branches or invoices.",
}


@frappe.whitelist()
def my_plan() -> dict:
    """B75 (after ECOUNT's subscription page): Help > Your plan. The tier, what it allows, what the
    site uses now, and the dates; the provider's contact for a change of plan."""
    from ph_cas.branding import provider_name, support_email

    u = usage()
    rows = []
    for key, label, used in (("max_users", _("Users"), u["users"]), ("max_companies", _("Companies"), u["companies"]),
                             ("max_branches", _("Branches besides the head office"), u["branches"]), ("monthly_invoice_limit", _("Invoices this month"), u["invoices_this_month"])):
        lim = u[key]
        rows.append({"label": label, "used": used, "limit": lim or None, "near": bool(lim and used >= 0.8 * lim)})
    status = check_subscription_status()
    return {"tier": u["tier"], "note": _(TIER_NOTES.get(u["tier"], "")), "rows": rows, "modules_on": u.get("modules_on") or [],
            "subscription_until": u.get("subscription_until"), "pilot_until": u.get("pilot_until"),
            "expired": status["expired"], "pilot_ended": status["pilot_ended"],
            "provider": provider_name(), "support_email": support_email()}
