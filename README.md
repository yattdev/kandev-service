# Kandev — Three-Host Architecture

Three **identical** kandev instances sharing live-replicated data.
**mini-desktop is the central hub** — it holds the Litestream replica and restic snapshot repo.
Satellites (sfl-desktop, yattara-pc) restore from the hub on startup and replicate back continuously.

## Hosts

| Host | IP | User | URL | Role |
|---|---|---|---|---|
| mini-desktop | 10.0.0.182 | alassane | https://board.home | Hub + always-on home dev |
| sfl-desktop | 192.168.50.211 | ayattara | http://board.sfl | Powerful workstation, office hours (SFL VPN) |
| yattara-pc | 127.0.0.1 | yattara | http://board.local | Local dev machine, VPN-independent fallback |

All hosts use:
- `~/Code` — projects/workspaces (bind-mounted as `/data/home/Code` in container)
- `~/.local/share/kandev` — kandev data dir (sqlite DB + sessions, mounted as `/data`)

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
├── docker-compose.yml             # Base service definition (upstream image)
├── docker-compose.override.yml    # Auto-merged: local build + host identity mounts
├── docker-compose.litestream.yml  # Litestream sidecar (live SQLite replication to hub)
├── docker-compose.ssh-agent.yml   # Optional overlay: SSH agent socket forwarding
├── Dockerfile.local               # Extends upstream image (ssh, gh, glab, git config)
├── Dockerfile.main-branch         # Temporary: builds kandev from github.com/kdlbs/kandev@main
├── kandev-build-main.sh           # Helper: build/run/revert the main-branch image (see below)
├── litestream.yml                 # Litestream config template (installed to ~/.config/)
├── kandev-start.sh                # Start helper: freshest-wins litestream restore → compose up
├── kandev-start-mini.sh           # Hub start helper: restore from freshest satellite replica
├── kandev-pull.sh                 # Manual/cron: check for newer data → pull if behind → start
├── kandev-restic-backup.sh        # Daily restic snapshot → mini-desktop repo
├── install-mini.sh                # Setup for mini-desktop (hub: replica dir, restic repo, crons)
├── install-sfl.sh                 # Setup for sfl-desktop (systemd, UFW, NAT, Litestream, crons)
├── install-yattara.sh             # Setup for yattara-pc (systemd, iptables, board.local, Litestream)
├── update.sh                      # Pull upstream + rebuild local image + restart + sync toolchains
├── setup-toolchains.sh            # Install/sync mise language toolchains into persistent volume
├── mise.default.toml              # Global mise tool versions (baked into image as /etc/mise/config.toml)
├── kandev-ssh-agent.sh            # Helper: start ssh-agent and restart kandev with it
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
| Google Chrome + `chromedriver` | Headless browser tests: karma `ChromeHeadless`, puppeteer, Selenium, Dusk (see below) |
| git system config | `safe.directory = *` — prevents "dubious ownership" errors (see below) |
| `sudo` (passwordless for `kandev`) | Lets the `kandev` user become root inside the container for one-off tasks (installing a missing package, fixing permissions) without `docker exec -u root` |

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
              ├── apt (dl.google.com repo): google-chrome-stable + fonts
              ├── chromedriver (Chrome-for-Testing, version-matched)
              ├── sudo (kandev: NOPASSWD:ALL via /etc/sudoers.d/kandev)
              └── git config --system safe.directory '*'
                      └─> kandev-local:latest
