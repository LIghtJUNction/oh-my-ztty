#!/usr/bin/env python3
"""Audit only published oh-my-ztty assets and its real default network installer."""
from pathlib import Path, PurePosixPath
import argparse, datetime, hashlib, json, os, platform, re, stat, subprocess, sys, tarfile, tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("tag", choices=["v0.1.2"])
parser.add_argument("--source-commit", required=True)
parser.add_argument("--workflow-run", required=True)
args = parser.parse_args()
tag = args.tag
assert re.fullmatch(r"[0-9a-f]{40}", args.source_commit), "full source commit required"
assert re.fullmatch(r"[0-9]+", args.workflow_run), "numeric workflow run required"
version = tag[1:]
expected_zshard_version = "0.1.3"
expected_zshard_commit = "a55c2d08b4299b25ec007b45641df87e8c0d0bbb"
repo = "LIghtJUNction/oh-my-ztty"
base = Path(__file__).resolve().parent / ("oh-my-ztty-public-" + tag)
base.mkdir(exist_ok=True)
report = {
    "schema": "oh-my-ztty.public-verification.v2",
    "tag": tag,
    "release_url": "https://github.com/" + repo + "/releases/tag/" + tag,
    "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "workflow_run": args.workflow_run,
    "expected_source_commit": args.source_commit,
    "expected_zshard": {"version": expected_zshard_version, "commit": expected_zshard_commit},
    "assets": [], "builds": [], "elf": [], "installer": {},
    "desktop_preference": {}, "passed": False,
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def persist():
    temporary = base / "verification.json.tmp"
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(base / "verification.json")

def command(argv,**kwargs):
    return subprocess.run([str(x) for x in argv],check=True,text=True,capture_output=True,timeout=180,**kwargs).stdout

try:
    # Read-only gates run before any public asset download or installation.
    workflow = json.loads(command(["gh", "api", f"repos/{repo}/actions/runs/{args.workflow_run}"]))
    assert workflow["status"] == "completed" and workflow["conclusion"] == "success", "release workflow has not succeeded"
    assert workflow["head_sha"] == args.source_commit, "workflow source commit mismatch"
    assert workflow["path"].split("@")[0] == ".github/workflows/release.yml", "wrong release workflow"
    report["workflow"] = {key: workflow[key] for key in
                          ("id", "html_url", "head_sha", "path", "event", "status", "conclusion", "run_attempt")}
    release = json.loads(command(["gh", "api", f"repos/{repo}/releases/tags/{tag}"]))
    assert not release["draft"] and not release["prerelease"], "release is not publicly final"
    assert release["tag_name"] == tag, "release tag mismatch"
    latest = json.loads(command(["gh", "api", f"repos/{repo}/releases/latest"]))
    assert latest["tag_name"] == tag, "latest release differs; do not exercise update against another release"
    report["latest_release_tag"] = latest["tag_name"]
    report["release_id"] = release["id"]
    report["published_at"] = release["published_at"]
    commit = json.loads(command(["gh", "api", f"repos/{repo}/commits/{tag}"]))
    assert commit["sha"] == args.source_commit, "tag source commit mismatch"
    report["source_commit"] = commit["sha"]
    tree_sha = commit["commit"]["tree"]["sha"]
    tree = json.loads(command(["gh", "api", f"repos/{repo}/git/trees/{tree_sha}?recursive=1"]))
    assert not tree["truncated"], "release tree was truncated"
    expected_sources = {item["path"].split("/", 1)[1]: item["sha"] for item in tree["tree"]
                        if item["mode"] == "160000" and item["path"].startswith("components/")}
    assert set(expected_sources) == {"ztty", "ssmcp", "zdot", "zshard"}, "unexpected component set"
    assert expected_sources["zshard"] == expected_zshard_commit, "release does not pin the expected zshard"
    report["release_gitlinks"] = expected_sources
    assets = {asset["name"]: asset for asset in release["assets"]}
    names=["install.sh","install.sh.sha256"]
    for arch in ("x86_64","aarch64"):
        name=f"oh-my-ztty-{version}-linux-{arch}.tar.gz"
        names.extend([name,name+".sha256"])
    assert set(assets) == set(names), "expected exactly the six published suite assets"
    for name in names:
        meta=assets[name]
        dst=base/name
        command(["curl","--fail","--silent","--show-error","--location","--proto","=https","--tlsv1.2",
                 "--max-time","120",meta["browser_download_url"],"-o",dst])
        digest=sha(dst.read_bytes())
        assert dst.stat().st_size==meta["size"], "asset size mismatch: "+name
        assert meta["digest"]=="sha256:"+digest, "GitHub asset digest mismatch: "+name
        report["assets"].append({"name":name,"bytes":meta["size"],"sha256":digest,"url":meta["browser_download_url"],
                                 "github_digest_verified":True})
        print("Downloaded and verified "+name,flush=True)
    for name in names:
        if name.endswith(".sha256"):
            digest,filename=(base/name).read_text().split()
            assert filename==name[:-7]
            assert digest==sha((base/filename).read_bytes())
    report["checksum_sidecars_verified"]=3
    native_payloads = {}
    for arch in ("x86_64","aarch64"):
        archive=base/f"oh-my-ztty-{version}-linux-{arch}.tar.gz"
        output=base/"elf"/arch
        output.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive) as tf:
            files={}
            for item in tf.getmembers():
                path=PurePosixPath(item.name)
                assert not path.is_absolute() and ".." not in path.parts
                assert path.parts[0]=="oh-my-ztty"
                assert item.isfile() or item.isdir(), "archive contains link or special file"
                if item.isfile():
                    assert item.name not in files, "duplicate archive entry"
                    files[item.name]=item
            manifest=tf.extractfile(files["oh-my-ztty/MANIFEST.sha256"]).read().decode()
            checked=set()
            manifest_hashes = {"oh-my-ztty/MANIFEST.sha256": sha(manifest.encode())}
            for line in manifest.splitlines():
                digest,rel=line.split("  ",1)
                name="oh-my-ztty/"+rel
                assert digest==sha(tf.extractfile(files[name]).read()), "embedded manifest mismatch: "+name
                checked.add(name)
                manifest_hashes[name] = digest
            assert checked==set(files)-{"oh-my-ztty/MANIFEST.sha256"}, "manifest coverage mismatch"
            assert tf.extractfile(files["oh-my-ztty/VERSION"]).read().decode().strip()==version
            assert tf.extractfile(files["oh-my-ztty/PLATFORM"]).read().decode().strip()=="linux-"+arch
            native_payloads[arch] = {
                "files": {
                    str(PurePosixPath(name).relative_to("oh-my-ztty")): {
                        "sha256": manifest_hashes[name], "mode": member.mode & 0o7777,
                    } for name, member in files.items()
                },
                "directories": {
                    str(PurePosixPath(member.name).relative_to("oh-my-ztty")): member.mode & 0o7777
                    for member in tf.getmembers() if member.isdir()
                },
            }
            build_bytes = tf.extractfile(files["oh-my-ztty/BUILD.json"]).read()
            metadata = json.loads(build_bytes)
            assert metadata["schema"] == 1, "unexpected BUILD.json schema"
            assert metadata["suite_version"] == version, "BUILD.json suite version mismatch"
            assert metadata["platform"] == "linux-" + arch, "BUILD.json platform mismatch"
            assert metadata["source_commits"] == expected_sources, "BUILD.json source commits do not match release gitlinks"
            zshard_version = tf.extractfile(files["oh-my-ztty/components/zshard/VERSION"]).read().decode().strip()
            assert zshard_version == expected_zshard_version, "bundled zshard version mismatch"
            assert tf.extractfile(files["oh-my-ztty/install.sh"]).read() == (base / "install.sh").read_bytes(), "bootstrap differs from bundled installer"
            report["builds"].append({
                "arch": arch, "manifest_files_verified": len(checked),
                "build_json_sha256": sha(build_bytes), "metadata": metadata,
                "zshard_version": zshard_version, "source_gitlinks_verified": True,
                "published_installer_matches_bundle": True,
            })
            for executable in ("ztty","ssmcp","zdot"):
                path=output/executable
                path.write_bytes(tf.extractfile(files["oh-my-ztty/bin/"+executable]).read())
                dyn=command(["readelf","-d",path])
                versions=command(["readelf","--version-info",path])
                headers=command(["readelf","-l",path])
                glibc=sorted(set(re.findall(r"Name: GLIBC_([0-9.]+)",versions)),
                             key=lambda s:tuple(map(int,s.split("."))))
                needed=re.findall(r"\(NEEDED\).*?\[([^]]+)\]",dyn)
                interpreter=re.findall(r"Requesting program interpreter: ([^\]]+)",headers)
                item={"arch":arch,"binary":executable,"bytes":path.stat().st_size,"sha256":sha(path.read_bytes()),
                      "minimum_glibc":glibc[-1] if glibc else None,"needed":needed,
                      "other_versions":sorted(set(re.findall(r"Name: ((?:GCC|GLIBCXX|CXXABI)_[^\s]+)",versions))),
                      "interpreter":interpreter[0] if interpreter else None}
                if executable=="zdot":
                    assert not needed and not interpreter and not glibc, "zdot is not static"
                report["elf"].append(item)
        print("Verified embedded manifest and ELF requirements: "+arch,flush=True)
    report["embedded_manifests_verified"]=2
    report["build_metadata_verified"] = 2
    installer = base / "install.sh"
    assert re.search(r"^VERSION=" + re.escape(version) + r"$", installer.read_text(), re.M), "bootstrap default version mismatch"
    native_arch = {"amd64": "x86_64", "arm64": "aarch64"}.get(platform.machine(), platform.machine())
    native_name = f"oh-my-ztty-{version}-linux-{native_arch}.tar.gz"
    native_hash = sha((base / native_name).read_bytes())

    def audit_lifecycle(opt_out):
        key = "desktop_preference" if opt_out else "installer"
        case_report = {
            "used_downloaded_installer": True, "default_network_path": True,
            "version_override": False, "local_archive_override": False,
            "download_url_override": False, "path_mock": False,
            "native_arch": native_arch, "host_glibc": os.confstr("CS_GNU_LIBC_VERSION"),
            "isolated_home_with_spaces": True, "ai_connection_started": False,
            "umask": "0022",
            "passed": False, "steps": [],
        }
        report[key] = case_report
        with tempfile.TemporaryDirectory(prefix=key + "-network-", dir=base) as temp:
            home = Path(temp) / "home with spaces"
            home.mkdir()
            assert home.resolve() != Path.home().resolve(), "refuse actual account HOME"
            runtime = home / ".runtime"
            runtime.mkdir(mode=0o700)
            temporary = home / ".tmp"
            temporary.mkdir()
            env = {
                "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8", "TERM": "dumb", "HOME": str(home),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "XDG_STATE_HOME": str(home / ".local/state"),
                "XDG_RUNTIME_DIR": str(runtime), "TMPDIR": str(temporary),
                "HISTFILE": str(home / ".history"),
                "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            }
            user_rc = home / ".zshrc"
            user_rc.write_text("# public release verification sentinel\n")
            suite_config = home / ".config/oh-my-ztty/local.zsh"
            suite_config.parent.mkdir(parents=True)
            suite_config.write_text("typeset -g OMZTTY_AUDIT_CONFIG=preserved\n")
            configurations = {path: path.read_bytes() for path in (user_rc, suite_config)}
            history_seed = b"public release history sentinel\n"
            history = home / ".local/state/oh-my-ztty/history"
            history.parent.mkdir(parents=True)
            history.write_bytes(history_seed)
            bin_dir = home / ".local/bin"
            bin_dir.mkdir(parents=True)
            foreign_command = bin_dir / "zdot"
            foreign_command.write_text("#!/bin/sh\nexit 23\n")
            foreign_command.chmod(0o755)
            foreign_command_bytes = foreign_command.read_bytes()
            foreign_target = home / "foreign-ztty"
            foreign_target.write_text("#!/bin/sh\nexit 24\n")
            foreign_target.chmod(0o755)
            foreign_link = bin_dir / "ztty"
            foreign_link.symlink_to(foreign_target)
            foreign_target_bytes = foreign_target.read_bytes()
            installbase = home / ".local/share/oh-my-ztty"
            current = installbase / "current"
            desktop = home / ".local/share/applications/oh-my-ztty.desktop"
            cli = bin_dir / "omztty"

            def clean(value):
                return value.replace(str(home), "<ISOLATED_HOME>").replace(str(base), "<DOWNLOAD_CACHE>")

            def run(label, *argv):
                result = subprocess.run([str(value) for value in argv], env=env, cwd=home,
                                        text=True, capture_output=True, timeout=180, umask=0o022)
                case_report["steps"].append({
                    "step": label, "exit_code": result.returncode,
                    "stdout": clean(result.stdout), "stderr": clean(result.stderr),
                })
                persist()
                assert result.returncode == 0, label + " failed: " + clean(result.stderr)
                print("Passed " + key + ": " + label, flush=True)
                return result.stdout

            def check_preserved_inputs():
                assert all(path.read_bytes() == data for path, data in configurations.items()), "user configuration changed"
                assert history.read_bytes() == history_seed, "installer changed existing history"
                assert foreign_command.read_bytes() == foreign_command_bytes and not foreign_command.is_symlink(), "foreign command replaced"
                assert foreign_link.is_symlink() and os.readlink(foreign_link) == str(foreign_target), "foreign command link replaced"
                assert foreign_target.read_bytes() == foreign_target_bytes, "foreign command target changed"

            def verify_installed_payload(target, stage):
                expected = native_payloads[native_arch]
                for relative, archive_mode in expected["directories"].items():
                    info = (target / relative).lstat()
                    assert stat.S_ISDIR(info.st_mode), "installed directory type differs: " + relative
                    assert stat.S_IMODE(info.st_mode) == archive_mode & ~0o022, "installed directory mode differs: " + relative
                for relative, entry in expected["files"].items():
                    installed = target / relative
                    info = installed.lstat()
                    assert stat.S_ISREG(info.st_mode), "installed file type differs: " + relative
                    assert stat.S_IMODE(info.st_mode) == entry["mode"] & ~0o022, "installed file mode differs: " + relative
                    assert sha(installed.read_bytes()) == entry["sha256"], "installed file differs from public manifest: " + relative
                actual_entries = {path.relative_to(target).as_posix() for path in target.rglob("*")}
                expected_entries = set(expected["files"]) | (set(expected["directories"]) - {"."}) | {".archive-sha256"}
                assert actual_entries == expected_entries, "installed release has missing or unexpected entries"
                digest_info = (target / ".archive-sha256").lstat()
                assert stat.S_ISREG(digest_info.st_mode) and stat.S_IMODE(digest_info.st_mode) == 0o644
                case_report.setdefault("installed_manifest_checks", []).append({
                    "stage": stage, "files_verified": len(expected["files"]),
                    "directories_verified": len(expected["directories"]),
                    "file_hashes_verified": True, "file_and_directory_modes_verified": True,
                    "no_unexpected_entries": True,
                })

            def check_installation(enabled, stage):
                target = current.resolve()
                assert target.parent == installbase / "releases", "active release escapes installation"
                verify_installed_payload(target, stage)
                assert (target / ".archive-sha256").read_text().strip() == native_hash, "installed archive differs from public asset"
                assert (target / "VERSION").read_text().strip() == version, "installed suite version mismatch"
                metadata = json.loads((target / "BUILD.json").read_text())
                assert metadata["source_commits"] == expected_sources, "installed source commits mismatch"
                assert (target / "components/zshard/VERSION").read_text().strip() == expected_zshard_version
                assert (installbase / ".desktop-enabled").read_text() == ("1\n" if enabled else "0\n")
                if enabled:
                    assert desktop.is_symlink() and os.readlink(desktop) == str(installbase / "oh-my-ztty.desktop")
                    assert (installbase / ".desktop-path").read_text().strip() == str(desktop)
                else:
                    assert not desktop.exists() and not desktop.is_symlink(), "disabled desktop entry remains"
                    assert not (installbase / ".desktop-path").exists(), "disabled entry still has a path record"
                check_preserved_inputs()

            # Real public URLs: no --from, --version, URL overrides, or PATH mocks.
            if opt_out:
                run("network_install_no_desktop", "sh", installer, "--no-desktop")
            else:
                run("network_install_first", "sh", installer)
            check_installation(not opt_out, "first_install")
            original_target = current.resolve()
            original_inode = current.lstat().st_ino
            run("network_install_second_without_options", "sh", installer)
            check_installation(not opt_out, "repeat_install")
            assert current.resolve() == original_target and current.lstat().st_ino == original_inode
            case_report["repeated_install_same_current_inode"] = True
            if opt_out:
                case_report["first_install_disabled"] = True
                case_report["default_repeat_preserves_disabled"] = True
                run("network_update_enable_desktop", cli, "update", "--desktop")
                check_installation(True, "update_desktop_on")
                case_report["explicit_update_enables_desktop"] = True
                assert current.resolve() == original_target and current.lstat().st_ino == original_inode
                run("network_update_disable_desktop", cli, "update", "--no-desktop")
                check_installation(False, "update_desktop_off")
                case_report["explicit_update_disables_desktop"] = True
                assert current.resolve() == original_target and current.lstat().st_ino == original_inode
                case_report["same_release_inode_stable_through_preference_updates"] = True
            else:
                run("doctor", cli, "doctor")
                shell_output = run("interactive_shell", cli, "shell", "-ic",
                                   'print -r -- OMZTTY_PUBLIC_SHELL_OK "$OMZTTY_AUDIT_CONFIG"')
                assert "OMZTTY_PUBLIC_SHELL_OK preserved" in shell_output, "suite customization was not loaded"
                context = json.loads(run("ai_local_context", cli, "ai", "context"))
                assert context["schema"] == "zshard.context.v1"
                assert context["history_included"] is False and context["environment_included"] is False
            case_report["network_archive_sha256_matches_public_asset"] = True
            case_report["installed_build_sources_verified"] = True
            case_report["existing_history_preserved_by_installer"] = True
            history_files = {path: path.read_bytes() for path in (home / ".local/state").rglob("*") if path.is_file()}
            assert history in history_files, "history preservation fixture missing"
            foreign_desktop_bytes = b"[Desktop Entry]\nName=User-owned sentinel\nType=Application\nExec=true\n"
            if opt_out:
                desktop.parent.mkdir(parents=True, exist_ok=True)
                desktop.write_bytes(foreign_desktop_bytes)
            run("uninstall", cli, "uninstall")
            assert not installbase.exists(), "suite installation remains"
            for name in ("omztty", "ssmcp", "zshard"):
                path = bin_dir / name
                assert not path.exists() and not path.is_symlink(), "managed command remains: " + name
            manpage = home / ".local/share/man/man1/omztty.1"
            assert not manpage.exists() and not manpage.is_symlink(), "managed manual link remains"
            if opt_out:
                assert desktop.read_bytes() == foreign_desktop_bytes and not desktop.is_symlink(), "foreign desktop file changed"
                case_report["foreign_desktop_preserved_after_uninstall"] = True
            else:
                assert not desktop.exists() and not desktop.is_symlink(), "managed desktop link remains"
            assert all(path.read_bytes() == data for path, data in configurations.items())
            assert all(path.read_bytes() == data for path, data in history_files.items())
            assert foreign_command.read_bytes() == foreign_command_bytes and not foreign_command.is_symlink()
            assert foreign_link.is_symlink() and os.readlink(foreign_link) == str(foreign_target)
            assert foreign_target.read_bytes() == foreign_target_bytes
            case_report.update(
                user_config_preserved=True,
                state_files_preserved_after_uninstall=len(history_files),
                managed_files_removed=True,
                foreign_command_file_preserved=True,
                foreign_command_link_preserved=True,
                passed=True,
            )
            persist()

    audit_lifecycle(False)
    audit_lifecycle(True)
    report["completed_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report["passed"]=True
    persist()
    print(json.dumps({"passed":True,"report":str(base/"verification.json"),"tag":tag,
                      "source_commit":report["source_commit"],"assets":len(report["assets"])}),flush=True)
except Exception as exc:
    report["error"]=str(exc)
    persist()
    raise
