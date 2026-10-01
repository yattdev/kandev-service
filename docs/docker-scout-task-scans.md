# Task-scoped Docker Scout CVE scans

Kandev installs Docker Scout 1.24.0 in `Dockerfile.local`. The guarded Docker
client accepts only `docker scout cves --only-severity critical <image>` for the
following exact task root and built Compose service pairs:

| Task ID | Task root | Build service |
| --- | --- | --- |
| `2999fa68-f6cc-4b96-8300-de99ef7e0a62` | `/data/tasks/task-8476-fix-vulner_4xmsmdbv` | `backend-stripe` |
| `e6c2c75c-a261-465e-bf48-8af7d735668c` | `/data/tasks/task-8476-fix-vulner_0cn6qbsh` | `prerender-backend` |

The broker requires a saved Compose model owned by the same task and checkout,
checks that the service has a local build, and matches the exact scoped image
tag. Scout receives `local://<image>` so it cannot fall back to a registry
image. The response starts with the local image ID and manifest digest, then
the complete critical CVE report (up to 64 MiB). An oversized report is
explicitly marked failed rather than reported as complete. The image tag is
checked again after the scan to detect a concurrent rebuild.

## Operator login

After Kandev has been deployed, sign in from a trusted shell in the Kandev
container, **not from a guarded task**:

```sh
docker exec -it -u kandev kandev sh -c \
  'DOCKER_CONFIG=/run/kandev-agent-docker/scout-auth docker login'
```

The named `kandev-scout-auth` volume persists across image rebuilds and normal
Kandev recreation. The agent guard replaces `/run` with its own tmpfs, hiding
the login file and daemon socket. The broker sets `DOCKER_CONFIG` only when it
runs the approved Scout command. Do not run a plain `docker login` with
`HOME=/data/home`: that location is readable by guarded agents.

## Task image builds and reports

The Stripe checkout's main Compose file references a missing `.env`. To build
only the requested image without requiring runtime secrets or starting its
dependencies, the task can create `scout.compose.yml` in its `jami` checkout:

```yaml
services:
  backend-stripe:
    build: ./jami-backend-stripe
```

The Pre-render checkout has a Dockerfile but no Compose file. Its task can
create `scout.compose.yml` in `jami-backend-prerender`:

```yaml
services:
  prerender-backend:
    build: .
```

From the corresponding checkout, use the guarded client:

```sh
docker compose -f scout.compose.yml build <service>
image=$(docker compose -f scout.compose.yml config --images)
docker scout cves --only-severity critical "$image" > scout-critical.txt 2>&1
```

`scout-critical.txt` contains the digest and full scan output. The file remains
inside the task checkout. The `image_id` is the local image identity; the
`manifest_digest` is Docker's descriptor digest (which can identify an OCI
index). If login or Scout's
vulnerability service is unavailable, the scan exits nonzero with the error.

To scan on an authorized runner instead, an operator with trusted Docker
access can inspect and export only the verified task image:

```sh
docker image inspect <scoped-task-image> --format '{{.Id}} {{json .RepoDigests}}'
docker save -o <task-image>.tar <scoped-task-image>
sha256sum <task-image>.tar
```

Transfer the tar through an authorized channel, then run
`docker scout cves --only-severity critical archive://<task-image>.tar` on the
runner. The archive checksum verifies transfer integrity; it is different
from the image manifest digest.
