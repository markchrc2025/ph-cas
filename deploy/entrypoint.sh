#!/usr/bin/env bash
# Runs as root: starts MariaDB and Redis, then the bench as the frappe user.
# Env: SITE_NAME (required), DB_ROOT_PASSWORD, ADMIN_PASSWORD (secrets), PORT (8000),
#      PH_PRODUCTION (0 = demo site that applies draft rules; 1 = production), PH_DEMO (1 = seed demo data once).
#      CLIENT_DOMAIN (default SITE_NAME): client sites are <name>.$CLIENT_DOMAIN, created with `ledger-site new <name>`.
#      BACKUP_REMOTE (optional rclone remote such as s3:ledger-backups) for the off-site copy of every site's backup.
#      PH_STAGING (1 = the staging QA site, docs/STAGING.md): QA data seeded once and restored at every
#      start, QA admin (STAGING_ADMIN_PASSWORD), and the QA connector on QA_MCP_PORT (QA_MCP_SECRET).
set -euo pipefail
trap 'echo "entrypoint failed at line $LINENO: $BASH_COMMAND" >&2' ERR
SITE="${SITE_NAME:?SITE_NAME is required}"
PORT="${PORT:-8000}"
DBROOT="${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is required}"
ADMIN="${ADMIN_PASSWORD:?ADMIN_PASSWORD is required}"
BENCH=/home/frappe/bench
CLIENT_DOMAIN="${CLIENT_DOMAIN:-$SITE}"
STAGING="${PH_STAGING:-0}"
if [ "$STAGING" = 1 ]; then
  [ "${PH_PRODUCTION:-0}" = 1 ] && { echo "PH_STAGING=1 with PH_PRODUCTION=1: refusing to start"; exit 1; }
  [ "${PH_DEMO:-0}" = 1 ] && { echo "PH_STAGING=1 with PH_DEMO=1: choose one"; exit 1; }
fi

echo "== MariaDB"
if [ ! -d /var/lib/mysql/mysql ]; then
  mariadb-install-db --user=mysql --datadir=/var/lib/mysql >/dev/null
  FRESH_DB=1
fi
chown -R mysql:mysql /var/lib/mysql
(mysqld_safe --user=mysql >/var/log/mysqld.log 2>&1 &)
# Wait for MariaDB. If another container still holds the data volume (swarm update order start-first),
# InnoDB cannot lock ibdata1; say so clearly instead of hanging silently.
for i in $(seq 1 180); do
  mysqladmin ping --silent 2>/dev/null && break
  if [ $((i % 15)) -eq 0 ]; then
    echo "waiting for MariaDB (${i}s)"; grep -ihE "lock|error" /var/log/mysqld.log /var/log/mysql/error.log 2>/dev/null | tail -2 || true
    grep -qh "Unable to lock" /var/log/mysqld.log /var/log/mysql/error.log 2>/dev/null && echo "another container holds /var/lib/mysql: set the Dokploy swarm update order to stop-first (Advanced > Swarm Settings)"
  fi
  sleep 1
done
mysqladmin ping --silent 2>/dev/null || { echo "MariaDB did not start; last log lines:"; tail -20 /var/log/mysqld.log /var/log/mysql/error.log 2>/dev/null; exit 1; }
# Root auth: the image ships a pre-initialised datadir with socket-only root, so set the
# password every start (idempotent) and allow root over TCP from the loopback address.
mysql -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('${DBROOT}');
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY '${DBROOT}';
ALTER USER 'root'@'127.0.0.1' IDENTIFIED BY '${DBROOT}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION; FLUSH PRIVILEGES;" \
  || mysql -uroot -p"${DBROOT}" -h127.0.0.1 -e "select 1" >/dev/null

echo "== Redis"
(redis-server --daemonize yes --save 60 1 --dir /var/lib/redis >/dev/null 2>&1 || redis-server --daemonize yes >/dev/null)

echo "== bench"
# sites/ may be a persistent volume: refresh the built assets and app list from this image.
if [ -d /home/frappe/sites-image ]; then
  mkdir -p "$BENCH/sites"
  rm -rf "$BENCH/sites/assets"
  cp -a /home/frappe/sites-image/assets "$BENCH/sites/assets"
  cp -a /home/frappe/sites-image/apps.txt /home/frappe/sites-image/apps.json "$BENCH/sites/"
  [ -f "$BENCH/sites/common_site_config.json" ] || cp -a /home/frappe/sites-image/common_site_config.json "$BENCH/sites/"
fi
id frappe; which bench; ls -la "$BENCH/sites" | head
chown -R frappe:frappe "$BENCH/sites"
su frappe -c "cd $BENCH && bench set-config -g db_host 127.0.0.1 && bench set-config -g redis_cache redis://127.0.0.1:6379 && bench set-config -g redis_queue redis://127.0.0.1:6379 && bench set-config -g redis_socketio redis://127.0.0.1:6379 && bench set-config -g default_site '$SITE' && bench set-config -g serve_default_site true && bench set-config -g webserver_port 8001"
if [ -n "${BACKUP_REMOTE:-}" ]; then su frappe -c "cd $BENCH && bench set-config -g ph_backup_remote '$BACKUP_REMOTE'"; fi
MARK="$BENCH/sites/$SITE/.ph_cas_installed"
if [ -d "$BENCH/sites/$SITE" ] && [ ! -f "$MARK" ]; then
  echo "== removing half-installed site $SITE from an interrupted first run"
  su frappe -c "cd $BENCH && bench drop-site '$SITE' --db-root-password '$DBROOT' --force --no-backup" || rm -rf "$BENCH/sites/$SITE"
