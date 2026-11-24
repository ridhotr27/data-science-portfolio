# Biznet Gio Production Deployment

This runbook deploys the Data Science Portfolio behind one standalone Caddy edge proxy. It does not deploy or route Indonesia Wildfire Intelligence.

For the disabled-by-default automatic deployment design, restricted identity, GitHub settings, and activation checklist, see `CI_CD_DEPLOYMENT.md`.

## Architecture

```text
Internet :80/:443
        |
  shared-edge/caddy
        | caddy_edge (external Docker network)
        +-- portfolio-frontend:8080
        +-- portfolio-backend:8000 (/api/* only)

ridho-portfolio/app (internal Docker network)
        +-- frontend
        +-- backend
```

Only Caddy publishes host ports. `8080` and `8000` are Docker-network ports and must never be published. Future projects may join `caddy_edge` with unique aliases and receive their own Caddy site blocks.

## Files on the VPS

```text
/opt/shared-edge/
├── .env.proxy
├── docker-compose.proxy.yml
└── deploy/Caddyfile

/opt/ridho-portfolio/
├── .env.production
└── docker-compose.prod.yml
```

Protect both environment files with mode `600`. `.env.proxy` contains the ACME contact email; `.env.production` contains image references and runtime settings. Neither file belongs in Git.

## DNS prerequisites

Create these records at the authoritative DNS provider:

| Type | Name/Host | Value | Purpose |
|---|---|---|---|
| A | `@` | `139.190.108.107` | Portfolio apex |
| CNAME | `www` | `ridhotrivo.com` | Redirect hostname |

Do not create a `wildfire` record yet. Do not add an `AAAA` record unless the VPS has verified public IPv6 routing. Remove conflicting apex or `www` A/AAAA/CNAME records. Use the provider's default TTL (or 300 seconds during rollout).

Verify before starting Caddy:

```bash
dig +short A ridhotrivo.com
dig +short A www.ridhotrivo.com
dig +short AAAA ridhotrivo.com
dig +short AAAA www.ridhotrivo.com
```

Both A lookups must ultimately resolve to `139.190.108.107`; AAAA lookups should be empty unless IPv6 is intentionally configured.

## Image policy and GHCR access

Use the exact commit-SHA and digest references in `.env.production.example`, never `latest`. Confirm the resolved image digests after pulling:

```bash
sudo docker image inspect --format '{{index .RepoDigests 0}}' "$FRONTEND_IMAGE"
sudo docker image inspect --format '{{index .RepoDigests 0}}' "$BACKEND_IMAGE"
```

If the GHCR packages are public, no registry login is required. If they are private, authenticate using a dedicated read-only package token through `--password-stdin`; never store it in either environment file.

## Pre-deployment validation

From the repository checkout or a staging directory:

```bash
docker compose --env-file .env.proxy.example -f docker-compose.proxy.yml config --quiet
docker compose --env-file .env.production.example -f docker-compose.prod.yml config --quiet
docker run --rm -e ACME_EMAIL=admin@example.com \
  -v "$PWD/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2.11.9-alpine@sha256:003a97808e781aa9f7e75cc2f43d34d461099031faf5e20faefb9f61126836f0 \
  caddy validate --config /etc/caddy/Caddyfile
```

## First deployment

These commands are production changes and require explicit approval:

```bash
sudo docker network create caddy_edge

cd /opt/ridho-portfolio
sudo docker compose --env-file .env.production -f docker-compose.prod.yml pull
sudo docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build
sudo docker compose --env-file .env.production -f docker-compose.prod.yml ps

cd /opt/shared-edge
sudo docker compose --env-file .env.proxy -f docker-compose.proxy.yml pull
sudo docker compose --env-file .env.proxy -f docker-compose.proxy.yml up -d --no-build
sudo docker compose --env-file .env.proxy -f docker-compose.proxy.yml ps
```

Start the Portfolio first so Caddy can resolve both upstream aliases when it loads the configuration.

## Acceptance checks

```bash
curl -fsS https://ridhotrivo.com/
curl -fsS https://ridhotrivo.com/api/health
curl -sS -o /dev/null -D - https://www.ridhotrivo.com/example
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
sudo docker stats --no-stream
sudo ss -lntup
```

Confirm that:

- `www` redirects permanently to the same path on `https://ridhotrivo.com`;
- frontend and backend health checks pass;
- only Caddy publishes `80/tcp`, `443/tcp`, and `443/udp`;
- backend `8000` and frontend `8080` are not host listeners;
- containers return after a controlled Docker service restart;
- memory, CPU, PIDs, logs, and restart counts remain within limits.

Uploaded datasets are in memory and disappear on backend restart or replacement.

## Update and rollback

Before an update, record the active image values and copy the protected environment file:

```bash
cd /opt/ridho-portfolio
cp -p .env.production .env.production.previous
sudo docker compose --env-file .env.production -f docker-compose.prod.yml config --images
```

Set both images to the new tested commit SHA, then:

```bash
sudo docker compose --env-file .env.production -f docker-compose.prod.yml pull
sudo docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build
```

To roll back, restore the previous image references (or `.env.production.previous`) and recreate the application containers:

```bash
cp -p .env.production.previous .env.production
sudo docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build
```

Do not run `down -v`: Caddy certificate state lives in named volumes. An application rollback cannot restore in-memory datasets.

For a Caddy configuration change, validate the candidate first, keep the previous `Caddyfile`, and recreate only the Caddy service. If acceptance fails, restore the previous file and recreate Caddy again.

## Troubleshooting boundaries

- Certificate failure: verify A/CNAME resolution, public reachability of TCP 80/443, and Caddy logs.
- GHCR pull denial: verify package visibility or read-only `read:packages` authentication.
- API 502: inspect backend health/OOM state and shared-network membership.
- CORS failure: `ALLOWED_ORIGINS` must be exactly `https://ridhotrivo.com`.
- Never publish `8000` or `8080` as a workaround.
