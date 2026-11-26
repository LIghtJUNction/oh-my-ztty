#!/usr/bin/env python3
"""Build a Linux release from synchronized default-branch sources."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

from managed_build import background_command

ROOT = Path(__file__).resolve().parents[1]
ARCHES = {"x86_64": 62, "aarch64": 183}
COMPONENTS = ("ztty", "ssmcp", "zshard", "zdot", "zrc", "zfetch", "zmem")
BINARIES = ("ssmcp", "zdot", "zfetch", "zmem")

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

def verify_sources(lock):
    if not isinstance(lock, dict) or lock.get("schema") != 2:
        raise RuntimeError("Run workspace.py sync to create the default-branch source lock")
    components = lock.get("components")
    if not isinstance(components, dict) or set(components) != set(COMPONENTS):
        raise RuntimeError("The source lock must contain all seven suite components")
    if not isinstance(lock.get("updated_at"), str) or not lock["updated_at"]:
        raise RuntimeError("The source lock has no synchronization time")
    sources = {}
    for name in COMPONENTS:
        spec = components[name]
        repository = f"https://github.com/LIghtJUNction/{name}.git"
        if (not isinstance(spec, dict) or spec.get("repository") != repository
                or not isinstance(spec.get("branch"), str) or not spec["branch"]
                or not isinstance(spec.get("commit"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", spec.get("commit", ""))):
            raise RuntimeError(f"Invalid default-branch source lock for {name}")
        source = ROOT / "components" / name
        head = run(["git", "rev-parse", "HEAD"], cwd=source)
        if head != spec["commit"]:
            raise RuntimeError(f"{name} source HEAD does not match dependencies.lock.json; run workspace.py sync")
        submodules = run(["git", "submodule", "status", "--recursive"], cwd=source)
        if any(line.startswith(("-", "+", "U")) for line in submodules.splitlines()):
            raise RuntimeError(f"{name} source tree has unresolved submodule commits; "
                               "run git submodule update --init --recursive")
        repositories = [source]
        while repositories:
            repository_path = repositories.pop()
            dirty = run(["git", "status", "--porcelain", "--untracked-files=all",
                         "--ignore-submodules=none"], cwd=repository_path)
            if dirty:
                location = repository_path.relative_to(ROOT)
                raise RuntimeError(f"{name} source tree has uncommitted changes in {location}")
            # Nested ignore settings can hide leaf changes from the component.
            # Inspect each repository directly, using NUL-delimited Git paths.
            entries = run(["git", "ls-files", "--stage", "-z"], cwd=repository_path)
            repositories.extend(repository_path / entry.split("\t", 1)[1]
                                for entry in entries.split("\0")
                                if entry.startswith("160000 "))
        sources[name] = head
    return sources

def build_component(name, arch):
    source = ROOT / "components" / name
    manifest = source / "Cargo.toml"
    command = ["cargo", "build", "--locked", "--release", "--bin", name,
               "--manifest-path", str(manifest),
               "--message-format=json-render-diagnostics"]
    if platform.machine() != arch:
        command.extend(["--target", f"{arch}-unknown-linux-gnu"])
    if name == "ztty":
        command.extend(["--features", "wayland"])
    # Cargo owns output placement, including the user's shared target directory.
    result = subprocess.run(background_command(command), cwd=source, check=True, text=True,
                            stdout=subprocess.PIPE)
    executables = set()
    for line in result.stdout.splitlines():
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Cargo returned invalid build metadata for {name}") from error
        target = message.get("target", {})
        if (message.get("reason") == "compiler-artifact"
                and target.get("name") == name and "bin" in target.get("kind", [])
                and message.get("executable")
                and Path(message.get("manifest_path", "")).resolve() == manifest.resolve()):
            executables.add(Path(message["executable"]))
    if len(executables) != 1:
        raise RuntimeError(f"Cargo did not report exactly one {name} executable")
    executable = executables.pop()
    if not executable.is_absolute():
        executable = source / executable
    check_elf(executable, arch)
    return executable

def check_elf(path, arch):
    with path.open("rb") as stream:
        header = stream.read(20)
    if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != ARCHES[arch]:
        raise RuntimeError(f"wrong executable architecture: {path}")

def tracked_component(name, destination):
    source = ROOT / "components" / name
    entries = subprocess.check_output(["git", "ls-files", "-z"], cwd=source).decode().split("\0")
    for entry in entries:
        if entry and not entry.startswith((".github/", "tests/", "scripts/")):
            copy(source / entry, destination / entry)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog=
        "Builds use an available verified zmem >=0.2 background class; "
        "set ZMEM_BUILD_BACKGROUND=0 to keep the caller's classification.")
    parser.add_argument("--arch", choices=ARCHES, default=platform.machine())
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args(argv)
    version = (ROOT / "VERSION").read_text().strip()
    lock_path = ROOT / "dependencies.lock.json"
    original_lock = lock_path.read_bytes()
    lock = json.loads(original_lock)
    sources = verify_sources(lock)
    args.output.mkdir(parents=True, exist_ok=True)
    (ROOT / ".cache").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bundle-", dir=ROOT / ".cache") as temp:
        stage = Path(temp) / "oh-my-ztty"
        stage.mkdir()
        for path in ["install.sh", "uninstall.sh", "LICENSE", "VERSION", "dependencies.lock.json", "bin/omztty", "bin/omztty-config", "bin/omztty-manage", "bin/omztty-setup", "bin/omztty-sync", "bin/omztty-completion", "bin/zshard"]:
            copy(ROOT / path, stage / path)
        for folder in ["config", "packaging"]:
            for source in sorted((ROOT / folder).rglob("*")):
                if source.is_file():
                    copy(source, stage / source.relative_to(ROOT))
        tracked_component("zshard", stage / "components/zshard")
        tracked_component("zrc", stage / "components/zrc")
        for name in BINARIES:
            # Copy each artifact immediately: another build may reuse Cargo's
            # shared output path while the remaining components compile.
            copy(build_component(name, args.arch), stage / "bin" / name)
            binary = stage / "bin" / name
            binary.chmod(0o755)
            check_elf(binary, args.arch)
        copy(ROOT / "components/ssmcp/src/code_mode.js", stage / "bin/code-mode.js")
        for name in ["omztty", "omztty-config", "omztty-manage", "omztty-setup", "omztty-sync", "omztty-completion", "zshard"]:
            (stage / "bin" / name).chmod(0o755)
        (stage / "install.sh").chmod(0o755)
        (stage / "uninstall.sh").chmod(0o755)
        for name in COMPONENTS:
            copy(ROOT / "components" / name / "LICENSE", stage / "licenses" / f"{name}.txt")
        if lock_path.read_bytes() != original_lock:
            raise RuntimeError("dependencies.lock.json changed during the build")
        verify_sources(lock)
        (stage / "PLATFORM").write_text(f"linux-{args.arch}\n")
        metadata = {"schema": 2, "suite_version": version, "platform": f"linux-{args.arch}",
                    "source_commits": sources, "sources_updated_at": lock["updated_at"],
                    "source_branches": {name: lock["components"][name]["branch"]
                                        for name in COMPONENTS}}
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
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print("bundle: " + str(error), file=sys.stderr)
        raise SystemExit(1)
