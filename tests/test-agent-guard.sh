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

# Sessionless host utilities run from a backend-owned temporary directory, not
# from a project. The guard must admit only the exact provider child while
# withholding task Docker and device capabilities.
utility_parent="$(sqlite3 -noheader /data/data/kandev.db "
    SELECT path
    FROM storage_temp_artifacts
    WHERE kind = 'host_utility' AND state = 'active'
      AND closed_at IS NULL AND deleted_at IS NULL
    ORDER BY created_at DESC
    LIMIT 1;
")"
backend_pid="$(basename "$utility_parent" | cut -d- -f4)"
utility_root="$utility_parent/claude-acp"
[[ -n "$utility_parent" && -d "$utility_root" ]] || {
    echo "ERROR: no live backend-owned host utility directory available for guard test" >&2
    exit 1
}
(cd "$utility_root" && "$GUARD" -- sh -ceu '
    test "${KANDEV_AGENT_GUARD_SCOPE:-}" = host_utility
    probe="$PWD/.kandev-host-utility-probe-$$"
    printf utility > "$probe"
    test "$(cat "$probe")" = utility
    rm -f "$probe"
    test ! -e /run/docker.sock
    test ! -S /var/run/docker.sock
    test -z "${KANDEV_AGENT_DOCKER_SOCKET:-}"
    test ! -e /dev/kvm
')

fake_utility_parent="/tmp/kandev-host-utility-$backend_pid-999999999"
fake_utility_root="$fake_utility_parent/claude-acp"
mkdir -p "$fake_utility_root"
chmod 0700 "$fake_utility_parent"
chmod 0755 "$fake_utility_root"
if (cd "$fake_utility_root" && "$GUARD" -- true) 2>/dev/null; then
    echo "ERROR: guard accepted a non-MkdirTemp host utility directory" >&2
    exit 1
fi
rm -f "$fake_utility_root"/* 2>/dev/null || true
rmdir "$fake_utility_root" "$fake_utility_parent"

utility_nested="$utility_root/nested"
mkdir "$utility_nested"
if (cd "$utility_nested" && "$GUARD" -- true) 2>/dev/null; then
    rmdir "$utility_nested"
    echo "ERROR: guard accepted a nested host utility working directory" >&2
    exit 1
fi
rmdir "$utility_nested"
(cd "$task_root" && "$GUARD" -- sh -ceu '
    grep -Eq "^NoNewPrivs:[[:space:]]+1$" /proc/self/status
    if sudo -n true 2>/dev/null; then
        echo "ERROR: guarded process escalated through sudo" >&2
        exit 1
    fi
')

# Mobile tasks inherit the read-only SDK/AVD catalogue and only the KVM device.
(cd "$task_root" && "$GUARD" -- sh -ceu '
    test -c /dev/kvm
    test -r /dev/kvm && test -w /dev/kvm
    test -x "${ANDROID_SDK_ROOT:?}/emulator/emulator"
    test -x "${ANDROID_SDK_ROOT:?}/platform-tools/adb"
    test -n "$(emulator -list-avds)"
    case ",$(findmnt -T "${ANDROID_AVD_HOME:?}" -n -o OPTIONS)," in
        *,ro,*) ;;
        *) echo "ERROR: shared Android AVD catalogue is not read-only" >&2; exit 1;;
    esac
    probe="$ANDROID_AVD_HOME/.kandev-avd-write-probe-$$"
    if touch "$probe" 2>/dev/null; then
        rm -f "$probe"
        echo "ERROR: guarded agent modified the host AVD catalogue" >&2
        exit 1
    fi
    test ! -e /tmp/.X11-unix
    test ! -e /run/user/1000/wayland-0
    mkdir -p "${ANDROID_USER_HOME:?}"
    state_probe="$ANDROID_USER_HOME/.kandev-state-probe-$$"
    printf state > "$state_probe"
    rm -f "$state_probe"
')

# Persistent language caches outside Code are writable without widening the
# guard to all of /data/home. Go's default GOMODCACHE lives below ~/go.
(cd "$task_root" && "$GUARD" -- sh -ceu '
    test -d /data/home/go
    probe=$(mktemp /data/home/go/.kandev-go-cache-probe.XXXXXX)
    rm -f "$probe"
')

# A linked task worktree may point to a repository nested at any depth below
# Code. Verify that Git works, while the source repository's working tree stays
# read-only. This is the layout used by inno-prod/projects/co-up.
linked_marker=""
while IFS= read -r candidate; do
    candidate_gitdir="$(sed -n 's/^gitdir: //p' "$candidate" | head -n 1)"
    [[ -n "$candidate_gitdir" && -f "$candidate_gitdir/commondir" ]] || continue
    candidate_common="$(realpath -e -- "$candidate_gitdir/$(head -n 1 "$candidate_gitdir/commondir")" 2>/dev/null || true)"
    if [[ "$candidate_common" == /data/home/Code/*/.git ]]; then
        linked_marker="$candidate"
        gitdir="$(realpath -e -- "$candidate_gitdir")"
        common="$candidate_common"
        break
    fi
