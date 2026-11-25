"""B88 (CLD-16): Sentire Ledger on Sentire Cloud.

Sign-in token checks, users linked to the Sentire Account, entitlement to PH CAS Settings, read-only
when unpaid, the paywall answer (HTTP 402) on limits, signed events and the /login redirect rule."""

import json
import re
import time
from unittest.mock import patch

import frappe
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from frappe.sentire import sign
from frappe.tests import IntegrationTestCase

from ph_cas.cloud import entitlements, events, sso
from ph_cas.hosting import tiers

CONF = {"issuer": "https://cloud.test", "org_id": "ORG1", "client_id": "sentire-ledger", "client_secret": "s" * 32, "event_secret": "e" * 32}


def ent(**kw):
    base = {"organizationId": "ORG1", "appId": "ledger", "state": "ACTIVE", "plan": "team", "addons": [], "features": [], "limits": {"users": {"value": 5, "mode": "HARD"}, "companies": {"value": 1, "mode": "HARD"}, "branches": {"value": 3, "mode": "HARD"}, "invoices_per_month": {"value": 1000, "mode": "HARD"}}, "periodEnd": "2027-11-25", "version": 1}
    base.update(kw)
    return base


class TestB88Cloud(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        sso.setup()
        self.conf = patch.dict(frappe.local.conf, {"sentire_cloud": CONF})
        self.conf.start()
        frappe.cache().delete_value(entitlements.STATE_KEY)
        frappe.db.set_default("ph_cas_cloud_state", "")
        self.saved = {f: frappe.db.get_single_value("PH CAS Settings", f) for f in ("subscription_tier", "max_users", "max_companies", "max_branches", "monthly_invoice_limit", "subscription_until")}

    def tearDown(self):
        self.conf.stop()
        frappe.cache().delete_value(entitlements.STATE_KEY)
        frappe.db.set_default("ph_cas_cloud_state", "")
        s = frappe.get_single("PH CAS Settings")
        for k, v in self.saved.items():
            s.set(k, v)
        s.flags.ignore_permissions = True
        s.save()
        frappe.db.rollback()

    def test_entitlement_sets_tier_limits_and_period(self):
        out = entitlements.apply(ent())
        s = frappe.get_single("PH CAS Settings")
        self.assertEqual(s.subscription_tier, "Team")
        self.assertEqual((s.max_users, s.max_companies, s.max_branches, s.monthly_invoice_limit), (5, 1, 3, 1000))
        self.assertEqual(str(s.subscription_until), "2027-11-25")
        self.assertEqual(out["state"], "ACTIVE")
        # unlimited is 0 in Ledger
        entitlements.apply(ent(plan="business", limits={"users": {"value": 15, "mode": "HARD"}, "branches": {"value": None, "mode": "HARD"}}, version=2))
        s = frappe.get_single("PH CAS Settings")
        self.assertEqual((s.subscription_tier, s.max_users, s.max_branches), ("Business", 15, 0))
        # an older version never wins
        entitlements.apply(ent(plan="solo", version=1))
        self.assertEqual(frappe.get_single("PH CAS Settings").subscription_tier, "Business")

    def test_read_only_refuses_changes_with_payment_required(self):
        entitlements.apply(ent(state="READ_ONLY", version=3))
        frappe.set_user("Guest")
        frappe.session.user = "someone@example.com"
        doc = frappe.get_doc({"doctype": "ToDo", "description": "B88 read-only"})
        frappe.flags.in_test = False
        try:
            with self.assertRaises(entitlements.PaymentRequired) as cm:
                entitlements.refuse_when_read_only(doc)
        finally:
            frappe.flags.in_test = True
        self.assertEqual(cm.exception.http_status_code, 402)
        self.assertEqual(frappe.local.response["sentire_paywall"]["code"], "PAYMENT_REQUIRED")
        frappe.set_user("Administrator")
        entitlements.apply(ent(state="ACTIVE", version=4))
        frappe.session.user = "someone@example.com"
        frappe.flags.in_test = False
        try:
            entitlements.refuse_when_read_only(doc)  # no error
        finally:
            frappe.flags.in_test = True
            frappe.set_user("Administrator")

    def test_limit_answers_402_with_upgrade_link(self):
        with self.assertRaises(entitlements.PaymentRequired):
            tiers._refuse("users", 1, "Solo")
        link = frappe.local.response["sentire_paywall"]["upgradeUrl"]
        self.assertTrue(link.startswith("https://cloud.test/upgrade?"))
        self.assertIn("feature=users", link)
        self.assertIn("org=ORG1", link)

    def test_id_token_checks_signature_audience_issuer_and_nonce(self):
        key = ec.generate_private_key(ec.SECP256R1())
        jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()))
        jwk.update({"kid": "k1", "alg": "ES256", "use": "sig"})
        claims = {"iss": "https://cloud.test", "aud": "sentire-ledger", "sub": "U1", "email": "ana@b88.ph", "nonce": "n1", "org_id": "ORG1", "app_access": True, "exp": int(time.time()) + 300, "iat": int(time.time())}
        good = jwt.encode(claims, key, algorithm="ES256", headers={"kid": "k1"})
        with patch.object(sso, "_jwks", return_value={"keys": [jwk]}):
            self.assertEqual(sso.verify_id_token(good, "n1")["sub"], "U1")
            with self.assertRaises(Exception):
                sso.verify_id_token(good, "other-nonce")
            bad_aud = jwt.encode({**claims, "aud": "sentire-payroll"}, key, algorithm="ES256", headers={"kid": "k1"})
            with self.assertRaises(jwt.InvalidAudienceError):
                sso.verify_id_token(bad_aud, "n1")
            other = ec.generate_private_key(ec.SECP256R1())
            forged = jwt.encode(claims, other, algorithm="ES256", headers={"kid": "k1"})
            with self.assertRaises(jwt.InvalidSignatureError):
                sso.verify_id_token(forged, "n1")

    def test_users_are_linked_to_the_sentire_account(self):
        email = "b88-owner@example.com"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        name = sso.ensure_user({"sub": "SUB-B88", "email": email, "name": "Ana Dela Cruz", "org_role": "OWNER"})
        u = frappe.get_doc("User", name)
        self.assertEqual(u.get(sso.SUB_FIELD), "SUB-B88")
        self.assertEqual([r.role_profile for r in u.role_profiles], ["Owner"])
        # same account again: the same user
        self.assertEqual(sso.ensure_user({"sub": "SUB-B88", "email": email, "org_role": "MEMBER"}), name)

    def test_member_removed_event_disables_the_user(self):
        email = "b88-member@example.com"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        name = sso.ensure_user({"sub": "SUB-M", "email": email, "name": "Mem Ber", "org_role": "MEMBER"})
        events.handle({"type": "account.member.removed", "company": "ORG1", "data": {"userId": "SUB-M"}})
        self.assertEqual(frappe.db.get_value("User", name, "enabled"), 0)

    def test_entitlement_event_applies(self):
        events.handle({"type": "account.entitlement.changed", "company": "ORG1", "data": ent(plan="solo", limits={"users": {"value": 1, "mode": "HARD"}}, version=9)})
        self.assertEqual(frappe.get_single("PH CAS Settings").subscription_tier, "Solo")

    def test_event_signature_matches_sentire_cloud_format(self):
        body = json.dumps({"specversion": "sentire.event.v1", "id": "x", "type": "t", "source": "sentire-cloud", "company": "ORG1", "time": "2026-11-25T00:00:00Z", "data": {}}).encode()
        from frappe.sentire import verify

        self.assertTrue(verify(body, sign(body, CONF["event_secret"]), CONF["event_secret"]))
        self.assertFalse(verify(body, sign(body, "wrong"), CONF["event_secret"]))

    def test_login_redirect_rule(self):
        rule = next(r for r in frappe.get_hooks("website_redirects") if "sso.login" in r["target"])
        pattern = rule["source"].strip("/ ") + "$"
        self.assertTrue(re.match(pattern, "login"))
        self.assertTrue(re.match(pattern, "login?redirect-to=%2Fapp%2Fsales-invoice"))
        self.assertFalse(re.match(pattern, "login?local=1"))
        self.assertEqual(rule, sso.LOGIN_REDIRECT)
