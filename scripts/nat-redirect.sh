#!/usr/bin/env bash
# nat-redirect.sh — install the *scoped* port 80 → 38429 NAT redirect (idempotent).
#
# Why this exists
# ───────────────
# Browsing http://board.<host> without typing :38429 needs a NAT redirect, and
# both installers used to add it unscoped:
#
#   -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 38429
#   -A OUTPUT     -p tcp --dport 80 -j REDIRECT --to-ports 38429
#
# A REDIRECT rule with no interface/destination constraint matches far more than
# "someone on the LAN asked for the board":
#
#   * PREROUTING also sees the egress of every container on a docker bridge.
#     `apt-get update` inside a build hits deb.debian.org:80, gets rewritten to
#     the host's kandev, and is answered with the kandev SPA — which surfaces as
#     `Clearsigned file isn't valid, got 'NOSPLIT'`, i.e. HTML where a Release
#     file was expected. Docker's own `-j DOCKER` jump sits *after* this rule,
#     so ours wins.
#   * OUTPUT also sees every port-80 request the host itself makes — including a
#     `network: host` docker build, and any http:// site in a browser. This is
#     the bug that made board.office/board.home show local data when browsed
#     from the laptop (see CLAUDE.md, "Common failure modes").
#
# The redirect is deliberate and stays. It is the *scope* that was missing:
#
#   PREROUTING  -i <lan-iface>   → only traffic that actually arrived from the
#                                  network. Container egress arrives on docker0
#                                  / br-* and no longer matches.
#   OUTPUT      -o lo            → only locally generated traffic addressed to
#                                  this machine. `ip route get` sends both
#                                  127.0.0.1 and the host's own LAN IP out `lo`,
#                                  so this covers http://localhost *and*
#                                  http://board.<host> from the host itself,
#                                  while anything leaving the box (deb.debian.org,
#                                  board.<other-host>) is left alone. It also
#                                  survives a DHCP lease change, which a
#                                  `-d <lan-ip>` scope would not.
#
# Trade-off, on purpose: a container on a docker bridge can no longer reach the
# board on port 80 by hostname — it must use <host-ip>:38429 directly. That is
# exactly the traffic class that was breaking apt.
#
# Usage
# ─────
#   sudo bash scripts/nat-redirect.sh            # apply live + persist (reboot-safe)
#   bash scripts/nat-redirect.sh --print         # show the rules; no root needed
#   sudo bash scripts/nat-redirect.sh --check    # verify live rules; exit 1 if wrong
#
# Knobs (both may live in the gitignored host.env):
#   KANDEV_PORT=38429            kandev's real listen port
#   KANDEV_LAN_IFACES="eth0 wlan0"   override interface autodetection
set -euo pipefail

_KANDEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
[ -f "$_KANDEV_DIR/host.env" ] && . "$_KANDEV_DIR/host.env"

PORT="${KANDEV_PORT:-38429}"
WEB_PORT="${KANDEV_WEB_PORT:-80}"
BEGIN_MARK="### BEGIN kandev nat (managed by scripts/nat-redirect.sh — do not edit)"
END_MARK="### END kandev nat"

MODE="apply"
case "${1:-}" in
    --print) MODE="print" ;;
    --check) MODE="check" ;;
    "")      MODE="apply" ;;
    *) echo "usage: $0 [--print|--check]" >&2; exit 2 ;;
esac

log() { echo "[nat-redirect] $*"; }

# Run iptables directly when already root, else via sudo.
IPT=(iptables)
if [[ "$(id -u)" -ne 0 ]]; then
    IPT=(sudo iptables)
fi

# ── LAN interface detection ──────────────────────────────────────────────────
# Everything that carries a globally-scoped IPv4 address and is not a container
# or VM bridge. Deliberately keeps tun*/wg*/tailscale* — those are real "arrived
# from the network" paths for reaching the board remotely; they are not what
# container egress rides on.
detect_lan_ifaces() {
    if [[ -n "${KANDEV_LAN_IFACES:-}" ]]; then
        tr ',' ' ' <<<"$KANDEV_LAN_IFACES" | tr -s ' ' '\n' | sed '/^$/d' | sort -u
        return
    fi
    ip -o -4 addr show scope global 2>/dev/null \
        | awk '{print $2}' \
        | grep -Ev '^(lo|docker[0-9]*|br-|veth|virbr|podman|cni|kube|flannel|cali|weave|lxcbr|lxdbr)' \
        | sort -u
}

