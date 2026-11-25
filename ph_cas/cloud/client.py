"""Calls from Ledger to Sentire Cloud with Ledger's machine token (OAuth client credentials)."""

import base64
import time

import frappe
import requests

from ph_cas.cloud import config

_TOKEN_KEY = "ph_cas:cloud:machine_token"


def machine_token() -> str:
    cached = frappe.cache().get_value(_TOKEN_KEY)
    if cached and cached.get("exp", 0) > time.time() + 30:
        return cached["token"]
    c = config.conf()
    basic = base64.b64encode(f"{config.client_id()}:{c['client_secret']}".encode()).decode()
    r = requests.post(
        f"{config.issuer()}/oidc/token",
        data={"grant_type": "client_credentials", "scope": "entitlements:read usage:write"},
        headers={"Authorization": f"Basic {basic}"},
        timeout=15,
    )
    r.raise_for_status()
    body = r.json()
    frappe.cache().set_value(_TOKEN_KEY, {"token": body["access_token"], "exp": time.time() + int(body.get("expires_in", 300))}, expires_in_sec=int(body.get("expires_in", 300)))
    return body["access_token"]


def get(path: str) -> dict:
    r = requests.get(f"{config.issuer()}{path}", headers={"Authorization": f"Bearer {machine_token()}"}, timeout=15)
    r.raise_for_status()
    return r.json()


def post(path: str, payload) -> dict:
    r = requests.post(f"{config.issuer()}{path}", json=payload, headers={"Authorization": f"Bearer {machine_token()}"}, timeout=15)
    r.raise_for_status()
    return r.json()
