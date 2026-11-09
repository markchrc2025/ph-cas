#!/usr/bin/env bash
# provision-pair.sh: prepare the two servers of an Enterprise client (B36).
#
#   scripts/enterprise/provision-pair.sh <client> <prod-ip> <standby-ip> [ssh-user]
#
# Both servers: Ubuntu 24.04 VPS (Contabo, Singapore and a second region), 8 GB, 4 vCPU, in
# MCRC's Contabo account, dedicated to this client. Run from an operator machine that can
# ssh to both as root (or a sudo user). What it does:
#   production  : updates, ufw (22, 80, 443), fail2ban, Docker, swap 4 GB, unattended upgrades,
#                 then prints the command to add it as a Remote Server in MCRC's Dokploy
#                 (or installs Dokploy locally with --own-dokploy).
#   standby     : updates, ufw (22 only, plus 80/443 for failover), Docker, swap, rclone,
#                 the restore-test timer (standby-restore-test.sh) and the UAT site folder.
set -euo pipefail
CLIENT="${1:?client slug}"; PROD="${2:?production ip}"; STANDBY="${3:?standby ip}"; USER="${4:-root}"
OWN_DOKPLOY=0; [ "${5:-}" = "--own-dokploy" ] && OWN_DOKPLOY=1
HERE=$(cd "$(dirname "$0")" && pwd)

common() {
  ssh -o StrictHostKeyChecking=accept-new "$USER@$1" bash -s <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq ufw fail2ban unattended-upgrades curl rclone ca-certificates gnupg
if ! swapon --show | grep -q swapfile; then fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab; fi
if ! command -v docker >/dev/null; then curl -fsSL https://get.docker.com | sh; fi
systemctl enable --now docker fail2ban unattended-upgrades >/dev/null 2>&1 || true
ufw default deny incoming >/dev/null; ufw default allow outgoing >/dev/null
ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
timedatectl set-timezone Asia/Manila
echo "prepared $(hostname) $(docker --version)"
REMOTE
}

echo "== production $PROD"; common "$PROD"
if [ "$OWN_DOKPLOY" = 1 ]; then
  ssh "$USER@$PROD" 'curl -sSL https://dokploy.com/install.sh | sh'
  echo "Dokploy installed on $PROD: open http://$PROD:3000, create the admin, add the GitHub source, deploy the Sentire Ledger app with SITE_NAME=$CLIENT.<client domain>, PH_PRODUCTION=1, PH_DEMO=0, volumes phcas-mysql and phcas-sites, BACKUP_REMOTE to the client's bucket."
else
  echo "Add $PROD as a Remote Server in MCRC's Dokploy (Settings > Remote Servers, SSH key), then deploy the Sentire Ledger app to it with SITE_NAME=$CLIENT.<client domain>, PH_PRODUCTION=1, PH_DEMO=0, volumes phcas-mysql and phcas-sites, BACKUP_REMOTE to the client's bucket."
fi

echo "== standby $STANDBY"; common "$STANDBY"
scp -q "$HERE/standby-restore-test.sh" "$USER@$STANDBY:/usr/local/bin/standby-restore-test"
ssh "$USER@$STANDBY" bash -s "$CLIENT" <<'REMOTE'
set -euo pipefail
CLIENT="$1"
chmod +x /usr/local/bin/standby-restore-test
mkdir -p /srv/ledger/$CLIENT/{backups,restore}
cat > /etc/systemd/system/ledger-restore-test.service <<EOS
[Unit]
Description=Sentire Ledger standby restore test ($CLIENT)
[Service]
Type=oneshot
EnvironmentFile=/etc/ledger-standby.env
ExecStart=/usr/local/bin/standby-restore-test
EOS
cat > /etc/systemd/system/ledger-restore-test.timer <<EOS
[Unit]
Description=Nightly restore test
[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
[Install]
WantedBy=timers.target
EOS
[ -f /etc/ledger-standby.env ] || cat > /etc/ledger-standby.env <<EOS
CLIENT=$CLIENT
SITE_NAME=$CLIENT.example.com
IMAGE=ghcr.io/markchrc2025/ph-cas:latest
BACKUP_REMOTE=s3:ledger-backups
BACKUP_KEY=paste-the-site-backup-key-here
DB_ROOT_PASSWORD=change-me
ADMIN_PASSWORD=change-me
RCLONE_CONFIG_S3_TYPE=s3
RCLONE_CONFIG_S3_PROVIDER=Other
RCLONE_CONFIG_S3_ENDPOINT=
RCLONE_CONFIG_S3_ACCESS_KEY_ID=
RCLONE_CONFIG_S3_SECRET_ACCESS_KEY=
EOS
chmod 600 /etc/ledger-standby.env
systemctl daemon-reload && systemctl enable --now ledger-restore-test.timer >/dev/null
echo "standby ready; edit /etc/ledger-standby.env (image, site, bucket, key) then: systemctl start ledger-restore-test"
REMOTE
echo "== done. Record both servers on the client's PH Subscription (Servers field) and put the backup key in the escrow record."
