# Local binary hotfix overlay

This directory is intentionally present in the Docker build context. Locally
built `agentctl` and `agentctl-linux-amd64` binaries may be placed here while a
tested Kandev source fix is waiting for an upstream image release. The binaries
are ignored by Git, but `Dockerfile.local` installs both into every local image
rebuild when they are present. Never place only one binary here.

Remove both binaries after the corresponding fix is verified in the upstream
base image; otherwise the local overlay deliberately continues to win.
