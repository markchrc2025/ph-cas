# syntax=docker/dockerfile:1
# ph_cas on ERPNext v16: one container with MariaDB, Redis and the bench.
# Built by Dokploy from the repository root (buildType dockerfile, this file).
#
# Prebuilt assets (CI only): the GHCR image is built on an Arm runner for x86 through QEMU,
# where esbuild (a Go binary) crashes. CI passes --build-arg ASSETS=native-assets so the
# JavaScript and CSS (identical on every CPU) are compiled natively in the stage below and
# copied in. Dokploy passes nothing: ASSETS defaults to "no-prebuilt-assets", the native
# stage is never built, and the image runs `bench build --production` itself, as before.
ARG ASSETS=no-prebuilt-assets
ARG FRAPPE_TAG=v16.55.2
ARG ERPNEXT_TAG=v16.54.0

FROM --platform=$BUILDPLATFORM python:3.14-bookworm AS native-assets-build
ARG FRAPPE_TAG
ARG ERPNEXT_TAG
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      libmariadb-dev libmariadb-dev-compat pkg-config build-essential libffi-dev libssl-dev git curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && apt-get install -y nodejs \
    && npm install -g yarn && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash frappe && pip install --no-cache-dir frappe-bench
USER frappe
WORKDIR /home/frappe
RUN yarn config set network-timeout 600000 -g && yarn config set network-concurrency 4 -g && npm config set fetch-retries 5 && npm config set fetch-retry-maxtimeout 120000
RUN for i in 1 2 3; do bench init bench --frappe-branch ${FRAPPE_TAG} --python python3 --skip-redis-config-generation --no-backups --skip-assets && break; rm -rf bench; sleep 10; done; test -d bench
WORKDIR /home/frappe/bench
RUN for i in 1 2 3; do bench get-app erpnext https://github.com/frappe/erpnext --branch ${ERPNEXT_TAG} --skip-assets && break; rm -rf apps/erpnext; sed -i '/^erpnext$/d' sites/apps.txt; sleep 10; done; test -d apps/erpnext
COPY --chown=frappe:frappe . /home/frappe/bench/apps/ph_cas
# Built files land in each app's public/ (sites/assets/<app> links there) and www/; ship those
# plus sites/assets, without node_modules.
RUN ./env/bin/pip install --no-cache-dir -e apps/ph_cas && sed -i -e "\$a\\" sites/apps.txt && echo ph_cas >> sites/apps.txt \
    && bench build --production \
    && tar -C /home/frappe/bench --exclude=node_modules -cf /home/frappe/assets.tar sites/assets \
         $(ls -d apps/*/*/public apps/*/*/www 2>/dev/null)

FROM scratch AS native-assets
COPY --from=native-assets-build /home/frappe/assets.tar /assets.tar

FROM alpine:3.20 AS no-prebuilt-assets

FROM ${ASSETS} AS prebuilt

FROM python:3.14-bookworm
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      mariadb-server mariadb-client redis-server libmariadb-dev libmariadb-dev-compat pkg-config \
      build-essential libffi-dev libssl-dev git curl ca-certificates cron wkhtmltopdf fonts-dejavu \
    && curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && apt-get install -y nodejs \
    && npm install -g yarn && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash frappe && pip install --no-cache-dir frappe-bench

ARG FRAPPE_TAG
ARG ERPNEXT_TAG
USER frappe
WORKDIR /home/frappe
# yarn on a busy server trips its 30-second default; wait longer and retry more
RUN yarn config set network-timeout 600000 -g && yarn config set network-concurrency 4 -g && npm config set fetch-retries 5 && npm config set fetch-retry-maxtimeout 120000
RUN for i in 1 2 3; do bench init bench --frappe-branch ${FRAPPE_TAG} --python python3 --skip-redis-config-generation --no-backups --skip-assets && break; rm -rf bench; sleep 10; done; test -d bench
WORKDIR /home/frappe/bench
RUN for i in 1 2 3; do bench get-app erpnext https://github.com/frappe/erpnext --branch ${ERPNEXT_TAG} --skip-assets && break; rm -rf apps/erpnext; sed -i '/^erpnext$/d' sites/apps.txt; sleep 10; done; test -d apps/erpnext

COPY --chown=frappe:frappe . /home/frappe/bench/apps/ph_cas
RUN --mount=type=bind,from=prebuilt,target=/prebuilt \
    ./env/bin/pip install --no-cache-dir -e apps/ph_cas && sed -i -e "\$a\\" sites/apps.txt && echo ph_cas >> sites/apps.txt && cat sites/apps.txt \
    && if [ -f /prebuilt/assets.tar ]; then echo "using natively built assets"; tar -C /home/frappe/bench -xf /prebuilt/assets.tar; \
       else bench build --production; fi \
    && cp -a sites /home/frappe/sites-image

USER root
RUN apt-get update && apt-get install -y --no-install-recommends nginx rclone && rm -rf /var/lib/apt/lists/*
COPY deploy/nginx.conf /etc/nginx/nginx.conf.template
COPY deploy/ledger-site.sh /usr/local/bin/ledger-site
RUN chmod +x /usr/local/bin/ledger-site
COPY deploy/mariadb.cnf /etc/mysql/mariadb.conf.d/99-frappe.cnf
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld
EXPOSE 8000
# Healthy while the first-run site install is in progress (marker file), otherwise ping the site.
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=5 CMD test -f /run/ph_cas_installing || curl -fsS http://127.0.0.1:8000/api/method/ping || exit 1
ENTRYPOINT ["/entrypoint.sh"]
