#!/usr/bin/python3
"""Operator-only adoption of an existing independent task checkout.

The guard reads the resulting retirement records; agents cannot write the
database through their read-only /data/data mount.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import uuid

TABLE = "kandev_workspace_repairs"
SCHEMA = f"""CREATE TABLE IF NOT EXISTS {TABLE} (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL, session_id TEXT NOT NULL,
 environment_id TEXT NOT NULL, environment_repo_id TEXT NOT NULL,
 task_repository_id TEXT NOT NULL, repository_id TEXT NOT NULL,
 task_root TEXT NOT NULL, retired_path TEXT NOT NULL, marker_sha256 TEXT NOT NULL,
 missing_gitdir TEXT NOT NULL, adopted_path TEXT NOT NULL, adopted_branch TEXT NOT NULL,
 created_at TEXT NOT NULL, backup_path TEXT NOT NULL, prior_rows TEXT NOT NULL,
 UNIQUE(environment_repo_id, retired_path)
)"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def connect(path, writable=False):
    database = sqlite3.connect(str(path) if writable else path.as_uri()+"?mode=ro", uri=not writable, timeout=30)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA busy_timeout=30000")
    return database


def git(path, *args):
    environment = {k:v for k,v in os.environ.items() if not k.startswith("GIT_")}
    result = subprocess.run(["/usr/bin/git", "--no-optional-locks", "-C", str(path), *args], capture_output=True, text=True, env=environment)
    require(result.returncode == 0, "Git validation failed (output withheld)")
    return result.stdout.strip()


def plain_child(root, child):
    return child.parent == root and not child.name.startswith(".") and not child.is_symlink() and child.resolve() == child


def plan(database, task_id, session_id, retired, adopted, tasks_base=Path("/data/tasks")):
    session = database.execute("SELECT * FROM task_sessions WHERE id=? AND task_id=?", (session_id, task_id)).fetchone()
    require(session is not None and session["state"] == "WAITING_FOR_INPUT", "repair requires this task's existing idle session")
    environment = database.execute("SELECT * FROM task_environments WHERE id=? AND task_id=?", (session["task_environment_id"], task_id)).fetchone()
    require(environment is not None and environment["status"] == "ready" and environment["executor_type"] == "worktree", "repair requires the existing ready worktree environment")
    task = database.execute("SELECT * FROM tasks WHERE id=? AND archived_at IS NULL", (task_id,)).fetchone()
    require(task is not None, "task is not active")
    root = tasks_base / environment["task_dir_name"]
    require(root.parent == tasks_base and root.is_dir() and root.resolve() == root, "invalid registered task root")
    require(environment["workspace_path"] == str(root) and session["workspace_path"] == str(root), "repair only supports an unchanged materialized task root")
    require(retired != adopted and plain_child(root, retired) and plain_child(root, adopted), "checkouts must be distinct direct children of this exact task root")
    require(retired.is_dir() and adopted.is_dir(), "both existing checkout directories are required")
    marker = retired / ".git"
    require(marker.is_file() and not marker.is_symlink(), "retired checkout must have a plain Git marker")
    line = marker.read_text().strip()
    require(line.startswith("gitdir: /"), "retired Git marker is invalid")
    missing = Path(line[8:])
    require(not missing.exists(), "only a binding with missing Git metadata can be retired")
    require((adopted / ".git").is_dir() and not (adopted / ".git").is_symlink(), "adopted checkout must be an independent existing clone")
    require(Path(git(adopted, "rev-parse", "--absolute-git-dir")).resolve() == adopted / ".git", "adopted Git metadata escapes its checkout")
    common = Path(git(adopted, "rev-parse", "--git-common-dir"))
    require((common if common.is_absolute() else adopted / common).resolve() == adopted / ".git", "adopted Git common directory escapes its checkout")
    require(Path(git(adopted, "rev-parse", "--show-toplevel")).resolve() == adopted, "adopted path is not the Git root")
    branch = git(adopted, "symbolic-ref", "--short", "HEAD")
    require(bool(branch), "adopted checkout must be on an existing branch")
    repos = list(database.execute("SELECT * FROM task_environment_repos WHERE task_environment_id=?", (environment["id"],)))
    matches = [r for r in repos if r["worktree_path"] == str(retired) and r["status"] == "active" and not r["deleted_at"]]
    require(len(matches) == 1, "retired path must identify exactly one active environment repository")
    binding = matches[0]
    repository = database.execute("SELECT * FROM repositories WHERE id=? AND workspace_id=? AND deleted_at IS NULL", (binding["repository_id"], task["workspace_id"])).fetchone()
    require(repository is not None, "repository is not registered to this task workspace")
    require(git(Path(repository["local_path"]), "config", "--get", "remote.origin.url") == git(adopted, "config", "--get", "remote.origin.url"), "adopted clone's origin differs from the registered repository")
    task_repos = list(database.execute("SELECT * FROM task_repositories WHERE task_id=?", (task_id,)))
    candidates = [r for r in task_repos if r["repository_id"] == binding["repository_id"] and r["checkout_branch"] == branch]
    require(len(candidates) == 1, "existing task repository must already select the adopted branch")
    require(not database.execute("SELECT 1 FROM task_environment_repos WHERE worktree_path=?", (str(adopted),)).fetchone(), "adopted path already has a materialized binding")
    running = list(database.execute("""SELECT er.status,ts.state FROM executors_running er
        JOIN task_sessions ts ON ts.id=er.session_id
        WHERE er.task_id=? AND ts.task_environment_id=?""", (task_id, environment["id"])))
    require(all(r["status"] not in ("running", "starting") and r["state"] not in ("RUNNING", "STARTING") for r in running), "task execution is busy")
    return dict(task_id=task_id, session_id=session_id, environment_id=environment["id"], environment_repo_id=binding["id"],
                task_repository_id=candidates[0]["id"], repository_id=binding["repository_id"], task_root=str(root),
                retired_path=str(retired), marker_sha256=hashlib.sha256(marker.read_bytes()).hexdigest(), missing_gitdir=str(missing),
                adopted_path=str(adopted), adopted_branch=branch,
                prior_rows=json.dumps({"environment_repos": [dict(r) for r in repos], "task_repositories": [dict(r) for r in task_repos]}))


