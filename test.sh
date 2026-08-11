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
# Same SIGPIPE hazard as the java check below: `head -1` closing the pipe can
# kill the upstream `docker exec` with 141 and abort the suite under pipefail.
# This awk prints only the first match but still drains the whole stream.
GH_KEY=$(docker exec -u kandev kandev ssh -G github.com 2>/dev/null | awk '/^identityfile/ { if (!seen++) print $2 }')
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

# Java (JDK) — pinned in the baked system config so every image guarantees it.
if docker run --rm kandev-local:latest sh -c 'grep -q "^java" /etc/mise/config.toml'; then
  ok "/etc/mise/config.toml pins a java (JDK) version"
else
  fail "/etc/mise/config.toml does not pin a java version"
fi

# Java installed into the persistent volume (listed by mise in the container).
if docker exec -u kandev kandev mise ls 2>/dev/null | grep -qi '^java'; then
  ok "mise reports java toolchain installed in volume"
else
  fail "java toolchain not installed in volume — run: bash setup-toolchains.sh java"
fi

# Java actually RUNS as user kandev the way agents invoke it: a non-login
# `bash -c` shell. Guards against the shim/PATH regression where `java` resolves
# in an interactive/login shell but not in the non-interactive shells agents use.
if docker exec -u kandev kandev java -version >/dev/null 2>&1; then
  # NB: no `| head -1` here. Under `set -euo pipefail`, head closing the pipe
  # after one line sends SIGPIPE to `docker exec`, which exits 141 and aborts
  # the whole suite. That is a race — it only fires when the producer is still
  # writing as head exits — so it made the run non-deterministic. Capture the
  # full output, then take the first line with parameter expansion instead.
  JAVA_VER="$(docker exec -u kandev kandev java -version 2>&1)"
  JAVA_VER="${JAVA_VER%%$'\n'*}"
  ok "java runs in container ($JAVA_VER)"
else
  fail "java installed but not runnable in container (shim missing / not on PATH)"
fi

# javac present too — proves a full JDK (compiler), not just a JRE.
if docker exec -u kandev kandev javac -version >/dev/null 2>&1; then
  ok "javac (JDK compiler) runs in container"
else
  fail "javac not runnable — java runtime present but not a full JDK"
fi

# sqlite3 in the image — required for the NO-DOWNTIME restic backup, which uses
# `sqlite3 .backup` (SQLite online-backup API) to snapshot kandev.db live rather
# than stopping the container. Without it kandev-restic-backup.sh has no way to
# take a consistent hot copy.
if docker run --rm kandev-local:latest which sqlite3 &>/dev/null; then
  ok "sqlite3 present in image (enables hot, no-stop DB backup)"
else
  fail "sqlite3 missing from image — hot backup would fall back to a torn live-DB copy"
fi

# ── 9. Headless browser (Chrome) ──────────────────────────────────────────────
section "9. Headless browser (Chrome)"

# Browser present, and `google-chrome` on PATH must hit the --no-sandbox wrapper
WHICH_CHROME=$(docker run --rm kandev-local:latest which google-chrome 2>/dev/null || echo "")
if [[ "$WHICH_CHROME" == "/usr/local/bin/google-chrome" ]]; then
  ok "google-chrome on PATH resolves to the --no-sandbox wrapper"
else
  fail "google-chrome on PATH = '${WHICH_CHROME}' (expected /usr/local/bin/google-chrome)"
fi

# Unwrapped browser binary must still be reachable
if docker run --rm kandev-local:latest test -x /usr/bin/google-chrome; then
  ok "unwrapped browser binary present at /usr/bin/google-chrome"
else
  fail "/usr/bin/google-chrome missing — browser not installed"
fi

# chromium alias resolves too (tools that look for the other name)
if docker run --rm kandev-local:latest which chromium &>/dev/null; then
  ok "chromium alias resolves to the installed browser"
else
  fail "chromium alias missing from image"
fi

CHROME_VERSION=$(docker run --rm kandev-local:latest google-chrome --version 2>/dev/null || echo "")
if [[ -n "$CHROME_VERSION" ]]; then
  ok "browser reports a version ($CHROME_VERSION)"
else
  fail "google-chrome --version produced no output"
fi

# chromedriver for Selenium/WebDriver clients
if docker run --rm kandev-local:latest chromedriver --version &>/dev/null; then
  ok "chromedriver present and runnable"
else
  fail "chromedriver missing or not runnable"
fi

# CHROME_BIN must be exported in the running container (karma, CI scripts read it)
CHROME_BIN_ENV=$(docker exec kandev printenv CHROME_BIN 2>/dev/null || echo "")
if [[ "$CHROME_BIN_ENV" == "/usr/local/bin/google-chrome" ]]; then
  ok "CHROME_BIN=/usr/local/bin/google-chrome in running container"
