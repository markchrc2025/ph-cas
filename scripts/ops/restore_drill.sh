#!/usr/bin/env bash
# restore_drill.sh <site> <db-root-password> <backup-key>: restore the latest backup into <site>-drill, verify, run the chain check, drop the drill site.
set -euo pipefail
SITE="$1"; DBROOT="$2"; KEY="$3"; DRILL="${SITE}-drill"
BDIR="sites/$SITE/private/backups"
LATEST_DB=$(ls -t "$BDIR"/*-database.sql.gz.enc 2>/dev/null | head -1 || true)
[ -z "$LATEST_DB" ] && LATEST_DB=$(ls -t "$BDIR"/*-database.sql.gz | head -1)
DB="$LATEST_DB"
if [[ "$LATEST_DB" == *.enc ]]; then
  DB="${LATEST_DB%.enc}"
  openssl enc -d -aes-256-cbc -pbkdf2 -in "$LATEST_DB" -out "$DB" -pass "pass:$KEY"
fi
MANIFEST="${DB%-database.sql.gz}-manifest.json"
bench --site "$SITE" execute ph_cas.ops.backup.verify_backup --kwargs "{\"manifest_path\": \"$MANIFEST\", \"key\": \"$KEY\"}"
bench new-site "$DRILL" --db-root-password "$DBROOT" --admin-password drill --install-app erpnext --install-app ph_cas --force
bench --site "$DRILL" --force restore "$DB" --db-root-password "$DBROOT"
bench --site "$DRILL" migrate
bench --site "$DRILL" execute ph_cas.audit.events.verify_chain
bench drop-site "$DRILL" --db-root-password "$DBROOT" --force --no-backup
[[ "$LATEST_DB" == *.enc ]] && rm -f "$DB"
echo "Restore drill of $SITE passed on $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "sites/$SITE/private/restore-drills.log"
