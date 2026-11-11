# Runbook: hosting and operations (D2, D3; Annex B items 7 and 11)

- **Where.** Production servers and the backup bucket in the Philippines (provider chosen by the owner, G9). One Frappe site per client on a shared bench; database per site.
- **Access.** SSH by key only, from the firm's addresses; no root sign-in; server login records kept. TLS for every site. Database bound to localhost.
- **Backups.** The daily scheduler job (ph_cas.ops.backup.scheduled_daily_backup) takes database plus private and public files, writes a manifest with SHA-256 hashes, encrypts with AES-256 (key in site_config ph_backup_key, kept in the firm's password manager, never on the client's side), and copies to the bucket (site_config ph_backup_remote) with rclone. Local copies kept ten years (keep_backups_for_hours 87600); the bucket's lifecycle rule also ten years. Verify: `bench --site <site> execute ph_cas.ops.backup.verify_backup --kwargs '{"manifest_path": "...", "key": "..."}'`.
- **Restore drill.** Monthly: `scripts/ops/restore_drill.sh <site> <db-root> <key>` restores the latest backup into a scratch site, migrates, runs the chain check and drops the scratch site; the result is appended to sites/<site>/private/restore-drills.log and kept for the RDO.
- **Monitoring.** ph_cas.ops.monitor.status (whitelisted) reports backup age, chain check, disk, scheduler and draft rules; the hourly job emails System Managers when a check fails. Add an external uptime check per site.
- **Retention.** Five years under EOPT, ten per the Annex B form (RETENTION-5Y rule); keep ten until the RDO answers question 7.
- **Data privacy.** The firm is a personal information processor for payee and employee data: data protection officer appointed, data processing agreement in the contract, NPC registration checked (owner action items 7.3). Backups and the bucket hold personal data: access limited to the operators.
- **Incidents.** A broken chain check, a failed restore drill or a security event is recorded in the event log and reported to the client and, where the law requires, to the NPC within 72 hours.

## Container deployment (Dockerfile at the repo root)

`deploy/entrypoint.sh` runs MariaDB, Redis, nginx, gunicorn, socket.io, a worker and the scheduler in one container, creates the site on first start and runs `bench migrate` on later starts. At every start it applies `ph_cas.deploy_config.apply`, which reads these environment variables:

| Variable | Purpose |
|---|---|
| `SITE_NAME`, `ADMIN_PASSWORD`, `DB_ROOT_PASSWORD` | Site name and secrets (required) |
| `PH_PRODUCTION` | 1 for a production site (draft rules refused), 0 for a demo |
| `PH_DEMO` | 1 seeds the demo company and documents |
| `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_FROM_NAME`, `SMTP_TLS` (1), `SMTP_SSL` (0) | Outgoing email account; needed for two-factor sign-in mails, password resets and notifications. `SEED_USER` and `SEED_PASSWORD` are accepted as aliases of the user and password. |
| `ADMIN_EMAIL` | Mailbox of the Administrator user (where its two-factor mails go) |
| `PH_2FA` | Demo sites only: 0 turns two-factor sign-in off until email works; ignored when `PH_PRODUCTION` is 1 |
| `PRODUCT_NAME`, `PROVIDER_NAME`, `SUPPORT_EMAIL` | Branding (B38): the product name goes into PH CAS Settings, System Settings, Website Settings, the Email Account name (so mail arrives from "Sentire Ledger <noreply@...>"), the About dialog and the desk boot; the provider name goes into the email and website footers; the support address becomes a help-menu item. Default `ADMIN_EMAIL` for support. |

Persist `/var/lib/mysql` and `/home/frappe/bench/sites` as volumes; without them every redeploy reinstalls the site.

## Branding (B38)

Nothing a user sees says Frappe or ERPNext: `ph_cas/branding.py` writes the product identity into Website Settings (app name, logo, favicon, splash, footer), Navbar Settings (logo, hidden framework help items, a contact item), System Settings (app name, framework email footer off, provider footer), every outgoing Email Account (sender name, wordmark header) and the users' default workspace. It runs on every start and after every migrate, so a demo reset or a new client site gets it too. The desk About dialog is replaced by `ph_cas/public/js/branding.js`; it keeps a licences line (GPL v3 for ERPNext and ph_cas, MIT for Frappe), which the licences require, and the source keeps every copyright header.

