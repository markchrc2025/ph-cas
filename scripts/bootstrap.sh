#!/usr/bin/env bash
# ph_cas bootstrap: pinned ERPNext v16 bench with ph_cas installed.
# Usage: scripts/bootstrap.sh [bench_dir]   (env: SKIP_ASSETS=1, SITE=test_site)
set -euo pipefail
BENCH_DIR="${1:-$HOME/ph-cas-bench}"
SITE="${SITE:-test_site}"
FRAPPE_TAG="${FRAPPE_TAG:-v16.55.2}"
ERPNEXT_TAG="${ERPNEXT_TAG:-v16.54.0}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-root}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

echo "== system packages (Debian or Ubuntu; skip elsewhere)"
if command -v apt-get >/dev/null && [ "${SKIP_APT:-0}" != 1 ]; then
  SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"
  $SUDO apt-get install -y -q libmariadb-dev libmariadb-dev-compat pkg-config build-essential \
    libffi-dev libssl-dev redis-server >/dev/null 2>&1 || echo "apt step skipped (no rights); install libmariadb-dev and pkg-config by hand"
fi
if [ "$(id -u)" = 0 ]; then echo "bench refuses to run as root; run this script as an ordinary user"; exit 1; fi

echo "== Python 3.14 via uv"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.14 >/dev/null
PY=$(uv python find 3.14)

echo "== Node 24"
if ! node --version 2>/dev/null | grep -q '^v24'; then
  NODE_DIR="$HOME/.local/node24"
  if [ ! -x "$NODE_DIR/node_modules/node/bin/node" ]; then
    mkdir -p "$NODE_DIR"
    # The npm registry hosts the Node binaries; nodejs.org is not always reachable.
    npm install --prefix "$NODE_DIR" node@24 >/dev/null
  fi
  export PATH="$NODE_DIR/node_modules/node/bin:$NODE_DIR/node_modules/.bin:$PATH"
fi
node --version
corepack enable >/dev/null 2>&1 || true
command -v yarn >/dev/null || npm install -g yarn >/dev/null

echo "== bench CLI"
uv tool install --python "$PY" frappe-bench >/dev/null 2>&1 || uv tool upgrade frappe-bench >/dev/null
export PATH="$HOME/.local/bin:$PATH"

echo "== bench init ($FRAPPE_TAG)"
if [ ! -d "$BENCH_DIR" ]; then
  bench init "$BENCH_DIR" --python "$PY" --frappe-branch "$FRAPPE_TAG" ${SKIP_ASSETS:+--skip-assets} --no-backups
fi
cd "$BENCH_DIR"
# Use the system Redis (bench start would run its own on 11000 and 13000)
REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379}"
bench set-config -g redis_cache "$REDIS_URL" >/dev/null
bench set-config -g redis_queue "$REDIS_URL" >/dev/null
bench set-config -g redis_socketio "$REDIS_URL" >/dev/null
[ -d apps/erpnext ] || bench get-app erpnext https://github.com/frappe/erpnext --branch "$ERPNEXT_TAG" ${SKIP_ASSETS:+--skip-assets}
[ -d apps/ph_cas ] || bench get-app ph_cas "$APP_DIR" ${SKIP_ASSETS:+--skip-assets}

echo "== site $SITE"
if [ ! -d "sites/$SITE" ]; then
  bench new-site "$SITE" --db-root-password "$DB_ROOT_PASSWORD" --admin-password "$ADMIN_PASSWORD" --install-app erpnext --install-app ph_cas
else
  bench --site "$SITE" install-app erpnext ph_cas 2>/dev/null || true
  bench --site "$SITE" migrate
fi
bench --site "$SITE" set-config developer_mode 1
echo "== done: $BENCH_DIR, site $SITE (Administrator / $ADMIN_PASSWORD)"
