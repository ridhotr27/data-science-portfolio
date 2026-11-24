# Portfolio CI/CD Design and Activation

Automatic production deployment is implemented but disabled by default. CI and immutable image publishing run on pushes to `main`; the deployment job runs only when the repository variable `ENABLE_PRODUCTION_DEPLOY` is exactly `true`.

The unresolved `www.ridhotrivo.com` authoritative-DNS problem is intentionally outside the deployment health gate. CD verifies only the working apex origin, `https://ridhotrivo.com`.

## Architecture

```text
push to main
    |
    +-- backend tests (read-only GITHUB_TOKEN)
    +-- frontend build (read-only GITHUB_TOKEN)
             |
             +-- publish frontend SHA tag -> capture sha256 digest
             +-- publish backend SHA tag  -> capture sha256 digest
                         |
                 ENABLE_PRODUCTION_DEPLOY=true?
                         |
                 GitHub production environment
                         |
                 forced-command SSH identity
                         |
                 sudo one root-owned wrapper
                         |
                 pull exact digests, update only
                 frontend/backend, health check
                         |
                     success
                       or
                 automatic rollback to the
                 previous verified environment
```

The Docker API remains a local Unix socket. It is never exposed over TCP and the GitHub deployment user is not a member of the `docker` group. The shared Caddy project and its certificate volumes are not part of the deployment command.

## Workflow behavior

`.github/workflows/ci.yml` provides:

- backend tests and frontend production build before publishing;
- separate frontend/backend publishing jobs with only `contents: read` and `packages: write`;
- one commit-SHA tag per image, with no mutable `latest` tag;
- digest outputs passed directly to the deployment job;
- queued, non-cancelling `main` and production concurrency;
- an environment-scoped deployment job with only `contents: read`;
- strict SSH host-key verification;
- a final public apex health check.

Pull requests run tests/builds but cannot publish or deploy. Forked pull requests do not receive production secrets.

## Dedicated deployment identity

Provisioning is a separate, explicitly approved production change. Do not reuse the interactive `deploy` account or its key.

Generate a dedicated Ed25519 key locally. A passphrase cannot be entered by an unattended runner, so compensate with a forced command, an environment-scoped secret, and a narrowly privileged server account:

```bash
ssh-keygen -t ed25519 -f ./portfolio_github_actions -C portfolio-github-actions
```

Never add either generated key to this repository. Store the private key only in the GitHub `production` environment secret described below.

After reviewing the files in `deploy/cd/`, an administrator installs them on the VPS:

```bash
sudo useradd --create-home --shell /bin/bash portfolio-deploy
sudo passwd --lock portfolio-deploy

sudo install -o root -g root -m 0755 \
  deploy/cd/portfolio-deploy /usr/local/sbin/portfolio-deploy
sudo install -o root -g root -m 0755 \
  deploy/cd/portfolio-deploy-ssh /usr/local/bin/portfolio-deploy-ssh

sudo visudo -cf deploy/cd/portfolio-deploy.sudoers
sudo install -o root -g root -m 0440 \
  deploy/cd/portfolio-deploy.sudoers /etc/sudoers.d/portfolio-deploy
sudo visudo -cf /etc/sudoers.d/portfolio-deploy

sudo install -d -o portfolio-deploy -g portfolio-deploy -m 0700 \
  /home/portfolio-deploy/.ssh
sudo install -o portfolio-deploy -g portfolio-deploy -m 0600 \
  /dev/null /home/portfolio-deploy/.ssh/authorized_keys
```

Add exactly one line to `authorized_keys`, replacing the placeholder with the dedicated public key:

```text
restrict,command="/usr/local/bin/portfolio-deploy-ssh" ssh-ed25519 REPLACE_WITH_PUBLIC_KEY portfolio-github-actions
```

Harden application configuration so the restricted identity cannot alter what root executes:

