# Deploying to a Biznet Gio Ubuntu VPS

This runbook prepares and operates the portfolio on a single Ubuntu VPS with Docker Compose, GitLab Container Registry, GitLab CI/CD, and Caddy-managed HTTPS. It does not provision or deploy a VPS automatically.

## 1. Recommended VPS specification

Start with:

- Ubuntu 22.04 LTS or 24.04 LTS
- 2 vCPU
- 4 GB RAM
- 30 GB SSD
- A public IPv4 address

The recommendation allows headroom for Pandas/SciPy imports, image pulls, and bounded analytics workloads. Monitor real memory and CPU before resizing. XGBoost is disabled, and the application is deliberately limited to one backend worker because sessions are process-local.

## 2. DNS and domain preparation

Before requesting HTTPS certificates:

1. Choose a domain such as `portfolio.example.com`.
2. Create an `A` record pointing to the VPS IPv4 address.
3. Add an `AAAA` record only if the VPS has correctly routed public IPv6.
4. Remove stale/conflicting records.
5. Wait for DNS propagation and verify from another network:

```bash
dig +short portfolio.example.com A
dig +short portfolio.example.com AAAA
```

Caddy certificate issuance will fail until the public domain reaches the VPS on ports 80 and 443.

## 3. Initial Ubuntu preparation

Log in using the initial provider account, update packages, and create a dedicated deployment user:

```bash
sudo apt update
sudo apt upgrade -y
sudo adduser deploy
sudo usermod -aG sudo deploy
```

Copy an administrator SSH public key to `/home/deploy/.ssh/authorized_keys`, then verify a new SSH session before changing SSH policy.

Recommended SSH hardening in `/etc/ssh/sshd_config.d/99-portfolio.conf`:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Validate and reload without closing the current session:

```bash
sudo sshd -t
sudo systemctl reload ssh
```

Do not disable password authentication until key-based login has been tested successfully.

## 4. Firewall and networking

Allow SSH before enabling UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
sudo ufw status verbose
```

Also configure the Biznet Gio security-group/firewall controls, if enabled, for the same ports. Do not expose ports 8000 or 8080. Docker publishes only Caddy's 80/443 mappings.

## 5. Install Docker Engine and Compose

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

Log out and back in so group membership is refreshed, then verify:

```bash
docker version
docker compose version
docker run --rm hello-world
```

Membership in the `docker` group is effectively root-level access. Limit the deployment account and protect its SSH key accordingly.

## 6. Prepare the deployment directory

As the `deploy` user:

```bash
sudo install -d -o deploy -g deploy -m 700 /opt/ridho-portfolio
cd /opt/ridho-portfolio
mkdir -m 700 deploy
```

The final server directory contains only:

```text
/opt/ridho-portfolio/
├── .env.production
├── .env.production.previous   # created after the first CI update
├── docker-compose.prod.yml
└── deploy/Caddyfile
```

Application source code is not required on the VPS because GitLab builds the images.

## 7. GitLab Container Registry access

Create a GitLab Deploy Token with `read_registry` only. Store its username/password as protected, masked CI/CD variables:

- `REGISTRY_DEPLOY_USER`
- `REGISTRY_DEPLOY_PASSWORD`

For a manual first deployment, authenticate without placing the password in shell history:

```bash
printf '%s' "$REGISTRY_DEPLOY_PASSWORD" | docker login registry.gitlab.com \
  --username "$REGISTRY_DEPLOY_USER" --password-stdin
