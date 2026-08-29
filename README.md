# Kandev — Three-Host Architecture

Three **identical** kandev instances sharing live-replicated data.
**home-server is the central hub** — it holds the Litestream replica and restic snapshot repo.
Satellites (office-desktop, laptop) restore from the hub on startup and replicate back continuously.

## Hosts

| Host | IP | User | URL | Role |
|---|---|---|---|---|
| home-server | 10.0.0.20 | bob | https://board.home | Hub + always-on home dev |
| office-desktop | 192.168.1.10 | alice | http://board.office | Powerful workstation, office hours (Corp VPN) |
| laptop | 127.0.0.1 | carol | http://board.local | Local dev machine, VPN-independent fallback |

All hosts use:
- `~/Code` — projects/workspaces (bind-mounted as `/data/home/Code` in container)
- `~/.local/share/kandev` — kandev data dir (sqlite DB + sessions, mounted as `/data`)

> **Placeholders — sanitized public repo.** Every hostname, username, LAN IP, and
> path in this repo (`office-desktop`/`alice`, `home-server`/`bob`, `laptop`/`carol`,
> `10.0.0.20`, `192.168.1.10`, `example-corp`, `Code/work-project`, …) is a **generic
> example**. Put your real values in a git-ignored **`host.env`** at the repo root —
> every script sources it and falls back to these placeholders when it is absent:
> ```bash
> cp host.env.example host.env   # then edit host.env with your real hosts/users/IPs
> ```
> `host.env` is listed in `.gitignore`, so it never gets pushed. See `host.env.example`
> for the full list of overridable values.

### Adding a repository in the UI

