# Enterprise: the dedicated pair (B36)

Decision C3 (9 Nov 2026): Enterprise clients run on two servers dedicated to them, owned by MCRC (MCRC's Contabo account), so the software is never distributed and the client still gets their own machines, region and URL.

## Shape
| | Server 1, production | Server 2, standby |
|---|---|---|
| Where | Contabo VPS, Singapore (about 40 ms from Manila), 8 GB, 4 vCPU | Contabo VPS, another region (Japan or Germany), same size |
| Runs | Docker, the Sentire Ledger image (one container: MariaDB, Redis, nginx, gunicorn, workers), volumes `phcas-mysql` and `phcas-sites` | Docker, rclone, the nightly restore test, the UAT/training copy on port 8080 |
| Managed by | MCRC's Dokploy as a Remote Server (preferred), or its own Dokploy (`--own-dokploy`) | systemd timer `ledger-restore-test` |
| Backups | ph_cas daily encrypted backup to the client's bucket (`BACKUP_REMOTE`) | pulls the newest set every night and restores it into a fresh container |

## Provisioning
```
scripts/enterprise/provision-pair.sh acme 1.2.3.4 5.6.7.8            # ssh as root to both
```
Then: add server 1 as a Remote Server in MCRC's Dokploy, create the app from the image `ghcr.io/markchrc2025/ph-cas:latest` (published by the Image workflow on every push to main; the package is private, so add a read-only GitHub token as the registry credential), environment as the shared app plus `SITE_NAME=acme.sentireledger.com`, `PH_PRODUCTION=1`, `PH_DEMO=0`, `CLIENT_DOMAIN=acme.sentireledger.com`, `BACKUP_REMOTE` and the `RCLONE_CONFIG_*` variables for the client's bucket, the two volumes, and the domain with its A record. On server 2 edit `/etc/ledger-standby.env` (image, site, bucket, backup key, root and admin passwords, rclone variables) and run `systemctl start ledger-restore-test` once by hand; check `/srv/ledger/acme/restore-test.log` says OK.

Record both servers and the bucket on the client's PH Subscription; put the backup key in the escrow record (one copy with the client, one with MCRC).

## Nightly restore test
`standby-restore-test` fetches the newest manifest and `.enc` files, decrypts them with the site's backup key, starts a fresh container from the same image, restores database and files, runs migrate, and checks `/api/method/ping` and `ph_cas.ops.monitor.status`. The result line goes to the log; a FAIL line is the alert (hook the log into the monitoring of your choice). The restored copy stays up on port 8080 as the client's UAT and training site until the next run.

## Failover (manual, target under one hour)
1. Confirm server 1 is down for longer than the client tolerates (not a Dokploy redeploy in progress).
2. On server 2: `systemctl stop ledger-restore-test.timer`, then run `standby-restore-test` once to load the newest backup (or keep last night's copy if the bucket is unreachable). Set `PH_PRODUCTION=1` on the UAT container: `docker exec ledger-uat-acme su frappe -c "cd /home/frappe/bench && bench --site acme.sentireledger.com set-config ph_cas_production 1"`, and re-point port 8080 to 80/443 behind a reverse proxy (Caddy one-liner: `caddy reverse-proxy --from acme.sentireledger.com --to 127.0.0.1:8080`).
3. DNS: change the client's A record to server 2 (TTL 600 on all client records, set at onboarding).
4. Tell the client: data is as of the last backup (the time is in the log line); documents issued since then must be re-entered; BIR serials continue from the restored counters, so check the last printed serial against the BIR Series before the first new invoice.
5. Afterwards: rebuild server 1, restore from server 2's backup, switch back in a maintenance window, re-enable the timer.

## SLA
99.5 percent with this manual failover. 99.9 percent needs automatic failover (a floating IP or a load balancer with health checks, replicated MariaDB) and is priced separately.

## Costs
Two VPS at about 15 to 25 euros a month each plus the bucket; the Enterprise fee covers them. Cancel both servers on offboarding (docs/runbooks/offboarding.md) after the deletion certificate.
