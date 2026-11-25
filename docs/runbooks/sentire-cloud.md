# Runbook: put a Ledger site on Sentire Cloud (B88)

Sentire Cloud (https://cloud.sentire.solutions, staging https://sentire-cloud-staging.apps.sentire.solutions) is where a client signs up, pays and manages its people. A Ledger site joins it once; after that, sign-in, plan and limits come from Sentire Cloud.

## When a client subscribes
1. The client buys a Ledger plan in Sentire Cloud. Their organization gets a Ledger instance with status "Setting up".
2. Create the site as today: `deploy/ledger-site.sh create <site>` (hosting runbook).
3. In the site config (`sites/<site>/site_config.json`) add:
   ```json
   "sentire_cloud": {
     "issuer": "https://cloud.sentire.solutions",
     "org_id": "<the organization id from Sentire Cloud staff console>",
     "client_id": "sentire-ledger",
     "client_secret": "<Ledger's OIDC client secret>",
     "event_secret": "<Ledger's event secret>"
   }
   ```
   The two secrets are created once in Sentire Cloud > Staff > Apps > Sentire Ledger (shown once) and kept in the Ledger app's Environment in Dokploy, never in chat or git.
4. `bench --site <site> migrate` (adds the Sentire Account ID field), then `bench --site <site> execute ph_cas.cloud.entitlements.pull`.
5. In Sentire Cloud staff console > Organizations > the client > Instances, click Mark ready with the site address. The Owner gets the link by email.

## Day to day
- Signing in: /login sends people to Sentire sign-in. The Administrator uses /login?local=1.
- Plan changes, read-only when unpaid, and member removal reach the site as events within a minute; an hourly pull covers missed events.
- Usage is reported daily.

## When a client leaves
1. At the end of the paid period Sentire Cloud asks the site for the export. The zip appears for the Owner on their billing page for 30 days.
2. After 30 days Sentire Cloud asks for deletion; the site answers "manual". Delete the site with `deploy/ledger-site.sh delete <site>` (offboarding runbook), generate the deletion certificate (`ph_cas.hosting.offboard.deletion_certificate`), and paste it in Sentire Cloud > Organizations > Instances > Record deletion.
