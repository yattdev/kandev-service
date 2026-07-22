# CLAUDE.md — AI assistant context for kandev

This file provides essential context for AI coding assistants working in this repository.
Read it fully before making any changes.

## What this project is

Infrastructure-as-code for running [kandev](https://github.com/kdlbs/kandev) on two hosts
that share a common workspace:

| Host | Role |
|---|---|
| **sfl-desktop** (`192.168.50.211`, user `ayattara`) | Powerful workstation, used during office hours via SFL VPN |
| **mini-desktop** (`10.0.0.182`, user `alassane`) | Always-on home machine, auto-syncs from sfl every 10 min |

The kandev UI is reachable at `http://board.sfl` and `http://board.home`.

---

## Build, test, run

### Build the local image

```bash
cd ~/Code/kandev
docker compose build           # uses docker-compose.override.yml automatically
```

> **Network (sfl-desktop):** A transparent corporate proxy intercepts connections.
> `build.network: host` is already set in `docker-compose.override.yml` to work around it.
> If you add new `RUN` steps with `curl` or `apt-get`, they inherit this setting automatically.

### Start / restart the container

```bash
docker compose up -d --force-recreate
```

### Run tests

```bash
bash ~/Code/kandev/test.sh
```

Or build and test in one step:

```bash
bash ~/Code/kandev/test.sh --build
```

### Check container health

```bash
docker ps --filter name=kandev
docker logs kandev --tail 30
docker inspect kandev --format 'status={{.State.Status}} restarts={{.RestartCount}}'
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:38429/
```

---

## Mandatory rule: tests must pass before reporting completion

**Every change that touches any of the following requires a passing `test.sh` run:**

| Change type | Why tests are needed |
|---|---|
| `Dockerfile.local` | New packages or layers might break the image build or remove a binary |
| `docker-compose.yml` or `docker-compose.override.yml` | Env var or volume changes affect identity, git, SSH, and service reachability |
| `docker-compose.ssh-agent.yml` | SSH agent socket forwarding must still work |
| `docker-entrypoint-local.sh` | Entrypoint regressions put the container in a crash loop |
| `update.sh` | Must still pull, rebuild, and restart correctly |
| Any `install-*.sh` | Host setup changes affect cron, mountpoints, and service continuity |

**Workflow for any change:**

```
1. Make the change
2. Rebuild if Dockerfile.local was modified:  docker compose build
3. Restart container if compose files changed: docker compose up -d --force-recreate
4. Run:  bash ~/Code/kandev/test.sh
5. All 29 tests must be green
6. Commit
7. Only then report the task as complete
```

If any test fails, **fix the root cause before committing**. Do not skip or weaken tests to
make them pass — fix the underlying issue instead.

---

## Architecture and key design decisions

### Docker Compose file layering

```
docker-compose.yml            ← upstream image, base env vars, core volumes
      +
docker-compose.override.yml   ← auto-merged: local build + host identity mounts
      +
docker-compose.ssh-agent.yml  ← optional: SSH agent socket forwarding
                                  (used only via kandev-ssh-agent.sh)
```

Docker Compose automatically merges `docker-compose.override.yml` on every
`docker compose` command. `docker-compose.ssh-agent.yml` is only applied when
explicitly passed with `-f`.

### Local image (`kandev-local:latest`)

`Dockerfile.local` extends `ghcr.io/kdlbs/kandev:latest` (Debian 12) with:
- `openssh-client`, `gh` (GitHub CLI), `glab` (GitLab CLI)
- `git config --system safe.directory '*'` baked into `/etc/gitconfig`
- A patched `docker-entrypoint.sh` (see below)

The built image is tagged `kandev-local:latest`. `docker-compose.override.yml` sets
both `build:` and `image: kandev-local:latest` so the tag is used for `docker compose up`.

### Entrypoint patch (`docker-entrypoint-local.sh`)

The upstream entrypoint does `chown -R kandev:kandev /data` under `set -e`.
Mounting `~/.ssh` and `~/.gitconfig` as `:ro` causes `chown` to fail → container
crash-loops. The patched version adds `2>/dev/null || true` so:
- All writable paths under `/data` are still chowned to `kandev:kandev`
- `:ro` mounts are silently skipped

**Critical:** if the upstream entrypoint changes in a new image version, the patch must
be re-verified. `test.sh` section 1 checks this automatically.

### UID matching

| | UID | GID |
|---|---|---|
| Host user `ayattara` | 1000 | 1000 |
| Container user `kandev` | 1000 | 999 |

UIDs match → all bind-mounted files (owned by UID 1000 on the host) are
readable/writable as `kandev` inside the container without `chmod` or `chown`.
GID difference is harmless because SSH keys and gitconfig are `600`/`700` (owner-only).

### `HOME=/data/home`

The container's home is `/data/home`, not `/home/kandev`. This is intentional:
- `~/.local/share/kandev` on the host maps to `/data` inside the container
- The `HOME` override makes `/data/home` the base so `~` expands correctly for SSH, git, gh, glab
- All `IdentityFile ~/.ssh/...` entries in `~/.ssh/config` resolve to `/data/home/.ssh/...`

### git `safe.directory = *`

The host `~/.gitconfig` contains `safe.directory = /home/ayattara/Code/scsl` (an absolute
host path). Inside the container the same repo is at `/data/home/Code/scsl`. Additionally,
docker-leftover root-owned files under `~/Code/` trigger git ownership errors.
`git config --system safe.directory '*'` in `/etc/gitconfig` bypasses all of this.

### Language toolchains (mise) — no Dockerfile edit per project

Projects need many runtimes (Node, Python, Go, Java, Ruby, PHP, .NET). Rather than
adding each dependency to `Dockerfile.local`, the image ships **`mise`** (a polyglot
version manager) plus `build-essential` and common dev headers. Design:

- **Global defaults** matched to the host live in `/etc/mise/config.toml`
  (baked from `mise.default.toml`). Projects override them with their own
  `mise.toml` / `.tool-versions` / `.nvmrc` / `.python-version`, which mise
  auto-installs on demand.
- **Nothing is pre-installed in the image.** Because `HOME=/data/home` is on the
  persistent bind mount, mise installs runtimes to
  `/data/home/.local/share/mise` — they **survive image rebuilds and container
  recreation**. The same is true for every default per-user cache
  (`~/.cache/pip`, `~/.npm`, `~/go`, `~/.cargo`, `~/.m2`).
- **Shims on PATH:** `Dockerfile.local` puts `…/mise/shims` on `PATH` via `ENV`
  so tools resolve even in non-interactive `bash -c` shells (how agents run).
- **First-time population:** run `bash setup-toolchains.sh` once to install the
  global toolchains into the volume. Precompiled tools (node/python/go/java/dotnet)
  are fast; ruby/php compile from source (hence the baked-in build headers).

Bottom line: adding a project or a new dependency requires **no Dockerfile change** —
the agent just runs the project's own install command (`pip install -r`, `npm install`,
`go mod download`, `bundle install`), and everything persists in `/data`.