```

Credentials are stored in the deployment user's Docker configuration. Review access and rotate the token periodically.

## 8. Deployment SSH key

Create a dedicated CI deployment key on a trusted workstation:

```bash
ssh-keygen -t ed25519 -C gitlab-portfolio-deploy -f gitlab-portfolio-deploy
```

Append only the public key to `/home/deploy/.ssh/authorized_keys`. Store the private key as a protected **file-type** variable named `SSH_PRIVATE_KEY` when possible. The pipeline also accepts key text in that variable, although GitLab masking rules can make multiline values impractical.

Capture the server host key from a trusted network and verify its fingerprint through the provider console:

```bash
ssh-keyscan -H YOUR_VPS_HOSTNAME
```

Store the verified output as protected variable `SSH_KNOWN_HOSTS`. The pipeline intentionally does not perform an unverified runtime `ssh-keyscan`.

## 9. Required GitLab CI/CD variables

Configure these under **Settings → CI/CD → Variables**. Mark production secrets protected and masked where GitLab permits.

| Variable | Example/purpose | Protected | Secret |
|---|---|---:|---:|
| `SSH_PRIVATE_KEY` | Dedicated deploy private key | Yes | Yes |
| `SSH_KNOWN_HOSTS` | Verified host-key line | Yes | No |
| `DEPLOY_HOST` | VPS hostname or IP | Yes | No |
| `DEPLOY_USER` | `deploy` | Yes | No |
| `DEPLOY_PATH` | `/opt/ridho-portfolio` | Yes | No |
| `PRODUCTION_DOMAIN` | `portfolio.example.com` | Yes | No |
| `ACME_EMAIL` | Certificate-notification email | Yes | No |
| `REGISTRY_DEPLOY_USER` | Read-only deploy-token username | Yes | Yes |
| `REGISTRY_DEPLOY_PASSWORD` | Read-only deploy-token secret | Yes | Yes |
| `DATASET_TTL_SECONDS` | Optional, default `900` | Yes | No |
| `MAX_DATASET_SESSIONS` | Optional, default `3` | Yes | No |
| `UPLOAD_RATE_LIMIT` | Optional, default `20` | Yes | No |
| `UPLOAD_RATE_WINDOW_SECONDS` | Optional, default `60` | Yes | No |

GitLab automatically provides `CI_REGISTRY`, `CI_REGISTRY_IMAGE`, `CI_REGISTRY_USER`, `CI_REGISTRY_PASSWORD`, and `CI_COMMIT_SHA` to jobs where the Container Registry is enabled.

Protect the `main` branch. The deployment rule requires both the default branch and `CI_COMMIT_REF_PROTECTED=true`.

## 10. Production environment file

The template is `.env.production.example`. Production uses:

```dotenv
DOMAIN=portfolio.example.com
ACME_EMAIL=admin@example.com
FRONTEND_IMAGE=registry.gitlab.com/namespace/project/frontend:COMMIT_SHA
BACKEND_IMAGE=registry.gitlab.com/namespace/project/backend:COMMIT_SHA
ALLOWED_ORIGINS=https://portfolio.example.com
DATASET_TTL_SECONDS=900
MAX_DATASET_SESSIONS=3
UPLOAD_RATE_LIMIT=20
UPLOAD_RATE_WINDOW_SECONDS=60
ENABLE_XGBOOST=false
VITE_ENABLE_XGBOOST=false
```

The CI deploy job generates this file with exact SHA-tagged images and uploads it with mode-restricted handling. Never commit `.env.production`.

## 11. Initial deployment

The preferred first deployment is a protected `main` pipeline after DNS, Docker, variables, directory ownership, and registry access are ready.

For a controlled manual first deployment:

1. Obtain `docker-compose.prod.yml`, `deploy/Caddyfile`, and an edited `.env.production` on the server.
2. Authenticate to the GitLab registry.
3. Validate and pull:

```bash
cd /opt/ridho-portfolio
chmod 600 .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build
```

4. Inspect startup and certificate issuance:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs caddy --tail=200
curl -fsS https://portfolio.example.com/api/health
```

Do not use placeholder domains or image references from the example file.

## 12. Automatic deployments

The GitLab pipeline performs:

1. backend tests and frontend build;
2. separate immutable frontend/backend image builds;
3. registry pushes tagged with the commit SHA;
4. protected-main SSH deployment;
5. Compose pull and rolling service recreation;
6. public frontend and API verification with retries.

Compose recreates only services whose image reference changed. Caddy remains running when its configuration and image are unchanged, reducing avoidable public endpoint downtime. Backend sessions are still lost whenever the backend container is replaced.

## 13. Health checks and monitoring

Inspect service and resource health:

