# Sentire Solutions website (B37, restructured 11 Nov 2026)

Static site, no build step, no tracking. `index.html` is the Sentire Solutions front page (the product family); the Sentire Ledger site lives under `ledger/` (index, pricing, demo, terms, privacy, data processing terms) and is served at `https://sentire.solutions/ledger/`.

Deployed on Dokploy as the app "Sentire Website" from this repository with build path `/website` (Dockerfile build, nginx on port 80), hostnames `sentire.solutions` and `www.sentire.solutions` (A records to 91.90.80.4). `sentireledger.com`, once registered, can be added as a third hostname and redirected to `/ledger/`.

The demo and pilot buttons point at the application site (`https://ledger.sentire.solutions/demo` and `/pilot`), where the forms live, because a static site cannot send mail or create users. Prices are the 9 November 2026 proposal; edit `pricing.html` when they change. Legal pages are drafts for counsel.
