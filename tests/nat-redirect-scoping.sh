#!/usr/bin/env bash
# nat-redirect-scoping.sh — regression test for the port 80 → 38429 NAT redirect.
#
# Proves the two properties the scoped rules must have:
#   1. Traffic that ARRIVES from the network on a LAN interface is redirected.
#   2. Traffic merely PASSING THROUGH from a container bridge is NOT — that is
#      the `apt-get update` → "Clearsigned file isn't valid, got 'NOSPLIT'"
#      breakage, and the reason the old unscoped rule had to be constrained.
#   3. Locally generated traffic to this machine is redirected (board.<host>
#      and localhost from the host itself), while traffic leaving the box is not.
#
# It never needs a listener: the nat table's per-rule packet counters say
# whether a rule matched, and the nat table sees the first packet of every
# connection regardless of whether anything answers.
#
# MUST be run inside a throwaway network namespace — it rewrites the nat table.
# test.sh runs it in a privileged, disposable container. Running it directly on
# a host would clobber that host's live rules; the guard below refuses unless
# KANDEV_NAT_TEST_OK=1 is set.
set -uo pipefail

if [[ "${KANDEV_NAT_TEST_OK:-0}" != "1" ]]; then
    echo "refusing to run: this test rewrites the nat table and must run in a" >&2
    echo "disposable container/netns. Set KANDEV_NAT_TEST_OK=1 if that is where you are." >&2
    exit 2
fi

REPO="${KANDEV_REPO:-/repo}"
PORT=38429
PASS=0
FAIL=0
ok()   { echo "  ✓ $1"; PASS=$((PASS + 1)); }
bad()  { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }

# Count packets that matched a nat rule, identified by an extended regex over
# its spec (iptables renders `--to-port` back as `--to-ports`, and inserts
# `-m tcp`, so patterns match loosely).
# iptables-save -c prefixes each rule with [packets:bytes].
matched() {
    iptables-save -c -t nat 2>/dev/null \
        | grep -E -- "$1" \
        | sed -n 's/^\[\([0-9]*\):[0-9]*\].*/\1/p' \
        | awk '{s += $1} END {print s + 0}'
}

# Fire a single SYN at a destination; nothing needs to answer.
# Wrapped in an extra `bash -c` so the SIGTERM from `timeout` is reaped inside
# that shell instead of printing "Terminated" into the test output.
poke() { bash -c 'timeout 1 bash -c "exec 3<>/dev/tcp/$0/$1"' "$1" "$2" >/dev/null 2>&1 || true; }
poke_peer() { bash -c 'ip netns exec peer timeout 1 bash -c "exec 3<>/dev/tcp/$0/$1"' "$1" "$2" >/dev/null 2>&1 || true; }

# ── A simulated container bridge: a peer netns routing out through us ────────
ip netns add peer
ip link add vhost0 type veth peer name vpeer0
ip link set vpeer0 netns peer
ip addr add 10.99.0.1/24 dev vhost0
ip link set vhost0 up
ip netns exec peer ip link set lo up
ip netns exec peer ip addr add 10.99.0.2/24 dev vpeer0
ip netns exec peer ip link set vpeer0 up
ip netns exec peer ip route add default via 10.99.0.1

LAN_IF="$(ip -o -4 addr show scope global | awk '{print $2}' | grep -v '^vhost0$' | head -1)"
LAN_IP="$(ip -o -4 addr show dev "$LAN_IF" scope global | awk '{print $4}' | cut -d/ -f1)"
echo "  (lan iface=$LAN_IF ip=$LAN_IP, simulated bridge=vhost0)"

echo ""
echo "  --- unscoped rules (the bug) ---"
iptables -t nat -F PREROUTING
iptables -t nat -F OUTPUT
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port "$PORT"
iptables -t nat -A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port "$PORT"

poke_peer 203.0.113.9 80
if [[ "$(matched '-A PREROUTING -p tcp')" -gt 0 ]]; then
    ok "unscoped PREROUTING really does hijack bridge egress (test exercises the path)"
