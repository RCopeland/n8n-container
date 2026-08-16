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
| Image | official n8n, pinned digest (2.28.6) — no custom build |
| Old workflows | Preserved via `n8n_data` volume |

## Services

| Service | Runs | Notes |
| --- | --- | --- |
| `n8n` | official n8n 2.28.6 (pinned digest) | the workflows + credentials live in the external `n8n_data` volume |
| `food-runner` | `python:3-alpine` + `food-runner.py` | executes the food scripts (see below); python has no place in the node runtime |
| `tailscale` | tailscale sidecar, hostname `n8n` | all services share its netns |

### Why no custom n8n image?

The official n8n base is a hardened Alpine with **no package manager**, and
installing n8n@2.28.6 from npm on a stock node base breaks (transitive dep
`@langchain/core` exports mismatch — n8n's official build uses pnpm + a
lockfile). So n8n stays 100% official/pinned, and python scripts run in the
separate `food-runner` container instead. Bonus: cleaner separation for a
general-purpose instance.

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
   cd ~/Dev/n8n && docker compose up -d
   ```

5. Verify:

   ```bash
   docker compose ps
   docker exec n8n-tailscale tailscale status   # node "n8n" should be up
   curl -sk https://n8n.tail4fde5e.ts.net -o /dev/null -w "%{http_code}\n"
   ```

6. Confirm your old workflows are still there (same `n8n_data` volume), then
   remove the retired `n8n-server-1` node in the Tailscale admin console.

## Food automation

The primary workflow (Sunday 8am):

1. `sync_tandoor.py` — reads the Tandoor meal plan + pantry, regenerates
   `delivery-list.md` (`/opt/food/delivery-list.md`)
2. `cart.py --json` — fills the Kroger cart from that list
3. n8n emails you the summary; you review + checkout in the Kroger app

n8n triggers both via `POST http://127.0.0.1:8731/run` (loopback inside the
shared netns) — the `food-runner` container executes them. Test the bridge:

```bash
docker exec food-runner wget -qO- --post-data='{"cmd":"sync"}' http://127.0.0.1:8731/run
```

## Importing a workflow

```bash
docker exec n8n n8n import:workflow --input=/workflows/kroger-weekly-order.json
docker exec n8n n8n import:workflow --input=/workflows/tandoor-saturday-nudge.json
```

## Notes

- **Webhook URLs change**: the serve URL moved from `n8n-server-1.tail4fde5e.ts.net`
  to `n8n.tail4fde5e.ts.net` — any existing workflow using webhooks needs its
  webhook URL re-pointed (and `N8N_WEBHOOK_URL` above matches the new base).
- Updating n8n intentionally: bump the digest in `compose.yaml`, then
  `docker compose pull && docker compose up -d`.
