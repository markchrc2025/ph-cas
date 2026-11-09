# Sentire Ledger website (B37)

Static site: index, pricing, demo, terms, privacy, data processing terms. No build step, no tracking.

Deploy on Dokploy as its own app from this repository with build path `/website` (Dockerfile build, nginx on port 80), domain `sentireledger.com` and `www` once the domain is registered; until then `www.ledger.sentire.solutions` or a `*.apps.sentire.solutions` subdomain.

The demo and pilot buttons point at the application site (`https://ledger.sentire.solutions/demo` and `/pilot`), where the forms live, because a static site cannot send mail or create users. Prices are the 9 November 2026 proposal; edit `pricing.html` when they change. Legal pages are drafts for counsel.
