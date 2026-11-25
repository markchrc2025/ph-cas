"""B88 (CLD-16, task 4.2): sign in to Ledger with the Sentire Account (OpenID Connect, code flow with PKCE).

/login redirects here when the site is on Sentire Cloud. /login?local=1 keeps the local form for the
site Administrator (operations only).
"""

import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import frappe
import jwt
import requests
from frappe import _

from ph_cas.cloud import config

ROLE_SET_FOR = {"OWNER": "Owner", "ADMIN": "Accounting Manager", "BILLING": "Staff", "MEMBER": "Staff"}
SUB_FIELD = "sentire_sub"
_JWKS_KEY = "ph_cas:cloud:jwks"


def setup():
    """Custom field linking a Ledger user to the Sentire Account (the OIDC subject). Idempotent."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(
        {"User": [{"fieldname": SUB_FIELD, "label": "Sentire Account ID", "fieldtype": "Data", "read_only": 1, "insert_after": "username", "unique": 1, "no_copy": 1}]},
        ignore_validate=True,
        update=True,
    )


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _redirect(url: str):
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = url


def _callback_url() -> str:
    return config.site_url() + "/api/method/ph_cas.cloud.sso.callback"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def login(redirect_to: str = "/app", **kwargs):
    redirect_to = frappe.form_dict.get("redirect-to") or redirect_to
    if not config.enabled():
        return _redirect("/login?local=1" + (f"&redirect-to={frappe.utils.quote(redirect_to)}" if redirect_to != "/app" else ""))
    if frappe.session.user != "Guest":
        return _redirect(redirect_to if redirect_to.startswith("/") else "/app")
    verifier = _b64(secrets.token_bytes(32))
    state = _b64(secrets.token_bytes(16))
    nonce = _b64(secrets.token_bytes(16))
    if not redirect_to.startswith("/") or redirect_to.startswith("//"):
        redirect_to = "/app"
    frappe.cache().set_value(f"ph_cas:cloud:state:{state}", {"verifier": verifier, "nonce": nonce, "redirect_to": redirect_to}, expires_in_sec=600)
    q = {
        "client_id": config.client_id(),
        "response_type": "code",
        "scope": "openid email profile org entitlements",
        "redirect_uri": _callback_url(),
        "code_challenge": _b64(hashlib.sha256(verifier.encode()).digest()),
        "code_challenge_method": "S256",
        "state": state,
        "nonce": nonce,
    }
    return _redirect(f"{config.issuer()}/oidc/auth?{urlencode(q)}")


def _jwks(force: bool = False) -> dict:
    cached = None if force else frappe.cache().get_value(_JWKS_KEY)
    if cached:
        return cached
    keys = requests.get(f"{config.issuer()}/oidc/jwks", timeout=10).json()
    frappe.cache().set_value(_JWKS_KEY, keys, expires_in_sec=3600)
    return keys


def verify_id_token(token: str, nonce: str | None) -> dict:
    kid = jwt.get_unverified_header(token).get("kid")
    keys = _jwks()
    match = [k for k in keys.get("keys", []) if k.get("kid") == kid]
    if not match:  # the provider rotated its key since we cached
        match = [k for k in _jwks(force=True).get("keys", []) if k.get("kid") == kid]
    if not match:
        raise frappe.AuthenticationError(_("Unknown signing key"))
    key = jwt.algorithms.ECAlgorithm.from_jwk(match[0])
    claims = jwt.decode(token, key=key, algorithms=["ES256"], audience=config.client_id(), issuer=config.issuer(), leeway=60)
    if nonce and claims.get("nonce") != nonce:
        raise frappe.AuthenticationError(_("Sign-in could not be verified"))
    return claims


def ensure_user(claims: dict) -> str:
    """Find the Ledger user for this Sentire Account (by subject, then email) or create it with a default role set."""
    sub, email = claims["sub"], (claims.get("email") or "").lower()
    name = frappe.db.get_value("User", {SUB_FIELD: sub}) or frappe.db.get_value("User", {"email": email})
    if name:
        user = frappe.get_doc("User", name)
        changed = False
        if not user.get(SUB_FIELD):
            user.set(SUB_FIELD, sub)
            changed = True
        if not user.enabled:
            user.enabled = 1
            changed = True
        if changed:
            user.flags.ignore_permissions = True
            user.save()
        return user.name
    role_set = ROLE_SET_FOR.get(claims.get("org_role") or "MEMBER", "Staff")
    parts = (claims.get("name") or email).split(" ", 1)
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": parts[0],
            "last_name": parts[1] if len(parts) > 1 else "",
            "user_type": "System User",
            "send_welcome_email": 0,
            SUB_FIELD: sub,
            "role_profiles": [{"role_profile": role_set}],
        }
    )
    user.flags.ignore_permissions = True
    user.flags.no_welcome_mail = True
    user.insert()
    return user.name


@frappe.whitelist(allow_guest=True, methods=["GET"])
def callback(code: str | None = None, state: str | None = None, error: str | None = None, **_):
    if error or not code or not state:
        return _redirect("/login?local=1&error=sso")
    saved = frappe.cache().get_value(f"ph_cas:cloud:state:{state}")
    frappe.cache().delete_value(f"ph_cas:cloud:state:{state}")
    if not saved:
        return _redirect("/api/method/ph_cas.cloud.sso.login")  # expired: start again
    c = config.conf()
    r = requests.post(
        f"{config.issuer()}/oidc/token",
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": _callback_url(), "code_verifier": saved["verifier"]},
        auth=(config.client_id(), c["client_secret"]),
        timeout=15,
    )
    if r.status_code != 200:
        frappe.log_error("Sentire sign-in: token exchange failed", r.text[:500])
        return _redirect("/login?local=1&error=sso")
    tokens = r.json()
    claims = verify_id_token(tokens["id_token"], saved["nonce"])
    if claims.get("org_id") != config.org_id() or not claims.get("app_access"):
        frappe.throw(_("Your Sentire Account is not a member of this organization, or has no access to Sentire Ledger."), frappe.PermissionError)
    ent = claims.get("ent") or {}
    if ent.get("state") == "OFF":
        frappe.throw(_("This organization's Sentire Ledger subscription is not active."), frappe.PermissionError)
    user = ensure_user(claims)
    frappe.local.login_manager.login_as(user)
    frappe.db.commit()
    return _redirect(saved.get("redirect_to") or "/app")


# hooks.website_redirects: bare /login (or /login?redirect-to=...) goes to Sentire sign-in; /login?local=1 keeps the
# local form for the site Administrator. On a site without Sentire Cloud, login() sends people back to the local form.
LOGIN_REDIRECT = {"source": r"login(?!\?(.*&)?local=1)(\?.*)?", "target": "/api/method/ph_cas.cloud.sso.login", "match_with_query_string": True, "forward_query_parameters": True, "redirect_http_status": 302}


def end_sessions(sub: str):
    """Sign a Sentire Account out of this site (member removed, or signed out of Sentire Cloud)."""
    from frappe.sessions import clear_sessions

    name = frappe.db.get_value("User", {SUB_FIELD: sub})
    if name:
        clear_sessions(user=name, force=True)
    return name


def now() -> int:
    return int(time.time())