mapfile -t LAN_IFACES < <(detect_lan_ifaces)

if [[ "${#LAN_IFACES[@]}" -eq 0 ]]; then
    echo "ERROR: no LAN interface detected — refusing to fall back to an unscoped" >&2
    echo "       redirect (that is the bug this script exists to prevent)." >&2
    echo "       Set KANDEV_LAN_IFACES=\"eth0 wlan0\" in host.env and re-run." >&2
    exit 1
fi

# ── Desired rule set ─────────────────────────────────────────────────────────
# One "<chain>|<args>" entry per rule.
DESIRED=()
for iface in "${LAN_IFACES[@]}"; do
    DESIRED+=("PREROUTING|-i $iface -p tcp --dport $WEB_PORT -j REDIRECT --to-port $PORT")
done
DESIRED+=("OUTPUT|-o lo -p tcp --dport $WEB_PORT -j REDIRECT --to-port $PORT")

# iptables echoes rules back in a normalised form (`-m tcp` inserted,
# `--to-port` rendered as `--to-ports`). Fold both spellings together so a live
# rule can be compared against a desired one as plain text.
canon() {
    sed -e 's/ -m tcp//g' -e 's/--to-ports /--to-port /g' -e 's/  */ /g' -e 's/^ //;s/ $//'
}

