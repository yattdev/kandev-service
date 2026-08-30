#!/usr/bin/env bash
# Install the root-only, predicate-complete Kandev Support cleanup operation.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "must run as root" >&2
  exit 64
fi
if [[ $# -ne 1 || ! $1 =~ ^[a-z_][a-z0-9_-]*$ ]]; then
  echo "usage: $0 <support-user>" >&2
  exit 64
fi

support_user=$1
support_uid=$(id -u "$support_user")
support_home=$(getent passwd "$support_user" | cut -d: -f6)
[[ -n $support_home && -d $support_home ]] || { echo "support user home is unavailable" >&2; exit 64; }
repo_dir=$(cd "$(dirname "$0")/.." && pwd -P)
data_dir="$support_home/.local/share/kandev"
install -d -o root -g root -m 0755 /usr/local/libexec
install -o root -g root -m 0755 "$repo_dir/scripts/kandev-support-process-cleanup" /usr/local/libexec/kandev-support-process-cleanup
printf '{"support_uid":%s,"data_dir":"%s","db_path":"%s/data/kandev.db","audit_path":"/var/log/kandev-support-process-cleanup/audit.jsonl"}\n' "$support_uid" "$data_dir" "$data_dir" > /etc/kandev-support-process-cleanup.json
chown root:root /etc/kandev-support-process-cleanup.json
chmod 0600 /etc/kandev-support-process-cleanup.json
printf '%s ALL=(root) NOPASSWD: /usr/local/libexec/kandev-support-process-cleanup\n' "$support_user" > /etc/sudoers.d/kandev-support-process-cleanup
chmod 0440 /etc/sudoers.d/kandev-support-process-cleanup
visudo -cf /etc/sudoers.d/kandev-support-process-cleanup
echo "installed root-only Kandev Support process cleanup for $support_user"
