#!/usr/bin/env bash
# Runs as root: starts MariaDB and Redis, then the bench as the frappe user.
# Env: SITE_NAME (required), DB_ROOT_PASSWORD, ADMIN_PASSWORD (secrets), PORT (8000),
#      PH_PRODUCTION (0 = demo site that applies draft rules; 1 = production), PH_DEMO (1 = seed demo data once).
set -euo pipefail
trap 'echo "entrypoint failed at line $LINENO: $BASH_COMMAND" >&2' ERR
SITE="${SITE_NAME:?SITE_NAME is required}"
PORT="${PORT:-8000}"
DBROOT="${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is required}"
ADMIN="${ADMIN_PASSWORD:?ADMIN_PASSWORD is required}"
BENCH=/home/frappe/bench

echo "== MariaDB"
if [ ! -d /var/lib/mysql/mysql ]; then
  mariadb-install-db --user=mysql --datadir=/var/lib/mysql >/dev/null
  FRESH_DB=1
fi
chown -R mysql:mysql /var/lib/mysql
(mysqld_safe --user=mysql >/var/log/mysqld.log 2>&1 &)
for i in $(seq 1 60); do mysqladmin ping --silent 2>/dev/null && break; sleep 1; done
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
    su frappe -c "cd $BENCH && bench --site '$SITE' execute ph_cas.demo.seed" || echo "demo seed failed (continuing)"
  fi
  touch "$MARK"; chown frappe:frappe "$MARK"
  rm -f /run/ph_cas_installing
else
  su frappe -c "cd $BENCH && bench --site '$SITE' migrate"
  if [ "${PH_DEMO:-0}" = 1 ]; then
    su frappe -c "cd $BENCH && bench --site '$SITE' execute ph_cas.demo.seed" || echo "demo seed failed (continuing)"
  fi
fi

echo "== apply container configuration (email, admin mailbox, demo 2FA switch)"
su frappe -c "cd $BENCH && bench --site '$SITE' execute ph_cas.deploy_config.apply" || echo "deploy_config failed (continuing)"

echo "== serve on $PORT (nginx -> gunicorn 8001, socketio 9000)"
cd $BENCH
su frappe -c "cd $BENCH && bench set-config -g socketio_port 9000 && bench set-config -g webserver_port 8001" >/dev/null
sed -e "s/__PORT__/$PORT/g" -e "s/__SITE__/$SITE/g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
nginx -t
su frappe -c "cd $BENCH && ./env/bin/gunicorn -b 127.0.0.1:8001 -w 2 -t 120 --chdir sites frappe.app:application" &
su frappe -c "cd $BENCH && node apps/frappe/socketio.js" &
nginx -g "daemon off;" &
su frappe -c "cd $BENCH && bench --site '$SITE' worker --queue short,default,long" &
su frappe -c "cd $BENCH && bench schedule" &
wait -n
exit 1
