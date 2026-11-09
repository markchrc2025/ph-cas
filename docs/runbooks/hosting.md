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

Persist `/var/lib/mysql` and `/home/frappe/bench/sites` as volumes; without them every redeploy reinstalls the site.

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
