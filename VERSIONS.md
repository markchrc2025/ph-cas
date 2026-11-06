# Pinned versions

| Component | Pin | Recorded |
|---|---|---|
| Frappe | v16.55.2 | 6 Nov 2026 (latest v16 tag that day) |
| ERPNext | v16.54.0 | 6 Nov 2026 (latest v16 tag that day) |
| Python | 3.14 (uv) | Frappe v16 requires >=3.14,<3.15 |
| Node | 24 | Frappe v16 requires >=24 |
| MariaDB | 10.11 or later | utf8mb4, see scripts/bootstrap.sh |

Change a pin only through a bundle that re-runs the full suite; record the old and new pin in docs/BUILD-LOG.md.
