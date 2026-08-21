---
name: kandev-change
description: Branch and verification rules for changing the kandev deployment in ~/Code/kandev. Use BEFORE editing or committing any infrastructure file here — Dockerfile.local, docker-compose*.yml, docker-entrypoint-local.sh, docker-host-path-wrapper.sh, apparmor/, seccomp/, scripts/, tests/, test.sh, update.sh, kandev-*.sh, install-*.sh, sync-*.sh, mise.default.toml, CLAUDE.md, AGENTS.md, README.md — and before running kandev-start.sh, update.sh, kandev-pull.sh, or any docker compose command. Also use when the kandev container crash-loops, when the board UI is unreachable, or after any git branch switch in this repo.
---

# Changing the kandev deployment

## Step 1 — be on `main` before you touch anything

`main` is the only branch that carries the deployment. The `*-workflow` branches
(`claude-workflow`, `codex-workflow`, `codex-copilotDI-workflow`,
`copilot-workflow`, `copilot-DeepInfra-workflow`) exist **only** to edit the agent
workflow definition under `workflows/`. They are stale forks of `main`, never
synced back, each carrying an old copy of every infra file.

```bash
cd ~/Code/kandev
git rev-parse --abbrev-ref HEAD    # must print: main
git switch main                    # if it does not
```

Decide by **which path you are editing**, not by which branch you happen to be on:

| Path being changed | Branch |
|---|---|
| `workflows/**` only | the relevant `*-workflow` branch |
| anything else | **`main`** |

A task that mixes both is two changes: infra on `main`, workflow on its branch.
Never carry an infra edit onto a workflow branch.

## Step 2 — never run the deployment from a non-`main` checkout

`kandev-start.sh`, `update.sh`, `kandev-pull.sh`, and any bare
`docker compose up` read the compose files **from the current working tree**. On a
`*-workflow` branch they build the container from that branch's outdated
`docker-compose.override.yml` / `Dockerfile.local` — silently dropping everything
`main` added since, including the `security_opt:` block the Codex bubblewrap
sandbox needs. Nothing in the output warns you.

`scripts/require-main-branch.sh` enforces this: those entry points abort with exit
78 off `main`. Do not bypass it with a direct `docker compose` call — switch
branch. Deliberate override for testing a compose change on a branch:
`KANDEV_ALLOW_BRANCH=1`.

Switching back to `main` does **not** repair an already-running container. After
any branch switch:

```bash
cd ~/Code/kandev && git switch main && docker compose -p kandev up -d --force-recreate
```

## Step 3 — verify

```bash
# security profiles actually landed (the 2026-08-21 crash-loop was their absence)
docker inspect kandev --format '{{.AppArmorProfile}} {{json .HostConfig.SecurityOpt}}'
#   want: kandev-codex  ["seccomp={...}","apparmor=kandev-codex"]
#   bad:  docker-default  null

docker inspect kandev --format 'status={{.State.Status}} restarts={{.RestartCount}}'
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://localhost:38429/
```

Then the suite — mandatory for any change to `Dockerfile.local`,
`docker-compose*.yml`, `docker-entrypoint-local.sh`, `update.sh`, or an
`install-*.sh`. Rebuild first if `Dockerfile.local` changed; recreate first if a
compose file changed:

```bash
bash ~/Code/kandev/test.sh     # all tests must be green before you commit
```

Fix the root cause of any failure — never weaken or skip a test.

## Crash-loop triage

`bwrap: No permissions to create new namespace` repeating in `docker logs kandev`
means the container is missing its `security_opt` — almost always because it was
created from a non-`main` tree. On hosts with
`kernel.apparmor_restrict_unprivileged_userns=1`, without the `kandev-codex`
AppArmor profile and `seccomp/kandev-bwrap.json` the entrypoint preflight exits 78
on every start. Fix with the Step 2 recreate command.

## Before acting on any hostname, user, or IP

Read the git-ignored `host.env` at the repo root first — the committed files use
sanitized placeholders, and `host.env`'s header maps each one to its real value.

Full context: `CLAUDE.md` and `AGENTS.md` in the repo root.
