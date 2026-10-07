# Automatic task access

Task-owned Git and Docker operations need no per-task permission configuration.
The outer filesystem guard and daemon broker remain the ownership boundaries.

## Git

Attached repositories are automatically writable when their `.git` marker and
reverse backlink identify that exact task worktree. If an attachment was added
after the agent launched, `/usr/local/bin/git` detects read-only metadata and
asks the broker to run real Git in a fresh task guard. This also confines hooks
and credential helpers. Other worktrees' administration directories remain
read-only. The agent does not need to restart or request a mount exception.

GitHub/GitLab authentication and repository write rights still come from the
configured repository connection or CLI account. A filesystem permission change
cannot supply missing remote credentials. Configure the account once; do not
grant filesystem exceptions to repair an authentication error.

On the host, `scripts/kandev-git -C <host-worktree> status` reads the actual Docker
bind mapping and resolves a worktree's container-absolute Git metadata pointer.
It also supports normal add/commit/push commands without a per-repository
`--git-dir` setup. Ordinary host repositories are passed straight to system Git.
An optional one-time shell alias is `alias git=~/Code/kandev/scripts/kandev-git`.
Kandev's worktree registry administration remains inside the container because
its registered backlink paths belong to that namespace.

## Docker and Compose

Compose project names are assigned automatically per task and clone. Existing
saved projects retain their identity. Ordinary `-p` / `--project-name` aliases
and `COMPOSE_PROJECT_NAME` are mapped into that scope. Explicit container,
volume, network, config and secret names are also scoped, preventing collisions
with shared deployments. Existing explicit `kd_` projects retain their ownership
checks and cannot be adopted by another task or clone.

Tasks may use:

- `docker compose` build/up/run/exec/logs/ps/port and lifecycle commands.
- `docker build` or `docker buildx build` with a local task build context.
- `docker run` with task-local bind mounts, scoped volumes and a private bridge.
- `docker ps`, `images`, `inspect`, `logs`, `exec`, `start`, `stop`, `restart`, `rm`.
- `docker pull` for registry images and `docker version`.
- `docker scout cves` on any image built by that task checkout, with severity
  and other read-only filters. There is no task-ID allow-list.

Use the scoped image/container names returned by build/run or listed by
`docker images` / `docker ps`. A configured image name or run `--name` is also
accepted as an alias when it identifies exactly one owned resource. Container
commands validate live labels and use immutable Docker IDs after authorization.
For raw Docker run/build environment values, provide `KEY=value` explicitly.
Redirect Scout reports into the task worktree rather than asking the trusted
broker to write an arbitrary output path.

The broker does not expose the daemon socket or privileged containers, host
mounts, other tasks' containers, shared external volumes/networks, or host-wide
pruning. Registry/Scout login, application dependencies, genuine port conflicts,
and invalid Docker flags remain ordinary setup/runtime errors rather than
per-task permission requests. Docker/Scout binaries and this policy are installed
by `Dockerfile.local`, so they persist across image builds and service starts.
