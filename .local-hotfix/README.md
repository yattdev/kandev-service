# Local binary hotfix overlay

This directory is intentionally present in the Docker build context. Locally
built `agentctl`, `agentctl-linux-amd64`, and backend `kandev` binaries may be
placed here while a tested Kandev source fix is waiting for an upstream image
release. The binaries are ignored by Git, but `Dockerfile.local` installs them
into every local image rebuild when they are present. Never place only one of
the two `agentctl` binaries here; the backend overlay is independent.

The current backend overlay is reproducible with
`scripts/build-kandev-liveness-hotfix`. It applies the versioned patch to the
exact upstream revision used by the deployed base image, runs the focused
lifecycle tests, builds and embeds the matching frontend bundle, and writes
`.local-hotfix/kandev`. Do not build the overlay with the backend-only
`build-kandev` target from a clean source tree: that embeds the fallback HTML
without JavaScript assets and produces a white page.

Remove an overlay after its corresponding fix is verified in the upstream base
image; otherwise the local overlay deliberately continues to win.
