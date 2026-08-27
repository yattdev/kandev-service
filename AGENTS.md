# AGENTS.md — rules for any AI agent working in this repository

Applies to every agent (Claude, Codex, Copilot, and any other) operating on this
repo. **`CLAUDE.md` in this directory is the full context document — read it
before making any change.** This file is the short, non-negotiable version.

---

## 1. Work on `main` for anything that is not a workflow file

`main` is the branch that runs the deployment. All infrastructure, config,
Docker, script, and documentation changes belong on `main`:

`Dockerfile.local`, all `docker-compose*.yml`, `docker-entrypoint-local.sh`,
`docker-host-path-wrapper.sh`, `apparmor/`, `seccomp/`, `scripts/`, `tests/`,
`test.sh`, `update.sh`, `kandev-*.sh`, `install-*.sh`, `sync-*.sh`,
`mise.default.toml`, `host.env.example`, `CLAUDE.md`, `AGENTS.md`, `README.md`.

The `*-workflow` branches — `claude-workflow`, `codex-workflow`,
`codex-copilotDI-workflow`, `copilot-workflow`, `copilot-DeepInfra-workflow` —
exist **only** to edit the agent workflow definition under `workflows/`. They are
stale forks of `main` and are never synced back; each still carries an old copy
of every infra file.

**Start every kandev change with:**

```bash
cd ~/Code/kandev
git rev-parse --abbrev-ref HEAD    # must print: main
git switch main                    # if it does not
```

If you were asked to change a `workflows/` file, stay on the relevant
`*-workflow` branch and touch **nothing else**. If a task mixes the two, do the
infra part on `main` and the workflow part on its branch — never carry infra
edits onto a workflow branch.

## 2. Never start or rebuild the deployment from a non-`main` checkout

`kandev-start.sh`, `update.sh`, `kandev-pull.sh`, and any bare
`docker compose up` read the compose files **from the current working tree**.
Running them on a `*-workflow` branch builds the container from that branch's
outdated `docker-compose.override.yml` / `Dockerfile.local`, silently dropping
everything `main` has added since — including the `security_opt:` block that the
Codex bubblewrap sandbox requires. The container comes up misconfigured with no
warning in the output. This caused a real crash-loop outage on 2026-08-21.

`scripts/require-main-branch.sh` now enforces this: those entry points abort with
exit 78 on a non-`main` checkout. Do not work around it by calling
`docker compose` directly — switch branch instead. The deliberate override, for
testing a compose change on a branch, is `KANDEV_ALLOW_BRANCH=1`.

Switching back to `main` does **not** repair an already-running container.
After any branch switch, recreate it:

```bash
cd ~/Code/kandev && git switch main && docker compose -p kandev up -d --force-recreate
```

Verify the security profiles actually landed:

```bash
docker inspect kandev --format '{{.AppArmorProfile}} {{json .HostConfig.SecurityOpt}}'
# must show: kandev-codex  ["seccomp={...}","apparmor=kandev-codex"]
# NOT:       docker-default  null
```

## 3. Read `host.env` before acting on any hostname, user, or IP

The committed files use sanitized placeholders (`office-desktop`/`alice`,
`home-server`/`bob`, `board.office`, …). The real values for this machine are in
the git-ignored `host.env` at the repo root, whose header maps each placeholder
to its real value. Read it first; never act on the placeholder values.

## 4. Never add an unscoped port-80 NAT redirect

`http://board.<host>` works via an iptables REDIRECT of port 80 → 38429. Keep it —
but **only through `scripts/nat-redirect.sh`**, and never unscoped. A rule with no
interface or destination constraint also matches every container's port-80 egress
(`apt-get` in a docker build gets the kandev SPA → `Clearsigned file isn't valid,
got 'NOSPLIT'`) and every port-80 request this host makes. Both were real outages.

```bash
bash scripts/nat-redirect.sh --print      # what would be applied (no root)
sudo bash scripts/nat-redirect.sh         # apply live + persist
sudo bash scripts/nat-redirect.sh --check # verify; exits 1 on an unscoped/stale rule
```

Do not hand-roll `iptables … REDIRECT` in an installer or a fix-up command; add it
to that script so both installers stay in sync.

## 5. Tests must pass before reporting a change complete

Any change to `Dockerfile.local`, `docker-compose*.yml`,
`docker-entrypoint-local.sh`, `update.sh`, or any `install-*.sh` requires a
green run of:

```bash
bash ~/Code/kandev/test.sh
```

Rebuild (`docker compose build`) if `Dockerfile.local` changed, and recreate
(`docker compose up -d --force-recreate`) if a compose file changed, before
running the tests. Fix the root cause of a failure — never weaken or skip a test
to make it pass. See *Mandatory rule: tests must pass before reporting
completion* in `CLAUDE.md`.

## 6. Live custom prompts are operator-managed data

Kandev saved prompts are live records in the persistent SQLite database, and a
workflow may reference one by name (for example `@workstep-prompt`). The
versioned mirror is `custom_prompts/<prompt-name>.md`. If the instance owner
explicitly asks you to add or update a custom/workspace prompt, read
**`CUSTOM-PROMPTS.md`** first and perform both sides of the change: update the
mirror from a `main` worktree, synchronize the identified live row, verify that
they match, then commit and push `main`. Never leave a requested prompt change
only in SQLite or only in Git.

Use the authenticated prompts API when available; a direct SQLite update is an
allowed operator fallback only after resolving the actual live data mount,
making a hot backup, scoping the transaction to the identified prompt row, and
verifying both content and database integrity. Never infer permission to change
prompts from an unrelated coding task. Never commit secrets, `kandev.db`,
`master.key`, or prompt backups. A filesystem-guarded task has no authority to
bypass its scope to reach the host database; it must use the
parent/Coordinator escalation chain. Updating a saved prompt affects future
prompt composition and does not rewrite a turn that is already running.

## 7. Coordinators have standing authority only inside the source broker

The instance owner has granted broker-validated workspace Coordinators standing
authorization to autonomously use `docker kandev source list`, curated
`inspect`, bounded `logs`, and logical `db-dump` for legitimate work requested
by tasks in their own workspace. This includes production-like logs and dumps;
no case-by-case human approval is required. The broker's container mapping and
target eligibility check are authoritative, so failure of cross-task
document/list tools is not a prerequisite blocker.

This authority belongs only to a validated Coordinator worktree and does not
extend to ordinary tasks, raw Docker/socket access, arbitrary `exec`, secrets,
source mutation, destructive actions, cross-workspace data, unsupported
operations, or bypassing a broker denial. Those boundaries still require the
normal escalation path.