done < <(find /data/tasks -mindepth 3 -maxdepth 3 -type f -name .git -print)
[[ -n "$linked_marker" ]] || { echo "ERROR: no linked task worktree available for guard test" >&2; exit 1; }
linked_root="$(dirname "$linked_marker")"
source_root="${common%/.git}"
sibling_gitdir=""
while IFS= read -r candidate; do
    candidate="$(realpath -e -- "$candidate")"
    if [[ "$candidate" != "$gitdir" ]]; then
        sibling_gitdir="$candidate"
        break
    fi
done < <(find "$common/worktrees" -mindepth 1 -maxdepth 1 -type d -print)
[[ -n "$sibling_gitdir" ]] || { echo "ERROR: no sibling Git worktree admin directory available" >&2; exit 1; }
(cd "$linked_root" && "$GUARD" -- sh -ceu '
    assert_mount_mode() {
        path="$1"
        expected="$2"
        label="$3"
        options="$(findmnt -T "$path" -n -o OPTIONS)"
        case ",$options," in
            *",$expected,"*) ;;
            *)
                echo "ERROR: $label mount is not $expected: $path ($options)" >&2
                exit 1
                ;;
        esac
    }

    assert_mount_mode "$1" rw "linked task worktree"
    assert_mount_mode "$2" rw "linked Git common directory"
    assert_mount_mode "$3" ro "source checkout"
    assert_mount_mode "$4" rw "own Git worktree admin directory"
    assert_mount_mode "$5" ro "sibling Git worktree admin directory"
    git -C "$1" status --porcelain >/dev/null
    git -C "$1" add -A --dry-run >/dev/null
' sh "$linked_root" "$common" "$source_root" "$gitdir" "$sibling_gitdir")
source_probe="$source_root/.kandev-guard-source-escape-$$"
if (cd "$linked_root" && "$GUARD" -- sh -c 'touch "$1"' sh "$source_probe") 2>/dev/null; then
    echo "ERROR: linked worktree guard wrote to the source repository working tree" >&2
    exit 1
fi
[[ ! -e "$source_probe" ]]

