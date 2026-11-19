#!/usr/bin/env python3
"""Inspect, validate and pin the suite's independent Git repositories."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ("ztty", "ssmcp", "zshard", "zdot", "zrc", "zfetch")

def run(*args, cwd=ROOT, capture=False):
    result = subprocess.run(args, cwd=cwd, check=True, text=True,
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

def new_asset_lock(name, ref):
    lock_path = ROOT / "dependencies.lock.json"
    lock = json.loads(lock_path.read_text())
    previous = lock["components"][name]
    release = json.loads(run("gh", "api", f"repos/{previous['repository']}/releases/tags/{ref}", capture=True))
    if release["draft"] or release["prerelease"]:
        raise RuntimeError("Upstream pin requires a published stable release")
    by_name = {asset["name"]: asset for asset in release["assets"]}
    updated = {"repository": previous["repository"], "tag": ref, "assets": {}}
    for arch, old in previous["assets"].items():
        filename = old["url"].rsplit("/", 1)[1]
        asset = by_name.get(filename)
        if asset is None:
            raise RuntimeError(f"Release has no expected {arch} asset: {filename}")
        url = asset["browser_download_url"]
        expected_prefix = f"https://github.com/{previous['repository']}/releases/download/{ref}/"
        if not url.startswith(expected_prefix):
            raise RuntimeError("Unexpected release asset URL")
        digest = asset.get("digest") or ""
        if digest.startswith("sha256:") and re.fullmatch(r"[0-9a-f]{64}", digest[7:]):
            sha = digest[7:]
        else:
            h = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=60) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            sha = h.hexdigest()
        updated["assets"][arch] = {"url": url, "sha256": sha}
    lock["components"][name] = updated
    return lock_path, json.dumps(lock, indent=2) + "\n"

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
        raise RuntimeError("dependencies.lock.json changed during pin; it was preserved")
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
            raise RuntimeError("dependencies.lock.json changed during pin; it was preserved")
        temporary.replace(destination)
    except (Exception, KeyboardInterrupt) as error:
        try:
            temporary.unlink()
        except OSError as cleanup_error:
            raise RuntimeError(
                f"Lock publication failed ({type(error).__name__}: {error}); "
                f"temporary file retained at {temporary}: {cleanup_error}") from error
        raise

def pin(name, ref):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+|[0-9a-f]{40}", ref):
        raise RuntimeError("Use a release tag vX.Y.Z or a full lowercase commit SHA")
    path = directory(name)
    snapshots = snapshot_sources(path)
    original_paths = {item["path"] for item in snapshots}
    lock_change = None
    lock_original = None
    if name in ("ztty", "ssmcp"):
        if not ref.startswith("v"):
            raise RuntimeError("Bundled upstream binaries require a release tag")
        lock_path = ROOT / "dependencies.lock.json"
        if run("git", "status", "--porcelain", "--untracked-files=all", "--",
               str(lock_path.relative_to(ROOT)), capture=True):
            raise RuntimeError("Commit or stash dependencies.lock.json changes first")
        lock_original = lock_path.read_bytes()
        lock_change = new_asset_lock(name, ref)
    run("git", "fetch", "--no-recurse-submodules", "--depth=1", "origin",
        "refs/tags/" + ref if ref.startswith("v") else ref, cwd=path)
    new_head = run("git", "rev-parse", "--verify", "FETCH_HEAD^{commit}",
                   cwd=path, capture=True)
    try:
        checkout(path, new_head)
        # A new gitlink must not take over an ignored, nonempty directory.
        for child in gitlinks(path):
            if child not in original_paths and child.exists():
                if not child.is_dir() or any(child.iterdir()):
                    raise RuntimeError(
                        f"New submodule directory is not empty: "
                        f"{child.relative_to(ROOT)}. Its contents were preserved.")
        run("git", "submodule", "sync", "--recursive", cwd=path)
        run("git", "submodule", "update", "--init", "--recursive", "--checkout",
            cwd=path)
        source_status = run("git", "submodule", "status", "--recursive",
                            cwd=path, capture=True)
        if any(line[:1] in ("-", "+", "U") for line in source_status.splitlines()):
            raise RuntimeError("Recursive submodule initialization left unresolved pins")
        if run("git", "status", "--porcelain", "--untracked-files=all",
               "--ignore-submodules=none", cwd=path, capture=True):
            raise RuntimeError("The selected source tree is not clean after recursive update")
        if lock_change:
            publish_lock(*lock_change, lock_original)
    except (Exception, KeyboardInterrupt) as error:
        recovery_errors = []
        try:
            additions = submodule_directories(path) - original_paths
        except Exception as inspection_error:
            additions = set()
            recovery_errors.append(f"Cannot inspect partial initialization: {inspection_error}")
        try:
            restore_checkout(snapshots[0])
        except Exception as recovery_error:
            recovery_errors.append(f"Component checkout: {recovery_error}")
        # Use native Git restoration; no force, deinit or clean, and no removal
        # of newly cloned worktrees.
        for arguments in (
            ("git", "submodule", "sync", "--recursive"),
            ("git", "submodule", "update", "--recursive", "--checkout", "--no-fetch"),
        ):
            try:
                run(*arguments, cwd=path)
            except Exception as recovery_error:
                recovery_errors.append(f"Recursive restoration: {recovery_error}")
        for snapshot in snapshots[1:]:
            try:
                restore_checkout(snapshot)
            except Exception as recovery_error:
                recovery_errors.append(f"{snapshot['path']}: {recovery_error}")
        for snapshot in snapshots:
            try:
                restore_configuration(snapshot["path"], snapshot["config"])
            except Exception as recovery_error:
                recovery_errors.append(str(recovery_error))
        retained = sorted(str(item.relative_to(ROOT))
                          for item in additions if item.exists())
        message = f"Pin {name} failed ({type(error).__name__}: {error}). "
        if recovery_errors:
            message += "Rollback incomplete: " + "; ".join(recovery_errors) + ". "
        else:
            message += "Previous source commits and checkout branches restored. "
        if lock_change:
            message += "The dependency lock was not replaced. "
        if retained:
            message += "Additional submodule directories retained for inspection: " + ", ".join(retained) + ". "
        raise RuntimeError(message.rstrip()) from error
    print(f"Pinned {name} to {new_head}, including recursive submodules. "
          "Run workspace.py check, then commit the gitlink and lock changes.")


def check(component):
    if component:
        run("make", "check", cwd=ROOT if component == "suite" else directory(component))
        return
    for name in ("zshard", "zdot", "zrc", "zfetch"):
        run("make", "check", cwd=directory(name))
    run("make", "check")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("status", help="show exact source pins and local changes")
    show.add_argument("--json", action="store_true")
    validate = commands.add_parser("check", help="run local checks for new components and the suite")
    validate.add_argument("--component", choices=("suite", "zshard", "zdot", "zrc", "zfetch"))
    update = commands.add_parser("pin", help="fetch and select one explicit component release")
    update.add_argument("component", choices=COMPONENTS)
    update.add_argument("ref")
    args = parser.parse_args()
    try:
        if args.command == "status": status(args.json)
        elif args.command == "check": check(args.component)
        else: pin(args.component, args.ref)
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print("workspace: " + str(error), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