```

`update.sh` pulls the upstream image daily and, if it changed, automatically rebuilds
`kandev-local:latest` on top of the new base before restarting the container. After a
successful rebuild it also runs `setup-toolchains.sh` to sync the mise language
toolchains (node, python, go, java, ruby, php, dotnet) into the persistent `/data`
volume — idempotent and cheap on days nothing changed, so this needs no manual step.
Set `SYNC_TOOLCHAINS=0` before calling `update.sh` to skip it.

### Running a fix from `main` ahead of release (`kandev-build-main.sh`)

When a fix has landed on [`kdlbs/kandev@main`](https://github.com/kdlbs/kandev) but
hasn't shipped in a tagged release yet, `kandev-build-main.sh` builds it from source
and swaps it in **temporarily**, without touching `Dockerfile.local`,
`docker-compose.override.yml`, or `update.sh`:

```bash
bash ~/Code/kandev/kandev-build-main.sh                # build + run main
bash ~/Code/kandev/kandev-build-main.sh --ref some-branch  # build a specific branch/tag/commit
bash ~/Code/kandev/kandev-build-main.sh --no-test       # skip the test.sh run at the end
bash ~/Code/kandev/kandev-build-main.sh --revert        # restore the last release-based backup
```

It compiles the Go backend + web app from source (`Dockerfile.main-branch`) and layers
just the resulting binaries onto the existing release-based `kandev-local:latest`,
health-checking the container afterward and auto-rolling back on failure — mirroring
`update.sh`'s own rollback safety net. Because the compose build config still points at
`Dockerfile.local` + the upstream release image, this is self-reverting: the next
`docker compose build` (run manually, or automatically by `update.sh` once the next
release ships) rebuilds `kandev-local:latest` from the release again and discards the
main-branch layer.

### Browser tests (headless Chrome)

Chrome, `chromedriver`, and the fonts/libraries headless rendering needs are baked into
the image, so browser test suites run inside the container with **no project-side
configuration**:

```bash
docker exec -u kandev kandev bash -lc 'cd /data/home/Code/<project> && npx ng test --watch=false --browsers=ChromeHeadless'
```

| Variable | Value | Used by |
|---|---|---|
| `CHROME_BIN` / `CHROMIUM_BIN` | `/usr/local/bin/google-chrome` | karma-chrome-launcher, most CI scripts |
| `CHROME_PATH` | `/usr/local/bin/google-chrome` | lighthouse, chrome-launcher |
| `PUPPETEER_EXECUTABLE_PATH` | `/usr/local/bin/google-chrome` | puppeteer / jest-puppeteer |
| `PUPPETEER_SKIP_DOWNLOAD` | `true` | stops every `npm install` re-downloading Chrome |

`/usr/local/bin/google-chrome` is a **wrapper** that adds `--no-sandbox` before exec'ing
the real binary at `/usr/bin/google-chrome`. Chrome's sandbox needs unprivileged user
namespaces, which Docker's default seccomp profile blocks — without the wrapper every
launch aborts with `Failed to move to new namespace … Operation not permitted`, and each
project would have to define its own `ChromeHeadlessNoSandbox` launcher. `/dev/shm` is
raised to 2 GB (`shm_size` in `docker-compose.override.yml`) because Chrome crashes
mid-suite on Docker's 64 MB default.

**Playwright** manages its own pinned browsers; install them once per project —
they persist in `~/.cache/ms-playwright` (on the `/data` bind mount):

```bash
docker exec -u kandev kandev bash -lc 'cd /data/home/Code/<project> && npx playwright install chromium'
```

Quick check that the browser stack is healthy:

```bash
docker exec -u kandev kandev google-chrome --headless --dump-dom https://example.com | head -3
docker exec -u kandev kandev chromedriver --version
```

### Root privileges for the `kandev` user

`kandev` has passwordless `sudo` inside the container (`/etc/sudoers.d/kandev`, baked
in by `Dockerfile.local`). Use it for one-off root tasks without switching to
`docker exec -u root`:

```bash
docker exec -u kandev kandev sudo apt-get update
docker exec -u kandev kandev sudo chown -R kandev:kandev /data/some/path
```

`/data` itself is already owned by `kandev:kandev` on every container start (the
entrypoint's `chown -R kandev:kandev /data`, see "Entrypoint patch" in `CLAUDE.md`), so
this is mainly for edge cases — files left behind with another owner, or installing a
package temporarily to debug something. It does **not** change what the mounted Docker
socket / `docker` group grants; that access is separate (see the Docker CLI section
above).

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

`/etc/hosts` on yattara-pc (already configured):

```
10.0.0.182        board.home
192.168.50.211    board.sfl
```

For `board.local` (yattara-pc's own kandev), `install-yattara.sh` adds:
```
127.0.0.1         board.local
```

| URL | Host | VPN needed |
|---|---|---|
| https://board.home | mini-desktop (10.0.0.182) | No — home LAN |
| http://board.sfl | sfl-desktop (192.168.50.211) | Yes — `sudo nmcli connection up "SFL Montreal VPN"` |
| http://board.local | yattara-pc (127.0.0.1) | No — local |

> **Fixed bug — `board.sfl`/`board.home` used to show wrong/stale data when browsed from yattara-pc.**
> Root cause: `install-yattara.sh` set an **unscoped** iptables `OUTPUT` NAT rule (`--dport 80 -j REDIRECT --to-port 38429` with no `-d` filter), so *any* outbound port-80 request from yattara-pc — including to board.sfl, board.home, or any external website — was silently redirected to yattara-pc's own local kandev instead of leaving the machine. Confirmed by stopping yattara-pc's local kandev: `board.sfl:80` then failed outright instead of reaching sfl-desktop.
> **Fix:** the OUTPUT rule is now scoped to `-d 127.0.0.1/32` (only catches the host's own loopback traffic for `board.local`). Re-run `bash ~/Code/kandev/install-yattara.sh` (needs sudo) to apply on hosts still running the old unscoped rule. See "Common failure modes" in `CLAUDE.md` for full details.

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

### mini-desktop (hub)

```bash
# 1. Sync scripts
rsync -avz stack/kandev/ alassane@10.0.0.182:~/Code/kandev/