def retired_marker(database, root, marker):
    """Attest one exact obsolete artifact; never grant its Git metadata writes."""
    if not database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone():
        return False
    rows = list(database.execute(f"SELECT * FROM {TABLE} WHERE task_root=? AND retired_path=?", (str(root), str(marker.parent))))
    if not rows:
        return False
    require(len(rows) == 1, "ambiguous retirement record")
    repair = rows[0]
    require(plain_child(root, marker.parent) and marker.name == ".git" and marker.is_file() and not marker.is_symlink(), "retired marker path changed")
    require(hashlib.sha256(marker.read_bytes()).hexdigest() == repair["marker_sha256"], "retired marker content changed")
    require(marker.read_text().strip() == "gitdir: " + repair["missing_gitdir"] and not Path(repair["missing_gitdir"]).exists(), "retired Git metadata was restored or changed")
    row = database.execute("""SELECT te.task_id,te.task_dir_name,te.workspace_path,te.status AS env_status,
        er.repository_id,er.worktree_path,er.worktree_branch,er.status,er.deleted_at,t.archived_at,t.workspace_id,r.workspace_id AS repo_workspace
        FROM task_environments te JOIN task_environment_repos er ON er.task_environment_id=te.id
        JOIN tasks t ON t.id=te.task_id JOIN repositories r ON r.id=er.repository_id
        WHERE te.id=? AND er.id=?""", (repair["environment_id"], repair["environment_repo_id"])).fetchone()
    require(row is not None and row["task_id"] == repair["task_id"] and row["task_dir_name"] == root.name and row["workspace_path"] == str(root)
            and row["env_status"] == "ready" and not row["archived_at"] and row["workspace_id"] == row["repo_workspace"]
            and row["repository_id"] == repair["repository_id"] and row["worktree_path"] == repair["adopted_path"]
            and row["worktree_branch"] == repair["adopted_branch"] and row["status"] == "active" and not row["deleted_at"], "retirement no longer matches live ownership")
    adopted = Path(repair["adopted_path"])
    require(plain_child(root, adopted) and (adopted / ".git").is_dir() and not (adopted / ".git").is_symlink(), "adopted independent checkout changed")
    require(not database.execute("SELECT 1 FROM task_environment_repos WHERE worktree_path=? AND status='active' AND deleted_at IS NULL", (str(marker.parent),)).fetchone(), "retired checkout is still active")
    return True