### Transparent proxy (sfl-desktop)

The corporate network uses a transparent proxy that intercepts HTTP/HTTPS and injects
its own TLS certificate. This causes `apt-get` and `curl` to fail during Docker builds
with `Clearsigned file isn't valid, got 'NOSPLIT'`. The fix is `network: host` in the
`build:` section of `docker-compose.override.yml`.

### SSH agent forwarding

Not required for daily use (keys are unprotected RSA keys, direct key-file auth works).
Use `kandev-ssh-agent.sh` when:
- Keys have a passphrase and you need caching
- You need `ssh -A` / `ProxyJump` forwarding through bastion hosts inside the container

---

## File reference

| File | What it does |
|---|---|
| `docker-compose.yml` | Base service: upstream image, restart policy, `network_mode: host`, core env vars and volumes |
| `docker-compose.override.yml` | Local build, `USER`/`LOGNAME` env, SSH/git/gh/glab identity mounts |
| `docker-compose.ssh-agent.yml` | Optional SSH agent socket overlay |
| `Dockerfile.local` | Extends upstream: adds SSH, gh, glab, Docker CLI, build toolchain, mise; patches git and entrypoint |
| `docker-entrypoint-local.sh` | Upstream entrypoint + `|| true` chown fix for :ro mounts |
| `mise.default.toml` | System-wide mise config (`/etc/mise/config.toml`): global language versions matched to host |
| `setup-toolchains.sh` | One-time helper: installs the mise language toolchains into the persistent `/data` volume |
| `test.sh` | 29 automated tests covering image, container, service, identity, SSH, git, CLI tools, toolchains |
| `update.sh` | Daily cron: pull upstream → rebuild local → restart if changed |
| `kandev-ssh-agent.sh` | Helper: start/reuse ssh-agent, load keys, restart kandev with socket forwarding |
| `install-mini.sh` | One-time mini-desktop setup: sync cron, update cron, `/data/home/Code` mountpoint |
| `install-sfl.sh` | One-time sfl-desktop setup: systemd unit, UFW rules, port 80 → 38429 NAT |
| `sync-from-sfl.sh` | Rsync sfl → mini (run by root cron on mini-desktop every 10 min) |
| `sync-to-sfl.sh` | Rsync mini → sfl (run manually before switching to office) |

