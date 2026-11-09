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