def adopted_checkout(database, path):
    if not database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone():
        return False
    rows = list(database.execute(f"SELECT * FROM {TABLE} WHERE adopted_path=?", (str(path),)))
    if not rows:
        return False
    require(len(rows) == 1, "ambiguous adoption record")
    record = rows[0]
    require(retired_marker(database, Path(record["task_root"]), Path(record["retired_path"])/".git"), "adoption retirement is invalid")
    common = Path(git(path,"rev-parse","--git-common-dir"))
    require((common if common.is_absolute() else path/common).resolve() == path/".git", "adopted common Git metadata changed")
    require(Path(git(path,"rev-parse","--show-toplevel")).resolve() == path, "adopted Git root changed")
    require(git(path,"symbolic-ref","--short","HEAD") == record["adopted_branch"], "adopted branch changed")
    repository = database.execute("SELECT local_path FROM repositories WHERE id=? AND deleted_at IS NULL", (record["repository_id"],)).fetchone()
    require(repository is not None and git(Path(repository[0]),"config","--get","remote.origin.url") == git(path,"config","--get","remote.origin.url"), "adopted origin changed")
    return True


def apply(database_path, arguments):
    require(os.environ.get("KANDEV_AGENT_GUARD_ACTIVE") != "1", "workspace repairs are operator-only")
    with connect(database_path) as reader:
        proposed = plan(reader, arguments.task, arguments.session, Path(arguments.retire), Path(arguments.checkout))
    public = {k: v for k, v in proposed.items() if k != "prior_rows"}
    if not arguments.apply:
        return {"mode": "preview", **public}
    repair_id = str(uuid.uuid4())
    backup_dir = database_path.parent.parent / "backups" / "workspace-repair" / repair_id
    backup_dir.mkdir(parents=True, mode=0o700)
    os.chmod(backup_dir, 0o700)
    backup = backup_dir / database_path.name
    with connect(database_path) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
    os.chmod(backup, 0o600)
    key = database_path.parent / "master.key"
    if key.is_file():
        shutil.copyfile(key, backup_dir / "master.key")
        os.chmod(backup_dir / "master.key", 0o600)
    now = datetime.now(timezone.utc).isoformat()
    with connect(database_path, writable=True) as database:
        database.execute("BEGIN IMMEDIATE")
        current = plan(database, arguments.task, arguments.session, Path(arguments.retire), Path(arguments.checkout))
        require(current == proposed, "registration changed since validation; retry")
        database.execute(SCHEMA)
        others = [dict(r) for r in database.execute("SELECT id FROM task_environment_repos WHERE task_environment_id=? AND id<>? ORDER BY position,id", (proposed["environment_id"], proposed["environment_repo_id"]))]
        for index, row in enumerate(others, 1):
            database.execute("UPDATE task_environment_repos SET position=?,updated_at=? WHERE id=?", (index, now, row["id"]))
        database.execute("UPDATE task_environment_repos SET worktree_path=?,worktree_branch=?,position=0,updated_at=? WHERE id=? AND worktree_path=?", (proposed["adopted_path"], proposed["adopted_branch"], now, proposed["environment_repo_id"], proposed["retired_path"]))
        task_others = list(database.execute("SELECT id FROM task_repositories WHERE task_id=? AND id<>? ORDER BY position,id", (proposed["task_id"], proposed["task_repository_id"])))
        for index, row in enumerate(task_others, 1):
            database.execute("UPDATE task_repositories SET position=?,updated_at=? WHERE id=?", (index, now, row["id"]))
        database.execute("UPDATE task_repositories SET position=0,updated_at=? WHERE id=?", (now, proposed["task_repository_id"]))
        record = {"id": repair_id, **proposed, "created_at": now, "backup_path": str(backup)}
        columns = list(record)
        database.execute(f"INSERT INTO {TABLE} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", [record[c] for c in columns])
        require(retired_marker(database, Path(proposed["task_root"]), Path(proposed["retired_path"]) / ".git"), "retirement validation failed")
        require(database.execute("PRAGMA quick_check").fetchone()[0] == "ok", "database integrity failed")
    return {"mode": "applied", "repair_id": repair_id, "backup_path": str(backup), **public}


