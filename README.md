# Kandev — Dual-Host Architecture

Two **identical** kandev instances, one always-on (mini-desktop), one powerful (sfl-desktop). Data syncs sfl → mini automatically; push mini → sfl manually before switching.

## Hosts

| Host | IP | User | Role |
|---|---|---|---|
| mini-desktop | 10.0.0.182 | alassane | always-on fallback (home dev) |
| sfl-desktop | 192.168.50.211 | ayattara | powerful, work hours (via SFL VPN) |

Both hosts use:
- `~/Code` — projects/workspaces (bind-mounted into container as `/data/home/Code`)
- `~/.local/share/kandev` — kandev data dir (sqlite + sessions, mounted as `/data`)

### Adding a repository in the UI

Kandev restricts repository paths to within the container `HOME` (`/data/home`). The host `~/Code` is **nested-bind-mounted** at `/data/home/Code` inside the container (a real directory, not a symlink — kandev's discovery scanner does not follow symlinks).

In the **Add Local Repository** dialog enter:

```
/data/home/Code/<project-name>
```

(Not the host path like `/home/alassane/Code/<project>` — that path doesn't exist inside the container.)

> The mountpoint `~/.local/share/kandev/home/Code` is created as an empty directory by `install-mini.sh` / `install-sfl.sh` so Docker can apply the nested bind on container (re)create.

## File structure

```
~/Code/kandev/
├── docker-compose.yml            # Base service definition (upstream image)
├── docker-compose.override.yml   # Auto-merged: local build + host identity mounts
├── docker-compose.ssh-agent.yml  # Optional overlay: SSH agent socket forwarding
├── Dockerfile.local              # Extends upstream image with extra packages
├── install-mini.sh               # One-time setup for mini-desktop (cron, mountpoints)
├── install-sfl.sh                # One-time setup for sfl-desktop (systemd, UFW, NAT)
├── update.sh                     # Pull upstream + rebuild local image + restart
├── sync-from-sfl.sh              # Rsync sfl → mini (run by cron on mini-desktop)
├── sync-to-sfl.sh                # Rsync mini → sfl (run manually)
├── kandev-ssh-agent.sh           # Helper: start ssh-agent and restart kandev with it
└── README.md
```

## Local image customization

The upstream image `ghcr.io/kdlbs/kandev:latest` does not include all tools needed for
daily development work. A local **`Dockerfile.local`** extends it with:

| Package | Purpose |
|---|---|
| `openssh-client` | `ssh`, `scp`, `ssh-keyscan` |
| `gh` (GitHub CLI) | `gh pr`, `gh repo`, `gh auth login`, etc. |
| `glab` (GitLab CLI) | `glab mr`, `glab repo`, `glab auth login`, etc. |
| git system config | `safe.directory = *` — prevents "dubious ownership" errors (see below) |

### Build

The image is built automatically via `docker-compose.override.yml` which Docker Compose
merges with `docker-compose.yml` on every `docker compose up`.

**First time or after modifying `Dockerfile.local`:**

```bash
cd ~/Code/kandev
docker compose build          # builds kandev-local:latest
docker compose up -d --force-recreate
```

> **Network note (sfl-desktop / transparent proxy):** the build must use `--network=host`
> (already set in `docker-compose.override.yml` under `build.network`) so `apt-get` and
> `curl` can reach the internet through the corporate proxy.

### What the build does

```
ghcr.io/kdlbs/kandev:latest          (upstream, Debian 12)
        │
        └─ Dockerfile.local
              ├── apt: openssh-client gnupg curl ca-certificates
              ├── apt (cli.github.com repo): gh
              ├── dpkg: glab  (downloaded from gitlab.com packages API)
              └── git config --system safe.directory '*'
                      └─> kandev-local:latest
```

`update.sh` pulls the upstream image daily and, if it changed, automatically rebuilds
`kandev-local:latest` on top of the new base before restarting the container.

### Adding more packages

Edit `Dockerfile.local` and add `apt-get install` lines in the *Core tools* `RUN` block,
then rebuild:

```bash
cd ~/Code/kandev && docker compose build && docker compose up -d --force-recreate
```

## Host identity mirroring

`docker-compose.override.yml` mounts host configuration into the container so that
`ssh`, `git`, `gh`, and `glab` inside kandev behave exactly as on the host.

### Environment variables

#### `docker-compose.yml` (base — kandev application)

| Variable | Value | Purpose |
|---|---|---|
| `KANDEV_NO_BROWSER` | `1` | Prevents kandev from trying to open the web UI in a desktop browser on startup. Required on headless servers — without it kandev may hang if no display is available. |
| `KANDEV_HOME_DIR` | `/data` | Root of the kandev data directory inside the container. Kandev stores its sqlite database, sessions, and internal config here. Must match the `~/.local/share/kandev:/data` volume mount. |
| `KANDEV_DOCKER_ENABLED` | `false` | Disables kandev's built-in per-project Docker container spawning. We run with `network_mode: host` and manage containers separately. The Docker socket is still mounted for manual use. |
| `HOME` | `/data/home` | Overrides the container user's home directory. All tools that expand `~` or read `$HOME` resolve config files here: `~/.ssh → /data/home/.ssh`, `~/.gitconfig → /data/home/.gitconfig`, etc. This is the anchor that makes all host identity mounts work. |
| `NPM_CONFIG_PREFIX` | `/data/.npm-global` | Redirects `npm install -g` to the persistent data volume. Without this, global npm packages land in the container's ephemeral root filesystem and are lost on every rebuild. With it, they survive in `~/.local/share/kandev/.npm-global`. |
| `HOSTNAME` | `0.0.0.0` | Bind address reported and used by the kandev server. With `network_mode: host` the container shares the host's network stack. `0.0.0.0` makes the UI reachable on all interfaces (LAN, loopback), enabling access from `http://board.home` and `http://board.sfl`. |
| `NODE_ENV` | `production` | Runs Node.js in production mode: disables dev-only middleware and verbose stack traces, enables caching and performance optimisations, and reduces log noise. Change to `development` only when debugging kandev itself. |

#### `docker-compose.override.yml` (host identity)

| Variable | Value | Purpose |
|---|---|---|
| `USER` | `${USER}` (host shell) | Propagates the host username into the container. The container OS user is `kandev`, but `git`, `ssh`, `gh`, `glab`, and shell scripts inspect `$USER` for identity. Without this they report `kandev` instead of `ayattara`. |
| `LOGNAME` | `${USER}` (host shell) | POSIX fallback for `$USER`. Some tools (older Unix utilities, certain git hooks, shell scripts) read `$LOGNAME` exclusively. Must match `$USER` for consistent identity across all tooling. |

#### `docker-compose.ssh-agent.yml` (optional SSH agent overlay)

| Variable | Value | Purpose |
|---|---|---|
| `SSH_AUTH_SOCK` | `/run/ssh-agent.sock` | Points SSH and any libssh/libssh2-based tool to the forwarded agent socket. Without this variable, SSH ignores the bind-mounted socket entirely and falls back to key-file auth only — defeating the purpose of agent forwarding. The path must match the container-side path in the volume mount. |

> **UID matching:** The container user is `kandev` (UID 1000). The host user is `ayattara`
> (UID 1000). Because the UIDs are identical, all bind-mounted files (SSH keys, gitconfig,
> CLI tokens) are accessible inside the container without any `chmod` or `chown`.

### Volume mounts

| Host path | Container path | Mode | Purpose |
|---|---|---|---|
| `~/.local/share/kandev` | `/data` | rw | Kandev data (sqlite DB, sessions) |
| `~/Code` | `/data/home/Code` | rw | Project workspaces |
| `/var/run/docker.sock` | `/var/run/docker.sock` | rw | Docker-in-Docker (disabled by default) |
| `~/.ssh` | `/data/home/.ssh` | **ro** | SSH keys, `config`, `known_hosts` |
| `~/.gitconfig` | `/data/home/.gitconfig` | **ro** | Git identity (name, email, aliases) |
| `~/.config/gh` | `/data/home/.config/gh` | rw | GitHub CLI auth tokens |
| `~/.config/glab-cli` | `/data/home/.config/glab-cli` | rw | GitLab CLI auth tokens |

> `~/.ssh/config` uses `~` for `IdentityFile` paths. Inside the container `HOME=/data/home`,
> so `~/.ssh/github_yattdev_sfldesktop` resolves to `/data/home/.ssh/github_yattdev_sfldesktop`
> — all host SSH host aliases and key mappings work as-is.

### Git `safe.directory`

`~/.gitconfig` contains `safe.directory = /home/ayattara/Code/scsl` (a host absolute path).
Inside the container the same repo lives at `/data/home/Code/scsl`. Rather than patching the
gitconfig, `Dockerfile.local` injects `git config --system safe.directory '*'` into
`/etc/gitconfig` so every directory is trusted. This also covers repos that Docker previously
created with `root` ownership.

### First-time CLI authentication

After starting the container for the first time (or on a new machine):

```bash
# GitHub
docker exec -it kandev gh auth login

# GitLab
docker exec -it kandev glab auth login
```

Tokens are written to the read-write config mounts and persist on the host, so they survive
container rebuilds and updates.

### Verify identity inside the container

```bash
docker exec -u kandev kandev sh -c "
  echo USER=\$USER
  git config --global user.name
  git config --global user.email
  git config --system  safe.directory
  ssh -G github.com | grep -E 'hostname|identityfile'
  gh  auth status 2>&1
  glab auth status 2>&1
"
```

Expected output:

```
USER=ayattara
ayattara
alassane.yattara@savoirfairelinux.com
*
hostname github.com
identityfile ~/.ssh/github_yattdev_sfldesktop
✓ Logged in to github.com as ...
✓ Logged in to gitlab.com as ...
```

## SSH agent forwarding (optional)

By default the container uses SSH key files directly from the `~/.ssh` mount — no agent
needed for unprotected keys (the common case). Use agent forwarding when:

- Your keys have a **passphrase** and you want it cached (no repeated prompts)
- You need **`ssh -A` / `ProxyJump`** agent forwarding through bastion hosts inside the container

### Using the helper script

```bash
bash ~/Code/kandev/kandev-ssh-agent.sh
```

This script:
1. Reuses an already-running `ssh-agent` if `SSH_AUTH_SOCK` is valid; otherwise starts one
2. Loads `~/.ssh/ayattara_key` and `~/.ssh/github_yattdev_sfldesktop` (edit the script to add/remove keys)
3. Restarts the kandev container with `docker-compose.ssh-agent.yml` layered in, which:
   - Bind-mounts the host agent socket at `/run/ssh-agent.sock` inside the container
   - Sets `SSH_AUTH_SOCK=/run/ssh-agent.sock` in the container environment

To load a different or extra key:

```bash
bash ~/Code/kandev/kandev-ssh-agent.sh ~/.ssh/socodevi
```

### Manual agent forwarding

```bash
eval $(ssh-agent) && ssh-add ~/.ssh/ayattara_key
SSH_AUTH_SOCK=$SSH_AUTH_SOCK docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f docker-compose.ssh-agent.yml \
  -p kandev up -d --force-recreate
```

### Verify agent is forwarded

```bash
docker exec -it kandev ssh-add -l   # should list loaded key fingerprints
```

## Client access (from yattara-pc)

Add to `/etc/hosts`:

```
10.0.0.182        board.home
192.168.50.211    board.sfl
```

Then open:
- http://board.home — mini-desktop kandev (always available)
- http://board.sfl — sfl-desktop kandev (SFL VPN must be up: `sudo nmcli connection up "SFL Montreal VPN"`)

Direct backend port is `38429`. On sfl-desktop, port `80` is redirected to `38429` via iptables NAT so `http://board.sfl` (no port) works. On mini-desktop, Caddy handles `board.home` — no port needed.

## Network / iptables (sfl-desktop)

### Port map

| Port | Bound to | What |
|---|---|---|
| `38429` | `0.0.0.0` | Kandev unified server — backend + web UI |
| `80` | N/A — no listener | Redirected → `38429` by iptables NAT |

### Why two iptables rules are required

Linux iptables NAT has two chains that must both be set for `http://board.sfl` to work everywhere:

| Chain | Applies to | Use case |
|---|---|---|
| `PREROUTING` | Packets arriving **from outside** the machine | Other PCs on the network (yattara-pc, mini-desktop) |
| `OUTPUT` | Packets generated **locally** on sfl-desktop | Browser/curl running on sfl-desktop itself |

**Classic symptom of a missing OUTPUT rule:** `http://board.sfl` works from yattara-pc but gives *Connection refused* from a browser or `curl` on sfl-desktop itself.

Both rules must be present:

```
-A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429
-A OUTPUT     -p tcp --dport 80 -j REDIRECT --to-port 38429
```

These are persisted in `/etc/ufw/before.rules` and applied at boot by UFW.

### Diagnose

```bash
# Are both rules active right now?
sudo iptables -t nat -L PREROUTING -n | grep 38429   # should show a line
sudo iptables -t nat -L OUTPUT     -n | grep 38429   # should show a line

# Quick connectivity test
curl -o /dev/null -w "%{http_code}" http://board.sfl/   # expect 200
curl -o /dev/null -w "%{http_code}" http://localhost:38429/  # direct, no NAT
```

### Fix (if rules are missing after reboot)

If UFW reload didn't pick up `before.rules` correctly, re-apply live without sudo using Docker:

```bash
# Apply both rules via privileged container (no sudo password needed — uses docker group)
docker run --rm --net=host --cap-add=NET_ADMIN --privileged alpine \
  sh -c 'apk add -q iptables && \
         iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429 && \
         iptables -t nat -A OUTPUT     -p tcp --dport 80 -j REDIRECT --to-port 38429 && \
         echo OK'

# Or simply re-run the idempotent install script (will prompt for sudo):
bash ~/Code/kandev/install-sfl.sh
```

## Deploy

### mini-desktop

```bash
# 1. Copy compose + scripts (deploy path: ~/Code/kandev)
rsync -avz stack/kandev/ alassane@10.0.0.182:~/Code/kandev/

# 2. (One-time) migrate existing named volume to bind path
ssh alassane@10.0.0.182 '
  mkdir -p ~/.local/share/kandev ~/Code
  if docker volume inspect kandev_kandev-data >/dev/null 2>&1; then
    docker run --rm -v kandev_kandev-data:/from -v ~/.local/share/kandev:/to alpine \
      sh -c "cp -a /from/. /to/"
  fi
'

# 3. Build local image then start
ssh alassane@10.0.0.182 "cd ~/Code/kandev && docker compose build && docker compose up -d --force-recreate"

# 4. Install sync cron (now runs as root via /etc/cron.d, not user crontab)
ssh alassane@10.0.0.182 "sudo bash ~/Code/kandev/install-mini.sh"

# 5. Verify
ssh alassane@10.0.0.182 "docker ps --filter name=kandev; ls ~/Code | head"
```

### sfl-desktop (when SFL VPN is up)

```bash
sudo nmcli connection up "SFL Montreal VPN"

rsync -avz stack/kandev/ ayattara@sfl-desktop:~/Code/kandev/

# Setup: systemd auto-start + UFW rules + port 80 → 38429 redirect + start kandev
ssh ayattara@sfl-desktop 'bash ~/Code/kandev/install-sfl.sh'

# One-time push current state from mini to sfl
sudo bash stack/kandev/sync-to-sfl.sh
```

`install-sfl.sh` is idempotent — re-run anytime to re-sync the systemd unit,
UFW rules and port-80 redirect. It will prompt for sudo when needed.

> **After deploy**, authenticate the CLI tools inside the container (once per host):
> ```bash
> docker exec -it kandev gh auth login
> docker exec -it kandev glab auth login
> ```

## Sync

| Direction | Mode | Trigger |
|---|---|---|
| sfl → mini | automatic | `/etc/cron.d/kandev-sync-from-sfl` runs `*/10 * * * *` as **root** on mini-desktop (only runs if VPN is up + ssh works) |
| mini → sfl | manual | `sudo bash stack/kandev/sync-to-sfl.sh` (run on mini-desktop) |

Logs: `~/logs/kandev-sync.log` on mini-desktop (root writes, alassane owns).

### Why root?

Some paths under `~/Code/` on mini-desktop are owned by `root:root` (typically `*/.github/mcp.json` created by docker containers writing to bind mounts). A user-cron rsync gets `Permission denied` writing into them and exits rc=23.

The scripts run as **root** so the rsync receiver can write anywhere, but pass `--chown=alassane:alassane` (sfl → mini) and `--chown=ayattara:ayattara` (mini → sfl) so files always end up owned by the **normal user** on the destination — the sync itself never creates root-owned files.

SSH still connects to sfl-desktop as the non-root user `ayattara`, using alassane's key (`-i /home/alassane/.ssh/mini-desk -o User=ayattara -F /home/alassane/.ssh/config`).

### Diagnostic

Each sync logs any paths under `~/Code/` not owned by `alassane` (no auto-fix — silently changing files owned by other processes could break them). Inspect:

```bash
ssh alassane@10.0.0.182 "grep -A50 'non-user-owned' ~/logs/kandev-sync.log | tail -60"
```

To normalize ownership of a specific path:

```bash
ssh alassane@10.0.0.182 "sudo chown -R alassane:alassane ~/Code/<path>"
```

What gets synced:
- `~/Code/` — projects (excludes `node_modules`, `.venv`, `__pycache__`, `.next`, `dist`, `build`)
- `~/.local/share/kandev/` — kandev sqlite DB, sessions, config

Why cron over realtime (Syncthing/inotify):
- No write conflicts when both hosts edit the same file
- Auditable log
- Survives offline periods cleanly

## Workflow

| Situation | What to do |
|---|---|
| Working at home (evenings, weekends) | Use board.home — mini-desktop has latest sfl state (synced every 10min while VPN was up) |
| About to switch back to office | If you made changes on mini, run `sync-to-sfl.sh` before resuming on sfl |
| Working at office | Use board.sfl — full power |
| VPN drops at home | Sync just skips; resumes next cycle automatically |

## Caveats — `~/Code` on mini-desktop

mini-desktop's `~/Code/` is **shared** between user workspaces AND production service dirs
referenced by systemd units (`~/Code/kandev/`, `~/Code/vpn/`, `~/Code/reverse-proxy/`,
`~/Code/nextcloud-data/`, `~/Code/agent-os/`, `~/Code/vaultwarden/`, `~/Code/nanoclaw/`,
`~/Code/onecli/`, `~/Code/vibe-kanban/`).

Sync scripts **explicitly exclude** these top-level dirs so the rsync `--delete` never
wipes production services. If you add a new infra service under `~/Code/` on mini-desktop,
**add it to the excludes** in both `sync-from-sfl.sh` and `sync-to-sfl.sh`.

## Update kandev

Docker images are **not** updated by `apt upgrade` or system updates — they must be pulled explicitly.

Both hosts run a **daily auto-update cron at 03:30** that:
1. Pulls the latest upstream image (`ghcr.io/kdlbs/kandev:latest`)
2. If the upstream digest changed, **rebuilds `kandev-local:latest`** on top of it (so
   SSH, gh, glab and git config are always present in the running container)
3. Restarts the container only if the image actually changed (no unnecessary restarts)

Set `SKIP_LOCAL_BUILD=1` in the environment to bypass the rebuild step and use the upstream
image directly (useful for debugging).

| Host | Mechanism | Log |
|---|---|---|
| mini-desktop | `/etc/cron.d/kandev-update` (root) | `~/logs/kandev-update.log` |
| sfl-desktop | user crontab (`ayattara`) | `~/logs/kandev-update.log` |

### Manual update

```bash
# mini-desktop
ssh alassane@10.0.0.182 "bash ~/Code/kandev/update.sh"
# sfl-desktop (with VPN)
ssh ayattara@sfl-desktop  "bash ~/Code/kandev/update.sh"
```

### Check update log

```bash
ssh alassane@10.0.0.182 "tail -20 ~/logs/kandev-update.log"
ssh ayattara@sfl-desktop  "tail -20 ~/logs/kandev-update.log"
```
