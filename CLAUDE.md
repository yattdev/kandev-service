# CLAUDE.md — AI assistant context for kandev

This file provides essential context for AI coding assistants working in this repository.
Read it fully before making any changes.

## What this project is

Infrastructure-as-code for running [kandev](https://github.com/kdlbs/kandev) on two hosts
that share a common workspace:

| Host | Role |
|---|---|
| **office-desktop** (`192.168.1.10`, user `alice`) | Powerful workstation, used during office hours via Corp VPN |
| **home-server** (`10.0.0.20`, user `bob`) | Always-on home machine, auto-syncs from office every 10 min |

The kandev UI is reachable at `http://board.office` and `http://board.home`.

> **Placeholders — this is a sanitized public repo.** All hostnames, usernames, and
> LAN IPs in the committed files (`office-desktop`/`alice`, `home-server`/`bob`,
> `laptop`/`carol`, `10.0.0.20`, `192.168.1.10`, `example-corp`, `Code/work-project`, …)
> are **generic examples**. The real values for THIS machine live in a git-ignored
> **`host.env`** at the repo root, which every script sources (falling back to the
> placeholders when it is absent). **Read `host.env` first** — its header maps each
> placeholder to the real host/user/IP so you don't act on the example values. If
> `host.env` is missing, copy it from `host.env.example`.

---

## Build, test, run

### Build the local image

```bash
cd ~/Code/kandev
docker compose build           # uses docker-compose.override.yml automatically
```

> **Network (office-desktop):** A transparent corporate proxy intercepts connections.
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
5. All 56 tests must be green
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
- Google Chrome + `chromedriver` for headless browser tests (see below)
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
| Host user `alice` | 1000 | 1000 |
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

The host `~/.gitconfig` contains `safe.directory = /home/alice/Code/work-project` (an absolute
host path). Inside the container the same repo is at `/data/home/Code/work-project`. Additionally,
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

### Headless browser testing (Chrome)

The upstream image ships no browser, so any project with browser tests (karma
`ChromeHeadless`, jest + puppeteer, Selenium/chromedriver, Rails system tests,
Laravel Dusk, Playwright) failed inside the container. `Dockerfile.local` now installs:

- **Google Chrome stable** from Google's apt repo on `amd64`; Debian `chromium` +
  `chromium-driver` on other architectures (Google publishes no arm64 Linux build).
  Both end up reachable as `google-chrome`, `chromium`, `chromium-browser`, `chrome`.
- **`chromedriver`**, version-matched to the installed Chrome via the
  Chrome-for-Testing download endpoint (falls back to "last known good" stable).
- **Fonts** (`fonts-liberation`, `fonts-noto*`, `fonts-dejavu-core`) — without real
  font packages headless renders come out as blank "tofu" boxes — plus the
  X/GTK/NSS libraries Playwright's own browser downloads need.

Two container-specific gotchas are handled so projects need no special config:

| Gotcha | Fix |
|---|---|
| Chrome's setuid sandbox needs unprivileged user namespaces, which Docker's default seccomp profile blocks → every launch aborts with `Failed to move to new namespace … Operation not permitted` | `/usr/local/bin/google-chrome` (ahead of `/usr/bin` on `PATH`) is a wrapper that `exec`s the real binary with `--no-sandbox`. Stock `ChromeHeadless` configs work unmodified; the unwrapped binary is still at `/usr/bin/google-chrome`. The alternative — `seccomp=unconfined` / `--cap-add=SYS_ADMIN` on the whole kandev container — was rejected as too broad. |
| Docker's default `/dev/shm` is 64 MB → Chrome dies mid-suite with `Target closed` / SIGBUS | `shm_size: 2gb` in `docker-compose.override.yml` (needs `docker compose up -d --force-recreate` to take effect, not just a rebuild) |

`CHROME_BIN`, `CHROMIUM_BIN`, `CHROME_PATH`, `PUPPETEER_EXECUTABLE_PATH` all point at
the wrapper, and `PUPPETEER_SKIP_DOWNLOAD=true` stops every `npm install` from pulling
a private Chrome copy. Playwright is left to manage its own pinned browsers — they land
in `~/.cache/ms-playwright`, which is persistent because `HOME=/data/home`
(`npx playwright install chromium`).

`test.sh` section 9 covers all of this, including a real headless render as user
`kandev` with **no** extra flags — that test is what proves the wrapper is in place.

### Docker-out-of-Docker and the host-path wrapper

`docker-compose.yml` bind-mounts `/var/run/docker.sock`. The container runs **no daemon
of its own** — the `docker` CLI is just an HTTP client, so every command it issues is
serviced by the **host's** daemon and every container it starts is a **sibling on the
host**, not a nested child. (`docker ps` inside the container lists the host's containers,
including `kandev` itself.) Three things make it work, and all three are required:

1. `docker-ce-cli` + the compose/buildx plugins in `Dockerfile.local` — client only.
2. The socket mount.
3. **Matching group GID.** The socket is `srw-rw---- root:docker`, so `Dockerfile.local`
   forces the container's `docker` group to the host's GID (`DOCKER_GID`, default 984)
   and adds `kandev` to it. The kernel checks the *number*, not the name — a mismatch
   gives `permission denied` on every command.

**The trap this creates.** The host daemon resolves every bind-mount source against the
**host** filesystem. Container-only paths do not exist there:

| Inside the container | On the host |
|---|---|
| `/data/tasks/<task>/<repo>` | `~/.local/share/kandev/tasks/<task>/<repo>` |
| `/data/home/Code/<project>` | `~/Code/<project>` |

Docker does **not** error on a missing bind source — it creates an empty root-owned
directory and mounts that. The sibling container comes up with an empty `/app`, the agent
concludes "my changes aren't showing up", and stray root-owned trees accumulate under the
host's `/data`. Nothing in the output hints at it. This bit twice in practice: a leftover
`/data/tasks/we-have-been-worked_yvbdlyql/performcoop` on the host, and the
`kandev-plugin-notes-docker-qa` container running for two days on an orphaned empty mount.

**The fix.** `docker-host-path-wrapper.sh` is installed as `/usr/local/bin/docker`, ahead
of `/usr/bin/docker` on `PATH` (the same shadowing trick as the `google-chrome`
`--no-sandbox` wrapper). It rewrites container paths to host paths using the
`KANDEV_HOST_HOME` / `KANDEV_HOST_DATA_DIR` / `KANDEV_HOST_CODE_DIR` env vars set in
`docker-compose.override.yml` — the inverse of the declared mounts, so nothing is
hardcoded per host. It covers:

- `-v` / `--volume` sources and `--mount source=`/`src=` (all subcommands)
- `-f` / `--file` and `--project-directory` (**compose only** — `docker build -f` reads
  that file from *our* filesystem, so rewriting it there would break the build)
- the **working directory** for `docker compose`, which is what makes a project's own
  unmodified compose file work: relative sources like `.:/var/www/html` are resolved by
  the compose CLI against the project directory, so running from the host-equivalent
  directory makes them come out as host paths

Left alone: named volumes (`myvol:/data`), anonymous volumes, and container-internal
flags like `-w`.

`docker-compose.override.yml` also adds **identity mounts** — `~/Code` and
`~/.local/share/kandev` mounted a second time at their own host paths. Nothing in kandev
reads them there; they exist so a rewritten host path is still readable inside the
container, which is what lets the wrapper `cd` into it and lets the compose CLI read the
compose file and build context afterwards.

**Escape hatch:** `/usr/bin/docker` is the untouched CLI, for when you really do mean a
path exactly as the host sees it. **Debug:** `docker --kandev-print-argv <args>` prints
the rewritten argv instead of executing. `test.sh` section 11 asserts the mapping,
including two end-to-end checks that a sibling container actually receives the real files.

**When adding a new host mount**, add the inverse entry to the `KANDEV_HOST_*` env vars
and to the `MAPPINGS` table in `docker-host-path-wrapper.sh` — nested mounts must be
listed **before** the `/data` catch-all (first match wins), or they resolve to their empty
mountpoints instead of the real files.

### Transparent proxy (office-desktop)

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
| `Dockerfile.local` | Extends upstream: adds SSH, gh, glab, Docker CLI (+ host-path wrapper), build toolchain, mise, Chrome + chromedriver, sqlite3 (for hot DB backup); patches git and entrypoint |
| `docker-entrypoint-local.sh` | Upstream entrypoint + `|| true` chown fix for :ro mounts |
| `docker-host-path-wrapper.sh` | Installed as `/usr/local/bin/docker`: rewrites container-only bind-mount paths to their host equivalents before calling the real CLI |
| `mise.default.toml` | System-wide mise config (`/etc/mise/config.toml`): global language versions matched to host |
| `setup-toolchains.sh` | One-time helper: installs the mise language toolchains into the persistent `/data` volume |
| `test.sh` | 56 automated tests covering image, container, service, identity, SSH, git, CLI tools, toolchains (incl. Java JDK), sqlite3, headless browser, Docker host-path wrapper |
| `update.sh` | Daily cron: pull upstream → rebuild local → restart if changed |
| `host.env` | **Git-ignored.** Real hosts/users/IPs for this machine + placeholder→real map (agent reference). Sourced by every script. |
| `host.env.example` | Committed template for `host.env`; copy and fill in per host. |
| `kandev-ssh-agent.sh` | Helper: start/reuse ssh-agent, load keys, restart kandev with socket forwarding |
| `install-hub.sh` | One-time home-server setup: sync cron, update cron, `/data/home/Code` mountpoint |
| `install-office.sh` | One-time office-desktop setup: systemd unit, UFW rules, port 80 → 38429 NAT |
| `sync-from-office.sh` | Rsync office → home (run by root cron on home-server every 10 min) |
| `sync-to-office.sh` | Rsync home → office (run manually before switching to office) |

---

## Common failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| Container crash-loops, logs full of `chown: Read-only file system` | Entrypoint patch missing or overwritten by image update | Verify `docker-entrypoint-local.sh` has `\|\| true`; rebuild |
| `apt-get` fails with `NOSPLIT` during build | Transparent proxy, missing `network: host` | Ensure `build.network: host` in `docker-compose.override.yml` |
| `git` reports "dubious ownership" inside container | `safe.directory` not set in system config | Rebuild image; check `git config --system safe.directory` = `*` |
| `gh`/`glab` not authenticated after rebuild | Config mount missing or wrong path | Check `~/.config/gh` and `~/.config/glab-cli` are mounted rw |
| `$USER` = `kandev` instead of `alice` | `USER` env missing from override | Check `docker-compose.override.yml` `environment:` block |
| SSH uses wrong key for a host | `~/.ssh` not mounted or `HOME` wrong | Verify mount and `HOME=/data/home` |
| A container started **from inside kandev** comes up with an empty `/app` (or empty data dir); "my code changes aren't showing up"; empty root-owned directories appear on the host under `/data` | The mounted socket drives the **host** daemon, which resolves bind sources on the **host** filesystem. A container-only path (`/data/...`) does not exist there, and Docker creates it empty instead of failing — see *Docker-out-of-Docker and the host-path wrapper* above | Should be handled automatically by `/usr/local/bin/docker`. If it recurs: check `docker exec -u kandev kandev bash -lc 'command -v docker'` returns `/usr/local/bin/docker` and that `KANDEV_HOST_*` are set; `docker --kandev-print-argv <args>` shows what the rewrite produces. Anything invoking `/usr/bin/docker` by absolute path bypasses the wrapper. Clean up strays with `docker run --rm -v /:/host debian:bookworm-slim rm -rf /host/data/<stray>` (host `sudo` needs a password) |
| `http://board.office` unreachable | iptables NAT rules missing after reboot | Re-run `install-office.sh` or apply rules via privileged container (see README) |
| `http://board.office` unreachable after our changes | Container crash-loop | Check `docker inspect kandev --format '{{.RestartCount}}'`; run `test.sh` |
| `http://board.office` (or `board.home`, or literally any `http://` site) shows the **wrong data** or a stale/empty "Default Workspace" **when browsed from laptop** | `install-laptop.sh` set an **unscoped** iptables `OUTPUT` NAT redirect — `-A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429` has no `-d` filter, so it matches port-80 packets to **any destination**, silently rewriting them to laptop's own local kandev (127.0.0.1:38429) instead of letting them leave the host. Confirmed by stopping laptop's local kandev container: `board.office:80` then failed outright (connection refused) instead of reaching office-desktop — proving the request never left the machine. (Earlier guess blaming the Corp corporate VPN was wrong — ruled out once the local-redirect rule was found.) | Fixed in `install-laptop.sh`: the OUTPUT rule is now scoped with `-d 127.0.0.1/32` so it only catches the host's own loopback traffic (browser on laptop → `board.local`), and the old unscoped rule is actively removed (live + persisted in `/etc/ufw/before.rules`). Re-run `bash ~/Code/kandev/install-laptop.sh` (needs sudo) to apply after pulling this fix. |
| **home-server only:** kandev container silently mounts `/root/...` (`~/.ssh`, `~/.gitconfig`, `~/.local/share/kandev`) instead of `/home/bob/...` after a nightly cron rebuild — DB, `master.key`, and toolchains end up on the wrong path, invisible to any manual `docker compose` command run as `bob` | `/etc/cron.d/kandev-update` runs `update.sh` **as root** (by design, for privileged ops), passing `USER_NAME=bob USER_HOME=/home/bob`. `update.sh` used `$USER_HOME` for its own `cd`/log paths but never did `export HOME="$USER_HOME"` — so `docker compose`'s own `${HOME}` substitution in `docker-compose.override.yml` independently resolved to root's real `$HOME=/root`, diverging silently. Confirmed via `~/logs/kandev-update.log`: the 2026-07-21 03:30 cron run flipped the mount; live DB + `master.key` were found only under `/root/.local/share/kandev/data/` (different `master.key` hash than bob's stale copy — the two data trees are not interchangeable, since `master.key` decrypts secrets stored inside the otherwise-plain SQLite `kandev.db`) | Fixed in `update.sh`: added `export HOME="$USER_HOME"` right after computing `USER_HOME`, on all three hosts, so `${HOME}`-based compose mounts always resolve consistently regardless of which user/cron context invokes the script. If this recurs: compare `docker inspect kandev --format '{{range .Mounts}}{{.Source}}{{println}}{{end}}'` against the expected user's home; if wrong, back up the current (possibly stale) target path, `docker exec kandev tar -C /data/data -cf - . \| tar -C <correct-path>/data -xf -` to migrate the live DB/key/backups out of the container before recreating it as the correct user. **`/usr/local/sbin/kandev-update.sh`** (the actual root-cron target on home-server) is a **static copy** made by `install-hub.sh` — it does NOT auto-update when `~/Code/kandev/update.sh` changes. Re-run `sudo bash ~/Code/kandev/install-hub.sh` on home-server to refresh it after any `update.sh` change. |
| **laptop:** `./update.sh` pulls a new upstream image, container crash-loops forever, `board.office`/`localhost:38429` unreachable; `docker logs kandev` shows `Failed to initialize repositories ... no such column: agent_execution_id` during the `task_sessions` migration | This host's live `kandev.db` had a divergent schema history (recorded as a non-release version like `f95d061d-dirty`, from an earlier dev/CI build): `agent_execution_id`/`container_id` had already been dropped from `task_sessions`, but the older `workflow_step_id` column was still present. Upstream's `migrateSessionsRemoveWorkflowStepID` migration (apps/backend/internal/task/repository/sqlite/base_migrations.go) is gated only on `workflow_step_id` being present, and unconditionally `SELECT`s `agent_execution_id, container_id` when rebuilding the table — it assumes those columns are always still there at that point, which isn't true for this DB's history. `update.sh` also had no post-restart health check, so the outage was silent. | One-time DB fix (safe/idempotent, matches upstream's final schema either way): `ALTER TABLE task_sessions ADD COLUMN agent_execution_id TEXT NOT NULL DEFAULT ''; ALTER TABLE task_sessions ADD COLUMN container_id TEXT NOT NULL DEFAULT '';` on the stopped container's `kandev.db`, then restart — lets the migration chain run to completion and drop the columns again correctly. **Permanent fix:** `update.sh` now (1) tags the running image as `<tag>-previous` before rebuilding, as a rollback safety net, and (2) polls `http://localhost:38429/` for HTTP 200 after `--force-recreate`; on failure it logs the crash logs, auto-rolls back to the `-previous` image, re-checks health, and exits non-zero either way so cron surfaces the failure instead of it going unnoticed. |
| **All hosts, on the first update past the 2026-08-10 upstream release:** container crash-loops; `docker logs kandev` shows `Failed to initialize repositories ... failed to initialize schema: cutover: N conflicting legacy ownership row(s)` listing session/worktree UUIDs | Upstream added a one-time cutover migration (`apps/backend/internal/task/repository/sqlite/worktree_ownership_normalize.go`) that collapses the legacy many-to-many `task_session_worktrees` into single worktree ownership. It aborts on any legacy row that is not *superseded*. Per `isSupersededSessionWorktree`, a row is superseded only if (a) the worktree is deleted (`status='deleted'` or `deleted_at` set), (b) it is authoritative for the owning task, or (c) the owning session is `COMPLETED`/`FAILED`/`CANCELLED` **and** a matching env-repo row exists for the same repo+branch. On office-desktop an `IDLE` session held two distinct `worktree_id`s pointing at one identical path+branch whose directory no longer existed on disk → 2 conflicts. Note the conflict is keyed on repository+`branch_slug`, and `branch_slug` is `''` on legacy rows, so many rows collapse to one key. | Read the session/worktree UUIDs out of the error, confirm with `SELECT * FROM task_session_worktrees WHERE session_id='<id>';` and check whether `worktree_path` still exists on disk. If it does not, mark the rows deleted so the DB matches the filesystem — this satisfies supersession rule (a) rather than bypassing the migration: `UPDATE task_session_worktrees SET status='deleted' WHERE session_id='<id>' AND worktree_id IN (...) AND status='active';` **Always validate on a copy first:** `docker exec kandev sqlite3 "file:/data/data/kandev.db?mode=ro" ".backup '/data/copy.db'"`, put it in a scratch dir as `data/kandev.db` next to a copy of `master.key`, then `docker run --rm -v <dir>:/data <image> kandev start --backend-port 38429 --verbose` and confirm it reaches `WebSocket hub started` with no `cutover` error. Back up `kandev.db` **together with `master.key`** — the key decrypts secrets stored inside the DB and the two are useless apart. Meanwhile the service self-heals: `update.sh`'s health gate auto-rolls-back to `<tag>-previous`. Beware that the rollback overwrites the `kandev-local:latest` tag, leaving the newly built image dangling as `<none>` — tag it (e.g. `kandev-local:candidate`) before any `docker system prune` reclaims it. |
