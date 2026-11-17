# Runbook: upgrades and releases

Owner's method, 15 Nov 2026 (docs/DECISIONS.md, "Release method"), checked against RMO 9-2021 Sec. V.8 and V.9. Every release is recorded in `ph_cas/setup/data/releases.json` with its class (empty until the owner declares the product done; the first entry will be 1.0.0, class major); `ph_cas.ops.releases.check_log` and the tests refuse a log that breaks the rules below.

## The two kinds
| | Major | Minor |
|---|---|---|
| What it is | A new major version: the first number changes (1.x to 2.0.0). An ERPNext major version (v15 to v16) is always one. | A bug fix or a small field change (for example manual entry to a searchable dropdown) within the same major version. |
| What only it may do | Add or remove a module, change a function with financial effect, change the database framework, change the invoice face, the books or the files sent to the BIR (RMO 9-2021 V.8) | Nothing structural: no new module, no new database framework |
| Client | Told ahead; chooses whether to move; files an update of registration (a new application, registration pack from the Company form) with its RDO before using it | Nothing to file per release |
| Notice | The client's new application | One combined written notice per client per quarter, listing that quarter's minor releases (RMO 9-2021 V.9) |
| Enterprise | Same | Same |

When in doubt, it is major: a change that is not plainly a fix or a field change waits for the next major version.

## Where each version runs
All client sites in one container share one codebase, so each major version runs in its own container (a Dokploy app per major version, same image built from its own branch, `release/1`, `release/2`, and so on). Minor releases are merged into that version's branch and deploy to every site on it. A client moves to the next major version only after its update of registration is filed:
1. Take a backup of the site (`scripts/ops/backup_now.sh <site>`).
2. Restore it into the new version's container (`ledger-site restore <site> <backup>`), run `bench --site <site> migrate`, open one invoice print and the chain check.
3. Point the client's domain at the new container; keep the old site read-only until the new Acknowledgement Certificate is issued, then archive it with its backups for the retention period (ten years).

## Minor release, step by step
1. Fix on the version's branch; the full suite passes in CI.
2. Add the release to `releases.json`: next minor or patch number, date, `"class": "minor"`, a one-line summary and one line per change in plain words (these lines go into the client's notice).
3. Bump `ph_cas/__init__.py`, record it in docs/BUILD-LOG.md, merge; the version's container redeploys.

## Quarterly notice
In the first two weeks after each quarter (the firm's policy; RMO 9-2021 sets no deadline), for each client: Company > Sentire Ledger > Quarterly notice of minor enhancements, pick the quarter, have both parties sign, and send it to the client's RDO. A quarter without a minor release needs no notice (the button says so). Keep the signed copy with the client's registration file.

## Major release, step by step
1. Build on a new branch `release/<n>`; full suite, the owner's paper print check, the BIR golden files re-run (RELIEF, Alphalist).
2. Add the release to `releases.json` with `"class": "major"`, the platform it runs on and the summary; bump `ph_cas/__init__.py` to `<n>.0.0`.
3. Create the new version's Dokploy app; tell every client ahead with what changes; move each client that chooses to, as above, after it files.

## Rollback
`bench --site <site> --force restore <backup>` from the pre-upgrade backup, then `bench migrate`; the chain check must pass. Record the rollback in the event log (a restore is a settings change, so it is recorded) and list it in that quarter's notice.
