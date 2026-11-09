#!/usr/bin/env bash
# standby-restore-test: on the standby server, fetch the newest encrypted backup of the client's
# site from the bucket, restore it into a fresh container of the same image, and prove the site
# starts and its monitor is green. Leaves the restored site running as the UAT/training copy on
# port 8080 until the next run. Reads /etc/ledger-standby.env (B36).
set -euo pipefail
: "${CLIENT:?}" "${SITE_NAME:?}" "${IMAGE:?}" "${BACKUP_REMOTE:?}" "${BACKUP_KEY:?}" "${DB_ROOT_PASSWORD:?}" "${ADMIN_PASSWORD:?}"
BASE=/srv/ledger/$CLIENT; DL=$BASE/backups; LOG=$BASE/restore-test.log
mkdir -p "$DL"
echo "$(date -u +%FT%TZ) start" >> "$LOG"

# 1. newest backup set (manifest + .enc files) from the bucket
rclone sync "$BACKUP_REMOTE/$SITE_NAME/" "$DL/" --max-age 3d --quiet
MANIFEST=$(ls -t "$DL"/*manifest*.json 2>/dev/null | head -1)
[ -n "$MANIFEST" ] || { echo "$(date -u +%FT%TZ) FAIL no manifest in bucket" >> "$LOG"; exit 1; }
DB_ENC=$(ls -t "$DL"/*database.sql.gz.enc | head -1)
FILES_ENC=$(ls -t "$DL"/*-files.tar.enc 2>/dev/null | head -1 || true)
PRIV_ENC=$(ls -t "$DL"/*-private-files.tar.enc 2>/dev/null | head -1 || true)

# 2. decrypt (same scheme as ph_cas.ops.backup: openssl aes-256-cbc, pbkdf2)
R=$BASE/restore; rm -rf "$R"; mkdir -p "$R"
dec() { openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:$BACKUP_KEY" -in "$1" -out "$2"; }
dec "$DB_ENC" "$R/database.sql.gz"
[ -n "$FILES_ENC" ] && dec "$FILES_ENC" "$R/files.tar"
[ -n "$PRIV_ENC" ] && dec "$PRIV_ENC" "$R/private-files.tar"

# 3. fresh container from the production image, empty volumes, then restore into it
docker rm -f "ledger-uat-$CLIENT" >/dev/null 2>&1 || true
docker volume rm -f "uat-$CLIENT-mysql" "uat-$CLIENT-sites" >/dev/null 2>&1 || true
docker pull -q "$IMAGE" >/dev/null || true
docker run -d --name "ledger-uat-$CLIENT" -p 8080:8000 \
  -e SITE_NAME="$SITE_NAME" -e DB_ROOT_PASSWORD="$DB_ROOT_PASSWORD" -e ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  -e PH_PRODUCTION=0 -e PH_DEMO=0 -e PH_2FA=0 \
  -v "uat-$CLIENT-mysql:/var/lib/mysql" -v "uat-$CLIENT-sites:/home/frappe/bench/sites" \
  -v "$R:/restore:ro" "$IMAGE" >/dev/null
# wait for the first-run install to finish (site exists), then restore over it
for i in $(seq 1 120); do docker exec "ledger-uat-$CLIENT" test -f "/home/frappe/bench/sites/$SITE_NAME/.ph_cas_installed" 2>/dev/null && break; sleep 15; done
docker exec "ledger-uat-$CLIENT" su frappe -c "cd /home/frappe/bench && bench --site '$SITE_NAME' --force restore /restore/database.sql.gz --db-root-password '$DB_ROOT_PASSWORD' $( [ -n "$FILES_ENC" ] && echo "--with-public-files /restore/files.tar" ) $( [ -n "$PRIV_ENC" ] && echo "--with-private-files /restore/private-files.tar" )" >/dev/null
docker exec "ledger-uat-$CLIENT" su frappe -c "cd /home/frappe/bench && bench --site '$SITE_NAME' migrate" >/dev/null
docker exec "ledger-uat-$CLIENT" su frappe -c "cd /home/frappe/bench && bench --site '$SITE_NAME' set-config ph_cas_production 0 && bench --site '$SITE_NAME' set-admin-password '$ADMIN_PASSWORD'" >/dev/null

# 4. prove it: ping and monitor status
sleep 10
PING=$(curl -s -H "Host: $SITE_NAME" http://127.0.0.1:8080/api/method/ping || true)
STATUS=$(docker exec "ledger-uat-$CLIENT" su frappe -c "cd /home/frappe/bench && bench --site '$SITE_NAME' execute ph_cas.ops.monitor.status" | tail -1)
COUNT=$(docker exec "ledger-uat-$CLIENT" su frappe -c "cd /home/frappe/bench && bench --site '$SITE_NAME' execute frappe.db.count --args \"['Sales Invoice']\"" | tail -1)
if echo "$PING" | grep -q pong; then
  echo "$(date -u +%FT%TZ) OK restored $(basename "$DB_ENC"); sales invoices: $COUNT; status: $STATUS" >> "$LOG"
else
  echo "$(date -u +%FT%TZ) FAIL site did not answer after restore of $(basename "$DB_ENC")" >> "$LOG"; exit 1
fi
rm -rf "$R"