The desk opens on the Sentire Ledger shell: `ph_cas/ph_cas/sidebar/sentire_ledger` ships a standard Sidebar (Home, the four daily documents, Books, Tax returns, Tax rules, Registration and audit, Masters, Settings) and `branding.apply` writes the site layer of the dock so that shell is first on the rail; every user's `default_workspace` is Sentire Ledger. Text the framework ships that names itself (the "Get to know ERPNext" guide and its steps) is rewritten to the product on every start.

Home page (B39): `/desk/sentire-ledger/sentire-home` is a desk Page (`ph_cas/ph_cas/page/sentire_home`) fed by one call, `ph_cas.home.dashboard.get(company, period)`: greeting, module tiles, create actions, the onboarding checklist until done or dismissed, the period's sales and purchases, cash and bank, receivable and payable, the VAT and withholding balances of the mapped accounts, drafts waiting, a 12-month chart and the next due dates from the compliance calendar. It is the first item of the Sentire Ledger sidebar; because Frappe can only land a user on a workspace, `branding.js` sends the first load of the Sentire Ledger workspace on to the page. The workspace stays as "Overview".

Logo files: `ph_cas/public/images/` (`logo.svg` square mark, `wordmark.svg` and `wordmark.png` for emails, `favicon.ico`, PNG icons 32 to 512). To replace the provisional mark, overwrite those files and redeploy; no settings change is needed. Prints show the product version only; the registration pack and the sworn statement still state the full platform (`platform_version()`), because the BIR is told what the system is built on.

## Multi-site hosting (B32)

One container serves many sites. The primary site is `SITE_NAME` (the demo on MCRC's own installation); client sites are `<name>.$CLIENT_DOMAIN`, each with its own database, created from the Dokploy terminal of the app:

```
ledger-site new acme --tier Team                 # https://acme.ledger.sentire.solutions, production flags on
ledger-site new acme --tier Business --pilot 14  # paid pilot: demo mode, pilot_until set, deleted at day 30 if not subscribed
ledger-site set-tier acme Business --until 2027-11-10 --max-users 20
ledger-site usage acme
ledger-site list
ledger-site backup acme
ledger-site password acme
ledger-site drop acme --yes                      # only after the export of docs/runbooks/offboarding.md
```

DNS: a wildcard `*.$CLIENT_DOMAIN` A record to the app server, and a wildcard domain on the Dokploy app (or one domain per client). nginx routes `<name>.$CLIENT_DOMAIN` to the site of that exact name and every other hostname to the primary site. At every container start each client site is migrated and receives the shared outgoing email account and branding; its Administrator password and two-factor setting are its own.

Tier limits live in PH CAS Settings (tier, max users, companies, branches, invoices per month) and are enforced when users, companies, branches or invoices are created. Provider staff users (User.ph_provider_staff) do not consume a seat. `Internal` has no limits. Limits per tier are in `ph_cas/hosting/tiers.py`.

Backups: every site runs its own encrypted daily backup (B31). Set `BACKUP_REMOTE` on the app (an rclone remote, e.g. `s3:ledger-backups`, configured through `RCLONE_CONFIG_*` environment variables) and every site's backup is copied off-site under its own folder.

Capacity: about 5 to 10 small sites per 4 GB container; a second app from the same image, or a dedicated pair (B36), beyond that.

## Open demo and pilots (B33)

Open demo (the primary site with `PH_DEMO=1`): `/demo` is a public signup page; the request creates a Demo User restricted to its own demo company and emails a one-click link (`/demo_login?token=...`) valid 24 hours. Requests are the lead list: appended to `sites/<site>/private/files/demo-requests.csv`, mailed to the Administrator's address, and posted as JSON to `DEMO_LEADS_WEBHOOK` when that variable is set (the newsletter tool's inbound webhook). Limits: one demo per email per 30 days, five requests per IP per day. The hourly job disables users whose 24 hours are over.

Nightly reset: after the seed the entrypoint stores a golden database snapshot (`ledger-site snapshot-demo`); every night at `DEMO_RESET_UTC_HOUR` (default 18 UTC, 02:00 Manila) `ledger-site reset-demo` restores it, re-applies the container configuration and re-issues access mails to demo users whose 24 hours are still running. Set `DEMO_RESET=0` to turn the reset off.

Pilots: `ledger-site new acme --tier Business --pilot 14` creates the client's own site in demo mode with `pilot_until` set. The daily job counts down a 30-day grace period after `pilot_until`; when it ends without a recorded subscription (`ledger-site set-tier acme Business --until <date>`), every user is disabled and the monitor reports it. The site is dropped by the provider after the export (docs/runbooks/offboarding.md), never automatically.
