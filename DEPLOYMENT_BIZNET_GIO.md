# Biznet Gio Deployment Runbook

> **Deployment status: disabled.** GitHub Actions tests the application and publishes images to GitHub Container Registry (GHCR), but it does not connect to, provision, or update a Biznet Gio VPS. The instructions below are retained for a future, separately approved manual deployment.

## Current automation boundary

On pushes to `main`, `.github/workflows/ci.yml`:

1. runs the FastAPI test suite;
2. builds the React/Vite frontend;
3. builds the production frontend and backend images;
4. publishes commit-SHA and `latest` tags to GHCR.

It intentionally has no deployment job, GitHub environment, SSH key, VPS address, production domain, remote Docker command, or public health check. A successful workflow run means the code and images passed CI; it does not mean production was deployed.

Published image names:

```text
ghcr.io/ridhotr27/data-science-portfolio-frontend:<commit-sha>
ghcr.io/ridhotr27/data-science-portfolio-backend:<commit-sha>
```

Use immutable commit-SHA tags for any future deployment. The `latest` aliases are convenient for inspection but should not be used as rollback references.

## Recommended future VPS specification

- Ubuntu 22.04 LTS or 24.04 LTS
- 2 vCPU
- 4 GB RAM
- 30 GB SSD
- Public IPv4 address

The backend is limited to one worker because dataset sessions are process-local. Uploaded datasets and cached results remain in memory and disappear whenever the backend restarts.

## Server preparation

These steps are **not authorized by the current GitHub Actions workflow** and must be run manually only after a separate deployment approval.

```bash
sudo apt update
sudo apt upgrade -y
sudo adduser deploy
sudo usermod -aG sudo deploy
```

Configure and test key-based SSH access before disabling password authentication. Recommended SSH policy:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Validate before reloading:

```bash
sudo sshd -t
sudo systemctl reload ssh
```

## Firewall and DNS

Allow SSH before enabling UFW, then expose only the reverse proxy:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
sudo ufw status verbose
```

Apply equivalent Biznet Gio firewall rules. Never expose backend port 8000 or frontend port 8080. Create a domain `A` record pointing to the VPS; add `AAAA` only when IPv6 is correctly routed.

## Docker installation

Use Docker's official Ubuntu repository:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker deploy
```

Membership in the `docker` group is effectively root-level access. Restrict the deployment account and its SSH keys.

## Deployment directory

```bash
sudo install -d -o deploy -g deploy -m 700 /opt/ridho-portfolio
sudo install -d -o deploy -g deploy -m 700 /opt/ridho-portfolio/deploy
```

The server requires only:

```text
/opt/ridho-portfolio/
├── .env.production
├── docker-compose.prod.yml
└── deploy/Caddyfile
```

## GHCR access

The images may initially be private even when the source repository is public. Either make each GHCR package public in GitHub package settings or authenticate the VPS with a fine-grained/read-only credential that can read packages. Do not reuse `GITHUB_TOKEN` outside GitHub Actions.

Authenticate interactively without placing a token in shell history:

```bash
export CR_PAT='REPLACE_WITH_READ_PACKAGES_TOKEN'
printf '%s' "$CR_PAT" | docker login ghcr.io --username ridhotr27 --password-stdin
unset CR_PAT
```

Review and rotate registry credentials periodically. Never store a token in `.env.production`.

## Production environment

Copy `.env.production.example` to `.env.production` on the server, then replace the domain, email, and `COMMIT_SHA` placeholders:

```dotenv
DOMAIN=portfolio.example.com
ACME_EMAIL=admin@example.com
FRONTEND_IMAGE=ghcr.io/ridhotr27/data-science-portfolio-frontend:COMMIT_SHA
BACKEND_IMAGE=ghcr.io/ridhotr27/data-science-portfolio-backend:COMMIT_SHA
ALLOWED_ORIGINS=https://portfolio.example.com
DATASET_TTL_SECONDS=900
MAX_DATASET_SESSIONS=3
UPLOAD_RATE_LIMIT=20
UPLOAD_RATE_WINDOW_SECONDS=60
ENABLE_XGBOOST=false
VITE_ENABLE_XGBOOST=false
```

Protect the file:

```bash
chmod 600 /opt/ridho-portfolio/.env.production
```

## Future manual deployment

No part of this procedure is run by GitHub Actions:

```bash
cd /opt/ridho-portfolio
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build --remove-orphans
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

Caddy requests and renews HTTPS certificates after DNS and ports 80/443 are correct. Verify manually:

```bash
curl -fsS https://portfolio.example.com/
curl -fsS https://portfolio.example.com/api/health
```

## Logs and health

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=200
docker stats --no-stream
```

Compose health checks cover Nginx, FastAPI, and Caddy configuration validity. They do not replace external availability monitoring. Caddy rejects request bodies above 6 MB; FastAPI separately enforces the 5 MB dataset limit and bounded session capacity.

## Manual update and rollback

Before an update, save the active environment file:

```bash
cp .env.production .env.production.previous
chmod 600 .env.production.previous
```

Set both image references to the new commit SHA, then run `docker compose pull` and `up -d`. To roll back, restore `.env.production.previous` or set both references to a known-good SHA and repeat those commands.

Rollback restores container versions only. It cannot restore in-memory datasets lost during container replacement.

## Troubleshooting

- **Certificate failure:** verify DNS, Biznet firewall, UFW, and Caddy logs.
- **Registry pull denied:** verify GHCR package visibility or the token's `read:packages` access.
- **API 502:** inspect backend health and OOM state; confirm the image supports the VPS architecture.
- **CORS error:** ensure `ALLOWED_ORIGINS` exactly equals the public HTTPS origin without a trailing slash.
- **SPA 404:** verify Caddy routes non-API requests to `frontend:8080` and the Nginx SPA fallback is present.
- **Session disappeared:** this is expected after expiration, restart, update, or capacity pressure.

## Enablement checklist for a future deployment

- [ ] Separate deployment approval completed
- [ ] VPS provisioned and patched
- [ ] SSH access and host fingerprints verified
- [ ] UFW and provider firewall reviewed
- [ ] DNS resolves to the VPS
- [ ] Docker Engine and Compose installed
- [ ] GHCR package visibility or read-only authentication configured
- [ ] Exact commit-SHA image references selected
- [ ] Production environment file reviewed and protected
- [ ] Compose configuration validated on the VPS
- [ ] Manual rollback tested
- [ ] External uptime monitoring configured
- [ ] Only non-confidential acceptance-test data used

Until every applicable item is complete, Biznet Gio deployment remains disabled.