# 2. (One-time) migrate existing named volume to bind path
ssh alassane@10.0.0.182 '
  mkdir -p ~/.local/share/kandev ~/Code
  if docker volume inspect kandev_kandev-data >/dev/null 2>&1; then
    docker run --rm -v kandev_kandev-data:/from -v ~/.local/share/kandev:/to alpine \
      sh -c "cp -a /from/. /to/"
  fi
'

# 3. Setup hub: create litestream-replicas/, init restic repo, fix crons, upgrade image
ssh alassane@10.0.0.182 "sudo bash ~/Code/kandev/install-mini.sh"

# 4. Build + start kandev
ssh alassane@10.0.0.182 "cd ~/Code/kandev && docker compose build && docker compose up -d --force-recreate"
```

### sfl-desktop (when SFL VPN is up)

```bash
sudo nmcli connection up "SFL Montreal VPN"

rsync -avz stack/kandev/ ayattara@sfl-desktop:~/Code/kandev/

# Setup: systemd, UFW, NAT, Litestream config, crons, start with restore
ssh ayattara@sfl-desktop 'bash ~/Code/kandev/install-sfl.sh'
```

> **Note:** `install-sfl.sh` will auto-detect the SSH key that reaches mini-desktop.
> If it prints a warning, add your key: `ssh-copy-id -i ~/.ssh/KEY alassane@10.0.0.182`

### yattara-pc (local)

```bash
# 1. Copy password from mini-desktop (one-time, after install-mini.sh has run)
scp alassane@10.0.0.182:.config/restic/kandev-backup-password \
    ~/.config/restic/kandev-backup-password
chmod 600 ~/.config/restic/kandev-backup-password

# 2. Sync scripts
rsync -avz stack/kandev/ ~/Code/kandev/

# 3. Setup: systemd, iptables 80→38429, board.local DNS, Litestream, restore + start
bash ~/Code/kandev/install-yattara.sh
```

## Sync — Litestream (live) + Restic (history)

### Architecture

```
kandev.db  ──Litestream──► ~/litestream-replicas/kandev/  on mini-desktop  (live WAL, seconds lag)
kandev/    ────Restic────► ~/restic-repos/kandev-backup   on mini-desktop  (daily snapshots)
```

**mini-desktop is the hub.** It stores the Litestream SFTP replica and the restic repo. It does NOT run Litestream itself.

### Litestream (live SQLite replication)

Litestream runs as a sidecar container alongside kandev on sfl-desktop and yattara-pc. It:
- Streams WAL (write-ahead log) changes to mini-desktop via SFTP — lag is seconds, not hours
- On container startup (`kandev-start.sh`): restores latest state from mini before kandev starts
- Is SQLite-native: no need to stop kandev, no corruption risk

```bash
# Check litestream is replicating (on sfl or yattara)
docker logs kandev-litestream 2>&1 | tail -5

# Check replica files on mini-desktop
ssh alassane@10.0.0.182 "ls -lh ~/litestream-replicas/kandev/"

# Manual restore (stop kandev first)
docker stop kandev
litestream restore sftp://alassane@10.0.0.182/litestream-replicas/kandev \
  ~/.local/share/kandev/data/kandev.db
docker start kandev
```

### Manual check & pull latest (`kandev-pull.sh`)

Litestream **pushes** the active host's writes to mini within ~1s, but other hosts
only **pull** that data when kandev restarts. `kandev-pull.sh` lets you pull the
freshest state on demand — run it when you sit down at a machine to make sure the
board matches where you left off on another host.

```bash
# On EITHER host (yattara-pc or sfl-desktop):
bash ~/Code/kandev/kandev-pull.sh            # check → pull if behind → ensure kandev is up
bash ~/Code/kandev/kandev-pull.sh --dry-run  # report only, change nothing
bash ~/Code/kandev/kandev-pull.sh --force    # pull the freshest replica no matter what
```

What it does:
1. Asks mini which host's replica is **freshest**, and how fresh **this** host's own
   push is (both mtimes read from mini's filesystem → no clock-skew guessing).
2. Reads who holds the **active-writer lock**.
3. Decides:
   - **This host is the active writer** → nothing to pull (your data is authoritative).
     `--force` overrides.
   - **A peer replica is newer** → you're behind → stops kandev, restores the freshest
     data (via `kandev-start.sh`), restarts.
   - **Already current / mini unreachable** → leaves a running kandev untouched.

Safe to run anytime: it no-ops when you're the writer, already current, or offline,
so it never reverts local edits or strips a live replication sidecar.

> **sfl-desktop only reaches mini when the `sfl-desktop` WireGuard tunnel is up.**
> If mini is unreachable the script reports it and leaves kandev running as-is —
> bring the tunnel up (`nmcli connection up sfl-desktop`) first.

This same script runs automatically via cron at **06:00 / 13:00 / 18:00** on both
satellites (see Cron summary) so cross-host visibility stays near-current without
manual restarts. Example output:

```
[pull] host-id=yattara  writer=none
[pull] freshest replica : 'sfl'  (2026-07-08 21:45:37)
[pull] our own replica  : 2026-07-08 05:42:27
[pull] BEHIND by ~57550s vs peer 'sfl' — pulling freshest data.
```

### Restic (snapshot history)

Daily at 03:00 on each satellite host, `kandev-restic-backup.sh`:
1. Briefly stops kandev for a consistent SQLite snapshot
2. Runs `restic backup` → new named snapshot in mini's repo
3. Prunes old snapshots (keeps 7 daily, 4 weekly, 3 monthly)
4. Restarts kandev

```bash
# View snapshot history (like git log)
~/bin/restic -r sftp:alassane@10.0.0.182:restic-repos/kandev-backup snapshots

