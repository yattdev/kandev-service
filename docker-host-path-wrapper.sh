#!/usr/bin/env bash
# docker-host-path-wrapper.sh — installed as /usr/local/bin/docker inside the
# kandev container, ahead of /usr/bin/docker on PATH.
#
# ── The problem ───────────────────────────────────────────────────────────────
# The container has no Docker daemon of its own. It drives the HOST's daemon
# through the bind-mounted /var/run/docker.sock (the "Docker-out-of-Docker"
# pattern), so every container it starts is a sibling on the host, and — this is
# the part that bites — every bind-mount source is resolved against the HOST
# filesystem, not ours.
#
# A path that is perfectly valid in here is usually meaningless up there:
#
#     in the container            on the host
#     /data/tasks/<task>/<repo>   (does not exist)
#     /data/home/Code/<project>   (does not exist)
#
# Docker does not error on a missing bind source. It CREATES it — an empty,
# root-owned directory — and mounts that instead. The sibling container comes up
# with an empty /app or an empty data dir, the agent concludes "my changes
# aren't showing up", and a stray root-owned tree is left behind on the host.
# The failure is completely silent; nothing in `docker run` output hints at it.
#
# ── The fix ───────────────────────────────────────────────────────────────────
# Rewrite container-only paths to their host equivalents before handing the
# command to the real CLI. The mapping is the inverse of the bind mounts
# declared in docker-compose.yml / docker-compose.override.yml, injected as
# KANDEV_HOST_* environment variables (so nothing is hardcoded and this file
# stays host-agnostic).
#
# Rewritten:
#   * -v / --volume sources                         (all subcommands)
#   * --mount source= / src=                        (all subcommands)
#   * -f / --file and --project-directory           (docker compose only)
#   * the working directory                         (docker compose only)
#
# The working-directory rewrite is what makes a project's own compose file work
# unmodified: relative sources like `.:/var/www/html` are resolved by the
# compose CLI against the project directory, so running from the host-equivalent
# directory makes them come out as host paths. That directory is readable in
# here because docker-compose.override.yml also mounts each host path at its own
# host path ("identity mounts").
#
# Escape hatch: /usr/bin/docker is the untouched CLI. Use it directly when you
# really do mean a path as the host sees it and want no rewriting at all.
#
# Debug: `docker --kandev-print-argv <args...>` prints the rewritten argv
# instead of executing it. test.sh uses this to assert the mapping.

set -uo pipefail

REAL_DOCKER=/usr/bin/docker

# ── Mapping table: container prefix -> host prefix ────────────────────────────
# Order matters: first match wins, so every nested mount must be listed BEFORE
# the /data catch-all. /data/home/Code, ~/.ssh, ~/.gitconfig and the CLI config
# dirs are all mounted from elsewhere on the host, so mapping them through
# /data -> KANDEV_HOST_DATA_DIR would point at their (empty) mountpoints
# instead of the real files.
MAPPINGS=()
[[ -n "${KANDEV_HOST_CODE_DIR:-}" ]] && MAPPINGS+=( "/data/home/Code|${KANDEV_HOST_CODE_DIR}" )
if [[ -n "${KANDEV_HOST_HOME:-}" ]]; then
  MAPPINGS+=(
    "/data/home/.ssh|${KANDEV_HOST_HOME}/.ssh"
    "/data/home/.gitconfig|${KANDEV_HOST_HOME}/.gitconfig"
    "/data/home/.config/gh|${KANDEV_HOST_HOME}/.config/gh"
    "/data/home/.config/glab-cli|${KANDEV_HOST_HOME}/.config/glab-cli"
  )
fi
[[ -n "${KANDEV_HOST_DATA_DIR:-}" ]] && MAPPINGS+=( "/data|${KANDEV_HOST_DATA_DIR}" )

