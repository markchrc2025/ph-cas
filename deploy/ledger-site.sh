#!/usr/bin/env bash
# ledger-site: manage client sites inside the Sentire Ledger container (run as root from the
# Dokploy terminal: `ledger-site <command>`). Each client is one Frappe site, its own database.
#
#   ledger-site new <name> --tier Solo|Team|Business|Enterprise [--pilot DAYS] [--demo]
#       creates <name>.$CLIENT_DOMAIN (or a full hostname if <name> contains a dot), production
#       flags on (pilot and demo sites stay in demo mode), backup key generated, tier limits set.
#       Prints the Administrator password once. Store it in the client record, nowhere else.
#   ledger-site set-tier <site> <tier> [--until YYYY-MM-DD] [--max-users N] [--max-branches N] [--max-companies N] [--invoices N]
#   ledger-site usage <site>          what the site uses against its limits
#   ledger-site list                  every site with tier, paid-until and pilot-until
#   ledger-site backup <site>         encrypted backup now (and off-site copy if BACKUP_REMOTE is set)
#   ledger-site password <site>       reset the Administrator password (prints the new one once)
#   ledger-site drop <site> --yes     drop a site after export (see docs/runbooks/offboarding.md)
#   ledger-site offboard <site>       export everything the client takes away (zip under sites/<site>/private/offboarding)
#   ledger-site certificate <site> "<client>" [--signatory NAME --position POS --accepted YYYY-MM-DD]
#                                     print the deletion certificate text after `drop`
#   ledger-site report                usage of every site as CSV (for the PH Subscription records on MCRC's site)
#   ledger-site snapshot-demo <site>  take the golden snapshot of a demo site (done once after the seed)
#   ledger-site reset-demo <site>     restore the golden snapshot and re-issue access to still-valid demo users
set -euo pipefail
BENCH=/home/frappe/bench
DOMAIN="${CLIENT_DOMAIN:-${SITE_NAME:-}}"
DBROOT="${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is required}"

as_frappe() { su frappe -c "cd $BENCH && $*"; }
site_of() { case "$1" in *.*) echo "$1" ;; *) echo "$1.$DOMAIN" ;; esac; }
rand() { openssl rand -base64 24 | tr -d '/+=' | cut -c1-20; }

