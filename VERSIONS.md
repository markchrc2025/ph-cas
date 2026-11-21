# Pinned versions

| Component | Pin | Recorded |
|---|---|---|
| Sentire Ledger (ph_cas) | 0.1.0 (pre-release) | Not versioned until the owner says the product is done; then 1.0.0, the first release for registration (ph_cas/setup/data/releases.json) |
| Sentire Framework | v16.60.2-sentire.1 (branch release/v16.60.2-sentire.1, commit 0e53f54d) | 21 Nov 2026 (B81): Sentire's own framework, github.com/markchrc2025/sentire-framework |
| Based on Frappe | v16.60.2 | upstream tag Sentire Framework is based on (was plain Frappe v16.60.2 in B80) |
| bench CLI | 5.31.1 | pinned in B81: it renames the cloned sentire-framework folder to apps/frappe |
| ERPNext | v16.60.0 | 20 Nov 2026 (latest v16 tag that day; was v16.54.0) |
| Python | 3.14 (uv) | Frappe v16 requires >=3.14,<3.15 |
| Node | 24 | Frappe v16 requires >=24 |
| MariaDB | 10.11 or later | utf8mb4, see scripts/bootstrap.sh |

Change a pin only through a bundle that re-runs the full suite; record the old and new pin in docs/BUILD-LOG.md.
