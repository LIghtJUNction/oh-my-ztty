#!/usr/bin/env python3
"""Bump the suite version; --release checks, commits, tags and pushes it."""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("part", choices=["major", "minor", "patch"])
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    current = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", current):
        raise SystemExit("VERSION is not a stable semantic version")
    values = [int(part) for part in current.split(".")]
    index = {"major": 0, "minor": 1, "patch": 2}[args.part]
    values[index] += 1
    for following in range(index + 1, 3):
        values[following] = 0
    version = ".".join(map(str, values))
    tag = "v" + version
    if args.release:
        if git("status", "--porcelain"):
            raise SystemExit("Release requires a clean checkout. Commit the current work first.")
        branch = git("symbolic-ref", "--short", "HEAD")
        if tag in git("tag", "--list", tag).splitlines():
            raise SystemExit(f"Tag already exists: {tag}")
        if git("ls-remote", "--tags", "origin", "refs/tags/" + tag):
            raise SystemExit(f"Remote tag already exists: {tag}")
    installer = ROOT / "install.sh"
    text = installer.read_text()
    text, count = re.subn(r"(?m)^VERSION=[0-9]+\.[0-9]+\.[0-9]+$", "VERSION=" + version, text)
    if count != 1:
        raise SystemExit("Installer must contain one VERSION assignment")
    (ROOT / "VERSION").write_text(version + "\n")
    installer.write_text(text)
    if args.release:
        subprocess.run(["make", "check"], cwd=ROOT, check=True)
        git("add", "VERSION", "install.sh")
        git("commit", "-m", "release: " + tag)
        git("tag", "-a", tag, "-m", "oh-my-ztty " + version)
        subprocess.run(["git", "push", "--atomic", "origin", "HEAD:refs/heads/" + branch, "refs/tags/" + tag], cwd=ROOT, check=True)
        print(f"Pushed {tag}; the formal release workflow builds and publishes both Linux architectures.")
    else:
        print(f"{current} -> {version}; VERSION and install.sh updated. Run make check before committing.")

if __name__ == "__main__":
    main()
