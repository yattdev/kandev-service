#!/usr/bin/env bash
# test.sh — Validate the kandev local image and running container.
#
# Usage:
#   bash ~/Code/kandev/test.sh          # run all tests
#   bash ~/Code/kandev/test.sh --build  # build image first, then test
#
# Exit code: 0 if all tests pass, 1 if any fail.
# All tests must be green before reporting a task as complete.
set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0
ERRORS=()

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'
BOLD='\033[1m'

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}✗${RESET} $1"; FAIL=$((FAIL + 1)); ERRORS+=("$1"); }
section() { echo -e "\n${BOLD}$1${RESET}"; }

# ── Optional --build flag ─────────────────────────────────────────────────────
if [[ "${1:-}" == "--build" ]]; then
  echo -e "${YELLOW}Building kandev-local:latest ...${RESET}"
  cd "$COMPOSE_DIR"
  docker compose build --quiet
  echo ""
fi

# ── 1. Image ──────────────────────────────────────────────────────────────────
section "1. Image"

if docker image inspect kandev-local:latest &>/dev/null; then
  ok "kandev-local:latest image exists"
else
  fail "kandev-local:latest image not found — run: docker compose build"
fi

# Entrypoint file on disk must contain the patched chown
if grep -q '|| true' "$COMPOSE_DIR/docker-entrypoint-local.sh"; then
  ok "docker-entrypoint-local.sh contains chown || true patch"
else
  fail "docker-entrypoint-local.sh is missing the chown || true patch"
fi

# Entrypoint inside the built image must also contain the patch
if docker run --rm kandev-local:latest cat /usr/local/bin/docker-entrypoint.sh 2>/dev/null \
    | grep -q '|| true'; then
  ok "entrypoint inside image has chown || true patch"
else
  fail "entrypoint inside image is missing the patch (rebuild required)"
fi

# Required binaries present in image
for bin in ssh gh glab git; do
  if docker run --rm kandev-local:latest which "$bin" &>/dev/null; then
    ok "$bin binary present in image"
  else
    fail "$bin binary missing from image"
  fi
done

# git system safe.directory must be '*'
SAFE=$(docker run --rm kandev-local:latest git config --system safe.directory 2>/dev/null || echo "")
if [[ "$SAFE" == "*" ]]; then
  ok "git system safe.directory = *"
else
  fail "git system safe.directory = '${SAFE}' (expected *)"
fi

# ── 2. Container ─────────────────────────────────────────────────────────────
section "2. Container"

CONTAINER_STATUS=$(docker inspect kandev --format '{{.State.Status}}' 2>/dev/null || echo "missing")
if [[ "$CONTAINER_STATUS" == "running" ]]; then
  ok "container is running"
else
  fail "container is not running (status: $CONTAINER_STATUS)"
fi

RESTARTS=$(docker inspect kandev --format '{{.RestartCount}}' 2>/dev/null || echo "999")
if [[ "$RESTARTS" -eq 0 ]]; then
  ok "container restart count = 0 (no crash loop)"
else
  fail "container has restarted ${RESTARTS} times — likely crash-looping"
fi

# ── 3. Service ────────────────────────────────────────────────────────────────
section "3. Service reachability"

HTTP_CODE="000"
for i in 1 2 3 4 5; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:38429/ 2>/dev/null || echo "000")
  [[ "$HTTP_CODE" == "200" ]] && break
  sleep 2
done
if [[ "$HTTP_CODE" == "200" ]]; then
  ok "HTTP 200 on localhost:38429"
else
  fail "Expected HTTP 200, got ${HTTP_CODE} on localhost:38429"
fi

# ── 4. Identity inside container ──────────────────────────────────────────────
section "4. Host identity inside container"

CONTAINER_USER=$(docker exec -u kandev kandev sh -c 'echo $USER' 2>/dev/null || echo "")
HOST_USER="${USER}"
if [[ "$CONTAINER_USER" == "$HOST_USER" ]]; then
  ok "\$USER = $HOST_USER (matches host)"
else
  fail "\$USER = '$CONTAINER_USER' inside container (expected '$HOST_USER')"
fi

CONTAINER_LOGNAME=$(docker exec -u kandev kandev sh -c 'echo $LOGNAME' 2>/dev/null || echo "")
if [[ "$CONTAINER_LOGNAME" == "$HOST_USER" ]]; then
  ok "\$LOGNAME = $HOST_USER (matches host)"
else
  fail "\$LOGNAME = '$CONTAINER_LOGNAME' inside container (expected '$HOST_USER')"
fi

CONTAINER_HOME=$(docker exec -u kandev kandev sh -c 'echo $HOME' 2>/dev/null || echo "")
if [[ "$CONTAINER_HOME" == "/data/home" ]]; then
  ok "\$HOME = /data/home"
else
  fail "\$HOME = '$CONTAINER_HOME' (expected /data/home)"
fi

# ── 5. Git ────────────────────────────────────────────────────────────────────
section "5. Git identity and config"

GIT_NAME=$(docker exec -u kandev kandev git config --global user.name 2>/dev/null || echo "")
if [[ -n "$GIT_NAME" ]]; then
  ok "git user.name = '$GIT_NAME'"
else
  fail "git user.name is not set (check ~/.gitconfig mount)"
fi

GIT_EMAIL=$(docker exec -u kandev kandev git config --global user.email 2>/dev/null || echo "")
if [[ -n "$GIT_EMAIL" ]]; then
  ok "git user.email = '$GIT_EMAIL'"
else
  fail "git user.email is not set (check ~/.gitconfig mount)"
fi

