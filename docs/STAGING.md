# Ledger staging

A separate copy of Sentire Ledger for testing work before it reaches the live site, on real screens with test data, and a QA connector that lets a Claude session drive it. The live site (ledger.sentire.solutions) and client sites are never touched.

## What it is

| Part | Where | Notes |
|---|---|---|
| Staging app | Dokploy, project "MCRC Tax and Accounting", app "Ledger Staging" | Deploys the `staging` branch with the same Dockerfile as the live site. |
| Web address | https://ledger-staging.apps.sentire.solutions | Sign in as the QA admin (below). |
| Database | MariaDB inside the staging container | No volumes: a redeploy starts from nothing. |
| QA connector | https://ledger-qa-mcp.apps.sentire.solutions/mcp/&lt;QA_MCP_SECRET&gt; | MCP server, staging only (ph_cas/qa/mcp_server.py). |
| Tutorial videos | The private bucket sentire-ledger-videos, read-only key | Videos uploaded on the live site play here too. |

The `staging` branch is `main` plus whatever is under test, combined with ordinary merges (never a force push). Nothing on it reaches `main` except through the normal PR of each change.

## Signing in

- Email: `qa.admin@sentire.solutions`
- Password: the value of `STAGING_ADMIN_PASSWORD` in the staging app's Environment tab in Dokploy. It is generated there and never written in chat or in the repo.
- Two-factor sign-in is off on staging.

## UAT (Sentire UAT Standard v1.0)

A separate UAT session tests each process with the workbook in docs/uat/<process>/ (see CLAUDE.md and docs/uat/UAT_STANDARD.md). For it the seed also adds (ph_cas/qa/uat.py):

| Account | Role set | Companies |
|---|---|---|
| mcrc.business.solutions+uat-owner-a@gmail.com | Owner | A, C, D |
| mcrc.business.solutions+uat-bookkeeper-a@gmail.com | Bookkeeper | A, C, D |
| mcrc.business.solutions+uat-cashier-a@gmail.com | Cashier | A |
| mcrc.business.solutions+uat-bookkeeper-b@gmail.com | Bookkeeper | B |

Companies: A Tala Trading Corporation (the demo company), B UAT Company B Corp. (the other tenant), C UAT Bagong Simula Corp. (fresh, go-live), D UAT Bagong Bukas Corp. (fresh, imports). The password of every UAT account is `STAGING_UAT_PASSWORD` (generated in Dokploy). `ph_cas.qa.uat.check_accounts` (System Manager) reports whether each signs in, without showing the password.

On staging every outgoing mail is sent to the test mailbox only (`STAGING_TEST_MAILBOX`, default mcrc.business.solutions@gmail.com), whoever it was addressed to; mails also stay listed under Email Queue. Outgoing mail needs `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM` in the staging app's Environment; without them mails stay in Email Queue unsent.

The build under test shows under Help > Your plan, Help > Get help and at `/api/method/ph_cas.qa.uat.build_info`. Do not deploy during a UAT run.

## Test data

On the container's first start the site is created and seeded (ph_cas.qa.api.seed): the demo VAT company with an invoice, a supplier bill and the quarter's 2550Q, every module switched on, and the QA admin with the System Manager, Accounting Manager and module roles. That state is kept as the QA snapshot.

**Reset:** restart the staging app in Dokploy. At every start the QA snapshot is restored (ledger-site reset-staging), so anything added by hand or by the connector is gone. A redeploy builds the site again from nothing. That is the point of staging.

More data on demand, through the connector's `seed_scenario`:

| Scenario | What it adds |
|---|---|
| `vat_quarter` | Three months of the current quarter: VATable, zero-rated and exempt sales (one customer a top withholding agent), and bills from a goods supplier and a law office with expanded withholding. The scenario lifts the posting-date lock for its own inserts only, on staging only, to write the history. |
| `non_vat_company` | A second company, QA Corner Store, non-VAT, with two sales (for the 2551Q). |

## Full pass (QA pass 4)

`call_method` with `ph_cas.qa.fullpass.run` and `{"section": ...}` runs one section of the whole-product pass as the QA admin and returns each step with ok or FAIL: companies, purchasing, sales, tasks, inventory, inventory_tracking, projects, assets, quality, crm, support, industries, roles, forms, reports (in that order; later sections use what earlier ones made). Seed `vat_quarter`, `income_year`, `non_vat_company` and `individual_year` first so the forms have history.

## The QA connector

An MCP server inside the staging container (port 8010). It signs in as the QA admin and calls the site's own HTTP API, so validation, permissions, BIR serials, approval chains and every Annex B control apply as for a person. It has no database access of its own.

Tools: `staging_status`, `list_documents`, `get_document`, `create_document`, `update_document`, `submit_document`, `cancel_document`, `call_method`, `run_report`, `get_print`, `seed_scenario`, `api_request` (any `/api/...` call except sign-in, sign-out and password endpoints).

`get_print` goes through the print page, as the Print button does, so each call is a print (the second one says REPRINT). With `preview: true` it renders the on-screen preview of the desk's Print page, which records nothing.

Safety, the same pattern as the Payroll QA connector:

- The URL is the key: `/mcp/<QA_MCP_SECRET>`. A wrong key or any other path is a 404. The secret is generated in Dokploy and must be at least 32 characters, or the connector does not start.
- It refuses to start unless `PH_STAGING=1`, `PH_PRODUCTION` is not 1, and the site config says `ph_staging_site: 1` (set only by the staging start). The entrypoint also refuses `PH_STAGING=1` together with `PH_PRODUCTION=1` or `PH_DEMO=1`.
- 120 calls a minute; one JSON audit line per call in the staging app's logs.
- If the connector stops, the site keeps running.

To add it to Claude: Settings, Connectors, add a custom connector with the URL above, taking the secret from the staging app's Environment tab.

## Environment (staging app only)

| Variable | Value |
|---|---|
| `PH_STAGING` | `1` |
| `PH_PRODUCTION`, `PH_DEMO`, `PH_2FA` | `0` |
| `PORT` | `8000` |
| `QA_MCP_PORT` | `8010` |
| `SITE_NAME` | `ledger-staging.apps.sentire.solutions` |
| `PRODUCT_NAME`, `PROVIDER_NAME` | as on the live site |
| `DB_ROOT_PASSWORD`, `ADMIN_PASSWORD`, `STAGING_ADMIN_PASSWORD`, `QA_MCP_SECRET` | generated in Dokploy |
| `PH_VIDEOS_S3_*` | read-only key for sentire-ledger-videos (grant_storage) |

Email is deliberately absent; mails stay unsent on staging.

## Putting a change under test

1. Open the change's PR against `main` as usual.
2. Merge the PR's branch into `staging` (`git checkout staging && git merge <branch> && git push`). Dokploy deploys it; the site is rebuilt from nothing (about 10 minutes).
3. Test through the QA connector or the screens.
4. Merge the PR into `main` once it passes. When `main` moves on, merge `main` into `staging`.
