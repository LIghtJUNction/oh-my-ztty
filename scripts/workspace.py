#!/usr/bin/env python3
"""Sync, inspect and validate the suite's independent Git repositories."""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from managed_build import background_command

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ("ztty", "ssmcp", "zshard", "zdot", "zrc", "zfetch", "zmem")

def run(*args, cwd=ROOT, capture=False):
    command = background_command(args) if args[:1] == ("cargo",) else args
    result = subprocess.run(command, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""

def directory(name):
    path = ROOT / "components" / name
    if not (path / ".git").exists():
        raise RuntimeError("Initialize submodules first: git submodule update --init --recursive")
    return path

def status(as_json):
    rows = []
    for name in COMPONENTS:
        path = ROOT / "components" / name
        if not (path / ".git").exists():
            rows.append({"component": name, "initialized": False})
            continue
        head = run("git", "rev-parse", "HEAD", cwd=path, capture=True)
        dirty = bool(run("git", "status", "--porcelain", "--untracked-files=normal", cwd=path, capture=True))
        recorded = run("git", "ls-files", "--stage", "--", "components/" + name, capture=True).split()
        rows.append({"component": name, "initialized": True, "head": head,
                     "recorded": recorded[1] if len(recorded) >= 2 else None, "dirty": dirty})
    if as_json:
        print(json.dumps({"schema": 1, "components": rows}, indent=2))
    else:
        for row in rows:
            if not row["initialized"]:
                print(f'{row["component"]:8} uninitialized')
            else:
                state = "dirty" if row["dirty"] else "clean"
                if row["head"] != row["recorded"]:
                    state += ", changed pin"
                print(f'{row["component"]:8} {row["head"][:12]}  {state}')


CONFIG_KEYS = r"^(submodule\..*|remote\..*\.url)$"

def optional_git(*args, cwd):
    """Read optional Git metadata; only status 1 means an absent value."""
    command = ("git", *args)
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(result.returncode, command,
                                            result.stdout, result.stderr)
    return result.stdout if result.returncode == 0 else ""

def gitlinks(path):
    entries = run("git", "ls-files", "--stage", "-z", cwd=path, capture=True)
    return [path / entry.split("\t", 1)[1]
            for entry in entries.split("\0")
            if entry.startswith("160000 ")]

def repositories(path):
    """Inspect initialized repositories without changing any checkout."""
    yield path
    for child in gitlinks(path):
        if (child / ".git").exists():
            yield from repositories(child)

def submodule_directories(path):
    found = set()
    for repo in repositories(path):
        for child in gitlinks(repo):
            if child.exists():
                found.add(child)
    return found

def configuration(path):
    values = {}
    output = optional_git("config", "--local", "--null", "--get-regexp",
                          CONFIG_KEYS, cwd=path)
    for entry in output.split("\0"):
        if entry:
            key, _, value = entry.partition("\n")
            values.setdefault(key, []).append(value)
    return values

def restore_configuration(path, previous):
    current = configuration(path)
    try:
        for key in sorted(current.keys() | previous.keys()):
            if current.get(key) == previous.get(key):
                continue
            if key in current:
                run("git", "config", "--local", "--unset-all", key, cwd=path)
            for value in previous.get(key, []):
                run("git", "config", "--local", "--add", key, value, cwd=path)
    except subprocess.CalledProcessError as error:
        # URL values can contain credentials; do not include them in diagnostics.
        raise RuntimeError(f"Could not restore Git configuration in {path}") from error

def snapshot_sources(path):
    snapshots = []
    for repo in repositories(path):
        label = repo.relative_to(ROOT)
        dirty = run("git", "status", "--porcelain", "--untracked-files=all",
                    "--ignore-submodules=none", cwd=repo, capture=True)
        if dirty:
            raise RuntimeError(f"Commit or stash source changes in {label} first")
        if repo != path:
            ignored = run("git", "status", "--porcelain", "--ignored=matching",
                          "--untracked-files=normal", "--ignore-submodules=none",
                          cwd=repo, capture=True)
            ignored = [line[3:] for line in ignored.splitlines()
                       if line.startswith("!! ")]
            if ignored:
                raise RuntimeError(
                    f"Initialized nested repository {label} has ignored paths "
                    f"(possibly build caches): {', '.join(ignored)}. "
                    "Use a clean nested checkout or move those paths aside; "
                    "recursive Git updates can overwrite ignored files.")
        for child in gitlinks(repo):
            if not (child / ".git").exists() and child.exists():
                if not child.is_dir() or any(child.iterdir()):
                    raise RuntimeError(
                        f"Uninitialized submodule directory is not empty: "
                        f"{child.relative_to(ROOT)}. Preserve or move its contents first.")
        snapshots.append({
            "path": repo,
            "head": run("git", "rev-parse", "HEAD", cwd=repo, capture=True),
            "branch": optional_git("symbolic-ref", "--quiet", "--short", "HEAD",
                                   cwd=repo).strip(),
            "config": configuration(repo),
        })
    return snapshots

def checkout(path, target, detached=True):
    arguments = ["git", "checkout", "--no-recurse-submodules",
                 "--no-overwrite-ignore"]
    if detached:
        arguments.append("--detach")
    run(*arguments, target, cwd=path)

def restore_checkout(snapshot):
    path, head, branch = (snapshot[key] for key in ("path", "head", "branch"))
    if branch:
        try:
            branch_head = run("git", "rev-parse", "--verify",
                              "refs/heads/" + branch, cwd=path, capture=True)
        except subprocess.CalledProcessError:
            branch_head = None
        if branch_head == head:
            checkout(path, branch, detached=False)
            return
    checkout(path, head)
    if branch:
        raise RuntimeError(
            f"Branch {branch} changed in {path}; restored the old commit detached "
            "and left that branch untouched")

def publish_lock(destination, text, original):
    if destination.read_bytes() != original:
        raise RuntimeError("dependencies.lock.json changed during sync; it was preserved")
    descriptor, filename = tempfile.mkstemp(
        prefix=".dependencies.lock.", suffix=".tmp", dir=destination.parent)
    temporary = Path(filename)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(destination.stat().st_mode & 0o777)
        if destination.read_bytes() != original:
            raise RuntimeError("dependencies.lock.json changed during sync; it was preserved")
        temporary.replace(destination)
    except (Exception, KeyboardInterrupt) as error:
        try:
            temporary.unlink()
        except OSError as cleanup_error:
            raise RuntimeError(
                f"Lock publication failed ({type(error).__name__}: {error}); "
                f"temporary file retained at {temporary}: {cleanup_error}") from error
        raise

def source_url(name):
    return f"https://github.com/LIghtJUNction/{name}.git"


def latest_source(name, path):
    """Resolve one live default branch and fetch that exact observation."""
    repository = source_url(name)
    advertised = run("git", "ls-remote", "--symref", repository, "HEAD",
                     cwd=path, capture=True)
    branch = head = None
    for line in advertised.splitlines():
        value, _, ref = line.partition("\t")
        if ref != "HEAD":
            continue
        if value.startswith("ref: refs/heads/"):
            branch = value.removeprefix("ref: refs/heads/")
        elif re.fullmatch(r"[0-9a-f]{40}", value):
            head = value
    if not branch or not head:
        raise RuntimeError(f"Cannot resolve the remote default branch for {name}")
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run("git", "fetch", "--no-tags", "--no-recurse-submodules", "--depth=1",
        repository, head, cwd=path)
    fetched = run("git", "rev-parse", "--verify", "FETCH_HEAD^{commit}",
                  cwd=path, capture=True)
    if fetched != head:
        raise RuntimeError(f"Fetched {name} source differs from the observed default branch")
    return {"repository": repository, "branch": branch, "commit": head,
            "observed_at": observed_at}


def select_source(snapshots, new_head):
    path = snapshots[0]["path"]
    original_paths = {item["path"] for item in snapshots}
    checkout(path, new_head)
    for child in gitlinks(path):
        if child not in original_paths and child.exists():
            if not child.is_dir() or any(child.iterdir()):
                raise RuntimeError(
                    f"New submodule directory is not empty: "
                    f"{child.relative_to(ROOT)}. Its contents were preserved.")
    run("git", "submodule", "sync", "--recursive", cwd=path)
    run("git", "submodule", "update", "--init", "--recursive", "--checkout", cwd=path)
    source_status = run("git", "submodule", "status", "--recursive",
                        cwd=path, capture=True)
    if any(line[:1] in ("-", "+", "U") for line in source_status.splitlines()):
        raise RuntimeError("Recursive submodule initialization left unresolved pins")
    if run("git", "status", "--porcelain", "--untracked-files=all",
           "--ignore-submodules=none", cwd=path, capture=True):
        raise RuntimeError("The selected source tree is not clean after recursive update")


def restore_sources(snapshots):
    path = snapshots[0]["path"]
    original_paths = {item["path"] for item in snapshots}
    errors = []
    try:
        additions = submodule_directories(path) - original_paths
    except Exception as error:
        additions = set()
        errors.append(f"Cannot inspect partial initialization: {error}")
    try:
        restore_checkout(snapshots[0])
    except Exception as error:
        errors.append(f"Component checkout: {error}")
    # Never force, deinit, clean or delete newly cloned worktrees during recovery.
    for arguments in (
        ("git", "submodule", "sync", "--recursive"),
        ("git", "submodule", "update", "--recursive", "--checkout", "--no-fetch"),
    ):
        try:
            run(*arguments, cwd=path)
        except Exception as error:
            errors.append(f"Recursive restoration: {error}")
    for snapshot in snapshots[1:]:
        try:
            restore_checkout(snapshot)
        except Exception as error:
            errors.append(f"{snapshot['path']}: {error}")
    for snapshot in snapshots:
        try:
            restore_configuration(snapshot["path"], snapshot["config"])
        except Exception as error:
            errors.append(str(error))
    retained = sorted(str(item.relative_to(ROOT)) for item in additions if item.exists())
    return errors, retained


def sync(component=None):
    names = (component,) if component else COMPONENTS
    lock_path = ROOT / "dependencies.lock.json"
    if run("git", "status", "--porcelain", "--untracked-files=all", "--",
           str(lock_path.relative_to(ROOT)), capture=True):
        raise RuntimeError("Commit or stash dependencies.lock.json changes first")
    original = lock_path.read_bytes()
    lock = json.loads(original)
    if component and lock.get("schema") != 2:
        raise RuntimeError("Run workspace.py sync without a component to migrate all source records")
    records = dict(lock.get("components", {})) if lock.get("schema") == 2 else {}
    # Check every selected checkout before fetching or changing any source tree.
    snapshots = {name: snapshot_sources(directory(name)) for name in names}
    updates = {name: latest_source(name, snapshots[name][0]["path"]) for name in names}
    applied = []
    try:
        for name in names:
            applied.append(name)
            select_source(snapshots[name], updates[name]["commit"])
        records.update(updates)
        updated = {"schema": 2,
                   "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "components": records}
        publish_lock(lock_path, json.dumps(updated, indent=2) + "\n", original)
    except (Exception, KeyboardInterrupt) as error:
        recovery_errors, retained = [], []
        for name in reversed(applied):
            errors, additions = restore_sources(snapshots[name])
            recovery_errors.extend(errors)
            retained.extend(additions)
        message = f"Sync {', '.join(names)} failed ({type(error).__name__}: {error}). "
        if recovery_errors:
            message += "Rollback incomplete: " + "; ".join(recovery_errors) + ". "
        else:
            message += "Previous source commits and checkout branches restored. "
        message += "The dependency lock was not replaced. "
        if retained:
            message += "Additional submodule directories retained for inspection: " + ", ".join(retained) + ". "
        raise RuntimeError(message.rstrip()) from error
    for name in names:
        record = updates[name]
        print(f"Synced {name} from {record['branch']} to {record['commit']}")
    print("Run workspace.py check, then commit the gitlinks and source lock together.")


def check(component):
    if component == "zrc":
        run(sys.executable, "scripts/check.py", cwd=directory(component))
    elif component == "zmem":
        run("cargo", "test", "--locked", cwd=directory(component))
        run("cargo", "check", "--locked", "--no-default-features", "--lib",
            cwd=directory(component))
    elif component:
        run("make", "check", cwd=ROOT if component == "suite" else directory(component))
    else:
        for name in ("zshard", "zdot", "zrc", "zfetch", "zmem", "suite"):
            check(name)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("status", help="show exact source pins and local changes")
    show.add_argument("--json", action="store_true")
    validate = commands.add_parser("check", help="run local checks for new components and the suite")
    validate.add_argument("--component", choices=("suite", "zshard", "zdot", "zrc", "zfetch", "zmem"))
    update = commands.add_parser("sync", help="fetch current default-branch source for one or all components")
    update.add_argument("component", nargs="?", choices=COMPONENTS)
    args = parser.parse_args()
    try:
        if args.command == "status": status(args.json)
        elif args.command == "check": check(args.component)
        else: sync(args.component)
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print("workspace: " + str(error), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
