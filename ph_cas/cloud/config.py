import frappe


def conf() -> dict:
    return frappe.conf.get("sentire_cloud") or {}


def enabled() -> bool:
    c = conf()
    return bool(c.get("issuer") and c.get("org_id") and c.get("client_secret"))


def issuer() -> str:
    return (conf().get("issuer") or "").rstrip("/")


def org_id() -> str:
    return conf().get("org_id") or ""


def client_id() -> str:
    return conf().get("client_id") or "sentire-ledger"


def site_url() -> str:
    return frappe.utils.get_url().rstrip("/")


def upgrade_url(feature: str, return_path: str = "/app") -> str:
    from urllib.parse import urlencode

    return f"{issuer()}/upgrade?" + urlencode({"org": org_id(), "feature": feature, "app": "ledger", "return": site_url() + return_path})
