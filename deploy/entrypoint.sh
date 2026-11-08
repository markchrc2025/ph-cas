#!/usr/bin/env bash
# Runs as root: starts MariaDB and Redis, then the bench as the frappe user.
# Env: SITE_NAME (required), DB_ROOT_PASSWORD, ADMIN_PASSWORD (secrets), PORT (8000),
#      PH_PRODUCTION (0 = demo site that applies draft rules; 1 = production), PH_DEMO (1 = seed demo data once).
set -euo pipefail
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
if [ "${FRESH_DB:-0}" = 1 ]; then
  mysql -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('${DBROOT}'); FLUSH PRIVILEGES;"
fi

echo "== Redis"
(redis-server --daemonize yes --save 60 1 --dir /var/lib/redis >/dev/null 2>&1 || redis-server --daemonize yes >/dev/null)

echo "== bench"
chown -R frappe:frappe "$BENCH/sites"
su frappe -c "cd $BENCH && bench set-config -g db_host 127.0.0.1 && bench set-config -g redis_cache redis://127.0.0.1:6379 && bench set-config -g redis_queue redis://127.0.0.1:6379 && bench set-config -g redis_socketio redis://127.0.0.1:6379 && bench set-config -g default_site '$SITE' && bench set-config -g serve_default_site true && bench set-config -g webserver_port $PORT" >/dev/null
if [ ! -d "$BENCH/sites/$SITE" ]; then
  echo "== new site $SITE"
  su frappe -c "cd $BENCH && bench new-site '$SITE' --db-root-password '$DBROOT' --admin-password '$ADMIN' --install-app erpnext --install-app ph_cas --set-default"
  su frappe -c "cd $BENCH && bench --site '$SITE' set-config ph_cas_production ${PH_PRODUCTION:-0} && bench --site '$SITE' set-config encryption_key \"\$(openssl rand -base64 32)\" && bench --site '$SITE' enable-scheduler"
  if [ "${PH_DEMO:-0}" = 1 ]; then
    su frappe -c "cd $BENCH && bench --site '$SITE' execute ph_cas.demo.seed" || echo "demo seed failed (continuing)"
  fi
else
  su frappe -c "cd $BENCH && bench --site '$SITE' migrate"
fi

echo "== serve on $PORT"
cd $BENCH
su frappe -c "cd $BENCH && ./env/bin/gunicorn -b 0.0.0.0:$PORT -w 2 -t 120 --chdir sites frappe.app:application" &
su frappe -c "cd $BENCH && bench --site '$SITE' worker --queue short,default,long" &
su frappe -c "cd $BENCH && bench schedule" &
wait -n
exit 1
