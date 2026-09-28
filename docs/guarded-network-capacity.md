# Guarded Compose network capacity

Docker's predefined address pools can be exhausted while a task still needs a
new isolated Compose project. The task-scoped Docker broker provides a network
reservation for the project's default bridge without exposing the Docker socket
or existing task networks to the agent.

From the task's own project directory, with a fresh `kd_` Compose project name:

```sh
export COMPOSE_PROJECT_NAME=kd_<unique-task-project>
docker compose config >/dev/null
docker kandev network reserve
docker compose up -d db
```

The `config` call binds the rendered Compose model to the authenticated task
root and exact project directory. `reserve` accepts only that saved model with
one unconfigured project-owned default bridge. It returns JSON containing the
project, network name, network ID, subnet, and whether this is an idempotent
retry. The broker checks host IPv4 routes, tries `/24` slots in the RFC 2544
benchmark range, and accepts a slot only after Docker creates and verifies the
network with matching task and Compose ownership labels. Docker rejects a slot
already allocated to any network. The agent cannot select a subnet or attach to
an external network.

Use the same `COMPOSE_PROJECT_NAME` for `config`, `reserve`, and `up`. Ordinary
`docker compose down -v` removes only that project's resources when its owner
is finished; no global prune or daemon configuration change is involved.

This deployment admission is an environment repair for Kandev platform owner
`3a64829a-8eff-4162-bb4d-166f8df5b4c6`. Draft PR #3686 remains the
canonical route for long-term stale-network reclamation.