---

## Common failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| Container crash-loops, logs full of `chown: Read-only file system` | Entrypoint patch missing or overwritten by image update | Verify `docker-entrypoint-local.sh` has `\|\| true`; rebuild |
| `apt-get` fails with `NOSPLIT` during build | Transparent proxy, missing `network: host` | Ensure `build.network: host` in `docker-compose.override.yml` |
| `git` reports "dubious ownership" inside container | `safe.directory` not set in system config | Rebuild image; check `git config --system safe.directory` = `*` |
| `gh`/`glab` not authenticated after rebuild | Config mount missing or wrong path | Check `~/.config/gh` and `~/.config/glab-cli` are mounted rw |
| `$USER` = `kandev` instead of `ayattara` | `USER` env missing from override | Check `docker-compose.override.yml` `environment:` block |
| SSH uses wrong key for a host | `~/.ssh` not mounted or `HOME` wrong | Verify mount and `HOME=/data/home` |
| `http://board.sfl` unreachable | iptables NAT rules missing after reboot | Re-run `install-sfl.sh` or apply rules via privileged container (see README) |
| `http://board.sfl` unreachable after our changes | Container crash-loop | Check `docker inspect kandev --format '{{.RestartCount}}'`; run `test.sh` |
| `http://board.sfl` (or `board.home`, or literally any `http://` site) shows the **wrong data** or a stale/empty "Default Workspace" **when browsed from yattara-pc** | `install-yattara.sh` set an **unscoped** iptables `OUTPUT` NAT redirect — `-A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429` has no `-d` filter, so it matches port-80 packets to **any destination**, silently rewriting them to yattara-pc's own local kandev (127.0.0.1:38429) instead of letting them leave the host. Confirmed by stopping yattara-pc's local kandev container: `board.sfl:80` then failed outright (connection refused) instead of reaching sfl-desktop — proving the request never left the machine. (Earlier guess blaming the SFL corporate VPN was wrong — ruled out once the local-redirect rule was found.) | Fixed in `install-yattara.sh`: the OUTPUT rule is now scoped with `-d 127.0.0.1/32` so it only catches the host's own loopback traffic (browser on yattara-pc → `board.local`), and the old unscoped rule is actively removed (live + persisted in `/etc/ufw/before.rules`). Re-run `bash ~/Code/kandev/install-yattara.sh` (needs sudo) to apply after pulling this fix. |
| **mini-desktop only:** kandev container silently mounts `/root/...` (`~/.ssh`, `~/.gitconfig`, `~/.local/share/kandev`) instead of `/home/alassane/...` after a nightly cron rebuild — DB, `master.key`, and toolchains end up on the wrong path, invisible to any manual `docker compose` command run as `alassane` | `/etc/cron.d/kandev-update` runs `update.sh` **as root** (by design, for privileged ops), passing `USER_NAME=alassane USER_HOME=/home/alassane`. `update.sh` used `$USER_HOME` for its own `cd`/log paths but never did `export HOME="$USER_HOME"` — so `docker compose`'s own `${HOME}` substitution in `docker-compose.override.yml` independently resolved to root's real `$HOME=/root`, diverging silently. Confirmed via `~/logs/kandev-update.log`: the 2026-07-21 03:30 cron run flipped the mount; live DB + `master.key` were found only under `/root/.local/share/kandev/data/` (different `master.key` hash than alassane's stale copy — the two data trees are not interchangeable, since `master.key` decrypts secrets stored inside the otherwise-plain SQLite `kandev.db`) | Fixed in `update.sh`: added `export HOME="$USER_HOME"` right after computing `USER_HOME`, on all three hosts, so `${HOME}`-based compose mounts always resolve consistently regardless of which user/cron context invokes the script. If this recurs: compare `docker inspect kandev --format '{{range .Mounts}}{{.Source}}{{println}}{{end}}'` against the expected user's home; if wrong, back up the current (possibly stale) target path, `docker exec kandev tar -C /data/data -cf - . \| tar -C <correct-path>/data -xf -` to migrate the live DB/key/backups out of the container before recreating it as the correct user. **`/usr/local/sbin/kandev-update.sh`** (the actual root-cron target on mini-desktop) is a **static copy** made by `install-mini.sh` — it does NOT auto-update when `~/Code/kandev/update.sh` changes. Re-run `sudo bash ~/Code/kandev/install-mini.sh` on mini-desktop to refresh it after any `update.sh` change. |
