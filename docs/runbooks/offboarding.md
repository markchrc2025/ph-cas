# Offboarding a client (B35)

Applies to every tier. The record of each step is the client's PH Subscription on MCRC's own site; the tooling runs in the client's container (`ledger-site`).

## Timeline
| Day | Step | Record |
|---|---|---|
| 0 | Notice received (60 days; 30 for Solo). Service continues to the end of the paid period. | Status: Notice given; Notice received, Service ends |
| before end | Final period closed by the client, year-end pack produced for the last year (Books workspace, Year-end pack). | |
| end of service | `ledger-site offboard <site>`: database and files backup, books of every company and year, registration packs, full audit trail and print records, registers with BIR serials, EXPORT-MANIFEST.json with SHA-256 of every file, README. The command prints the archive path and its hash. | |
| same day | Deliver the archive and the hash on a link valid 30 days (or on media for Enterprise). Written confirmation requested. | Export delivered |
| client confirms | Client accepts the export. | Export accepted |
| same week | Client notifies its RDO of the change of accounting system or provider (the sworn statement names the provider). Remind in writing; keep MCRC's copy of the registration pack and audit trail extracts for the professional liability period. | Client notified RDO |
| termination date | Licence to the Sentire Ledger name and marks ends. | Brand licence ended |
| within 30 days of acceptance | `ledger-site drop <site> --yes`, delete the off-site backups of that site, destroy the backup key (remove it from the escrow record). Enterprise: wipe and cancel both servers. | Site and backups deleted |
| same day | `ledger-site certificate <site> "<client>" --signatory "<name>" --position "<position>" --accepted <date>`, sign, send; attach to the record. | Deletion certificate; Status: Ended |

## Pilot that does not convert
The daily job disables the pilot's users 30 days after `pilot_until`. Run `ledger-site offboard` only if the client asks for their test data; otherwise `ledger-site drop <site> --yes` and send the deletion confirmation. Record Ended with the drop date.

## Non-payment
Paid until passes without renewal: status Suspended after 15 days (users disabled with `ledger-site set-tier <site> <tier> --max-users 0` is not enough; disable from the site as Administrator or wait for the provider to run `bench --site <site> set-maintenance-mode on`). Data is kept 90 days, then the offboarding steps above apply with the export delivered on request.

## What MCRC keeps
Registration pack and audit trail extracts of the client (04_audit of the export) for the professional liability period; the signed deletion certificate; the subscription record. Nothing else.
