# n8n 2.28.6 + python3.
#
# Why not extend the official image? The official base is an Alpine
# "hardened" image with no package manager (no apk, no apt) — python3 cannot
# be added to it. So we build n8n from the official npm package on a plain
# Debian node base instead:
#   - n8n@2.28.6 — the exact version the previous deployment ran, so the
#     existing n8n_data volume (workflows, credentials, encryption key,
#     SQLite DB) is fully compatible
#   - glibc base -> prebuilt native modules (better-sqlite3, sharp) work
#   - python3 for Execute Command workflows (food automation is stdlib-only)
FROM node:22-bookworm-slim

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g n8n@2.28.6 --no-audit --no-fund
USER node

# the official image's entrypoint is the n8n CLI; the node base has none,
# so bare `node` (its default CMD) exits immediately without a TTY
ENTRYPOINT ["n8n"]
CMD ["start"]