Kandev restricts repository paths to within the container `HOME` (`/data/home`). The host `~/Code` is **nested-bind-mounted** at `/data/home/Code` inside the container (a real directory, not a symlink — kandev's discovery scanner does not follow symlinks).

In the **Add Local Repository** dialog enter:

```
/data/home/Code/<project-name>
```

(Not the host path like `/home/bob/Code/<project>` — that path doesn't exist inside the container.)

> The mountpoint `~/.local/share/kandev/home/Code` is created as an empty directory by `install-hub.sh` / `install-office.sh` so Docker can apply the nested bind on container (re)create.

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
├── kandev-start-hub.sh           # Hub start helper: restore from freshest satellite replica
├── kandev-pull.sh                 # Manual/cron: check for newer data → pull if behind → start
├── kandev-restic-backup.sh        # Daily restic snapshot → remote or local fallback
├── install-hub.sh                # Setup for home-server (hub: replica dir, restic repo, crons)
├── install-office.sh                 # Setup for office-desktop (systemd, UFW, NAT, Litestream, crons)
├── install-laptop.sh             # Setup for laptop (systemd, iptables, board.local, Litestream)
├── update.sh                      # Pull upstream + rebuild local image + restart + sync toolchains
├── setup-toolchains.sh            # Install/sync mise language toolchains into persistent volume
├── mise.default.toml              # Global mise tool versions (baked into image as /etc/mise/config.toml)
├── kandev-ssh-agent.sh            # Helper: start ssh-agent and restart kandev with it
├── host.env.example               # Template for git-ignored host.env (real hosts/users/IPs)
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

> **Network note (office-desktop / transparent proxy):** the build must use `--network=host`
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

Each local image records the exact upstream image ID in its
`com.kandev.base-id` label. The updater compares this label on every run; an
empty or `unknown` label is deliberately treated as stale. Consequently, if a
release pull succeeds but the build is interrupted (for example by the disk
space preflight), the next run resumes the rebuild even though `docker pull`
now reports that the upstream image is already present.

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

### Codex workspace-write sandbox

Codex agents run inside this Kandev worker container. On Linux, the Codex
`workspace-write` sandbox uses Bubblewrap, which creates an unprivileged user +
mount namespace and then bind-mounts only the allowed workspace paths. The
host's `kernel.unprivileged_userns_clone=1` setting is necessary but not
sufficient: Docker's built-in seccomp profile rejects Bubblewrap's
`clone(CLONE_NEWUSER|CLONE_NEWNS|...)`, and Docker's `docker-default` AppArmor
profile rejects the subsequent staging mounts.

The launch chain is Compose's `kandev start` command → the upstream Kandev
backend/`agentctl` executor → the persistent Codex CLI at
`/data/.npm-global/bin/codex`. Bubblewrap is selected internally by that Codex
CLI; Kandev has no separate `bwrap` toggle. This local image explicitly installs
`/usr/bin/bwrap` so the dependency does not rely on the current upstream image.

This repository supplies two worker-only policies:

- `seccomp/kandev-bwrap.json` is Docker's pinned default seccomp profile plus a
  `clone` exception that matches only calls containing `CLONE_NEWUSER`, and the
  namespace-local mount syscalls Bubblewrap uses. It does not add
  `CAP_SYS_ADMIN` or use `seccomp=unconfined`.
- `apparmor/kandev-codex` retains Docker's default `/proc`, `/sys`, signal,
  ptrace, file, capability, and network restrictions. Its mount rules are
  limited to Bubblewrap's `/tmp`, `/oldroot`, and `/newroot` staging trees.

AppArmor profiles are host kernel state and Docker Compose cannot load one.
Install or refresh it after cloning/updating this repository, before starting
the worker:

```bash
cd ~/Code/kandev
sudo bash scripts/install-codex-apparmor.sh
docker compose build
docker compose up -d --force-recreate
```

The image entrypoint runs `codex-sandbox-preflight` before Kandev accepts work.
If nested user namespaces, seccomp, or AppArmor are incompatible, startup exits
with an actionable error instead of letting every agent fail at `apply_patch`.

### Full agent permissions inside the outer guard

Every agent provider runs without its own redundant approval/filesystem
restrictions **inside** `kandev-agent-guard`: Codex uses
`agent-full-access`, Claude uses `bypassPermissions`, and Copilot receives its
`--allow-all-paths`, `--allow-all-tools`, and `--allow-all-urls` flags. This
does not give agents full host access. The outer Bubblewrap guard remains the
kernel-enforced boundary and bind-mounts only the agent's task root plus the
backlink-verified Git common directory read-write. Sibling tasks, unrelated
repositories, the Code root, the raw Docker socket, and host privilege
escalation remain unavailable.

The policy is enforced in both the profile/session launch snapshot and the
persisted per-session runtime configuration. Kandev applies runtime selections
after the profile, so protecting only the profile is insufficient: a stale
`runtime_config.mode=agent` would silently restore Codex's inner
`workspace-write` sandbox. Database triggers prevent later UI/turn-state writes
from reintroducing that override.

For an ordinary linked worktree, the shared Git common directory is writable
for objects and refs, but its `worktrees/` registry is overlaid read-only and
only that task's own administrative entry is rebound read-write. This preserves
normal Git writes without exposing sibling worktree index/HEAD metadata.

These bind mounts live in a **private mount namespace per agent process**. A
normal agent inspecting its namespace sees exactly its own task override and
cannot infer another agent's permissions from that view. A validated
Coordinator deliberately receives additional exact paths registered to its
own `workspace_id`, but still does not see another agent's private overrides.
Never make `/data/tasks` or `/data/home/Code` globally read-write: the guard
enumerates exact authorized paths instead.

Verify a reported worktree from a fresh guard invocation rooted in that exact
repository. Both the worktree and its Git common directory must report `rw`,
the source checkout must report `ro`, and the dry-run must succeed:

```bash
docker exec -u kandev kandev sh -lc '
  cd /data/tasks/<task>/<repo> || exit
  /usr/local/bin/kandev-agent-guard -- sh -ceu '\''
    common=$(git rev-parse --git-common-dir)
    findmnt -T "$PWD" -n -o TARGET,OPTIONS
    findmnt -T "$common" -n -o TARGET,OPTIONS
    git add -A --dry-run >/dev/null
  '\''
'
```

`tests/test-agent-guard.sh` performs these mount-mode and Git-index checks on a
real linked task worktree during the deployment test suite.

This split is especially necessary for linked worktrees. Codex's nested
`workspace-write` sandbox reclassifies the external common Git directory as
read-only, so source edits appear to work but `git add`/`git commit` fail when
Git tries to create `.git/worktrees/<id>/index.lock`. The startup policy in
`scripts/enforce-agent-guard.sh` updates existing profiles and installs
database triggers so newly created or edited profiles retain this
full-access-inside-the-guard invariant for every provider.

Operator diagnostic (runs the same preflight in the actual worker image and
with the same two policies as Compose):

```bash
docker run --rm \
  --security-opt seccomp=./seccomp/kandev-bwrap.json \
  --security-opt apparmor=kandev-codex \
  kandev-local:latest /usr/local/bin/codex-sandbox-preflight
```

For a fresh `exec-worktree` task, the apply-patch regression is:

```bash
bash tests/codex-sandbox-regression.sh
```

It uses the task's real injected `apply_patch` helper to create a file, update
that new file, and update a tracked file through `codex sandbox -P :workspace`.

Runtime requirements and safe deployment equivalents:

- Docker/Compose: apply both supplied profiles to the `kandev` service; keep
  `privileged: false`, do not add `SYS_ADMIN`, and do not select
  `seccomp=unconfined` or `apparmor=unconfined`.
- Kubernetes: install equivalent node-local seccomp and AppArmor profiles, set
  `securityContext.seccompProfile.type: Localhost`, select the
  `kandev-codex` AppArmor profile, keep `privileged: false`,
  `allowPrivilegeEscalation: false`, and drop `SYS_ADMIN`. Schedule only onto
  nodes where both profiles are installed.
- Nested Docker/LXC: the outer runtime must pass through unprivileged user
  namespace creation and AppArmor namespace-local mount mediation. Mounting a
  Docker socket is unrelated; this worker uses the host daemon, not Docker in
  Docker.
- The normal Codex network boundary remains Bubblewrap's `CLONE_NEWNET`; the
  policies grant no host networking or filesystem paths. Workspace visibility
  remains determined by Codex's bind-mount allowlist.

Useful diagnosis:

```bash
docker inspect kandev --format \
  '{{json .HostConfig.SecurityOpt}} privileged={{.HostConfig.Privileged}} caps={{json .HostConfig.CapAdd}} apparmor={{.AppArmorProfile}}'
docker exec -u kandev kandev sh -lc \
  'id; grep -E "NoNewPrivs|Seccomp" /proc/self/status; /usr/local/bin/codex-sandbox-preflight'
```

### Task-scoped Docker for guarded agents

The outer Kandev service retains the host Docker socket for orchestration, but
an agent's Bubblewrap namespace never receives `/var/run/docker.sock`. Instead,
`docker compose` is routed through `kandev-agent-docker-broker`:

- an HMAC token binds every request to the agent's assigned task/repository;
- Compose files, includes, and env files are resolved inside that Bubblewrap
  scope, then the broker executes only the resulting sanitized model;
- the Compose project name is derived from the task, so containers, networks,
  images built by the task, and named volumes cannot collide with production or
  another task;
- external volumes/networks, privileged containers, devices, added
  capabilities, host namespaces, daemon-socket mounts, and extra `run -v`
  mounts are rejected;
- every host/task bind is forced read-only. Use task-prefixed named volumes for
  database and other mutable container state; edit source from the agent shell.

This supports `docker compose up`, `build`, `exec`, `logs`, `down`, and the other
normal lifecycle commands. Raw `docker run` and direct Docker API access are
intentionally unavailable. The image includes `mariadb-dump`, so an agent can
dump a source database exposed on a TCP port into its worktree and restore it
into an isolated Compose database volume without access to the source
container's Docker control plane.

### Workspace coordinator source access

Agents whose **task worktree has exactly one registered repository**, the
workspace's `/data/home/Code/coordinator` repository, receive an additional
read-only information capability. Authorization comes from Kandev's SQLite
task/environment/repository metadata—not the task title, prompt, branch name,
or an agent-writable `.git` file. The coordinator and every source/target task
must belong to the same `workspace_id`.

```bash
docker kandev source list
docker kandev source inspect <container>
docker kandev source logs <container> --tail 200 --since 30m
docker kandev source db-dump <container> \
  --target-task <full-task-uuid> --name source.sql
docker kandev workspace probe <full-task-uuid>
docker kandev workspace description-update PROMPT.md
docker kandev support send support-request.json
docker kandev support status <request-uuid>
docker kandev support receive <request-uuid>
```

`list`, `inspect`, and bounded/redacted `logs` expose only containers whose
Compose working directory or broker-owned task project maps to a repository or
task in the coordinator's workspace. `db-dump` supports MariaDB/MySQL and
PostgreSQL. The broker reads the container's configured database credentials,
keeps them out of agent argv/output, performs a logical read over the container
network, and atomically creates a mode-0600 artifact at:

```text
/data/tasks/<target-task>/.kandev-coordinator-inbox/<name>
```

The target must be an active task in the same workspace and the file may not
already exist. Every coordinator source request is appended to
`/data/logs/coordinator-source-audit.jsonl` without credentials.

The validated Coordinator also receives exact active task roots, registered
repository checkouts, and registered folder sources for its own workspace
read-write. The Code/task parent directories and every other workspace remain
read-only. Eligibility is derived from live task/environment/repository/session
records plus the coordinator Git backlink on every launch. Kandev v0.92's
exported task/session pair is validated exactly and the workspace is derived
from that task; when a newer backend also exports workspace ID, it must match.
If no launch IDs are exported, the guard requires exactly one active executor
launch matching the exact materialized task root. This handles the brief launch
window where the session row still says `WAITING_FOR_INPUT` without authorizing
an idle session. Other partial, malformed, or mismatched IDs fail closed. The selected session is rechecked every
15 seconds; a failed recheck terminates the elevated process. Scope grants and
revocations are recorded in
`/data/logs/coordinator-workspace-audit.jsonl`. This records elevated scope,
not every individual filesystem write; full per-file auditing still requires a
host audit/fanotify facility.

`docker kandev workspace probe` runs a fresh guard rooted in the named
same-workspace task and reports mount modes, a reversible task write, and the
`git add -A --dry-run` result. Use it instead of inferring target writability
from the Coordinator's own private mount table.

`docker kandev workspace description-update <file>` replaces only the calling
Coordinator task's description from a UTF-8 file inside its own task root
(maximum 1 MiB). The broker mints a five-minute operator token internally,
calls the normal Kandev API so task-update events are published, verifies the
persisted content, and revokes the token before replying. The credential is
never exposed to the agent, and no target task ID can be supplied.

`docker kandev support send` accepts a JSON request file inside the calling
Coordinator task with four required strings: `problem`, `evidence`,
`expected_outcome`, and `security_constraints`. It returns a request UUID;
`status` polls it and `receive` returns the Support worker's final response.
Status values are `queued`, `processing`, and `complete`; a completed request
is successful only when its `returncode` is zero and `resolution_status` is
`resolved`. The worker must own safe authorized work through implementation and
verification; diagnosis-only output cannot be reported as success. A genuine
unresolved external boundary is `resolution_status: blocked` with return code
75, while a response that omits the explicit outcome contract fails with return
code 70. Request lifecycle and outcome are also written to the user-service
journal. Requests that failed before a
worker fix remain terminal and must be replaced with a fresh request.
Delivery runs on the host through a dedicated persistent Codex support thread,
so it does not contend with an operator's interactive Codex conversation. The
worker is approval-reviewed and the broker still validates Coordinator identity
and scopes every request/response to its originating task and workspace.
Its persistent thread ID is kept outside the repository in the mode-0600 host
file `~/.config/kandev/support.env`; the user service fails closed if that file
is absent.

Logical dumps may contain sensitive application data. The current Bubblewrap
policy is a write-confinement boundary, not a distinct-UID confidentiality
boundary: other guarded agents cannot modify the inbox but may be able to read
paths elsewhere under `/data`. Import the artifact promptly, remove it when no
longer needed, and use per-task UIDs/encrypted broker delivery before treating
the inbox as suitable for secrets. Log redaction is best-effort key-pattern
redaction; request only the smallest time/tail range required.

This capability never provides raw `docker exec`, a shell, arbitrary container
names outside the workspace, container environment output, or the host Docker
socket. The shared main coordinator checkout is denied when it cannot identify
one unique task/workspace; coordinators must run from their materialized Kandev
task worktrees.

### Android emulator access for guarded agents

Mobile tasks can run hardware-accelerated, headless Android UI QA from any
guarded agent session:

```bash
emulator -list-avds
emulator -avd Pixel_8 &
adb wait-for-device
adb shell getprop sys.boot_completed
```

The local image supplies `emulator` and `adb` wrappers. Compose mounts the
host's `~/Android/Sdk` and `~/.android/avd` at their original absolute paths
**read-only**, and passes only `/dev/kvm` into the container and Bubblewrap
session. The emulator wrapper adds `-read-only -no-snapshot -no-window
-no-audio -no-boot-anim -no-metrics` and software GPU rendering to every AVD
launch. Because the emulator still needs local lock files in read-only mode, the
wrapper copies only `config.ini` into a disposable runtime AVD directory and
disables the SD card; the large base images stay untouched. Mutable adb keys and
tool state persist at `/data/home/.android`, outside `~/Code`; the base AVD
images cannot be overwritten.

This contract intentionally does not expose `/dev/dri`, `/tmp/.X11-unix`, a
Wayland socket, or the host desktop. UI inspection and automation use adb,
screenshots, uiautomator/Appium, or the project's test framework. All sessions
share the host network and adb server, so emulator instances are not confidential
from other same-host agents. Kandev uses its own adb server on port 5038 rather
than the host's differently keyed server on 5037. Use `adb -s <serial>` when several are running and
stop task-owned instances with `adb -s <serial> emu kill` when QA finishes.

Host prerequisites are `~/Android/Sdk/emulator/emulator`, at least one AVD under
`~/.android/avd`, `/dev/kvm`, and the correct KVM group ID. The office default is
`KVM_GID=993`; override it in the launch environment if `getent group kvm`
reports another value, then rebuild/recreate Kandev. The value is both a Compose
runtime `group_add` and a Dockerfile build argument: the image creates the
matching group and adds `kandev` to it so the entrypoint/agentctl user transition
cannot discard access. A direct `docker exec -u kandev` check alone is
insufficient because Docker applies `group_add` specially to that fresh exec.

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
| `HOSTNAME` | `0.0.0.0` | Bind address reported and used by the kandev server. With `network_mode: host` the container shares the host's network stack. `0.0.0.0` makes the UI reachable on all interfaces (LAN, loopback), enabling access from `http://board.home` and `http://board.office`. |
| `NODE_ENV` | `production` | Runs Node.js in production mode: disables dev-only middleware and verbose stack traces, enables caching and performance optimisations, and reduces log noise. Change to `development` only when debugging kandev itself. |

#### `docker-compose.override.yml` (host identity)

| Variable | Value | Purpose |
|---|---|---|
| `USER` | `${USER}` (host shell) | Propagates the host username into the container. The container OS user is `kandev`, but `git`, `ssh`, `gh`, `glab`, and shell scripts inspect `$USER` for identity. Without this they report `kandev` instead of `alice`. |
| `LOGNAME` | `${USER}` (host shell) | POSIX fallback for `$USER`. Some tools (older Unix utilities, certain git hooks, shell scripts) read `$LOGNAME` exclusively. Must match `$USER` for consistent identity across all tooling. |

#### `docker-compose.ssh-agent.yml` (optional SSH agent overlay)

| Variable | Value | Purpose |
|---|---|---|
| `SSH_AUTH_SOCK` | `/run/ssh-agent.sock` | Points SSH and any libssh/libssh2-based tool to the forwarded agent socket. Without this variable, SSH ignores the bind-mounted socket entirely and falls back to key-file auth only — defeating the purpose of agent forwarding. The path must match the container-side path in the volume mount. |

> **UID matching:** The container user is `kandev` (UID 1000). The host user is `alice`
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
> so `~/.ssh/github_office` resolves to `/data/home/.ssh/github_office`
> — all host SSH host aliases and key mappings work as-is.

### Git `safe.directory`

`~/.gitconfig` contains `safe.directory = /home/alice/Code/work-project` (a host absolute path).
Inside the container the same repo lives at `/data/home/Code/work-project`. Rather than patching the
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
USER=alice
alice
dev@example.com
*
hostname github.com
identityfile ~/.ssh/github_office
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
2. Loads `~/.ssh/id_ed25519` and `~/.ssh/github_office` (edit the script to add/remove keys)
3. Restarts the kandev container with `docker-compose.ssh-agent.yml` layered in, which:
   - Bind-mounts the host agent socket at `/run/ssh-agent.sock` inside the container
   - Sets `SSH_AUTH_SOCK=/run/ssh-agent.sock` in the container environment

To load a different or extra key:

```bash
bash ~/Code/kandev/kandev-ssh-agent.sh ~/.ssh/work-client
```

### Manual agent forwarding

```bash
eval $(ssh-agent) && ssh-add ~/.ssh/id_ed25519
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

## Client access (from laptop)

`/etc/hosts` on laptop (already configured):

```
10.0.0.20        board.home
192.168.1.10    board.office
```

For `board.local` (laptop's own kandev), `install-laptop.sh` adds:
```
127.0.0.1         board.local
```

| URL | Host | VPN needed |
|---|---|---|
| https://board.home | home-server (10.0.0.20) | No — home LAN |
| http://board.office | office-desktop (192.168.1.10) | Yes — `sudo nmcli connection up "Corp VPN"` |
| http://board.local | laptop (127.0.0.1) | No — local |

> **Fixed bug — an unscoped port-80 redirect hijacked traffic that was never meant for kandev.**
> Both installers used to add `--dport 80 -j REDIRECT --to-port 38429` with no interface or
> destination constraint, in *both* NAT chains. That matched far more than "someone asked for
> the board":
> * **`OUTPUT`** caught every port-80 request the host itself made — so from laptop,
>   `board.office`, `board.home` and any plain-`http://` site were silently answered by
>   laptop's own kandev. Confirmed by stopping laptop's local kandev: `board.office:80`
>   then failed outright instead of reaching office-desktop.
> * **`PREROUTING`** caught the egress of every container on a docker bridge — `apt-get
>   update` reaching `deb.debian.org:80` got the kandev SPA instead, which surfaces as
>   `Clearsigned file isn't valid, got 'NOSPLIT'` during a build.
>
> **Fix:** the redirect stays — it is the whole point of `http://board.<host>` — but it is now
> *scoped*, and both installers delegate to a single `scripts/nat-redirect.sh`. See
> [Network / iptables](#network--iptables) below. Re-run `bash ~/Code/kandev/install-office.sh`
> (or `install-laptop.sh`), or just `sudo bash ~/Code/kandev/scripts/nat-redirect.sh`, on any
> host still carrying the old rules.

## Network / iptables

### Port map

| Port | Bound to | What |
|---|---|---|
| `38429` | `0.0.0.0` | Kandev unified server — backend + web UI |
| `80` | N/A — no listener | Redirected → `38429` by iptables NAT |

### The two chains, and why each needs a scope

`http://board.<host>` with no port number needs a NAT redirect in both chains — and each
one, left unscoped, catches traffic that has nothing to do with kandev:

| Chain | Must catch | Also caught when unscoped | Scope used |
|---|---|---|---|
| `PREROUTING` | Packets arriving **from the network** — other PCs asking for the board | The egress of every container on a docker bridge (`apt-get` → `deb.debian.org:80` is answered with the kandev SPA → `NOSPLIT`) | `-i <lan-iface>`, one rule per detected LAN interface |
| `OUTPUT` | Packets generated **on this host** and addressed **to this host** — a browser or `curl` here opening `board.<host>` or `localhost` | Every port-80 request the host makes, including a `network: host` docker build and any `http://` site in the browser | `-o lo` |

`-o lo` is the right scope because `ip route get` sends **both** `127.0.0.1` **and the host's
own LAN IP** out the loopback device, so one rule covers `http://localhost` and
`http://board.<host>` from the host itself — and unlike a `-d <lan-ip>` scope it keeps
working after a DHCP lease change. Anything actually leaving the machine goes out
`enp*`/`wl*` and is left alone.

**Classic symptom of a missing OUTPUT rule:** `http://board.office` works from another PC
but gives *Connection refused* from a browser or `curl` on office-desktop itself.

**Deliberate trade-off:** a container on a docker bridge can no longer reach the board on
port 80 by hostname — it must use `<host-ip>:38429`. That is precisely the traffic class
that was breaking `apt`.

### Managing the rules

One script owns the live rules *and* their persisted copy in `/etc/ufw/before.rules`
(falling back to `iptables-persistent`). It is idempotent, and it removes the older
unscoped rules wherever it finds them:

```bash
bash ~/Code/kandev/scripts/nat-redirect.sh --print    # show the rules; no root needed
sudo bash ~/Code/kandev/scripts/nat-redirect.sh       # apply live + persist
sudo bash ~/Code/kandev/scripts/nat-redirect.sh --check  # verify; exit 1 if wrong/unscoped
```

LAN interfaces are autodetected: every globally-addressed IPv4 interface that is not
`lo`, `docker0`, `br-*`, `veth*` or `virbr*`. Override with `KANDEV_LAN_IFACES="eth0 wlan0"`
in `host.env` — for example to add a VPN interface the board is reached over. If nothing is
detected the script **fails** rather than falling back to an unscoped rule.

`install-office.sh` and `install-laptop.sh` both call it; neither runs `iptables` itself.

### Diagnose

```bash
# Are the rules present and correctly scoped?
sudo bash ~/Code/kandev/scripts/nat-redirect.sh --check

# Raw view (no sudo password needed — uses the docker group)
docker run --rm --net=host --privileged alpine \
  sh -c 'apk add -q iptables && iptables -t nat -S PREROUTING && iptables -t nat -S OUTPUT'

# Connectivity
curl -o /dev/null -w "%{http_code}\n" http://board.office/       # via NAT, expect 200
curl -o /dev/null -w "%{http_code}\n" http://localhost:38429/    # direct, no NAT

# Is a container's :80 egress being hijacked? (the apt symptom)
docker run --rm alpine sh -c 'apk add -q curl && curl -sI http://deb.debian.org/ | head -1'
```

An unscoped rule shows up in `--check` output as `UNSCOPED/STALE`.

### Fix (if rules are missing after reboot)

```bash
sudo bash ~/Code/kandev/scripts/nat-redirect.sh
```

If `ufw reload` is not picking up `before.rules`, the script says so; the live rules are
applied either way. `/etc/ufw/before.rules.kandev.bak` holds the copy from before the last
run.

## Deploy

### home-server (hub)

```bash
# 1. Sync scripts
rsync -avz stack/kandev/ bob@10.0.0.20:~/Code/kandev/

# 2. (One-time) migrate existing named volume to bind path
ssh bob@10.0.0.20 '
  mkdir -p ~/.local/share/kandev ~/Code
  if docker volume inspect kandev_kandev-data >/dev/null 2>&1; then
    docker run --rm -v kandev_kandev-data:/from -v ~/.local/share/kandev:/to alpine \
      sh -c "cp -a /from/. /to/"
  fi
'

# 3. Setup hub: create litestream-replicas/, init restic repo, fix crons, upgrade image
ssh bob@10.0.0.20 "sudo bash ~/Code/kandev/install-hub.sh"

# 4. Build + start kandev
ssh bob@10.0.0.20 "cd ~/Code/kandev && docker compose build && docker compose up -d --force-recreate"
```

### office-desktop (when Corp VPN is up)

```bash
sudo nmcli connection up "Corp VPN"

rsync -avz stack/kandev/ alice@office-desktop:~/Code/kandev/

# Setup: systemd, UFW, NAT, Litestream config, crons, start with restore
ssh alice@office-desktop 'bash ~/Code/kandev/install-office.sh'
```

> **Note:** `install-office.sh` will auto-detect the SSH key that reaches home-server.
> If it prints a warning, add your key: `ssh-copy-id -i ~/.ssh/KEY bob@10.0.0.20`

### laptop (local)

```bash
# 1. Copy password from home-server (one-time, after install-hub.sh has run)
scp bob@10.0.0.20:.config/restic/kandev-backup-password \
    ~/.config/restic/kandev-backup-password
chmod 600 ~/.config/restic/kandev-backup-password

# 2. Sync scripts
rsync -avz stack/kandev/ ~/Code/kandev/

# 3. Setup: systemd, iptables 80→38429, board.local DNS, Litestream, restore + start
bash ~/Code/kandev/install-laptop.sh
```

## Sync — Litestream (live) + Restic (history)

### Architecture

```
kandev.db  ──Litestream──► ~/litestream-replicas/kandev/  on home-server  (live WAL, seconds lag)
kandev/    ────Restic────► ~/restic-repos/kandev-backup   on home-server
                    └────► ~/.Backups/restic/kandev-backup hidden local fallback when offline
```

**home-server is the hub.** It stores the Litestream SFTP replica and the restic repo. It does NOT run Litestream itself.

### Litestream (live SQLite replication)

Litestream runs as a sidecar container alongside kandev on office-desktop and laptop. It:
- Streams WAL (write-ahead log) changes to home-server via SFTP — lag is seconds, not hours
- On container startup (`kandev-start.sh`): restores latest state from home before kandev starts
- Is SQLite-native: no need to stop kandev, no corruption risk

```bash
# Check litestream is replicating (on office or carol)
docker logs kandev-litestream 2>&1 | tail -5

# Check replica files on home-server
ssh bob@10.0.0.20 "ls -lh ~/litestream-replicas/kandev/"

# Manual restore (stop kandev first)
docker stop kandev
litestream restore sftp://bob@10.0.0.20/litestream-replicas/kandev \
  ~/.local/share/kandev/data/kandev.db
docker start kandev
```

### Manual check & pull latest (`kandev-pull.sh`)

Litestream **pushes** the active host's writes to home within ~1s, but other hosts
only **pull** that data when kandev restarts. `kandev-pull.sh` lets you pull the
freshest state on demand — run it when you sit down at a machine to make sure the
board matches where you left off on another host.

```bash
# On EITHER host (laptop or office-desktop):
bash ~/Code/kandev/kandev-pull.sh            # check → pull if behind → ensure kandev is up
bash ~/Code/kandev/kandev-pull.sh --dry-run  # report only, change nothing
bash ~/Code/kandev/kandev-pull.sh --force    # pull the freshest replica no matter what
```

What it does:
1. Asks home which host's replica is **freshest**, and how fresh **this** host's own
   push is (both mtimes read from home's filesystem → no clock-skew guessing).
2. Reads who holds the **active-writer lock**.
3. Decides:
   - **This host is the active writer** → nothing to pull (your data is authoritative).
     `--force` overrides.
   - **A peer replica is newer** → you're behind → stops kandev, restores the freshest
     data (via `kandev-start.sh`), restarts.
   - **Already current / home unreachable** → leaves a running kandev untouched.

Safe to run anytime: it no-ops when you're the writer, already current, or offline,
so it never reverts local edits or strips a live replication sidecar.

> **office-desktop only reaches home when the `office-desktop` WireGuard tunnel is up.**
> If home is unreachable the script reports it and leaves kandev running as-is —
> bring the tunnel up (`nmcli connection up office-desktop`) first.

This same script runs automatically via cron at **06:00 / 13:00 / 18:00** on both
satellites (see Cron summary) so cross-host visibility stays near-current without
manual restarts. Example output:

```
[pull] host-id=laptop  writer=none
[pull] freshest replica : 'office'  (2026-07-08 21:45:37)
[pull] our own replica  : 2026-07-08 05:42:27
[pull] BEHIND by ~57550s vs peer 'office' — pulling freshest data.
```

### Restic (snapshot history)

Daily at 03:00 on each satellite host, `kandev-restic-backup.sh` (runs with
**zero downtime** — kandev is never stopped):
1. Takes a transactionally-consistent hot copy of `kandev.db` via SQLite's
   online-backup API (`sqlite3 .backup`, run in a throwaway container from the
   kandev image) → `data/kandev.db.backup-snapshot`
2. Runs `restic backup` → new named snapshot in home's repo, **excluding** the
   live `kandev.db`/`-wal`/`-shm` (which would be torn if copied mid-write) and
   including the consistent snapshot in their place
   If the hub/VPN/SFTP path is unavailable, the same snapshot is written to the
   hidden local fallback repo at `~/.Backups/restic/kandev-backup` instead. This path is
   deliberately outside both `~/Code` and the Kandev data tree.
3. Removes the temporary database snapshot and prunes the selected repo (keeps 7 daily,
   4 weekly, 3 monthly)

> Because kandev is an AI-agent orchestrator, stopping it would kill every
> in-flight agent session/task. This backup therefore never stops it, and it
> also no longer aborts on a restic error (a prior `set -e` bug left the
> container stopped whenever restic failed, e.g. the hub repo running out of
> disk space).

```bash
# View snapshot history (like git log)
~/bin/restic -r sftp:bob@10.0.0.20:restic-repos/kandev-backup snapshots

# Restore a specific snapshot
~/bin/restic -r sftp:bob@10.0.0.20:restic-repos/kandev-backup restore SNAPSHOT_ID \
  --target / --include ~/.local/share/kandev/
# The DB is restored as data/kandev.db.backup-snapshot; put it in place with:
mv ~/.local/share/kandev/data/kandev.db.backup-snapshot \
   ~/.local/share/kandev/data/kandev.db
# (Normal recovery uses Litestream via kandev-start.sh, which already yields a
#  ready-to-use kandev.db — this restic path is the deep-history fallback.)

# Manual backup now
bash ~/Code/kandev/kandev-restic-backup.sh
```

Restic password file: `~/.config/restic/kandev-backup-password` (same on all hosts, generated by `install-hub.sh`).

#### Hidden local fallback: find, verify, and restore

The leading dot intentionally hides `.Backups` from ordinary directory listings.
It is not an undiscoverable location: the script, `host.env.example`, and this
runbook all use the same path. Use `ls -la ~` to see it.

```bash
LOCAL_REPO="$HOME/.Backups/restic/kandev-backup"
PASSWORD="$HOME/.config/restic/kandev-backup-password"

# Show local snapshots and verify repository metadata/data references.
RESTIC_PASSWORD_FILE="$PASSWORD" restic -r "$LOCAL_REPO" snapshots
RESTIC_PASSWORD_FILE="$PASSWORD" restic -r "$LOCAL_REPO" check

# Restore into a staging directory first; never overwrite the live tree directly.
mkdir -p "$HOME/.Backups/restores/kandev-latest"
RESTIC_PASSWORD_FILE="$PASSWORD" restic -r "$LOCAL_REPO" restore latest \
  --target "$HOME/.Backups/restores/kandev-latest"
```

The restored database is named `kandev.db.backup-snapshot`; restore it together
with the matching `data/master.key`. Stop Kandev and make a safety copy of the
current live data before replacing either file.

### Cron summary

| Host | Cron | What |
|---|---|---|
| home-server | `30 3 * * *` (root, `/etc/cron.d/kandev-update`) | Image update |
| home-server | `0 3 * * *` (root, `/etc/cron.d/kandev-backup`) | Restic snapshot |
| office-desktop | `30 3 * * *` (user crontab) | Image update |
| office-desktop | `0 3 * * *` (user crontab) | Restic snapshot |
| office-desktop | `0 6,13,18 * * *` (user crontab) | **Pull latest** (`kandev-pull.sh`) |
| laptop | `30 3 * * *` (user crontab) | Image update |
| laptop | `0 3 * * *` (user crontab) | Restic snapshot |
| laptop | `0 6,13,18 * * *` (user crontab) | **Pull latest** (`kandev-pull.sh`) |

Litestream replication is continuous (always-on, no cron needed). The periodic pull
only matters on the non-writer host(s), where it refreshes the board to the latest
synced state; it no-ops on the active writer.

### Logs

```bash
# Litestream replication (office or carol)
docker logs kandev-litestream --tail 20

# Manual/periodic pull (office or carol)
tail -30 ~/logs/kandev-sync.log

# Restic backup
tail -30 ~/logs/kandev-backup.log

# Image update
tail -30 ~/logs/kandev-update.log
```

## Workflow

| Situation | What to do |
|---|---|
| **Working at office (office-desktop)** | Use `board.office` — Corp VPN required. Litestream replicates changes to home in seconds |
| **Switching to home** | Just open `board.home` or `board.local` — Litestream restore on start gives you office's latest state |
| **Working at home on laptop** | Use `board.local` (127.0.0.1) — VPN-independent local instance |
| **Working on home-server** | Use `board.home` — always available, Caddy serves HTTPS |
| **office-desktop down / VPN not available** | Use `board.home` (home) or `board.local` (laptop) — same data |
| **Recover past state** | `restic snapshots` to browse history, `restic restore` to go back |

## Caveats — `~/Code` on home-server

home-server's `~/Code/` is **shared** between user workspaces AND production service dirs
referenced by systemd units (`~/Code/kandev/`, `~/Code/vpn/`, `~/Code/reverse-proxy/`,
`~/Code/nextcloud-data/`, `~/Code/agent-os/`, `~/Code/vaultwarden/`, `~/Code/nanoclaw/`,
`~/Code/onecli/`, `~/Code/vibe-kanban/`).

Sync scripts **explicitly exclude** these top-level dirs so the rsync `--delete` never
wipes production services. If you add a new infra service under `~/Code/` on home-server,
**add it to the excludes** in both `sync-from-office.sh` and `sync-to-office.sh`.

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
| home-server | `/etc/cron.d/kandev-update` (root) | `~/logs/kandev-update.log` |
| office-desktop | user crontab (`alice`) | `~/logs/kandev-update.log` |
| laptop | user crontab (`carol`) | `~/logs/kandev-update.log` |

### Manual update

```bash
ssh bob@10.0.0.20 "bash ~/Code/kandev/update.sh"           # home-server
ssh alice@office-desktop "bash ~/Code/kandev/update.sh"           # office-desktop (VPN)
bash ~/Code/kandev/update.sh                                       # laptop (local)
```

### Check update log

```bash
ssh bob@10.0.0.20 "tail -20 ~/logs/kandev-update.log"
ssh alice@office-desktop "tail -20 ~/logs/kandev-update.log"
tail -20 ~/logs/kandev-update.log                                  # laptop
```