else
    bad "test harness did not reproduce the bug — bridge egress never hit PREROUTING"
fi

poke 203.0.113.9 80
if [[ "$(matched '-A OUTPUT -p tcp')" -gt 0 ]]; then
    ok "unscoped OUTPUT really does hijack the host's own outbound :80"
else
    bad "test harness did not reproduce the bug — host egress never hit OUTPUT"
fi

echo ""
echo "  --- scoped rules (the fix) ---"
iptables -t nat -F PREROUTING
iptables -t nat -F OUTPUT
if KANDEV_LAN_IFACES="$LAN_IF" bash "$REPO/scripts/nat-redirect.sh" >/dev/null 2>&1; then
    ok "nat-redirect.sh applied cleanly and self-verified"
else
    bad "nat-redirect.sh failed to apply"
fi

if iptables -t nat -S PREROUTING | grep -q -- "-i $LAN_IF .*--dport 80 -j REDIRECT --to-ports $PORT"; then
    ok "PREROUTING redirect is scoped to the LAN interface"
else
    bad "PREROUTING redirect is missing or unscoped"
fi

if iptables -t nat -S OUTPUT | grep -q -- "-o lo .*--dport 80 -j REDIRECT --to-ports $PORT"; then
    ok "OUTPUT redirect is scoped to locally-destined traffic (-o lo)"
else
    bad "OUTPUT redirect is missing or unscoped"
fi

# 1. Bridge egress must now be left alone — this is the apt fix.
iptables -t nat -Z
poke_peer 203.0.113.9 80
if [[ "$(matched "--dport 80 -j REDIRECT --to-ports $PORT")" -eq 0 ]]; then
    ok "container/bridge egress to an external :80 is NOT redirected"
else
    bad "container/bridge egress still hits the redirect (apt would break)"
fi

# 2. The host's own outbound :80 must be left alone (network:host builds).
iptables -t nat -Z
poke 203.0.113.9 80
if [[ "$(matched "--dport 80 -j REDIRECT --to-ports $PORT")" -eq 0 ]]; then
    ok "the host's own outbound :80 is NOT redirected"
else
    bad "the host's own outbound :80 still hits the redirect"
fi

# 3. localhost:80 on this machine must still reach kandev.
iptables -t nat -Z
poke 127.0.0.1 80
if [[ "$(matched "-o lo .*--dport 80 -j REDIRECT --to-ports $PORT")" -gt 0 ]]; then
    ok "http://localhost from this machine is still redirected to $PORT"
else
    bad "localhost:80 is no longer redirected — board.<host> would break on the host itself"
fi

# 4. …and so must the host's own LAN IP, which is how board.<host> resolves.
iptables -t nat -Z
poke "$LAN_IP" 80
if [[ "$(matched "-o lo .*--dport 80 -j REDIRECT --to-ports $PORT")" -gt 0 ]]; then
    ok "the host's own LAN IP on :80 is still redirected (board.<host> from the host)"
else
    bad "the host's own LAN IP on :80 is not redirected — board.<host> breaks locally"
fi

# 5. Traffic arriving from the network on the LAN interface must be redirected.
#    Simulated by re-pointing the scope at the veth the peer netns arrives on.
iptables -t nat -F PREROUTING
iptables -t nat -A PREROUTING -i vhost0 -p tcp --dport 80 -j REDIRECT --to-port "$PORT"
iptables -t nat -Z
poke_peer 10.99.0.1 80
if [[ "$(matched "-i vhost0 .*--dport 80 -j REDIRECT --to-ports $PORT")" -gt 0 ]]; then
    ok "traffic arriving from the network on a scoped interface IS redirected"
else
    bad "interface-scoped PREROUTING did not match traffic arriving on it"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
    echo "  nat scoping: $PASS/$PASS passed"
    exit 0
fi
echo "  nat scoping: $FAIL of $((PASS + FAIL)) FAILED"
exit 1
