"""B34: Sentire Ledger onboarding.

1. Videos. No card plays YouTube: ERPNext's intro videos are cleared and the cards play our own
   tutorials from the Sentire server (ph_cas.tutorials). Which step plays which video is data
   (tutorials/data/tutorials.json, seeded into PH Tutorial Video on install and migrate).
2. The "Get to know Sentire Ledger" module onboarding: six steps a Philippine business walks
   that ERPNext has no concept of. Created as records (not fixtures) so they survive ERPNext
   upgrades and can be edited here in one place.
3. The Sentire Ledger workspace that carries the onboarding card and the BIR shortcuts.
"""

import json

import frappe

MODULE = "PH CAS"
ONBOARDING = "Sentire Ledger Onboarding"
WORKSPACE = "Sentire Ledger"

STEPS = [
    {
        "name": "PH Set Up Company",
        "title": "Set up the Philippine company",
        "action": "Go to Page",
        "path": "/app/company",
        "action_label": "Open Company",
        "description": "Open your Company and fill in the BIR details from the Certificate of Registration: TIN, branch code, RDO, VAT or Non-VAT, registered name and business style. Then click **Set up Philippine company**: it adds the Philippine accounts, the account mapping and the BIR Series for the head office.",
        "validate_action": 0,
    },
    {
        "name": "PH Confirm Tax Rules",
        "title": "Confirm your tax rules",
        "action": "Go to Page",
        "path": "/app/ph-tax-rule",
        "action_label": "Open Tax Rules",
        "description": "Every rate the system applies (VAT, withholding, percentage tax, income tax brackets) is a dated rule here. Rules start as drafts; your accountant confirms them and the confirmed set is what a production site applies. Review the ones that match your registration.",
        "validate_action": 0,
    },
    {
        "name": "PH First BIR Invoice",
        "title": "Print your first BIR invoice",
        "action": "Create Entry",
        "reference_document": "Sales Invoice",
        "action_label": "New Sales Invoice",
        "description": "Submit a Sales Invoice and print the **PH Sales Invoice** format. The serial number is taken from the BIR Series the moment you submit (never on a draft), the header shows your registration, and the original and duplicate are marked. Issued invoices cannot be amended or deleted; corrections are credit or debit notes.",
        "validate_action": 1,
    },
    {
        "name": "PH Run 2550Q",
        "title": "Run the 2550Q figures",
        "action": "Go to Page",
        "path": "/app/ph-tax-return-figures/new",
        "action_label": "New Tax Return Figures",
        "description": "Pick the return (2550Q, 2551Q, 0619-E, 1601-EQ and the income tax forms), the company and the period. The figures are computed from your books, item by item of the form, ready to be keyed into eBIRForms.",
        "validate_action": 0,
    },
    {
        "name": "PH Export Books",
        "title": "Export the books",
        "action": "View Report",
        "reference_report": "PH Sales Journal",
        "action_label": "Open the Sales Journal",
        "description": "The seven books (sales journal, purchase journal, cash receipts, cash disbursements, general journal, general ledger, inventory) are reports with totals and tie-outs; export any of them with the BIR header. The year-end pack bundles them with a manifest and transmittal.",
        "validate_action": 0,
    },
    {
        "name": "PH Registration Pack",
        "title": "Build the registration pack",
        "action": "Go to Page",
        "path": "/app/ph-cas-settings",
        "action_label": "Open Settings",
        "description": "PH CAS Settings holds the provider and signatory details printed on the registration documents. From there, **Download registration pack** produces the Annex B answers, sworn statement, specimen prints, books and audit trail for your RDO.",
        "validate_action": 0,
    },
]


def apply_videos() -> dict:
    """No onboarding card plays YouTube: every intro_video_url is cleared, and the cards play our
    own tutorial videos from the Sentire server instead (ph_cas.tutorials, public/js/tutorials.js).
    Which step plays which video is the PH Tutorial Video records' `steps`."""
    from ph_cas.tutorials.api import seed

    cleared = frappe.get_all("Onboarding Step", filters={"intro_video_url": ["is", "set"]}, pluck="name")
    for name in cleared:
        frappe.db.set_value("Onboarding Step", name, "intro_video_url", None, update_modified=False)
    return {"cleared": cleared, "tutorials": seed()}


def ensure_steps():
    for s in STEPS:
        doc = frappe.get_doc("Onboarding Step", s["name"]) if frappe.db.exists("Onboarding Step", s["name"]) else frappe.new_doc("Onboarding Step")
        values = {k: v for k, v in s.items() if k != "name"}
        values.update({"is_complete": doc.get("is_complete") or 0, "is_skipped": 0, "show_form_tour": 0, "is_single": 0})
        if doc.is_new():
            doc.name = s["name"]
            doc.update(values)
            doc.flags.name_set = True
            doc.insert(ignore_permissions=True)
        else:
            changed = any(doc.get(k) != v for k, v in values.items() if k not in ("is_complete",))
            if changed:
                doc.update(values)
                doc.save(ignore_permissions=True)


