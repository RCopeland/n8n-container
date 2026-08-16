# n8n

General-purpose n8n on the Tailscale-connected host (192.168.4.37),
reachable **only** over the tailnet. Same pattern as `romm` / `neon-crate`:
a Tailscale sidecar whose network namespace the app shares, fronted by
`tailscale serve` (not funnel) — no public exposure, no published ports.

Replaces the old single-purpose `neon-crate` deployment. The `n8n_data`
volume is **external** on purpose: it's the same named volume neon-crate
used, so existing workflows/credentials carry over untouched.

## Result

| Item | Value |
| --- | --- |
| URL | `https://n8n.tail4fde5e.ts.net` (was `n8n-server-1.tail4fde5e.ts.net`) |
| Access | Tailnet only (MagicDNS + HTTPS cert) |
| App port (inside netns) | `5678` (n8n default) |
| Image | n8n 2.28.6 (pinned digest) + python3 |
| Old workflows | Preserved via `n8n_data` volume |

## Storage layout (host)

| Path | Purpose |
| --- | --- |
| `~/Dev/n8n/.env` | `TS_AUTHKEY`, `TS_CERT_DOMAIN`, `N8N_WEBHOOK_URL` — never commit |
| `n8n_data` (external volume) | n8n workflows + credentials |
| `~/Dev/food` | mounted at `/opt/food` — food automation scripts (rw: sync writes `delivery-list.md`) |
| `~/.config/kroger`, `~/.config/tandoor` | API credentials, mounted read-only |

## Quickstart (on the host)

1. Clone this repo: `git clone git@github.com:RCopeland/n8n.git ~/Dev/n8n`

2. Create `.env` from `.env.example` and fill in:
   - `TS_AUTHKEY` — tailnet pre-auth key (node joins as `n8n`)
   - `TS_CERT_DOMAIN` — `n8n.tail4fde5e.ts.net` (default)
   - `N8N_WEBHOOK_URL` — `https://n8n.tail4fde5e.ts.net/`

3. Stop the old stack first (name collision otherwise — containers are both
   named `n8n`):

   ```bash
   cd ~/Dev/neon-crate && docker compose down
   ```

4. Bring it up:

   ```bash
   cd ~/Dev/n8n && docker compose up -d --build
   ```

5. Verify:

   ```bash
   docker compose ps
   docker exec n8n-tailscale tailscale status   # node "n8n" should be up
   curl -sk https://n8n.tail4fde5e.ts.net -o /dev/null -w "%{http_code}\n"
   ```

6. Confirm your old workflows are still there (same `n8n_data` volume), then
   remove the retired `n8n-server-1` node in the Tailscale admin console.

## Importing a workflow

```bash
docker exec n8n n8n import:workflow --input=/opt/food/workflows/kroger-weekly-order.json
```

## Notes

- **Webhook URLs change**: the serve URL moved from `n8n-server-1.tail4fde5e.ts.net`
  to `n8n.tail4fde5e.ts.net` — any existing workflow using webhooks needs its
  webhook URL re-pointed (and `N8N_WEBHOOK_URL` above matches the new base).
- The food automation is the primary workflow: `sync_tandoor.py` (meal plan +
  pantry → `delivery-list.md`) then `cart.py --json` (fills the Kroger cart).
  Both are stdlib-only python3 and run via Execute Command nodes.
- Updating: `docker compose build --pull && docker compose up -d` (only pulls
  a new n8n when you intentionally change the pinned digest).