SAFE_IN_CONTAINER=$(docker exec -u kandev kandev git config --system safe.directory 2>/dev/null || echo "")
if [[ "$SAFE_IN_CONTAINER" == "*" ]]; then
  ok "git system safe.directory = * (inside running container)"
else
  fail "git system safe.directory = '$SAFE_IN_CONTAINER' in container (expected *)"
fi

# ── 6. SSH ────────────────────────────────────────────────────────────────────
section "6. SSH keys and config"

SSH_DIR_EXISTS=$(docker exec -u kandev kandev sh -c '[ -d /data/home/.ssh ] && echo yes || echo no' 2>/dev/null)
if [[ "$SSH_DIR_EXISTS" == "yes" ]]; then
  ok "/data/home/.ssh directory is mounted"
else
  fail "/data/home/.ssh is not mounted"
fi

SSH_CONFIG_EXISTS=$(docker exec -u kandev kandev sh -c '[ -f /data/home/.ssh/config ] && echo yes || echo no' 2>/dev/null)
if [[ "$SSH_CONFIG_EXISTS" == "yes" ]]; then
  ok "/data/home/.ssh/config is present"
else
  fail "/data/home/.ssh/config not found (check ~/.ssh mount)"
fi

# SSH config must resolve github.com to *some* identity file that actually
# exists on disk. The exact filename is host-specific (each host's ~/.ssh
# uses its own key names), so this is intentionally not hardcoded to one
# host's key — it only checks that resolution + the key file both work.
GH_KEY=$(docker exec -u kandev kandev ssh -G github.com 2>/dev/null | grep '^identityfile' | head -1 | awk '{print $2}')
GH_KEY_EXISTS=$(docker exec -u kandev kandev sh -c "[ -n \"$GH_KEY\" ] && eval [ -f $GH_KEY ] && echo yes || echo no" 2>/dev/null)
if [[ -n "$GH_KEY" && "$GH_KEY_EXISTS" == "yes" ]]; then
  ok "github.com resolves to an existing identity file ($GH_KEY)"
else
  fail "github.com identity file = '$GH_KEY' (missing or unresolved)"
fi

# ~/.ssh must be read-only — attempt a write and expect failure
RO_SSH=$(docker exec kandev sh -c 'touch /data/home/.ssh/.write-test 2>&1 || echo READONLY')
if echo "$RO_SSH" | grep -q 'READONLY\|Read-only\|Permission denied'; then
  ok "~/.ssh mount is read-only (cannot write)"
else
  fail "~/.ssh mount is NOT read-only — keys could be modified by container"
fi

# ── 7. CLI tool configs ───────────────────────────────────────────────────────
section "7. CLI tool config mounts"

GH_DIR=$(docker exec -u kandev kandev sh -c '[ -d /data/home/.config/gh ] && echo yes || echo no' 2>/dev/null)
if [[ "$GH_DIR" == "yes" ]]; then
  ok "/data/home/.config/gh is mounted (gh auth state persists)"
else
  fail "/data/home/.config/gh not mounted — gh auth login will not persist"
fi

GLAB_DIR=$(docker exec -u kandev kandev sh -c '[ -d /data/home/.config/glab-cli ] && echo yes || echo no' 2>/dev/null)
if [[ "$GLAB_DIR" == "yes" ]]; then
  ok "/data/home/.config/glab-cli is mounted (glab auth state persists)"
else
  fail "/data/home/.config/glab-cli not mounted — glab auth login will not persist"
fi

# .gitconfig must be read-only
RO_GIT=$(docker exec kandev sh -c 'touch /data/home/.gitconfig 2>&1 || echo READONLY')
if echo "$RO_GIT" | grep -q 'READONLY\|Read-only\|Permission denied'; then
  ok "~/.gitconfig mount is read-only"
else
  fail "~/.gitconfig mount is NOT read-only"
fi

# ── 8. Language toolchains (mise) ─────────────────────────────────────────────
section "8. Language toolchains (mise)"

# mise binary present in image
if docker run --rm kandev-local:latest which mise &>/dev/null; then
  ok "mise binary present in image"
else
  fail "mise binary missing from image"
fi

# Build toolchain present (native extensions, ruby/php source builds)
if docker run --rm kandev-local:latest which gcc &>/dev/null; then
  ok "gcc / build-essential present in image"
else
  fail "gcc / build-essential missing from image"
fi

# System-wide mise config baked in and listing the expected tools
if docker run --rm kandev-local:latest sh -c \
    'test -f /etc/mise/config.toml && grep -q "^node" /etc/mise/config.toml'; then
  ok "/etc/mise/config.toml present with global tool versions"
else
  fail "/etc/mise/config.toml missing or does not list tools"
fi

# mise shims directory must be on PATH inside the running container
if docker exec kandev printenv PATH 2>/dev/null | grep -q '/data/home/.local/share/mise/shims'; then
  ok "mise shims dir is on container PATH"
else
  fail "mise shims dir not on container PATH — installed tools would not resolve"
fi

# mise inside the running container parses the config and lists the tools
if docker exec -u kandev kandev mise ls 2>/dev/null | grep -qi '^node'; then
  ok "mise lists configured toolchains inside container"
else
  fail "mise does not list configured toolchains (config not parsed/trusted)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo ""
echo -e "${BOLD}────────────────────────────────────────${RESET}"
if [[ "$FAIL" -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}All $TOTAL tests passed.${RESET}"
  exit 0
else
  echo -e "${RED}${BOLD}$FAIL/$TOTAL tests FAILED:${RESET}"
  for err in "${ERRORS[@]}"; do
    echo -e "  ${RED}✗${RESET} $err"
  done
  exit 1
fi