cmd="${1:-}"; shift || true
case "$cmd" in
  new)
    NAME="${1:?site name}"; shift
    TIER="Team"; PILOT=""; DEMO=0
    while [ $# -gt 0 ]; do
      case "$1" in
        --tier) TIER="$2"; shift 2 ;;
        --pilot) PILOT="$2"; shift 2 ;;
        --demo) DEMO=1; shift ;;
        *) echo "unknown option $1"; exit 2 ;;
      esac
    done
    SITE=$(site_of "$NAME")
    [ -d "$BENCH/sites/$SITE" ] && { echo "site $SITE already exists"; exit 1; }
    ADMIN=$(rand); KEY=$(openssl rand -base64 32)
    echo "== creating $SITE (tier $TIER${PILOT:+, pilot $PILOT days}${DEMO:+, demo})"
    as_frappe "bench new-site '$SITE' --db-root-password '$DBROOT' --admin-password '$ADMIN' --install-app erpnext --install-app ph_cas"
    PROD=1; [ -n "$PILOT" ] && PROD=0; [ "$DEMO" = 1 ] && PROD=0
    as_frappe "bench --site '$SITE' set-config ph_cas_production $PROD"
    as_frappe "bench --site '$SITE' set-config ph_backup_key '$KEY'"
    as_frappe "bench --site '$SITE' set-config keep_backups_for_hours 87600"
    as_frappe "bench --site '$SITE' set-config encryption_key \"\$(openssl rand -base64 32)\""
    as_frappe "bench --site '$SITE' enable-scheduler"
    UNTIL=""; [ -n "$PILOT" ] && UNTIL=$(date -u -d "+$PILOT days" +%F)
    as_frappe "bench --site '$SITE' execute ph_cas.hosting.tiers.set_tier --kwargs \"{'tier': '$TIER', 'pilot_until': '$UNTIL'}\"" >/dev/null
    [ "$DEMO" = 1 ] && as_frappe "bench --site '$SITE' execute ph_cas.demo.seed" >/dev/null
    as_frappe "bench --site '$SITE' execute ph_cas.deploy_config.apply_shared" >/dev/null || true
    touch "$BENCH/sites/$SITE/.ph_cas_installed"; chown frappe:frappe "$BENCH/sites/$SITE/.ph_cas_installed"
    echo "== $SITE ready"
    echo "   URL:            https://$SITE"
    echo "   Administrator:  $ADMIN   (shown once; store it in the client record)"
    echo "   Backup key:     stored in site_config (ph_backup_key); copy it to the key escrow now:"
    echo "   $KEY"
    echo "   Next: sign in, run Set up Philippine company, enter the BIR Series ranges, invite users (docs/runbooks/onboarding.md)."
    ;;
  set-tier)
    SITE=$(site_of "${1:?site}"); TIER="${2:?tier}"; shift 2
    KW="'tier': '$TIER'"
    while [ $# -gt 0 ]; do
      case "$1" in
        --until) KW="$KW, 'subscription_until': '$2'"; shift 2 ;;
        --max-users) KW="$KW, 'max_users': $2"; shift 2 ;;
        --max-branches) KW="$KW, 'max_branches': $2"; shift 2 ;;
        --max-companies) KW="$KW, 'max_companies': $2"; shift 2 ;;
        --invoices) KW="$KW, 'monthly_invoice_limit': $2"; shift 2 ;;
        *) echo "unknown option $1"; exit 2 ;;
      esac
    done
    as_frappe "bench --site '$SITE' execute ph_cas.hosting.tiers.set_tier --kwargs \"{$KW}\""
    ;;
  usage)
    SITE=$(site_of "${1:?site}")
    as_frappe "bench --site '$SITE' execute ph_cas.hosting.tiers.usage"
    ;;
  list)
    for d in "$BENCH"/sites/*/; do
      s=$(basename "$d"); [ -f "$d/site_config.json" ] || continue
      printf '%-45s ' "$s"
      as_frappe "bench --site '$s' execute ph_cas.hosting.tiers.limits" 2>/dev/null | tail -1 || echo
    done
    ;;
  backup)
    SITE=$(site_of "${1:?site}")
    as_frappe "bench --site '$SITE' execute ph_cas.ops.backup.run_backup"
    ;;
  password)
    SITE=$(site_of "${1:?site}"); NEW=$(rand)
    as_frappe "bench --site '$SITE' set-admin-password '$NEW'" >/dev/null
    echo "Administrator password for $SITE: $NEW (shown once)"
    ;;
  drop)
    SITE=$(site_of "${1:?site}"); [ "${2:-}" = "--yes" ] || { echo "add --yes after exporting (docs/runbooks/offboarding.md)"; exit 2; }
    as_frappe "bench drop-site '$SITE' --db-root-password '$DBROOT' --force --no-backup"
    echo "dropped $SITE"
    ;;
  offboard)
    SITE=$(site_of "${1:?site}")
    OUT=$(as_frappe "bench --site '$SITE' execute ph_cas.hosting.offboard.export_site" | tail -1)
    DIR=$(python3 -c "import ast,sys; print(ast.literal_eval(sys.argv[1])['target'])" "$OUT" 2>/dev/null || echo "")
    [ -n "$DIR" ] && [ -d "$DIR" ] || { echo "export failed: $OUT"; exit 1; }
    ( cd "$(dirname "$DIR")" && tar -czf "$(basename "$DIR").tar.gz" "$(basename "$DIR")" && sha256sum "$(basename "$DIR").tar.gz" > "$(basename "$DIR").tar.gz.sha256" )
    chown -R frappe:frappe "$(dirname "$DIR")"
    echo "export: $DIR.tar.gz"; cat "$DIR.tar.gz.sha256"
    echo "Deliver the archive and its sha256 to the client, record 'Export delivered' on the PH Subscription, wait for acceptance, then: ledger-site drop $SITE --yes"
    ;;
  certificate)
    SITE=$(site_of "${1:?site}"); CLIENT="${2:?client name}"; shift 2
    SIGN=""; POS=""; ACC=""
    while [ $# -gt 0 ]; do case "$1" in --signatory) SIGN="$2"; shift 2;; --position) POS="$2"; shift 2;; --accepted) ACC="$2"; shift 2;; *) shift;; esac; done
    as_frappe "bench --site '${SITE_NAME:?}' execute ph_cas.hosting.offboard.deletion_certificate --kwargs "{'site': '$SITE', 'client': '$CLIENT', 'provider': '${PROVIDER_NAME:-MCRC Tax and Accounting Services}', 'export_accepted_on': '$ACC', 'signatory': '$SIGN', 'position': '$POS'}""
    ;;
  report)
    echo "site,tier,users,max_users,companies,max_companies,branches,max_branches,invoices_this_month,monthly_invoice_limit,subscription_until,pilot_until"
    for d in "$BENCH"/sites/*/; do
      s=$(basename "$d"); [ -f "$d/site_config.json" ] || continue
      as_frappe "bench --site '$s' execute ph_cas.hosting.tiers.usage" 2>/dev/null | tail -1 | python3 -c "
import ast,sys; u=ast.literal_eval(sys.stdin.read().strip()); print(','.join(str(u.get(k,'')) for k in ['site' if False else 'tier','users','max_users','companies','max_companies','branches','max_branches','invoices_this_month','monthly_invoice_limit','subscription_until','pilot_until']))" | sed "s/^/$s,/"
    done
    ;;
  snapshot-demo)
    SITE=$(site_of "${1:?site}")
    as_frappe "bench --site '$SITE' backup" >/dev/null
    LATEST=$(ls -t "$BENCH/sites/$SITE/private/backups/"*-database.sql.gz | head -1)
    cp "$LATEST" "$BENCH/sites/$SITE/private/golden-database.sql.gz"; chown frappe:frappe "$BENCH/sites/$SITE/private/golden-database.sql.gz"
    echo "golden snapshot: $BENCH/sites/$SITE/private/golden-database.sql.gz"
    ;;
  reset-demo)
    SITE=$(site_of "${1:?site}")
    GOLD="$BENCH/sites/$SITE/private/golden-database.sql.gz"
    [ -f "$GOLD" ] || { echo "no golden snapshot for $SITE; run ledger-site snapshot-demo first"; exit 1; }
    as_frappe "bench --site '$SITE' --force restore '$GOLD' --db-root-password '$DBROOT'" >/dev/null
    as_frappe "bench --site '$SITE' migrate" >/dev/null
    as_frappe "bench --site '$SITE' execute ph_cas.deploy_config.apply" >/dev/null || true
    as_frappe "bench --site '$SITE' execute ph_cas.hosting.demo_access.recreate_active_users"
    as_frappe "bench --site '$SITE' clear-cache" >/dev/null
    echo "demo $SITE reset from golden snapshot"
    ;;
  *)
    sed -n '2,21p' "$0"; exit 2 ;;
esac
