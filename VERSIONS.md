# Pinned versions

| Component | Pin | Recorded |
|---|---|---|
| Sentire Ledger (ph_cas) | 0.1.0 (pre-release) | Not versioned until the owner says the product is done; then 1.0.0, the first release for registration (ph_cas/setup/data/releases.json) |
| Frappe | v16.60.2 | 20 Nov 2026 (latest v16 tag that day; carries a security fix; was v16.55.2) |
| ERPNext | v16.60.0 | 20 Nov 2026 (latest v16 tag that day; was v16.54.0) |
| Python | 3.14 (uv) | Frappe v16 requires >=3.14,<3.15 |
| Node | 24 | Frappe v16 requires >=24 |
| MariaDB | 10.11 or later | utf8mb4, see scripts/bootstrap.sh |

Change a pin only through a bundle that re-runs the full suite; record the old and new pin in docs/BUILD-LOG.md.