def ensure_module_onboarding():
    if frappe.db.exists("Module Onboarding", ONBOARDING):
        mo = frappe.get_doc("Module Onboarding", ONBOARDING)
    else:
        mo = frappe.new_doc("Module Onboarding")
        mo.name = ONBOARDING
        mo.flags.name_set = True
    mo.title = "Get to know Sentire Ledger"
    mo.module = MODULE
    mo.set("steps", [{"step": s["name"], "is_optional": 0} for s in STEPS])
    mo.set("allow_roles", [{"role": r} for r in ("System Manager", "Accounts Manager", "Accounts User", "Accounting Manager") if frappe.db.exists("Role", r)])
    mo.flags.ignore_permissions = True
    if mo.is_new():
        mo.insert()
    else:
        mo.save()
    frappe.db.set_value("Onboarding Step", {"name": ["in", [s["name"] for s in STEPS]]}, "module_onboarding", ONBOARDING, update_modified=False)


def ensure_workspace():
    content = [
        {"id": "sl_onb", "type": "onboarding", "data": {"onboarding_name": ONBOARDING, "col": 12}},
        {"id": "sl_h1", "type": "header", "data": {"text": "<span class=\"h4\"><b>Every day</b></span>", "col": 12}},
        {"id": "sl_s1", "type": "shortcut", "data": {"shortcut_name": "Sales Invoice", "col": 3}},
        {"id": "sl_s2", "type": "shortcut", "data": {"shortcut_name": "Purchase Invoice", "col": 3}},
        {"id": "sl_s3", "type": "shortcut", "data": {"shortcut_name": "Payment Entry", "col": 3}},
        {"id": "sl_s4", "type": "shortcut", "data": {"shortcut_name": "Journal Entry", "col": 3}},
        {"id": "sl_h2", "type": "header", "data": {"text": "<span class=\"h4\"><b>BIR</b></span>", "col": 12}},
        {"id": "sl_s5", "type": "shortcut", "data": {"shortcut_name": "Tax Return Figures", "col": 3}},
        {"id": "sl_s6", "type": "shortcut", "data": {"shortcut_name": "2307 Issued", "col": 3}},
        {"id": "sl_s7", "type": "shortcut", "data": {"shortcut_name": "BIR Audit Trail", "col": 3}},
        {"id": "sl_s8", "type": "shortcut", "data": {"shortcut_name": "Settings", "col": 3}},
        {"id": "sl_h3", "type": "header", "data": {"text": "<span class=\"h4\"><b>Books and rules</b></span>", "col": 12}},
        {"id": "sl_c1", "type": "card", "data": {"card_name": "Books", "col": 4}},
        {"id": "sl_c2", "type": "card", "data": {"card_name": "Tax", "col": 4}},
        {"id": "sl_c3", "type": "card", "data": {"card_name": "Registration and audit", "col": 4}},
    ]
    shortcuts = [
        ("Sales Invoice", "DocType", "Sales Invoice"),
        ("Purchase Invoice", "DocType", "Purchase Invoice"),
        ("Payment Entry", "DocType", "Payment Entry"),
        ("Journal Entry", "DocType", "Journal Entry"),
        ("Tax Return Figures", "DocType", "PH Tax Return Figures"),
        ("2307 Issued", "DocType", "PH 2307 Issued"),
        ("BIR Audit Trail", "Report", "BIR Audit Trail"),
        ("Settings", "DocType", "PH CAS Settings"),
    ]
    links = []

    def card(label, items):
        links.append({"type": "Card Break", "label": label, "link_count": len(items)})
        for lt, name in items:
            label = name[3:] if name.startswith("PH ") else name
            links.append({"type": "Link", "label": label, "link_type": lt, "link_to": name})

    card("Books", [("Report", r) for r in ("PH Sales Journal", "PH Purchase Journal", "PH Cash Receipts Book", "PH Cash Disbursements Book", "PH General Journal", "PH General Ledger Book", "PH Inventory Book")])
    card("Tax", [("DocType", "PH Tax Rule"), ("Report", "PH Draft Tax Rules"), ("Report", "PH Compliance Calendar"), ("Report", "PH Book to Tax Reconciliation"), ("DocType", "PH 2307 Received"), ("DocType", "PH Alphalist File")])
    card("Registration and audit", [("DocType", "BIR Series"), ("DocType", "PH Event Log"), ("Report", "PH Chain Check"), ("DocType", "PH Print Record"), ("DocType", "PH RDO")])
    links = [l for l in links if l["type"] == "Card Break" or frappe.db.exists(l["link_type"], l["link_to"])]

    if frappe.db.exists("Workspace", WORKSPACE):
        ws = frappe.get_doc("Workspace", WORKSPACE)
    else:
        ws = frappe.new_doc("Workspace")
        ws.name = WORKSPACE
        ws.flags.name_set = True
    ws.update(
        {
            "title": WORKSPACE,
            "label": WORKSPACE,
            "module": MODULE,
            "public": 1,
            "is_hidden": 0,
            "icon": "accounting",
            "indicator_color": "blue",
            "sequence_id": 0.5,
            "module_onboarding": ONBOARDING,
            "content": json.dumps(content),
        }
    )
    ws.set("shortcuts", [{"label": l, "type": t, "link_to": n} for l, t, n in shortcuts if frappe.db.exists(t, n)])
    ws.set("links", links)
    ws.flags.ignore_permissions = True
    ws.flags.ignore_links = True
    if ws.is_new():
        ws.insert()
    else:
        ws.save()


def setup():
    """Called from setup_all. Idempotent."""
    ensure_steps()
    ensure_module_onboarding()
    ensure_workspace()
    apply_videos()