else
  fail "CHROME_BIN='${CHROME_BIN_ENV}' in container (expected /usr/local/bin/google-chrome)"
fi

# /dev/shm must be larger than Docker's 64 MB default or Chrome crashes mid-suite
SHM_MB=$(docker exec kandev sh -c "df -m /dev/shm | awk 'NR==2 {print \$2}'" 2>/dev/null || echo "0")
if [[ "${SHM_MB:-0}" -ge 512 ]]; then
  ok "/dev/shm is ${SHM_MB}MB (large enough for Chrome)"
else
  fail "/dev/shm is only ${SHM_MB}MB — Chrome will crash; set shm_size in compose"
fi

# Real headless render as the kandev user, WITHOUT passing --no-sandbox — this
# is what a stock karma/puppeteer config does, so it proves the wrapper works.
if docker exec -u kandev kandev sh -c \
    'google-chrome --headless --disable-gpu --dump-dom about:blank 2>/dev/null' \
    | grep -qi '<html'; then
  ok "headless Chrome renders as user kandev with no extra flags"
else
  fail "headless Chrome failed to render as kandev (sandbox wrapper not working?)"
fi

# ── 10. sudo / root privileges for kandev ─────────────────────────────────────
section "10. sudo / root privileges for kandev"

if docker run --rm kandev-local:latest which sudo &>/dev/null; then
  ok "sudo binary present in image"
else
  fail "sudo binary missing from image"
fi

# /etc/sudoers.d/kandev is 0440 root-only by design. The image's entrypoint
# always drops privileges to kandev via gosu even when `-u root` is passed, so
# bypass it with --entrypoint to read the file as the real root user.
SUDOERS_PATCH=$(docker run --rm --entrypoint sh kandev-local:latest -c 'cat /etc/sudoers.d/kandev 2>/dev/null' || echo "")
if echo "$SUDOERS_PATCH" | grep -q 'kandev ALL=(ALL) NOPASSWD:ALL'; then
  ok "/etc/sudoers.d/kandev grants passwordless root to kandev"
else
  fail "/etc/sudoers.d/kandev missing or does not grant NOPASSWD root"
fi

SUDOERS_PERMS=$(docker run --rm --entrypoint stat kandev-local:latest -c '%a' /etc/sudoers.d/kandev 2>/dev/null || echo "")
if [[ "$SUDOERS_PERMS" == "440" ]]; then
  ok "/etc/sudoers.d/kandev has correct 0440 permissions"
else
  fail "/etc/sudoers.d/kandev permissions = '${SUDOERS_PERMS}' (expected 440)"
fi

# kandev must be able to become root without a password inside the running container
SUDO_WHOAMI=$(docker exec -u kandev kandev sudo -n whoami 2>&1 || echo "")
if [[ "$SUDO_WHOAMI" == "root" ]]; then
  ok "kandev can 'sudo -n whoami' -> root (no password needed)"
else
  fail "kandev could not sudo to root (got: '${SUDO_WHOAMI}')"
fi

# kandev must own /data (the entrypoint chown, backed by sudo if it ever needs
# to self-heal permissions on files it doesn't already own)
DATA_OWNER=$(docker exec kandev stat -c '%U:%G' /data 2>/dev/null || echo "")
if [[ "$DATA_OWNER" == "kandev:kandev" ]]; then
  ok "/data is owned by kandev:kandev"
else
  fail "/data owner = '${DATA_OWNER}' (expected kandev:kandev)"
fi

DATA_WRITABLE=$(docker exec -u kandev kandev sh -c 'touch /data/.write-test 2>&1 && rm -f /data/.write-test && echo yes || echo no')
if [[ "$DATA_WRITABLE" == "yes" ]]; then
  ok "kandev can write to /data"
else
  fail "kandev cannot write to /data"
fi

# ── 11. Docker host-path wrapper ──────────────────────────────────────────────
# The mounted docker.sock drives the HOST daemon, which resolves bind-mount
# sources on the HOST filesystem. Container-only paths do not exist there and
# Docker does not error on a missing source — it creates an empty root-owned
# directory and mounts that, silently. /usr/local/bin/docker rewrites those
# paths; these tests are what prove the rewrite is actually in effect.
section "11. Docker host-path wrapper"

WRAPPER_PATH=$(docker exec -u kandev kandev bash -lc 'command -v docker' 2>/dev/null || echo "")
if [[ "$WRAPPER_PATH" == "/usr/local/bin/docker" ]]; then
  ok "docker resolves to the wrapper (/usr/local/bin/docker) ahead of /usr/bin"
else
  fail "docker resolves to '${WRAPPER_PATH}' (expected /usr/local/bin/docker)"