# Restore a specific snapshot
~/bin/restic -r sftp:alassane@10.0.0.182:restic-repos/kandev-backup restore SNAPSHOT_ID \
  --target / --include ~/.local/share/kandev/

# Manual backup now
bash ~/Code/kandev/kandev-restic-backup.sh
```

Restic password file: `~/.config/restic/kandev-backup-password` (same on all hosts, generated by `install-mini.sh`).

### Cron summary

| Host | Cron | What |
|---|---|---|
| mini-desktop | `30 3 * * *` (root, `/etc/cron.d/kandev-update`) | Image update |
| mini-desktop | `0 3 * * *` (root, `/etc/cron.d/kandev-backup`) | Restic snapshot |
| sfl-desktop | `30 3 * * *` (user crontab) | Image update |
| sfl-desktop | `0 3 * * *` (user crontab) | Restic snapshot |
| sfl-desktop | `0 6,13,18 * * *` (user crontab) | **Pull latest** (`kandev-pull.sh`) |
| yattara-pc | `30 3 * * *` (user crontab) | Image update |
| yattara-pc | `0 3 * * *` (user crontab) | Restic snapshot |
| yattara-pc | `0 6,13,18 * * *` (user crontab) | **Pull latest** (`kandev-pull.sh`) |

Litestream replication is continuous (always-on, no cron needed). The periodic pull
only matters on the non-writer host(s), where it refreshes the board to the latest
synced state; it no-ops on the active writer.

### Logs

```bash
# Litestream replication (sfl or yattara)
docker logs kandev-litestream --tail 20

# Manual/periodic pull (sfl or yattara)
tail -30 ~/logs/kandev-sync.log

# Restic backup
tail -30 ~/logs/kandev-backup.log

# Image update
tail -30 ~/logs/kandev-update.log
```

## Workflow

| Situation | What to do |
|---|---|
| **Working at office (sfl-desktop)** | Use `board.sfl` — SFL VPN required. Litestream replicates changes to mini in seconds |
| **Switching to home** | Just open `board.home` or `board.local` — Litestream restore on start gives you sfl's latest state |
| **Working at home on yattara-pc** | Use `board.local` (127.0.0.1) — VPN-independent local instance |
| **Working on mini-desktop** | Use `board.home` — always available, Caddy serves HTTPS |
| **sfl-desktop down / VPN not available** | Use `board.home` (mini) or `board.local` (yattara-pc) — same data |
| **Recover past state** | `restic snapshots` to browse history, `restic restore` to go back |

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

All three hosts run a **daily auto-update cron at 03:30** that:
1. Pulls the latest upstream image (`ghcr.io/kdlbs/kandev:latest`)
2. If the upstream digest changed, **rebuilds `kandev-local:latest`** on top of it
3. Restarts the container only if the image actually changed
4. If rebuilt, syncs mise language toolchains into the persistent volume via
   `setup-toolchains.sh` (idempotent — a no-op on days nothing changed)

| Host | Mechanism | Log |
|---|---|---|
| mini-desktop | `/etc/cron.d/kandev-update` (root) | `~/logs/kandev-update.log` |
| sfl-desktop | user crontab (`ayattara`) | `~/logs/kandev-update.log` |
| yattara-pc | user crontab (`yattara`) | `~/logs/kandev-update.log` |

### Manual update

```bash
ssh alassane@10.0.0.182 "bash ~/Code/kandev/update.sh"           # mini-desktop
ssh ayattara@sfl-desktop "bash ~/Code/kandev/update.sh"           # sfl-desktop (VPN)
bash ~/Code/kandev/update.sh                                       # yattara-pc (local)
```

### Check update log

```bash
ssh alassane@10.0.0.182 "tail -20 ~/logs/kandev-update.log"
ssh ayattara@sfl-desktop "tail -20 ~/logs/kandev-update.log"
tail -20 ~/logs/kandev-update.log                                  # yattara-pc
```
