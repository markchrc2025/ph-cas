#!/usr/bin/env bash
# new_client_site.sh <site-name> <db-root-password> <admin-password> <backup-key> <rclone-remote>
# One site per client (D2). Production flags on, backups configured.
set -euo pipefail
SITE="$1"; DBROOT="$2"; ADMIN="$3"; KEY="$4"; REMOTE="${5:-}"
bench new-site "$SITE" --db-root-password "$DBROOT" --admin-password "$ADMIN" --install-app erpnext --install-app ph_cas
bench --site "$SITE" set-config ph_cas_production 1
bench --site "$SITE" set-config ph_backup_key "$KEY"
[ -n "$REMOTE" ] && bench --site "$SITE" set-config ph_backup_remote "$REMOTE"
bench --site "$SITE" set-config keep_backups_for_hours 87600   # ten years, local copies
bench --site "$SITE" set-config encryption_key "$(openssl rand -base64 32)"
bench --site "$SITE" enable-scheduler
echo "Site $SITE ready. Next: sign in, run Set up Philippine company, enter the BIR Series ranges from the AC, load opening balances with a locked opening Journal Entry (see docs/runbooks/onboarding.md)."