fi

# The wrapper is a no-op without these; they are the inverse of the mounts.
HOST_ENV_OK=$(docker exec -u kandev kandev bash -lc \
  '[[ -n "$KANDEV_HOST_HOME" && -n "$KANDEV_HOST_DATA_DIR" && -n "$KANDEV_HOST_CODE_DIR" ]] && echo yes || echo no' 2>/dev/null || echo "no")
if [[ "$HOST_ENV_OK" == "yes" ]]; then
  ok "KANDEV_HOST_HOME / _DATA_DIR / _CODE_DIR are set in the container"
else
  fail "KANDEV_HOST_* env vars missing — check docker-compose.override.yml"
fi

# /data/... -> host data dir
TRANSLATED_DATA=$(docker exec -u kandev kandev bash -lc \
  'docker --kandev-print-argv run -v /data/tasks/x/repo:/app img 2>/dev/null | grep ":/app"' 2>/dev/null || echo "")
EXPECT_DATA="${HOME}/.local/share/kandev/tasks/x/repo:/app"
if [[ "$TRANSLATED_DATA" == "$EXPECT_DATA" ]]; then
  ok "-v /data/tasks/... rewritten to the host data dir"
else
  fail "-v /data/... rewrote to '${TRANSLATED_DATA}' (expected '${EXPECT_DATA}')"
fi

# /data/home/Code/... -> host ~/Code (must win over the /data catch-all)
TRANSLATED_CODE=$(docker exec -u kandev kandev bash -lc \
  'docker --kandev-print-argv run -v /data/home/Code/proj:/src img 2>/dev/null | grep ":/src"' 2>/dev/null || echo "")
EXPECT_CODE="${HOME}/Code/proj:/src"
if [[ "$TRANSLATED_CODE" == "$EXPECT_CODE" ]]; then
  ok "-v /data/home/Code/... rewritten to the host Code dir"
else
  fail "-v /data/home/Code/... rewrote to '${TRANSLATED_CODE}' (expected '${EXPECT_CODE}')"
fi

# Named volumes and container-internal flags must be left alone.
UNTOUCHED=$(docker exec -u kandev kandev bash -lc \
  'docker --kandev-print-argv run -v myvol:/var/lib/mysql -w /data/foo img 2>/dev/null | tr "\n" " "' 2>/dev/null || echo "")
if [[ "$UNTOUCHED" == *"myvol:/var/lib/mysql"* && "$UNTOUCHED" == *"-w /data/foo"* ]]; then
  ok "named volumes and container-internal paths (-w) left untouched"
else
  fail "wrapper altered a named volume or -w path: '${UNTOUCHED}'"
fi

# Identity mounts: a host path must be readable inside the container, otherwise
# the compose chdir cannot work.
IDENTITY_OK=$(docker exec -u kandev kandev bash -lc \
  "[[ -d '${HOME}/Code' && -d '${HOME}/.local/share/kandev' ]] && echo yes || echo no" 2>/dev/null || echo "no")
if [[ "$IDENTITY_OK" == "yes" ]]; then
  ok "identity mounts present (host paths valid inside the container)"
else
  fail "identity mounts missing — host paths not visible inside the container"
fi

# End-to-end: a sibling container started with a CONTAINER path must receive the
# real files. Without the wrapper this mounts an empty directory and prints
# nothing. Uses kandev-local:latest so no image pull is needed.
E2E_MOUNT=$(docker exec -u kandev kandev bash -lc \
  'docker run --rm -v /data/home/Code/kandev:/src kandev-local:latest ls /src 2>/dev/null | grep -c "^test.sh$"' 2>/dev/null || echo "0")
if [[ "$E2E_MOUNT" == "1" ]]; then
  ok "sibling container mounting a container path receives the real host files"
else
  fail "sibling container got an empty mount — host-path rewrite is not working"
fi

# End-to-end: relative sources in a project's own compose file ("./x:/app") are
# resolved by the compose CLI against the working directory. This is the case
# that caused the original stray root-owned trees under the host's /data.
COMPOSE_SRC=$(docker exec -u kandev kandev bash -lc '
  d=/data/.wrapper-selftest-$$
  mkdir -p "$d" && printf "services:\n  app:\n    image: alpine\n    volumes:\n      - .:/app\n" > "$d/docker-compose.yml"
  cd "$d" && docker compose config 2>/dev/null | grep "source:" | head -1 | awk "{print \$2}"
  rm -rf "$d"' 2>/dev/null || echo "")
if [[ "$COMPOSE_SRC" == "${HOME}/.local/share/kandev/"* ]]; then
  ok "compose resolves relative volume sources to host paths"
else
  fail "compose relative source resolved to '${COMPOSE_SRC}' (expected a host path under ${HOME})"
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