desired_canon() {
    local d
    for d in "${DESIRED[@]}"; do
        printf '%s|%s\n' "${d%%|*}" "$(canon <<<"${d#*|}")"
    done
}

# Live kandev-owned rules only: a REDIRECT to our port. Never touches Docker's
# own NAT rules or anything else in the table.
live_rules() {
    local chain line
    for chain in PREROUTING OUTPUT; do
        while IFS= read -r line; do
            [[ "$line" == -A\ * ]] || continue
            [[ "$line" == *"-j REDIRECT"* ]] || continue
            [[ "$line" == *"--to-ports $PORT"* || "$line" == *"--to-port $PORT"* ]] || continue
            printf '%s|%s\n' "$chain" "$(canon <<<"${line#-A $chain }")"
        done < <("${IPT[@]}" -t nat -S "$chain")
    done
}

# ── Persisted form ───────────────────────────────────────────────────────────
render_block() {
    printf '%s\n' "$BEGIN_MARK"
    printf '*nat\n:PREROUTING ACCEPT [0:0]\n:OUTPUT ACCEPT [0:0]\n'
    local d
    for d in "${DESIRED[@]}"; do
        printf -- '-A %s %s\n' "${d%%|*}" "${d#*|}"
    done
    printf 'COMMIT\n'
    printf '%s\n' "$END_MARK"
}

if [[ "$MODE" == "print" ]]; then
    log "LAN interfaces: ${LAN_IFACES[*]}"
    log "kandev port:    $PORT (web $WEB_PORT)"
    echo ""
    render_block
    exit 0
fi

# ── Check mode ───────────────────────────────────────────────────────────────
if [[ "$MODE" == "check" ]]; then
    RC=0
    LIVE="$(live_rules)"
    WANT="$(desired_canon)"

    while IFS= read -r want; do
        if grep -Fxq "$want" <<<"$LIVE"; then
            log "ok      ${want/|/ }"
        else
            log "MISSING ${want/|/ }"
            RC=1
        fi
    done <<<"$WANT"

    while IFS= read -r have; do
        [[ -n "$have" ]] || continue
        if ! grep -Fxq "$have" <<<"$WANT"; then
            log "UNSCOPED/STALE ${have/|/ }"
            RC=1
        fi
    done <<<"$LIVE"

    [[ "$RC" -eq 0 ]] && log "live NAT redirect is correctly scoped"
    exit "$RC"
fi

# ── Apply mode ───────────────────────────────────────────────────────────────
log "LAN interfaces: ${LAN_IFACES[*]}"

WANT="$(desired_canon)"

# 1. Drop every kandev REDIRECT rule that is not in the desired set — this is
#    what removes the old unscoped rules, and any rule for an interface that no
#    longer exists.
while IFS= read -r have; do
    [[ -n "$have" ]] || continue
    if ! grep -Fxq "$have" <<<"$WANT"; then
        chain="${have%%|*}"
        args="${have#*|}"
        # shellcheck disable=SC2086 -- args is a rule spec, word splitting is intended
        "${IPT[@]}" -t nat -D "$chain" $args
        log "removed unscoped/stale rule: $chain $args"
    fi
done < <(live_rules)

# 2. Add whatever is missing.
for d in "${DESIRED[@]}"; do
    chain="${d%%|*}"
    args="${d#*|}"
    # shellcheck disable=SC2086
    if ! "${IPT[@]}" -t nat -C "$chain" $args 2>/dev/null; then
        # shellcheck disable=SC2086
        "${IPT[@]}" -t nat -A "$chain" $args
        log "added: $chain $args"
    fi
done

# 3. Persist so the rules survive a reboot.
BEFORE_RULES="/etc/ufw/before.rules"
IPTABLES_RULES="/etc/iptables/rules.v4"
SUDO=()
[[ "$(id -u)" -ne 0 ]] && SUDO=(sudo)

if [[ -f "$BEFORE_RULES" ]]; then
    "${SUDO[@]}" cp -a "$BEFORE_RULES" "${BEFORE_RULES}.kandev.bak"

    TMP="$(mktemp)"
    # Strip our managed block, the pre-2026-08-22 unmarked block (it always
    # opened with this comment and ran to its own COMMIT), and any stray
    # REDIRECT line left behind by an older installer.
    "${SUDO[@]}" sed \
        -e "/^### BEGIN kandev nat/,/^### END kandev nat/d" \
        -e "/^# kandev: port ${WEB_PORT} /,/^COMMIT\$/d" \
        -e "/^-A PREROUTING .*--dport ${WEB_PORT} -j REDIRECT --to-port[s]* ${PORT}\$/d" \
        -e "/^-A OUTPUT .*--dport ${WEB_PORT} -j REDIRECT --to-port[s]* ${PORT}\$/d" \
        "$BEFORE_RULES" > "$TMP"

    BLOCK="$(render_block)"
    TMP2="$(mktemp)"
    awk -v block="$BLOCK" '
        /^\*filter/ && !done { print block; done = 1 }
        { print }
        END { if (!done) print block }
    ' "$TMP" > "$TMP2"

    if "${SUDO[@]}" cmp -s "$TMP2" "$BEFORE_RULES"; then
        log "before.rules already up to date"
    else
        "${SUDO[@]}" cp "$TMP2" "$BEFORE_RULES"
        log "persisted in $BEFORE_RULES (backup: ${BEFORE_RULES}.kandev.bak)"
        if command -v ufw >/dev/null 2>&1; then
            "${SUDO[@]}" ufw reload >/dev/null 2>&1 || log "WARNING: 'ufw reload' failed — rules are live but may not survive a reboot"
        fi
    fi
    rm -f "$TMP" "$TMP2"
elif command -v iptables-save >/dev/null 2>&1 && [[ -d "$(dirname "$IPTABLES_RULES")" ]]; then
    "${SUDO[@]}" sh -c "iptables-save > '$IPTABLES_RULES'"
    log "persisted via iptables-save → $IPTABLES_RULES"
else
    log "WARNING: no /etc/ufw/before.rules and no iptables-persistent — rules are live but will NOT survive a reboot"
fi

# 4. Re-read the live table and fail loudly if it still disagrees.
if ! bash "$0" --check >/dev/null 2>&1; then
    echo "ERROR: NAT rules still do not match after applying — run 'bash $0 --check' for detail." >&2
    exit 1
fi
log "done — port ${WEB_PORT} → ${PORT}, scoped to [${LAN_IFACES[*]}] inbound + lo local"
