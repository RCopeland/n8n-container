# n8n + python3.
#
# Base image pinned to the digest that was running before this repo existed
# (n8n 2.28.6) — building does NOT upgrade n8n, it only adds python3 for
# Execute Command workflows (food automation scripts are stdlib-only).
FROM docker.n8n.io/n8nio/n8n@sha256:f3284c9ad6892dc578dadd506d0969adc28046a5e010cb0c3bc892cae1ef292d

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
USER node
