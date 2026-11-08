#!/usr/bin/env bash
# backup_now.sh <site>: database and files, encrypted, uploaded, manifest written.
set -euo pipefail
bench --site "$1" execute ph_cas.ops.backup.run_backup