def rollback(database_path, repair_id):
    """Restore only this repair's binding/order; never restore the entire DB."""
    require(os.environ.get("KANDEV_AGENT_GUARD_ACTIVE") != "1", "workspace repairs are operator-only")
    with connect(database_path, writable=True) as database:
        database.execute("BEGIN IMMEDIATE")
        record = database.execute(f"SELECT * FROM {TABLE} WHERE id=?", (repair_id,)).fetchone()
        require(record is not None, "repair record was not found")
        require(retired_marker(database, Path(record["task_root"]), Path(record["retired_path"])/".git"), "repair no longer matches live ownership")
        session = database.execute("SELECT state FROM task_sessions WHERE id=? AND task_id=?", (record["session_id"], record["task_id"])).fetchone()
        require(session is not None and session[0] == "WAITING_FOR_INPUT", "rollback requires the existing idle session")
        prior = json.loads(record["prior_rows"])
        current_env = {r[0] for r in database.execute("SELECT id FROM task_environment_repos WHERE task_environment_id=?", (record["environment_id"],))}
        current_task = {r[0] for r in database.execute("SELECT id FROM task_repositories WHERE task_id=?", (record["task_id"],))}
        require(current_env == {r["id"] for r in prior["environment_repos"]} and current_task == {r["id"] for r in prior["task_repositories"]}, "attachment set changed; automatic rollback refused")
        for row in prior["environment_repos"]:
            live = database.execute("SELECT * FROM task_environment_repos WHERE id=?", (row["id"],)).fetchone()
            excluded = {"position", "updated_at"}
            if row["id"] == record["environment_repo_id"]:
                excluded |= {"worktree_path", "worktree_branch"}
            require(live is not None and all(live[k] == v for k,v in row.items() if k not in excluded), "environment binding changed after repair")
            database.execute("UPDATE task_environment_repos SET worktree_path=?,worktree_branch=?,position=?,updated_at=? WHERE id=?", (row["worktree_path"],row["worktree_branch"],row["position"],row["updated_at"],row["id"]))
        for row in prior["task_repositories"]:
            live = database.execute("SELECT * FROM task_repositories WHERE id=?", (row["id"],)).fetchone()
            require(live is not None and all(live[k] == v for k,v in row.items() if k not in {"position","updated_at"}), "task repository changed after repair")
            database.execute("UPDATE task_repositories SET position=?,updated_at=? WHERE id=?", (row["position"],row["updated_at"],row["id"]))
        # The immutable record remains as an audit, outside the guard's active
        # retirement table; deleting the active attestation restores fail-closed.
        database.execute(f"CREATE TABLE IF NOT EXISTS {TABLE}_rolled_back AS SELECT *,'' AS rolled_back_at FROM {TABLE} WHERE 0")
        database.execute(f"INSERT INTO {TABLE}_rolled_back SELECT *,? FROM {TABLE} WHERE id=?", (datetime.now(timezone.utc).isoformat(),repair_id))
        database.execute(f"DELETE FROM {TABLE} WHERE id=?", (repair_id,))
    return {"mode":"rolled-back","repair_id":repair_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("/data/data/kandev.db"))
    sub = parser.add_subparsers(dest="operation", required=True)
    check = sub.add_parser("check-retired")
    check.add_argument("root", type=Path)
    check.add_argument("marker", type=Path)
    inspect = sub.add_parser("check-adopted")
    inspect.add_argument("path", type=Path)
    adopt = sub.add_parser("adopt")
    for name in ("task", "session", "retire", "checkout"):
        adopt.add_argument("--"+name, required=True)
    adopt.add_argument("--apply", action="store_true")
    undo = sub.add_parser("rollback")
    undo.add_argument("--repair-id", required=True)
    args = parser.parse_args()
    try:
        if args.operation == "check-retired":
            with connect(args.db) as database:
                return 0 if retired_marker(database, args.root, args.marker) else 1
        if args.operation == "check-adopted":
            with connect(args.db) as database:
                return 0 if adopted_checkout(database,args.path) else 1
        print(json.dumps(rollback(args.db,args.repair_id) if args.operation == "rollback" else apply(args.db, args), indent=2))
        return 0
    except (ValueError, sqlite3.Error, OSError) as exc:
        print("kandev-workspace-registration: " + str(exc), file=__import__("sys").stderr)
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
