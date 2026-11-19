#!/usr/bin/env python3
"""Build a complete, deterministic Linux release from pinned inputs."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ARCHES = {"x86_64": 62, "aarch64": 183}

def run(argv, cwd=ROOT, **kwargs):
    return subprocess.check_output(argv, cwd=cwd, text=True, **kwargs).strip()

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def copy(source, destination):
    if source.is_symlink() or not source.is_file():
        raise RuntimeError(f"expected a regular file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

def download(spec):
    path = ROOT / ".cache" / spec["url"].rsplit("/", 1)[-1]
    path.parent.mkdir(exist_ok=True)
    if path.exists() and digest(path) == spec["sha256"]:
        return path
    temporary = path.with_suffix(path.suffix + ".part")
    request = urllib.request.Request(spec["url"], headers={"User-Agent": "oh-my-ztty-release/1"})
    with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as out:
        shutil.copyfileobj(response, out)
    if digest(temporary) != spec["sha256"]:
        temporary.unlink()
        raise RuntimeError(f"upstream checksum mismatch: {path.name}")
    temporary.replace(path)
    return path

def extract_member(archive, basename, destination, required=True):
    with tarfile.open(archive, "r:gz") as stream:
        candidates = [entry for entry in stream.getmembers() if entry.isfile() and entry.name.rsplit("/", 1)[-1] == basename]
        if not candidates and not required:
            return
        if len(candidates) != 1:
            raise RuntimeError(f"expected exactly one {basename} in {archive.name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(stream.extractfile(candidates[0]).read())

def check_elf(path, arch):
    header = path.read_bytes()[:20]
    if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != ARCHES[arch]:
        raise RuntimeError(f"wrong executable architecture: {path}")

def tracked_component(name, destination):
    source = ROOT / "components" / name
    entries = subprocess.check_output(["git", "ls-files", "-z"], cwd=source).decode().split("\0")
    for entry in entries:
        if entry and not entry.startswith((".github/", "tests/", "scripts/")):
            copy(source / entry, destination / entry)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=ARCHES, default=platform.machine())
    parser.add_argument("--zdot", type=Path, help="existing binary matching the target architecture")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text().strip()
    lock = json.loads((ROOT / "dependencies.lock.json").read_text())
    sources = {}
    for name in ["ztty", "ssmcp", "zshard", "zdot"]:
        source = ROOT / "components" / name
        sha = run(["git", "rev-parse", "HEAD"], cwd=source)
        sources[name] = sha
        if name in lock["components"]:
            expected = run(["git", "rev-parse", lock["components"][name]["tag"] + "^{commit}"], cwd=source)
            if sha != expected:
                raise RuntimeError(f"{name} gitlink does not match the locked release tag")
    if args.zdot is None:
        if platform.machine() != args.arch:
            raise RuntimeError("cross packaging requires --zdot with a cross-built binary")
        target = f"{args.arch}-unknown-linux-gnu"
        target_dir = ROOT / "target" / "zdot"
        subprocess.run(["cargo", "build", "--locked", "--release", "--target", target,
                        "--manifest-path", str(ROOT / "components/zdot/Cargo.toml")],
                       check=True, cwd=ROOT / "components/zdot", env={**os.environ, "CARGO_TARGET_DIR": str(target_dir)})
        args.zdot = target_dir / target / "release/zdot"
    check_elf(args.zdot, args.arch)
    args.output.mkdir(parents=True, exist_ok=True)
    (ROOT / ".cache").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bundle-", dir=ROOT / ".cache") as temp:
        stage = Path(temp) / "oh-my-ztty"
        stage.mkdir()
        for path in ["install.sh", "uninstall.sh", "LICENSE", "VERSION", "dependencies.lock.json", "bin/omztty", "bin/zshard"]:
            copy(ROOT / path, stage / path)
        for folder in ["config", "packaging"]:
            for source in sorted((ROOT / folder).rglob("*")):
                if source.is_file():
                    copy(source, stage / source.relative_to(ROOT))
        tracked_component("zshard", stage / "components/zshard")
        copy(args.zdot, stage / "bin/zdot")
        for name, spec in lock["components"].items():
            archive = download(spec["assets"][args.arch])
            extract_member(archive, name, stage / "bin" / name)
            extract_member(archive, "LICENSE", stage / "licenses" / f"{name}.txt")
            if name == "ssmcp":
                extract_member(archive, "code-mode.js", stage / "bin/code-mode.js", required=False)
        for name in ["ztty", "ssmcp", "zdot"]:
            binary = stage / "bin" / name
            binary.chmod(0o755)
            check_elf(binary, args.arch)
        for name in ["omztty", "zshard"]:
            (stage / "bin" / name).chmod(0o755)
        (stage / "install.sh").chmod(0o755)
        (stage / "uninstall.sh").chmod(0o755)
        for name in ["zshard", "zdot"]:
            copy(ROOT / "components" / name / "LICENSE", stage / "licenses" / f"{name}.txt")
        (stage / "PLATFORM").write_text(f"linux-{args.arch}\n")
        metadata = {"schema": 1, "suite_version": version, "platform": f"linux-{args.arch}", "source_commits": sources}
        (stage / "BUILD.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
        manifest = []
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                manifest.append(f"{digest(path)}  {path.relative_to(stage).as_posix()}")
        (stage / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n")
        archive = args.output / f"oh-my-ztty-{version}-linux-{args.arch}.tar.gz"
        with archive.open("wb") as out, gzip.GzipFile(fileobj=out, mode="wb", filename="", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tar:
            for path in [stage, *sorted(stage.rglob("*"))]:
                info = tar.gettarinfo(str(path), arcname=str(path.relative_to(stage.parent)))
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                info.mode = 0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644
                if path.is_file():
                    with path.open("rb") as contents:
                        tar.addfile(info, contents)
                else:
                    tar.addfile(info)
        checksum = digest(archive)
        archive.with_name(archive.name + ".sha256").write_text(f"{checksum}  {archive.name}\n")
        print(json.dumps({"archive": str(archive), "sha256": checksum, "bytes": archive.stat().st_size, "sources": sources}, indent=2))

if __name__ == "__main__":
    main()
