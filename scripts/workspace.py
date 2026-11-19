#!/usr/bin/env python3
"""Inspect, validate and pin the suite's independent Git repositories."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ("ztty", "ssmcp", "zshard", "zdot")

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

def pin(name, ref):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+|[0-9a-f]{40}", ref):
        raise RuntimeError("Use a release tag vX.Y.Z or a full lowercase commit SHA")
    path = directory(name)
    if run("git", "status", "--porcelain", cwd=path, capture=True):
        raise RuntimeError(f"Commit or stash changes in components/{name} first")
    old_head = run("git", "rev-parse", "HEAD", cwd=path, capture=True)
    lock_change = None
    if name in ("ztty", "ssmcp"):
        if not ref.startswith("v"):
            raise RuntimeError("Bundled upstream binaries require a release tag")
        lock_change = new_asset_lock(name, ref)
    run("git", "fetch", "--depth=1", "origin", "refs/tags/" + ref if ref.startswith("v") else ref, cwd=path)
    new_head = run("git", "rev-parse", "--verify", "FETCH_HEAD^{commit}", cwd=path, capture=True)
    run("git", "checkout", "--detach", new_head, cwd=path)
    try:
        if lock_change:
            destination, text = lock_change
            temp = destination.with_suffix(".json.new")
            temp.write_text(text)
            temp.replace(destination)
    except OSError:
        run("git", "checkout", "--detach", old_head, cwd=path)
        raise
    print(f"Pinned {name} to {new_head}. Run workspace.py check, then commit the gitlink and lock changes.")

def check(component):
    if component:
        run("make", "check", cwd=ROOT if component == "suite" else directory(component))
        return
    for name in ("zshard", "zdot"):
        run("make", "check", cwd=directory(name))
    run("make", "check")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("status", help="show exact source pins and local changes")
    show.add_argument("--json", action="store_true")
    validate = commands.add_parser("check", help="run local checks for new components and the suite")
    validate.add_argument("--component", choices=("suite", "zshard", "zdot"))
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