fi
if [ ! -d "$BENCH/sites/$SITE" ]; then
  echo "== new site $SITE"
  touch /run/ph_cas_installing
  su frappe -c "cd $BENCH && bench new-site '$SITE' --db-root-password '$DBROOT' --admin-password '$ADMIN' --install-app erpnext --install-app ph_cas --set-default"
  su frappe -c "cd $BENCH && bench --site '$SITE' set-config ph_cas_production ${PH_PRODUCTION:-0} && bench --site '$SITE' set-config encryption_key \"\$(openssl rand -base64 32)\" && bench --site '$SITE' enable-scheduler"
  if [ "${PH_DEMO:-0}" = 1 ]; then
    su frappe -c "cd $BENCH && bench --site '$SITE' set-config ph_demo_site 1"
    su frappe -c "cd $BENCH && bench --site '$SITE' execute ph_cas.demo.seed" || echo "demo seed failed (continuing)"
    ledger-site snapshot-demo "$SITE" || echo "golden snapshot failed (continuing)"
  fi
  if [ "$STAGING" = 1 ]; then
    echo "== staging: QA data"
    su frappe -c "cd $BENCH && bench --site '$SITE' set-config ph_staging_site 1"
    su frappe -c "cd $BENCH && bench --site '$SITE' execute ph_cas.qa.api.seed"
    ledger-site snapshot-demo "$SITE"
  fi
  touch "$MARK"; chown frappe:frappe "$MARK"
  rm -f /run/ph_cas_installing
elif [ "$STAGING" = 1 ] && [ -f "$BENCH/sites/$SITE/private/golden-database.sql.gz" ]; then
  echo "== staging: restore the QA data (anything added since the last start is gone)"
  ledger-site reset-staging "$SITE"
else
  su frappe -c "cd $BENCH && bench --site '$SITE' migrate"
  if [ "${PH_DEMO:-0}" = 1 ]; then
    su frappe -c "cd $BENCH && bench --site '$SITE' set-config ph_demo_site 1"
    su frappe -c "cd $BENCH && bench --site '$SITE' execute ph_cas.demo.seed" || echo "demo seed failed (continuing)"
    [ -f "$BENCH/sites/$SITE/private/golden-database.sql.gz" ] || ledger-site snapshot-demo "$SITE" || echo "golden snapshot failed (continuing)"
  fi
  su frappe -c "cd $BENCH && bench --site '$SITE' clear-cache" >/dev/null || true
fi

echo "== apply container configuration (email, admin mailbox, demo 2FA switch)"
su frappe -c "cd $BENCH && bench --site '$SITE' execute ph_cas.deploy_config.apply" || echo "deploy_config failed (continuing)"

# Client sites (created earlier with ledger-site) live in the same sites volume: migrate each and share email/branding.
for d in "$BENCH"/sites/*/; do
  s=$(basename "$d")
  [ "$s" = "$SITE" ] && continue
  [ -f "$d/site_config.json" ] || continue
  if [ ! -f "$d/.ph_cas_installed" ]; then echo "== skipping half-installed client site $s"; continue; fi
  echo "== client site $s: migrate"
  su frappe -c "cd $BENCH && bench --site '$s' migrate" || echo "migrate failed for $s (continuing)"
  su frappe -c "cd $BENCH && bench --site '$s' execute ph_cas.deploy_config.apply_shared" || echo "deploy_config failed for $s (continuing)"
done

echo "== serve on $PORT (nginx -> gunicorn 8001, socketio 9000)"
cd $BENCH
su frappe -c "cd $BENCH && bench set-config -g socketio_port 9000 && bench set-config -g webserver_port 8001" >/dev/null
DOMAIN_RE=$(printf '%s' "$CLIENT_DOMAIN" | sed 's/\./\\\\./g')
sed -e "s/__PORT__/$PORT/g" -e "s/__SITE__/$SITE/g" -e "s/__DOMAIN_RE__/$DOMAIN_RE/g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
nginx -t
su frappe -c "cd $BENCH && ./env/bin/gunicorn -b 127.0.0.1:8001 -w 2 -t 120 --chdir sites frappe.app:application" &
su frappe -c "cd $BENCH && node apps/frappe/socketio.js" &
nginx -g "daemon off;" &
su frappe -c "cd $BENCH && bench worker --queue short,default,long" &
su frappe -c "cd $BENCH && bench schedule" &
if [ "$STAGING" = 1 ]; then
  # The QA connector (ph_cas/qa/mcp_server.py). It checks PH_STAGING, the site config and the secret
  # itself and exits if any is wrong; the site keeps serving either way.
  # su keeps the environment (QA_MCP_SECRET, STAGING_ADMIN_PASSWORD), so no secret is on a command line.
  # If it stops, it sleeps instead of exiting, so `wait -n` below does not take the site down with it.
  ( su frappe -c "cd $BENCH && SITE_NAME='$SITE' ./env/bin/python -m ph_cas.qa.mcp_server" || { echo "QA connector stopped"; sleep infinity; } ) &
fi
if [ "${PH_DEMO:-0}" = 1 ] && [ "${DEMO_RESET:-1}" = 1 ]; then
  # Nightly reset of the open demo at DEMO_RESET_UTC_HOUR (default 18 UTC = 02:00 Manila).
  ( while true; do
      now=$(date -u +%H:%M)
      if [ "$now" = "$(printf '%02d:00' "${DEMO_RESET_UTC_HOUR:-18}")" ]; then
        echo "== nightly demo reset"; ledger-site reset-demo "$SITE" || echo "demo reset failed"; sleep 120
      fi
      sleep 50
    done ) &
fi
wait -n
exit 1