```bash
cd /opt/ridho-portfolio
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker stats --no-stream
curl -fsS https://portfolio.example.com/
curl -fsS https://portfolio.example.com/api/health
```

The Compose health checks cover Nginx, FastAPI, and Caddy configuration validity. GitLab verifies the public paths after deployment. This is basic availability checking, not full observability. Add an external uptime monitor for the public HTTPS URL if desired.

Caddy rejects request bodies above 6 MB before proxying. FastAPI separately enforces the documented 5 MB dataset limit, row/column limits, bounded session capacity, and process-local upload throttling.

## 14. Logs

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f --tail=200
docker compose --env-file .env.production -f docker-compose.prod.yml logs backend --tail=200
docker compose --env-file .env.production -f docker-compose.prod.yml logs caddy --tail=200
```

Docker JSON logs rotate at 10 MB with three files per service. Caddy emits structured JSON access logs to stdout. Uploaded dataset contents are not intentionally logged.

## 15. Updating containers manually

Edit only the image SHA tags in `.env.production`, then:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build --remove-orphans
docker image prune -f
```

Confirm both public endpoints after every update.

## 16. Rollback

Before CI uploads a new environment file, it copies the current file to `.env.production.previous`. To roll back:

```bash
cd /opt/ridho-portfolio
cp .env.production .env.production.failed
cp .env.production.previous .env.production
chmod 600 .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-build --remove-orphans
curl -fsS https://portfolio.example.com/api/health
```

Alternatively, edit `FRONTEND_IMAGE` and `BACKEND_IMAGE` to a known-good commit SHA from the GitLab Container Registry. Rollback restores application images, not in-memory datasets from before the update.

## 17. Backup and recovery

Application uploads are deliberately ephemeral and are not backed up. Persist and back up only operational state:

- Docker volume `ridho-portfolio_caddy_data` contains Caddy certificates/account state.
- `.env.production` and `.env.production.previous` contain deployment configuration but no registry password.
- GitLab Container Registry retains image history according to its cleanup policy.

If Caddy state is lost, it can request new certificates, subject to certificate-authority rate limits. Avoid repeatedly deleting its volumes.

## 18. Troubleshooting

### Certificate not issued

- Confirm `A`/`AAAA` records resolve to the VPS.
- Confirm provider firewall and UFW allow TCP 80/443.
- Remove an invalid `AAAA` record if IPv6 is not routed.
- Inspect `docker compose ... logs caddy`.

### API returns 502

- Run `docker compose ... ps` and inspect backend health/logs.
- Confirm the backend image supports the VPS CPU architecture.
- Confirm memory limits are not causing OOM termination (`docker inspect`).

### Browser CORS error

- `ALLOWED_ORIGINS` must exactly equal `https://$DOMAIN`.
- Recreate the backend after changing `.env.production`.
- Do not include a trailing slash in the origin.

### SPA route returns 404

- Confirm the frontend image contains `deploy/nginx.conf`.
- Confirm Caddy proxies non-API paths to `frontend:8080`.
- Rebuild the frontend image rather than editing the running container.

### Registry pull denied

- Confirm the deploy token has `read_registry`.
- Re-run `docker login` as the same user running Compose.
- Confirm exact project image paths and SHA tags exist.

### Upload session disappears

This is expected after 15 minutes of inactivity, backend restart, container update, or capacity pressure. The backend is intentionally single-worker and process-local. Re-upload the source file.

## 19. Pre-deployment checklist

- [ ] VPS created and updated
- [ ] Deployment SSH key verified
- [ ] Root/password SSH policy reviewed safely
- [ ] Docker Engine and Compose v2 installed
- [ ] UFW and provider firewall allow only SSH, 80, and 443 as required
- [ ] DNS resolves correctly
- [ ] GitLab Container Registry enabled
- [ ] Protected deploy token created
- [ ] Protected `main` branch configured
- [ ] All GitLab CI/CD variables configured
- [ ] Production Compose config validated
- [ ] Test/build pipeline passes
- [ ] No confidential data used for acceptance testing

Actual VPS provisioning, DNS changes, GitLab variable creation, and production deployment remain manual and were not performed by this repository change.
