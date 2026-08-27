#!/usr/bin/env bash
# Run inside the Kandev container after it has started.
set -euo pipefail

GUARD=/usr/local/bin/kandev-agent-guard
task_root="$(find /data/tasks -mindepth 1 -maxdepth 1 -type d ! -name '.*' -print -quit)"
[[ -n "$task_root" ]] || { echo "ERROR: no task workspace available for guard test" >&2; exit 1; }

probe="$task_root/.kandev-guard-write-probe-$$"
(cd "$task_root" && "$GUARD" -- sh -ceu 'printf allowed > "$1"; test "$(cat "$1")" = allowed; rm -f "$1"' sh "$probe")
[[ ! -e "$probe" ]]

if (cd "$task_root" && "$GUARD" -- sh -c 'touch /data/home/Code/.kandev-guard-escape-probe') 2>/dev/null; then
    echo "ERROR: guarded process wrote to the Code root" >&2
    exit 1
fi
[[ ! -e /data/home/Code/.kandev-guard-escape-probe ]]

(cd "$task_root" && "$GUARD" -- sh -ceu 'test ! -e /run/docker.sock; test ! -S /var/run/docker.sock')
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

if (cd / && "$GUARD" -- true) 2>/dev/null; then
    echo "ERROR: guard accepted an unscoped root workspace" >&2
    exit 1
fi

echo "PASS: linked task worktrees work; task writes allowed; source/Code-root writes, sudo, Docker socket, and / workspace blocked"
