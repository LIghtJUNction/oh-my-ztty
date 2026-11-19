#!/usr/bin/env python3
"""Publish complete, immutable release assets; identical reruns are safe."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text().strip()
    if args.tag != "v" + version:
        raise SystemExit("tag does not match VERSION")
    names = ["install.sh", "install.sh.sha256"]
    for arch in ["x86_64", "aarch64"]:
        names.extend([f"oh-my-ztty-{version}-linux-{arch}.tar.gz",
                      f"oh-my-ztty-{version}-linux-{arch}.tar.gz.sha256"])
    assets = {}
    for name in names:
        path = args.dist / name
        if not path.is_file():
            raise SystemExit(f"missing release asset: {path}")
        assets[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in [item for item in names if item.endswith(".sha256")]:
        text = (args.dist / name).read_text().split()
        if text != [assets[name[:-7]], name[:-7]]:
            raise SystemExit(f"checksum sidecar does not match {name}")
    found = subprocess.run(["gh", "release", "view", args.tag, "--json", "assets,isDraft"],
                           cwd=ROOT, capture_output=True, text=True)
    existing = {}
    draft = True
    if found.returncode == 0:
        release = json.loads(found.stdout)
        existing = {asset["name"]: asset for asset in release["assets"]}
        draft = release["isDraft"]
    else:
        subprocess.run(["gh", "release", "create", args.tag, "--draft", "--verify-tag",
                        "--title", "oh-my-ztty " + args.tag, "--generate-notes"], cwd=ROOT, check=True)
    for name, checksum in assets.items():
        if name in existing:
            if existing[name].get("digest") != "sha256:" + checksum:
                raise SystemExit(f"immutable release asset differs: {name}")
            print(f"unchanged {name}")
        else:
            subprocess.run(["gh", "release", "upload", args.tag, str(args.dist / name)], cwd=ROOT, check=True)
            print(f"uploaded {name}")
    if draft:
        subprocess.run(["gh", "release", "edit", args.tag, "--draft=false"], cwd=ROOT, check=True)
    print(f"Published complete release {args.tag}")

if __name__ == "__main__":
    main()
