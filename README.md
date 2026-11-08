# ph_cas

A Frappe app that makes ERPNext v16 a BIR-registrable computerized accounting system (CAS) for Philippine micro and small taxpayers, built and hosted by MCRC.

- Start here: `docs/BUILD-LOG.md` (what each bundle built and assumed), `docs/CONFORMANCE.md` (RMC 5-2021 Annex B, item by item), `docs/DECISIONS.md`.
- Build plan and bundles: `docs/reference/cas-build-bundles.md`; the rules: `docs/reference/ph-tax-rules-catalogue.md`.
- Run it: `scripts/bootstrap.sh` (not as root) builds a bench at the pinned tags in `VERSIONS.md` with a test site. Tests: `bench --site test_site run-tests --app ph_cas`.
- Operate it: `docs/runbooks/` and `scripts/ops/`; users: `docs/user-guide.md`.
- Tax rules are data and stay draft until the CPA's sign-off (`bench --site <site> ph-cas-sign-off <file>`); a production site (`ph_cas_production: 1`) refuses draft rules.
- Never commit BIR installers or real taxpayer data.