```bash
sudo chown root:root /opt/ridho-portfolio
sudo chmod 0755 /opt/ridho-portfolio
sudo chown root:root \
  /opt/ridho-portfolio/docker-compose.prod.yml \
  /opt/ridho-portfolio/.env.production
sudo chmod 0644 /opt/ridho-portfolio/docker-compose.prod.yml
sudo chmod 0600 /opt/ridho-portfolio/.env.production
```

The account must not join `sudo`, `docker`, `lxd`, or another privileged group. The sudoers rule permits only `/usr/local/sbin/portfolio-deploy`; that root-owned wrapper independently validates every image reference.

## GitHub production environment

Create a GitHub environment named `production`. Configure deployment-branch protection for `main`; optional required reviewers provide an additional manual gate.

Environment secrets:

| Name | Value |
|---|---|
| `PROD_SSH_PRIVATE_KEY` | Complete dedicated private key, including header/footer |
| `PROD_SSH_KNOWN_HOSTS` | Previously verified VPS host-key line from a trusted local `known_hosts` file |

Repository or environment variables:

| Name | Value |
|---|---|
| `PROD_SSH_HOST` | `139.190.108.107` |
| `PROD_SSH_PORT` | `22` |
| `PROD_SSH_USER` | `portfolio-deploy` |
| `ENABLE_PRODUCTION_DEPLOY` | Leave unset or `false` until activation approval |

The workflow uses the repository-scoped `GITHUB_TOKEN` only to publish GHCR packages. No GHCR token is sent to the VPS because the packages are public. If package visibility changes, configure a separate VPS-side read-only credential; never place it in workflow command arguments.

## Deployment and rollback behavior

The root wrapper:

1. takes a non-blocking deployment lock;
2. refuses to deploy if the current stack is unhealthy;
3. accepts only digest references for the two Portfolio GHCR repositories;
4. pulls both exact digests before changing configuration;
5. saves the active mode-`0600` environment as `.env.production.previous`;
6. updates only `FRONTEND_IMAGE` and `BACKEND_IMAGE`;
7. validates Compose and recreates only `frontend` and `backend`;
8. verifies Docker health plus homepage and API health through the existing Caddy apex route;
9. restores the previous environment and recreates both services if any step fails.

Rollback never runs `compose down`, never touches Caddy, and never deletes networks or volumes. Backend in-memory upload sessions are unavoidably lost whenever its container is replaced.

## Pre-activation validation

Before enabling CD:

```bash
bash -n deploy/cd/portfolio-deploy
bash -n deploy/cd/portfolio-deploy-ssh
sudo visudo -cf deploy/cd/portfolio-deploy.sudoers
docker compose --env-file .env.production.example -f docker-compose.prod.yml config --quiet
```

Test the forced identity from a trusted workstation. This must be rejected:

```bash
ssh -i ./portfolio_github_actions portfolio-deploy@139.190.108.107 uname -a
```

A deployment-shaped command with invalid repositories or digests must also be rejected by the root wrapper. Do not run a valid deployment command during provisioning validation.

## Activation checklist

- [ ] Review and commit the complete deployment changes
- [ ] Push and confirm tests plus both GHCR publish jobs succeed
- [ ] Provision the dedicated forced-command identity
- [ ] Make `/opt/ridho-portfolio` configuration root-owned
- [ ] Validate sudoers with `visudo`
- [ ] Confirm the account is not in privileged groups
- [ ] Add verified host key and dedicated private key to the `production` environment
- [ ] Add host, port, and username variables
- [ ] Keep `ENABLE_PRODUCTION_DEPLOY` unset during a publish-only workflow test
- [ ] Confirm both GHCR packages remain publicly pullable
- [ ] Take note of the currently deployed frontend/backend digests
- [ ] Set `ENABLE_PRODUCTION_DEPLOY=true` only after explicit approval
- [ ] Observe the first deployment and verify apex health, container health, and rollback state
- [ ] Repair `dua.neodns.id` separately before treating `www` as production-ready

To disable future automatic deployments without changing code, set `ENABLE_PRODUCTION_DEPLOY=false` or remove it. CI and immutable image publishing continue.
