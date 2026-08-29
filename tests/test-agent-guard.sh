#!/usr/bin/env bash
# Run inside the Kandev container after it has started.
set -euo pipefail

GUARD=/usr/local/bin/kandev-agent-guard
task_root=""
while IFS= read -r task_dir_name; do
    candidate="/data/tasks/$task_dir_name"
    if [[ -d "$candidate" ]]; then
        task_root="$candidate"
        break
    fi
done < <(sqlite3 /data/data/kandev.db "
    SELECT te.task_dir_name
    FROM task_environments te
    JOIN tasks t ON t.id = te.task_id
    WHERE t.archived_at IS NULL AND te.task_dir_name <> ''
      AND NOT EXISTS (
          SELECT 1 FROM task_repositories tr
          JOIN repositories r ON r.id = tr.repository_id
          WHERE tr.task_id = t.id
            AND r.local_path = '/data/home/Code/coordinator'
            AND r.deleted_at IS NULL
      )
    ORDER BY t.updated_at DESC;
")
[[ -n "$task_root" ]] || { echo "ERROR: no ordinary task workspace available for guard test" >&2; exit 1; }

probe="$task_root/.kandev-guard-write-probe-$$"
(cd "$task_root" && "$GUARD" -- sh -ceu 'printf allowed > "$1"; test "$(cat "$1")" = allowed; rm -f "$1"' sh "$probe")
[[ ! -e "$probe" ]]

if (cd "$task_root" && "$GUARD" -- sh -c 'touch /data/home/Code/.kandev-guard-escape-probe') 2>/dev/null; then
    echo "ERROR: guarded process wrote to the Code root" >&2
    exit 1
fi
[[ ! -e /data/home/Code/.kandev-guard-escape-probe ]]

(cd "$task_root" && "$GUARD" -- sh -ceu '
    test ! -e /run/docker.sock
    test ! -S /var/run/docker.sock
    test -S "${KANDEV_AGENT_DOCKER_SOCKET:?}"
    docker compose version >/dev/null
    if docker kandev source list >/dev/null 2>&1; then
        echo "ERROR: ordinary task received coordinator source access" >&2
        exit 1
    fi
')
(cd "$task_root" && "$GUARD" -- sh -ceu '
    grep -Eq "^NoNewPrivs:[[:space:]]+1$" /proc/self/status
    if sudo -n true 2>/dev/null; then
        echo "ERROR: guarded process escalated through sudo" >&2
        exit 1
    fi
')

# A linked task worktree may point to a repository nested at any depth below
# Code. Verify that Git works, while the source repository's working tree stays
# read-only. This is the layout used by inno-prod/projects/co-up.
linked_marker="$(find /data/tasks -mindepth 3 -maxdepth 3 -type f -name .git -print -quit)"
[[ -n "$linked_marker" ]] || { echo "ERROR: no linked task worktree available for guard test" >&2; exit 1; }
linked_root="$(dirname "$linked_marker")"
gitdir="$(sed -n 's/^gitdir: //p' "$linked_marker" | head -n 1)"
common="$(realpath -e -- "$gitdir/$(head -n 1 "$gitdir/commondir")")"
(cd "$linked_root" && "$GUARD" -- git status --porcelain >/dev/null)
source_root="${common%/.git}"
source_probe="$source_root/.kandev-guard-source-escape-$$"
if (cd "$linked_root" && "$GUARD" -- sh -c 'touch "$1"' sh "$source_probe") 2>/dev/null; then
    echo "ERROR: linked worktree guard wrote to the source repository working tree" >&2
    exit 1
fi
[[ ! -e "$source_probe" ]]

# The agent can start an isolated Compose project through the broker. Task-local
# bind mounts may be read-write, while any source outside this task is rejected.
(cd "$linked_root" && "$GUARD" -- sh -ceu '
    runtime_dir="$PWD/.kandev-docker-guard-test-$$"
    mkdir "$runtime_dir"
    cleanup() {
        (cd "$runtime_dir" && docker compose down -v --remove-orphans >/dev/null 2>&1) || true
        rm -f "$runtime_dir/Containerfile.test" "$runtime_dir/docker-compose.yml" \
            "$runtime_dir/outside.yml" "$runtime_dir/container-write"
        rmdir "$runtime_dir" 2>/dev/null || true
    }
    trap cleanup EXIT HUP INT TERM
    printf "%s\n" "FROM alpine:latest" > "$runtime_dir/Containerfile.test"
    printf "%s\n" \
        "services:" \
        "  probe:" \
        "    build:" \
        "      context: ." \
        "      dockerfile: Containerfile.test" \
        "    command: [sh, -c, \"echo ready >/state/ready; sleep 300\"]" \
        "    volumes:" \
        "      - type: bind" \
        "        source: ." \
        "        target: /workspace" \
        "      - type: volume" \
        "        source: state" \
        "        target: /state" \
        "volumes:" \
        "  state: {}" > "$runtime_dir/docker-compose.yml"
    cd "$runtime_dir"
    docker compose up -d --build >/dev/null
    docker compose exec -T probe test -f /state/ready
    docker compose exec -T probe sh -c "echo container-write >/workspace/container-write"
    test "$(cat container-write)" = container-write
    printf "%s\n" \
        "services:" \
        "  escape:" \
        "    image: alpine:latest" \
        "    volumes:" \
        "      - /data/home/Code:/escape" > outside.yml
    if docker compose -f outside.yml up -d >/dev/null 2>&1; then
        echo "ERROR: broker accepted a bind outside the task" >&2
        exit 1
    fi
')

# Every materialized coordinator worktree is authorized from Kandev's trusted
# task/workspace/repository metadata. The shared source checkout is deliberately
# not used because multiple workspace coordinators can point at it.
coordinator_root=""
while IFS= read -r task_dir_name; do
    candidate="/data/tasks/$task_dir_name/coordinator"
    if [[ -f "$candidate/.git" ]]; then
        coordinator_root="$candidate"
        break
    fi
done < <(sqlite3 /data/data/kandev.db "
    SELECT te.task_dir_name
    FROM task_environments te
    JOIN tasks t ON t.id = te.task_id
    WHERE t.archived_at IS NULL AND te.task_dir_name <> ''
      AND (SELECT COUNT(*) FROM task_repositories tr WHERE tr.task_id = t.id) = 1
      AND EXISTS (
          SELECT 1 FROM task_repositories tr
          JOIN repositories r ON r.id = tr.repository_id
          WHERE tr.task_id = t.id AND r.workspace_id = t.workspace_id
            AND r.local_path = '/data/home/Code/coordinator'
            AND r.deleted_at IS NULL
      )
    ORDER BY t.updated_at DESC;
")
[[ -n "$coordinator_root" ]] || {
    echo "ERROR: no registered coordinator task worktree available for source policy test" >&2
    exit 1
}
coordinator_sources="$(cd "$coordinator_root" && "$GUARD" -- docker kandev source list)"
grep -q '"workspace"' <<<"$coordinator_sources"
grep -q '"containers"' <<<"$coordinator_sources"

# A coordinator worktree can fast-forward/publish the shared knowledge checkout.
coordinator_probe="/data/home/Code/coordinator/.kandev-shared-write-probe-$$"
(cd "$coordinator_root" && "$GUARD" -- sh -ceu '
    printf coordinator > "$1"
    test "$(cat "$1")" = coordinator
    rm -f "$1"
' sh "$coordinator_probe")
[[ ! -e "$coordinator_probe" ]]

if (cd / && "$GUARD" -- true) 2>/dev/null; then
    echo "ERROR: guard accepted an unscoped root workspace" >&2
    exit 1
fi

echo "PASS: linked tasks, writable isolated Compose, and coordinator shared/source scope work; task writes allowed; unrelated source/Code-root writes, raw Docker socket, sudo, and / workspace blocked"
