#!/usr/bin/env python3
"""Bump the suite version; --release checks, commits, tags and pushes it."""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def planned_files(current, version):
    """Update current-release guidance while preserving historical evidence."""
    changes = {ROOT / "VERSION": version + "\n"}
    installer = ROOT / "install.sh"
    text, count = re.subn(r"(?m)^VERSION=" + re.escape(current) + r"$",
                          "VERSION=" + version, installer.read_text())
    if count != 1:
        raise SystemExit("Installer must contain one matching VERSION assignment")
    changes[installer] = text

    overview = ROOT / "site/content/index.md"
    old = f"The current suite release is **{current}**"
    text = overview.read_text()
    if text.count(old) != 1:
        raise SystemExit("Overview must declare the current suite release once")
    changes[overview] = text.replace(old, f"The current suite release is **{version}**")

    guide = ROOT / "site/content/installation.md"
    text = guide.read_text()
    old_tag = f"https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v{current}"
    old_archive = f"oh-my-ztty-{current}-linux-"
    if old_tag not in text or old_archive not in text:
        raise SystemExit("Installation guide must identify the current release and archive")
    text = text.replace(old_tag, f"https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v{version}")
    changes[guide] = text.replace(old_archive, f"oh-my-ztty-{version}-linux-")
    return changes

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
    changes = planned_files(current, version)
    for path, text in changes.items():
        path.write_text(text)
    if args.release:
        subprocess.run(["make", "check"], cwd=ROOT, check=True)
        git("add", *(str(path.relative_to(ROOT)) for path in changes))
        git("commit", "-m", "release: " + tag)
        git("tag", "-a", tag, "-m", "oh-my-ztty " + version)
        subprocess.run(["git", "push", "--atomic", "origin", "HEAD:refs/heads/" + branch, "refs/tags/" + tag], cwd=ROOT, check=True)
        print(f"Pushed {tag}; the formal release workflow builds and publishes both Linux architectures.")
    else:
        print(f"{current} -> {version}; VERSION, installer and current-release docs updated. Run make check before committing.")

if __name__ == "__main__":
    main()
