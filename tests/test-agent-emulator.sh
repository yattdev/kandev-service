#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
mkdir -p "$tmpdir/sdk/emulator" "$tmpdir/sdk/platform-tools" \
    "$tmpdir/source/Pixel_Test.avd" "$tmpdir/user"

cat > "$tmpdir/sdk/emulator/emulator" <<'SH'
#!/bin/sh
printf '%s\n' "$@"
SH
cat > "$tmpdir/sdk/platform-tools/adb" <<'SH'
#!/bin/sh
printf 'adb:%s\n' "$*"
SH
chmod +x "$tmpdir/sdk/emulator/emulator" "$tmpdir/sdk/platform-tools/adb"
printf 'target=android-test\npath=%s\n' "$tmpdir/source/Pixel_Test.avd" > "$tmpdir/source/Pixel_Test.ini"
printf 'image.sysdir.1=system-images/test/\n' > "$tmpdir/source/Pixel_Test.avd/config.ini"

list_out="$(ANDROID_SDK_ROOT="$tmpdir/sdk" ANDROID_AVD_HOME="$tmpdir/source" \
    "$repo_root/scripts/kandev-agent-emulator" -list-avds)"
[[ "$list_out" == "-list-avds" ]]

launch_out="$(ANDROID_SDK_ROOT="$tmpdir/sdk" ANDROID_AVD_HOME="$tmpdir/source" \
    ANDROID_USER_HOME="$tmpdir/user" \
    "$repo_root/scripts/kandev-agent-emulator" -avd Pixel_Test)"
for required in -avd Pixel_Test -read-only -no-snapshot -no-snapstorage -no-window -no-audio -no-boot-anim -no-metrics swiftshader_indirect; do
    grep -Fxq -- "$required" <<<"$launch_out"
done

adb_out="$(ANDROID_SDK_ROOT="$tmpdir/sdk" "$repo_root/scripts/kandev-agent-adb" devices)"
[[ "$adb_out" == "adb:devices" ]]

echo "PASS: Android wrappers preserve discovery and enforce safe headless launch defaults"
