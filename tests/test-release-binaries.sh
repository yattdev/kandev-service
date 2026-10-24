#!/usr/bin/env bash
set -euo pipefail

BASE_IMAGE_ID="$(docker image inspect ghcr.io/kdlbs/kandev:latest --format '{{.Id}}')"
LOCAL_BASE_ID="$(docker image inspect kandev-local:latest --format '{{index .Config.Labels "com.kandev.base-id"}}')"
if [[ "$LOCAL_BASE_ID" != "$BASE_IMAGE_ID" ]]; then
    echo "local image is not built on the current upstream base" >&2
    exit 1
fi

UPSTREAM_VERSION="$(docker run --rm --entrypoint /app/apps/backend/bin/kandev "$BASE_IMAGE_ID" --version)"
LOCAL_VERSION="$(docker run --rm --entrypoint /app/apps/backend/bin/kandev kandev-local:latest --version)"
if [[ "$UPSTREAM_VERSION" == "dev" || "$LOCAL_VERSION" != "$UPSTREAM_VERSION" ]]; then
    echo "local backend version '$LOCAL_VERSION' differs from upstream release '$UPSTREAM_VERSION'" >&2
    exit 1
fi

BINARIES=(
    /app/apps/backend/bin/kandev
    /usr/local/bin/agentctl
    /app/apps/backend/bin/agentctl-linux-amd64
)
UPSTREAM_HASHES="$(docker run --rm --entrypoint sha256sum "$BASE_IMAGE_ID" "${BINARIES[@]}")"
LOCAL_HASHES="$(docker run --rm --entrypoint sha256sum kandev-local:latest "${BINARIES[@]}")"
if [[ "$LOCAL_HASHES" != "$UPSTREAM_HASHES" ]]; then
    echo "local backend or agentctl binaries differ from the upstream release" >&2
    exit 1
fi

echo "local backend and agentctl binaries match upstream $UPSTREAM_VERSION"
