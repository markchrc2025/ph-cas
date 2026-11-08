# Runbook: upgrades

Every client's CAS registration names the software and version. An upgrade is either minor (a written notice to the RDO) or major (a new application), per RMO 9-2021 and the RDO's answer to question 4.

## Minor (patch releases of ph_cas; ERPNext and Frappe patch releases within v16)
1. Read the release notes of the new ERPNext and Frappe tags; stop if a change touches posting, deletion, numbering, printing or the ledger (that makes it major).
2. On the staging bench: `bench get-app` at the new tags, `bench update --patch`, run `bench --site test_site run-tests --app ph_cas`. All green or stop.
3. Change VERSIONS.md and docs/BUILD-LOG.md (old and new pins) in a PR; CI must pass.
4. Take a backup of every client site (`scripts/ops/backup_now.sh <site>`), then upgrade production during the announced window; `bench migrate` each site; open one invoice print and the chain check on each.
5. Send the RDO the notice letter (template: docs/runbooks/notice-of-minor-enhancement.md) for each client, naming the old and new versions.

## Major (a new ERPNext major version, or any change to the controls, books, invoice face or files)
1. Treat as a new product release: the full suite, the owner's paper print check, golden files re-run.
2. A new application per client (registration pack from the Company form), filed before the switch; keep the old version running until the new AC is issued.
3. Keep the old version's backups for the retention period; the e-books of past years are regenerated from the old version if asked.

## Rollback
`bench --site <site> --force restore <backup>` from the pre-upgrade backup, then `bench migrate`; the chain check must pass. Record the rollback in the event log (it is, automatically, as a restore is a settings change) and tell the RDO if a notice was already sent.
