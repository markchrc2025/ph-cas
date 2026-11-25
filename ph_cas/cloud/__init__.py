"""B88: Sentire Ledger on Sentire Cloud.

Each Ledger site belongs to one Sentire Cloud organization. Site config:

    "sentire_cloud": {
        "issuer": "https://cloud.sentire.solutions",
        "org_id": "<organization id>",
        "client_id": "sentire-ledger",
        "client_secret": "<OIDC client secret>",
        "event_secret": "<event secret>"
    }

Without that block nothing here runs, and the site keeps its own sign-in and PH CAS Settings tiers.
"""