# Kandev-managed task worktrees keep their shared Git directory below the
# workspace-scoped repository store rather than below /data/home/Code. The
# backlink check below must authorize this normal layout without making the
# managed repository's working tree writable.
managed_marker=""
while IFS= read -r candidate; do
    candidate_gitdir="$(sed -n 's/^gitdir: //p' "$candidate" | head -n 1)"
    [[ -n "$candidate_gitdir" && -f "$candidate_gitdir/commondir" ]] || continue
    candidate_common="$(realpath -e -- "$candidate_gitdir/$(head -n 1 "$candidate_gitdir/commondir")" 2>/dev/null || true)"
    candidate_root="$(dirname "$candidate")"
    if [[ "$candidate_common" == /data/repos/workspaces/*/github/kdlbs/kandev/.git \
          && -f "$candidate_root/mise.toml" ]]; then
        managed_marker="$candidate"
        managed_gitdir="$(realpath -e -- "$candidate_gitdir")"
        managed_common="$candidate_common"
        break
    fi
done < <(find /data/tasks -mindepth 3 -maxdepth 3 -type f -name .git -print)
[[ -n "$managed_marker" ]] || { echo "ERROR: no managed kdlbs/kandev task worktree with mise.toml available for guard test" >&2; exit 1; }
managed_root="$(dirname "$managed_marker")"
managed_source="${managed_common%/.git}"
(cd "$managed_root" && "$GUARD" -- sh -ceu '
    case ",$(findmnt -T "$1" -n -o OPTIONS)," in *,rw,*) ;; *) exit 1;; esac
    case ",$(findmnt -T "$2" -n -o OPTIONS)," in *,rw,*) ;; *) exit 1;; esac
    case ",$(findmnt -T "$3" -n -o OPTIONS)," in *,ro,*) ;; *) exit 1;; esac
    git -C "$1" status --porcelain >/dev/null
    git -C "$1" add -A --dry-run >/dev/null
    case ":${MISE_TRUSTED_CONFIG_PATHS:-}:" in
        *":$1:"*) ;;
        *) echo "ERROR: managed kdlbs/kandev mise config is not trusted inside guard" >&2; exit 1 ;;
    esac
    npx --version >/dev/null
' sh "$managed_root" "$managed_common" "$managed_source")
managed_source_probe="$managed_source/.kandev-guard-managed-source-escape-$$"
if (cd "$managed_root" && "$GUARD" -- sh -c 'touch "$1"' sh "$managed_source_probe") 2>/dev/null; then
    echo "ERROR: managed worktree guard wrote to the source repository working tree" >&2
    exit 1
fi
[[ ! -e "$managed_source_probe" ]]

# Codex's unified-exec can delay a completed command result past the bounded
# ACP probe window.  The guard must disable it only for the codex-acp npx
# launcher while retaining unrelated CODEX_CONFIG settings.  A task-local fake
# npx proves the exact child environment without invoking an agent or changing
# its profile.
codex_probe_dir="$(mktemp -d "$managed_root/.kandev-codex-config-test.XXXXXX")"
trap 'rm -rf -- "$codex_probe_dir"' EXIT
cat > "$codex_probe_dir/npx" <<'EOF'
#!/bin/sh
printf '%s\n' "${CODEX_CONFIG:-}"
EOF
chmod 700 "$codex_probe_dir/npx"
codex_probe_config="$(cd "$managed_root" && PATH="$codex_probe_dir:$PATH" \
    CODEX_CONFIG='{"model":"preserved","features":{"other_feature":true}}' \
    "$GUARD" -- "$codex_probe_dir/npx" --yes @agentclientprotocol/codex-acp@1.7.0)"
python3 -c '
import json
import sys
config = json.loads(sys.stdin.read())
assert config["model"] == "preserved"
assert config["features"]["other_feature"] is True
assert config["features"]["unified_exec"] is False
' <<<"$codex_probe_config"
rm -rf -- "$codex_probe_dir"
trap - EXIT

# The agent can start an isolated Compose project through the broker. Task-local
# bind mounts may be read-write, while any source outside this task is rejected.
(cd "$linked_root" && "$GUARD" -- sh -ceu '
    runtime_dir="$(mktemp -d "$PWD/.kandev-docker-guard-test.XXXXXX")"
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
        "    ports:" \
        "      - \"\${DB_PORT:-3306}:3306\"" \
        "      - \"\${WEB_PORT:-8080}:8080\"" \
        "    labels:" \
        "      guard.compose.scope: \"\${COMPOSE_PROJECT_NAME}\"" \
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
    rendered="$(COMPOSE_PROJECT_NAME=guard-compose-scope DB_PORT=13306 WEB_PORT=18080 docker compose config)"
    project_name="$(printf "%s\n" "$rendered" | sed -n "s/^name: //p" | head -n 1)"
    case "$project_name" in
        kd_*) ;;
        *) echo "ERROR: broker did not enforce a task-scoped Compose project name" >&2; exit 1 ;;
    esac
    printf "%s\n" "$rendered" | grep -Eq "published: [\"\047]?13306[\"\047]?"
    printf "%s\n" "$rendered" | grep -Eq "published: [\"\047]?18080[\"\047]?"
    printf "%s\n" "$rendered" | grep -Eq "guard.compose.scope: [\"\047]?$project_name[\"\047]?"
    attempt=0
    until docker compose up -d --build >/dev/null; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 5 ]; then
            echo "ERROR: task Compose project did not settle after $attempt attempts" >&2
            exit 1
        fi
        sleep "$attempt"
    done
    # `run --rm` is the pre-push-hook path. Its successful exit must propagate
    # through the broker after Compose removes the one-off container.
    if ! run_output="$(docker compose run --rm probe sh -ceu "sleep 2; exit 0" 2>&1)"; then
        echo "ERROR: task Compose run --rm did not propagate a successful exit" >&2
        printf "%s\n" "$run_output" >&2
        exit 1
    fi
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
    [[ -f "$candidate/.git" ]] || continue
    candidate_gitdir="$(sed -n 's/^gitdir: //p' "$candidate/.git" | head -n 1)"
    [[ -n "$candidate_gitdir" && -d "$candidate_gitdir" ]] || continue
    candidate_common="$candidate_gitdir"
    if [[ -f "$candidate_gitdir/commondir" ]]; then
        candidate_common="$(realpath -e -- "$candidate_gitdir/$(head -n 1 "$candidate_gitdir/commondir")")"
    fi
    if [[ "$candidate_common" == "/data/home/Code/coordinator/.git" ]]; then
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
# An explicit but mismatched/partial launch attestation must fail closed even
# when the Git backlink looks like a coordinator worktree.
unauthenticated_coordinator_probe="/data/home/Code/coordinator/.kandev-unattested-probe-$$"
if (
    export KANDEV_TASK_ID=00000000-0000-0000-0000-000000000000
    export KANDEV_SESSION_ID=00000000-0000-0000-0000-000000000000
    export KANDEV_WORKSPACE_ID=00000000-0000-0000-0000-000000000000
    cd "$coordinator_root"
    "$GUARD" -- touch "$unauthenticated_coordinator_probe"
) 2>/dev/null; then
    rm -f "$unauthenticated_coordinator_probe"
    echo "ERROR: mismatched coordinator attestation received workspace elevation" >&2
    exit 1
fi
[[ ! -e "$unauthenticated_coordinator_probe" ]]
partial_coordinator_probe="/data/home/Code/coordinator/.kandev-partial-attestation-probe-$$"
if (
    export KANDEV_TASK_ID=00000000-0000-0000-0000-000000000000
    unset KANDEV_SESSION_ID KANDEV_WORKSPACE_ID
    cd "$coordinator_root"
    "$GUARD" -- touch "$partial_coordinator_probe"
) 2>/dev/null; then
    rm -f "$partial_coordinator_probe"
    echo "ERROR: incomplete coordinator task/session pair received workspace elevation" >&2
    exit 1
fi
[[ ! -e "$partial_coordinator_probe" ]]
coordinator_sources="$(cd "$coordinator_root" && "$GUARD" -- docker kandev source list)"
grep -q '"workspace"' <<<"$coordinator_sources"
grep -q '"containers"' <<<"$coordinator_sources"

coordinator_task_dir="${coordinator_root#/data/tasks/}"
coordinator_task_dir="${coordinator_task_dir%%/*}"
coordinator_context="$(sqlite3 -separator '|' /data/data/kandev.db "
    SELECT t.id, t.workspace_id
    FROM tasks t
    JOIN task_environments te ON te.task_id = t.id
    WHERE te.task_dir_name = '$coordinator_task_dir' AND t.archived_at IS NULL
    LIMIT 1;
")"
IFS='|' read -r coordinator_task_id coordinator_workspace_id <<<"$coordinator_context"
[[ -n "$coordinator_task_id" && -n "$coordinator_workspace_id" ]]
coordinator_session_id="$(sqlite3 /data/data/kandev.db "
    SELECT id FROM task_sessions
    WHERE task_id = '$coordinator_task_id'
      AND state IN ('CREATED', 'STARTING', 'RUNNING', 'WAITING_FOR_INPUT')
    ORDER BY is_primary DESC, updated_at DESC LIMIT 1;
")"
[[ -n "$coordinator_session_id" ]] || {
    echo "ERROR: no live coordinator session available for attestation test" >&2
    exit 1
}

# Kandev v0.92 does not export launch IDs. Verify the authoritative fallback:
# the exact task root plus one active executor launch in a read-only DB grants
# scope even during the launch-order window where the session still says idle.
fallback_db="${coordinator_root%/coordinator}/.kandev-guard-fallback-$$.db"
fallback_audit="${coordinator_root%/coordinator}/.kandev-guard-fallback-audit-$$.jsonl"
fallback_session_id=11111111-1111-1111-1111-111111111111
sqlite3 "$fallback_db" <<SQL
CREATE TABLE workspaces (id TEXT PRIMARY KEY, name TEXT);
CREATE TABLE tasks (id TEXT PRIMARY KEY, workspace_id TEXT, archived_at TEXT);
CREATE TABLE task_environments (task_id TEXT, task_dir_name TEXT);
CREATE TABLE task_sessions (id TEXT PRIMARY KEY, task_id TEXT, state TEXT, workspace_path TEXT);
CREATE TABLE executors_running (session_id TEXT, task_id TEXT, status TEXT, agent_execution_id TEXT, worktree_path TEXT);
CREATE TABLE task_repositories (task_id TEXT, repository_id TEXT);
CREATE TABLE repositories (id TEXT PRIMARY KEY, workspace_id TEXT, local_path TEXT, deleted_at TEXT);
CREATE TABLE task_workspace_folders (task_id TEXT, local_path TEXT);
INSERT INTO workspaces VALUES ('$coordinator_workspace_id', 'fallback-test');
INSERT INTO tasks VALUES ('$coordinator_task_id', '$coordinator_workspace_id', NULL);
INSERT INTO task_environments VALUES ('$coordinator_task_id', '$coordinator_task_dir');
INSERT INTO task_sessions VALUES ('$fallback_session_id', '$coordinator_task_id', 'WAITING_FOR_INPUT', '$coordinator_root');
INSERT INTO executors_running VALUES ('$fallback_session_id', '$coordinator_task_id', 'starting', '33333333-3333-3333-3333-333333333333', '$coordinator_root');
INSERT INTO repositories VALUES ('22222222-2222-2222-2222-222222222222', '$coordinator_workspace_id', '/data/home/Code/coordinator', NULL);
INSERT INTO task_repositories VALUES ('$coordinator_task_id', '22222222-2222-2222-2222-222222222222');
SQL
fallback_probe="/data/home/Code/coordinator/.kandev-fallback-probe-$$"
(
    unset KANDEV_TASK_ID KANDEV_SESSION_ID KANDEV_WORKSPACE_ID
    export KANDEV_DB="$fallback_db"
    export KANDEV_COORDINATOR_SCOPE_AUDIT_LOG="$fallback_audit"
    cd "$coordinator_root"
    "$GUARD" -- sh -ceu 'printf fallback > "$1"; rm -f "$1"' sh "$fallback_probe"
)
[[ ! -e "$fallback_probe" ]]
grep -q "\"session_id\": \"$fallback_session_id\"" "$fallback_audit"
rm -f "$fallback_db" "$fallback_audit"
coordinator_guard() {
    (
        export KANDEV_TASK_ID="$coordinator_task_id"
        export KANDEV_SESSION_ID="$coordinator_session_id"
        # Match the live v0.92 launch environment: workspace_id is derived
        # authoritatively after the exact task/session pair is validated.
        unset KANDEV_WORKSPACE_ID
        cd "$coordinator_root"
        exec "$GUARD" -- "$@"
    )
}

workspace_target_id=""
workspace_target_root=""
while IFS='|' read -r candidate_id candidate_dir; do
    candidate_root="/data/tasks/$candidate_dir"
    if [[ -d "$candidate_root" && "$candidate_root" != "${coordinator_root%/coordinator}" ]]; then
        workspace_target_id="$candidate_id"
        workspace_target_root="$candidate_root"
        break
    fi
done < <(sqlite3 -separator '|' /data/data/kandev.db "
    SELECT t.id, te.task_dir_name
    FROM tasks t
    JOIN task_environments te ON te.task_id = t.id
    WHERE t.workspace_id = '$coordinator_workspace_id'
      AND t.archived_at IS NULL AND te.task_dir_name <> ''
      AND EXISTS (
          SELECT 1 FROM task_repositories tr
          JOIN repositories r ON r.id = tr.repository_id
          WHERE tr.task_id = t.id
            AND r.local_path LIKE '/data/home/Code/%'
            AND r.deleted_at IS NULL
      )
      AND NOT EXISTS (
          SELECT 1 FROM task_repositories tr
          JOIN repositories r ON r.id = tr.repository_id
          WHERE tr.task_id = t.id
            AND (r.local_path NOT LIKE '/data/home/Code/%' OR r.deleted_at IS NOT NULL)
      )
      AND NOT EXISTS (
          SELECT 1 FROM task_sessions ts
          WHERE ts.task_id = t.id AND ts.state IN ('STARTING', 'RUNNING')
      )
    ORDER BY t.updated_at DESC;
")
[[ -n "$workspace_target_id" && -n "$workspace_target_root" ]] || {
    echo "ERROR: no same-workspace target task available for coordinator scope test" >&2
    exit 1
}

# Coordinator elevation covers exact registered same-workspace task roots and
# repositories, while the managed parents and another workspace remain RO.
registered_repo=""
while IFS= read -r candidate_repo; do
    if [[ -d "$candidate_repo" ]]; then
        registered_repo="$candidate_repo"
        break
    fi
done < <(sqlite3 /data/data/kandev.db "
    SELECT local_path FROM repositories
    WHERE workspace_id = '$coordinator_workspace_id' AND deleted_at IS NULL
      AND local_path <> '/data/home/Code/coordinator'
      AND (local_path LIKE '/data/home/Code/%'
           OR local_path LIKE '/data/repos/workspaces/$coordinator_workspace_id/%')
    ORDER BY CASE WHEN local_path LIKE '/data/repos/workspaces/%' THEN 0 ELSE 1 END,
             local_path;
")
[[ -d "$registered_repo" ]] || { echo "ERROR: no registered source repository for coordinator test" >&2; exit 1; }
foreign_task_root=""
while IFS= read -r candidate_dir; do
    candidate_root="/data/tasks/$candidate_dir"
    if [[ -d "$candidate_root" ]]; then
        foreign_task_root="$candidate_root"
        break
    fi
done < <(sqlite3 /data/data/kandev.db "
    SELECT te.task_dir_name
    FROM tasks t
    JOIN task_environments te ON te.task_id = t.id
    WHERE t.workspace_id <> '$coordinator_workspace_id'
      AND t.archived_at IS NULL AND te.task_dir_name <> ''
    ORDER BY t.updated_at DESC;
")
[[ -n "$foreign_task_root" ]] || { echo "ERROR: no foreign workspace task for isolation test" >&2; exit 1; }

coordinator_guard sh -ceu '
    for path in "$1" "$2"; do
        options="$(findmnt -T "$path" -n -o OPTIONS)"
        case ",$options," in *",rw,"*) ;; *) echo "ERROR: coordinator path is not rw: $path ($options)" >&2; exit 1;; esac
        probe="$path/.kandev-coordinator-workspace-probe-$$"
        printf allowed > "$probe"
        rm -f "$probe"
    done
    if touch "$3/.kandev-coordinator-foreign-probe-$$" 2>/dev/null; then
        rm -f "$3/.kandev-coordinator-foreign-probe-$$"
        echo "ERROR: coordinator wrote into another workspace" >&2
        exit 1
    fi
' sh "$workspace_target_root" "$registered_repo" "$foreign_task_root"

workspace_probe="$(coordinator_guard docker kandev workspace probe "$workspace_target_id")"
grep -q 'task_write=ok' <<<"$workspace_probe"

# A coordinator worktree can fast-forward/publish the shared knowledge checkout.
coordinator_probe="/data/home/Code/coordinator/.kandev-shared-write-probe-$$"
coordinator_guard sh -ceu '
    printf coordinator > "$1"
    test "$(cat "$1")" = coordinator
    rm -f "$1"
' sh "$coordinator_probe"
[[ ! -e "$coordinator_probe" ]]

# Coordinator processes are supervised in the background for periodic scope
# rechecks. Their original stdin must remain connected for ACP JSON-RPC.
printf 'coordinator-stdin\n' \
    | coordinator_guard sh -ceu 'IFS= read -r line; test "$line" = coordinator-stdin'

if (cd / && "$GUARD" -- true) 2>/dev/null; then
    echo "ERROR: guard accepted an unscoped root workspace" >&2
    exit 1
fi

echo "PASS: linked-task Git isolation, registered host-utility scope, writable task Compose/Android QA, attested coordinator workspace/source/probe scope, and cross-workspace/Code-root/raw-socket/sudo boundaries work"
