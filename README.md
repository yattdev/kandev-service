# Kandev — Dual-Host Architecture

Two **identical** kandev instances, one always-on (mini-desktop), one powerful (sfl-desktop). Data syncs sfl → mini automatically; push mini → sfl manually before switching.

## Hosts

| Host | IP | User | Role |
|---|---|---|---|
| mini-desktop | 10.0.0.182 | alassane | always-on fallback (home dev) |
| sfl-desktop | 192.168.50.211 | ayattara | powerful, work hours (via SFL VPN) |

Both hosts use:
- `~/Code` — projects/workspaces (bind-mounted into container as `/data/home/Code`)
- `~/.local/share/kandev` — kandev data dir (sqlite + sessions, mounted as `/data`)

### Adding a repository in the UI

Kandev restricts repository paths to within the container `HOME` (`/data/home`). The host `~/Code` is **nested-bind-mounted** at `/data/home/Code` inside the container (a real directory, not a symlink — kandev's discovery scanner does not follow symlinks).

In the **Add Local Repository** dialog enter:

```
/data/home/Code/<project-name>
```

(Not the host path like `/home/alassane/Code/<project>` — that path doesn't exist inside the container.)

> The mountpoint `~/.local/share/kandev/home/Code` is created as an empty directory by `install-mini.sh` / `install-sfl.sh` so Docker can apply the nested bind on container (re)create.

## Client access (from yattara-pc)

Add to `/etc/hosts`:

```
10.0.0.182        board.home
192.168.50.211    board.sfl
```

Then open:
- http://board.home — mini-desktop kandev (always available)
- http://board.sfl — sfl-desktop kandev (SFL VPN must be up: `sudo nmcli connection up "SFL Montreal VPN"`)

Direct backend port is `38429`. On sfl-desktop, port `80` is redirected to `38429` via iptables NAT so `http://board.sfl` (no port) works. On mini-desktop, Caddy handles `board.home` — no port needed.

## Network / iptables (sfl-desktop)

### Port map

| Port | Bound to | What |
|---|---|---|
| `38429` | `0.0.0.0` | Kandev unified server — backend + web UI |
| `80` | N/A — no listener | Redirected → `38429` by iptables NAT |

### Why two iptables rules are required

Linux iptables NAT has two chains that must both be set for `http://board.sfl` to work everywhere:

| Chain | Applies to | Use case |
|---|---|---|
| `PREROUTING` | Packets arriving **from outside** the machine | Other PCs on the network (yattara-pc, mini-desktop) |
| `OUTPUT` | Packets generated **locally** on sfl-desktop | Browser/curl running on sfl-desktop itself |

**Classic symptom of a missing OUTPUT rule:** `http://board.sfl` works from yattara-pc but gives *Connection refused* from a browser or `curl` on sfl-desktop itself.

Both rules must be present:

```
-A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429
-A OUTPUT     -p tcp --dport 80 -j REDIRECT --to-port 38429
```

These are persisted in `/etc/ufw/before.rules` and applied at boot by UFW.

### Diagnose

```bash
# Are both rules active right now?
sudo iptables -t nat -L PREROUTING -n | grep 38429   # should show a line
sudo iptables -t nat -L OUTPUT     -n | grep 38429   # should show a line

# Quick connectivity test
curl -o /dev/null -w "%{http_code}" http://board.sfl/   # expect 200
curl -o /dev/null -w "%{http_code}" http://localhost:38429/  # direct, no NAT
```

### Fix (if rules are missing after reboot)

If UFW reload didn't pick up `before.rules` correctly, re-apply live without sudo using Docker:

```bash
# Apply both rules via privileged container (no sudo password needed — uses docker group)
docker run --rm --net=host --cap-add=NET_ADMIN --privileged alpine \
  sh -c 'apk add -q iptables && \
         iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429 && \
         iptables -t nat -A OUTPUT     -p tcp --dport 80 -j REDIRECT --to-port 38429 && \
         echo OK'

# Or simply re-run the idempotent install script (will prompt for sudo):
bash ~/Code/kandev/install-sfl.sh
```

## Deploy

### mini-desktop

```bash
# 1. Copy compose + scripts (deploy path: ~/Code/kandev)
rsync -avz stack/kandev/ alassane@10.0.0.182:~/Code/kandev/

# 2. (One-time) migrate existing named volume to bind path
ssh alassane@10.0.0.182 '
  mkdir -p ~/.local/share/kandev ~/Code
  if docker volume inspect kandev_kandev-data >/dev/null 2>&1; then
    docker run --rm -v kandev_kandev-data:/from -v ~/.local/share/kandev:/to alpine \
      sh -c "cp -a /from/. /to/"
  fi
'

# 3. Up
ssh alassane@10.0.0.182 "cd ~/Code/kandev && docker compose up -d --force-recreate"

# 4. Install sync cron (now runs as root via /etc/cron.d, not user crontab)
ssh alassane@10.0.0.182 "sudo bash ~/Code/kandev/install-mini.sh"

# 5. Verify
ssh alassane@10.0.0.182 "docker ps --filter name=kandev; ls ~/Code | head"
```

### sfl-desktop (when SFL VPN is up)

```bash
sudo nmcli connection up "SFL Montreal VPN"

rsync -avz stack/kandev/ ayattara@sfl-desktop:~/Code/kandev/

# Setup: systemd auto-start + UFW rules + port 80 → 38429 redirect + start kandev
ssh ayattara@sfl-desktop 'bash ~/Code/kandev/install-sfl.sh'

# One-time push current state from mini to sfl
sudo bash stack/kandev/sync-to-sfl.sh
```

`install-sfl.sh` is idempotent — re-run anytime to re-sync the systemd unit,
UFW rules and port-80 redirect. It will prompt for sudo when needed.

## Sync

| Direction | Mode | Trigger |
|---|---|---|
| sfl → mini | automatic | `/etc/cron.d/kandev-sync-from-sfl` runs `*/10 * * * *` as **root** on mini-desktop (only runs if VPN is up + ssh works) |
| mini → sfl | manual | `sudo bash stack/kandev/sync-to-sfl.sh` (run on mini-desktop) |

Logs: `~/logs/kandev-sync.log` on mini-desktop (root writes, alassane owns).

### Why root?

Some paths under `~/Code/` on mini-desktop are owned by `root:root` (typically `*/.github/mcp.json` created by docker containers writing to bind mounts). A user-cron rsync gets `Permission denied` writing into them and exits rc=23.

The scripts run as **root** so the rsync receiver can write anywhere, but pass `--chown=alassane:alassane` (sfl → mini) and `--chown=ayattara:ayattara` (mini → sfl) so files always end up owned by the **normal user** on the destination — the sync itself never creates root-owned files.

SSH still connects to sfl-desktop as the non-root user `ayattara`, using alassane's key (`-i /home/alassane/.ssh/mini-desk -o User=ayattara -F /home/alassane/.ssh/config`).

### Diagnostic

Each sync logs any paths under `~/Code/` not owned by `alassane` (no auto-fix — silently changing files owned by other processes could break them). Inspect:

```bash
ssh alassane@10.0.0.182 "grep -A50 'non-user-owned' ~/logs/kandev-sync.log | tail -60"
```

To normalize ownership of a specific path:

```bash
ssh alassane@10.0.0.182 "sudo chown -R alassane:alassane ~/Code/<path>"
```

What gets synced:
- `~/Code/` — projects (excludes `node_modules`, `.venv`, `__pycache__`, `.next`, `dist`, `build`)
- `~/.local/share/kandev/` — kandev sqlite DB, sessions, config

Why cron over realtime (Syncthing/inotify):
- No write conflicts when both hosts edit the same file
- Auditable log
- Survives offline periods cleanly

## Workflow

| Situation | What to do |
|---|---|
| Working at home (evenings, weekends) | Use board.home — mini-desktop has latest sfl state (synced every 10min while VPN was up) |
| About to switch back to office | If you made changes on mini, run `sync-to-sfl.sh` before resuming on sfl |
| Working at office | Use board.sfl — full power |
| VPN drops at home | Sync just skips; resumes next cycle automatically |

## Caveats — `~/Code` on mini-desktop

mini-desktop's `~/Code/` is **shared** between user workspaces AND production service dirs
referenced by systemd units (`~/Code/kandev/`, `~/Code/vpn/`, `~/Code/reverse-proxy/`,
`~/Code/nextcloud-data/`, `~/Code/agent-os/`, `~/Code/vaultwarden/`, `~/Code/nanoclaw/`,
`~/Code/onecli/`, `~/Code/vibe-kanban/`).

Sync scripts **explicitly exclude** these top-level dirs so the rsync `--delete` never
wipes production services. If you add a new infra service under `~/Code/` on mini-desktop,
**add it to the excludes** in both `sync-from-sfl.sh` and `sync-to-sfl.sh`.

## Update kandev

Docker images are **not** updated by `apt upgrade` or system updates — they must be pulled explicitly.

Both hosts run a **daily auto-update cron at 03:30** that pulls the latest image and restarts the container only if the image actually changed (no unnecessary restarts on quiet nights).

| Host | Mechanism | Log |
|---|---|---|
| mini-desktop | `/etc/cron.d/kandev-update` (root) | `~/logs/kandev-update.log` |
| sfl-desktop | user crontab (`ayattara`) | `~/logs/kandev-update.log` |

### Manual update

```bash
# mini-desktop
ssh alassane@10.0.0.182 "bash ~/Code/kandev/update.sh"
# sfl-desktop (with VPN)
ssh ayattara@sfl-desktop  "bash ~/Code/kandev/update.sh"
```

### Check update log

```bash
ssh alassane@10.0.0.182 "tail -20 ~/logs/kandev-update.log"
ssh ayattara@sfl-desktop  "tail -20 ~/logs/kandev-update.log"
```