# Not inside a configured kandev container (no mapping injected) — stay out of
# the way entirely.
if [[ ${#MAPPINGS[@]} -eq 0 ]]; then
  exec "$REAL_DOCKER" "$@"
fi

REWROTE=0

# translate_path <abs-path> — echo the host equivalent, or the input unchanged.
translate_path() {
  local p=$1 entry from to
  for entry in "${MAPPINGS[@]}"; do
    from=${entry%%|*}
    to=${entry#*|}
    if [[ "$p" == "$from" || "$p" == "$from"/* ]]; then
      REWROTE=1
      printf '%s' "${to}${p#"$from"}"
      return
    fi
  done
  printf '%s' "$p"
}

# rewrite_volume_spec <src:dst[:opts]> — translate the source field only.
# Left alone: named volumes (source has no leading /) and anonymous volumes
# (-v /some/container/path, no colon at all — that is a container path).
rewrite_volume_spec() {
  local spec=$1 src rest
  [[ "$spec" != *:* ]] && { printf '%s' "$spec"; return; }
  src=${spec%%:*}
  rest=${spec#*:}
  [[ "$src" != /* ]] && { printf '%s' "$spec"; return; }
  printf '%s:%s' "$(translate_path "$src")" "$rest"
}

# rewrite_mount_spec <type=bind,source=...,target=...> — translate source=/src=.
# A `type=volume` mount names a volume rather than a path, so the leading-slash
# check skips it.
rewrite_mount_spec() {
  local spec=$1 out="" part key val
  local IFS=,
  for part in $spec; do
    case "$part" in
      source=*|src=*)
        key=${part%%=*}
        val=${part#*=}
        [[ "$val" == /* ]] && val=$(translate_path "$val")
        part="${key}=${val}"
        ;;
    esac
    out="${out:+$out,}$part"
  done
  printf '%s' "$out"
}

# ── Is this a `docker compose ...` invocation? ────────────────────────────────
# Find the first token that is not a flag; global flags that take a value
# (--context, --host, --config, --log-level) would otherwise be mistaken for it.
IS_COMPOSE=0
skip_next=0
for arg in "$@"; do
  if [[ $skip_next -eq 1 ]]; then skip_next=0; continue; fi
  case "$arg" in
    -c|--context|-H|--host|--config|-l|--log-level) skip_next=1 ;;
    -*) ;;
    *) [[ "$arg" == "compose" ]] && IS_COMPOSE=1; break ;;
  esac
done

# ── Debug mode ────────────────────────────────────────────────────────────────
PRINT_ARGV=0
if [[ "${1:-}" == "--kandev-print-argv" ]]; then
  PRINT_ARGV=1
  shift
fi

# ── Rewrite the argument vector ───────────────────────────────────────────────
ARGS=()
expect=""
for arg in "$@"; do
  case "$expect" in
    volume) ARGS+=( "$(rewrite_volume_spec "$arg")" ); expect=""; continue ;;
    mount)  ARGS+=( "$(rewrite_mount_spec  "$arg")" ); expect=""; continue ;;
    path)   ARGS+=( "$(translate_path      "$arg")" ); expect=""; continue ;;
  esac

  case "$arg" in
    -v|--volume)          ARGS+=( "$arg" ); expect=volume ;;
    --volume=*)           ARGS+=( "--volume=$(rewrite_volume_spec "${arg#--volume=}")" ) ;;
    --mount)              ARGS+=( "$arg" ); expect=mount ;;
    --mount=*)            ARGS+=( "--mount=$(rewrite_mount_spec "${arg#--mount=}")" ) ;;

    # compose only: -f in `docker build -f Dockerfile` is read by the CLI from
    # OUR filesystem, so translating it there would break the build.
    -f|--file)            if [[ $IS_COMPOSE -eq 1 ]]; then ARGS+=( "$arg" ); expect=path
                          else ARGS+=( "$arg" ); fi ;;
    --file=*)             if [[ $IS_COMPOSE -eq 1 ]]; then ARGS+=( "--file=$(translate_path "${arg#--file=}")" )
                          else ARGS+=( "$arg" ); fi ;;
    --project-directory)  ARGS+=( "$arg" ); expect=path ;;
    --project-directory=*) ARGS+=( "--project-directory=$(translate_path "${arg#--project-directory=}")" ) ;;

    *)                    ARGS+=( "$arg" ) ;;
  esac
done

# ── Run from the host-equivalent working directory (compose only) ─────────────
# Gives relative sources in the project's own compose file ("./src:/app") a host
# path to resolve against. Only for compose: `docker run -v ./x:/y` is expanded
# by the CLI against $PWD too, but changing directory under other subcommands
# would surprise things like `docker build .`.
CWD_NOTE=""
if [[ $IS_COMPOSE -eq 1 ]]; then
  host_cwd=$(translate_path "$PWD")
  if [[ "$host_cwd" != "$PWD" ]]; then
    if cd "$host_cwd" 2>/dev/null; then
      CWD_NOTE=" (cwd -> $host_cwd)"
    else
      echo "docker[kandev]: warning: cannot enter $host_cwd — is the identity mount missing from docker-compose.override.yml? Relative volume paths may mount empty directories." >&2
    fi
  fi
fi

if [[ $REWROTE -eq 1 ]]; then
  echo "docker[kandev]: rewrote container paths to host paths for the host daemon${CWD_NOTE}" >&2
fi

if [[ $PRINT_ARGV -eq 1 ]]; then
  printf '%s\n' "${ARGS[@]}"
  exit 0
fi

exec "$REAL_DOCKER" "${ARGS[@]}"
