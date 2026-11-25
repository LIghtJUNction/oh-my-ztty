#!/usr/bin/env python3
"""Exercise a real release archive in a temporary home, with no AI connection."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--zrun", type=Path, help="Also verify default mode with this native zrun executable")
    args = parser.parse_args()
    archive = args.archive.resolve()
    with tempfile.TemporaryDirectory(prefix="oh-my-ztty real smoke ") as temp:
        home = Path(temp) / "home with spaces"
        home.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("XDG_", "ZSHARD_", "OMZTTY_", "ZDOTDIR"))}
        env.update(HOME=str(home), XDG_DATA_HOME=str(home / ".local/share"),
                   XDG_CONFIG_HOME=str(home / ".config"), XDG_CACHE_HOME=str(home / ".cache"),
                   XDG_STATE_HOME=str(home / ".local/state"))
        def run(*argv):
            result = subprocess.run([str(x) for x in argv], env=env, text=True, capture_output=True, timeout=45)
            print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="")
            result.check_returncode()
            return result.stdout
        # A bundle smoke runs in a temporary HOME and must not install a host service.
        install = ["sh", ROOT / "install.sh", "--from", archive, "--no-memory-manager"]
        run(*install)
        current = home / ".local/share/oh-my-ztty/current"
        first_target = current.resolve()
        first_inode = current.lstat().st_ino
        run(*install)
        assert current.resolve() == first_target and current.lstat().st_ino == first_inode
        cli = home / ".local/bin/omztty"
        if args.zrun:
            env["OMZTTY_ZRUN"] = str(args.zrun.resolve(strict=True))
            run(cli, "doctor")
            assert "native-ready" in run(cli, "shell", "-c", "async t -- printf native-ready; await t")
        else:
            env["OMZTTY_SHELL"] = "zsh"
            run(cli, "doctor")
        run(cli, "shell", "--zsh", "-ic", "print -r -- OMZTTY_SHELL_OK")
        context = json.loads(run(cli, "ai", "context"))
        assert context["schema"] == "zshard.context.v1"
        assert context["history_included"] is False and context["environment_included"] is False
        run(cli, "dot", "--help")
        run(cli, "ssmcp", "--help")
        run(cli, "ztty", "--version")
        run(cli, "memory", "--version")
        memory = json.loads(run(cli, "memory", "status", "--json"))
        assert isinstance(memory, dict) and memory.get("schema")
        info = json.loads(run(cli, "info", "--json"))
        assert info["schema"] == "zfetch.system.v1"
        boot_stages = ["firmware", "bootloader", "kernel", "initramfs", "system_manager",
                       "system_target", "login", "user_session", "desktop"]
        for command in [("info", "--boot", "--json"),
                        ("zfetch", "--boot", "--format=json")]:
            boot = json.loads(run(cli, *command))
            assert boot["schema"] == "zfetch.boot.v1"
            assert boot["ordering"] == "structural"
            assert [stage["stage"] for stage in boot["stages"]] == boot_stages
            assert all(stage["status"] in {"observed", "configured", "unavailable"}
                       for stage in boot["stages"])
        # Exercise adoption with the actual no_std binary, including conflict recovery.
        original = "print -r -- ORIGINAL_SHELL_CONFIG\\n"
        (home / ".zshrc").write_text(original)
        run(cli, "config", "init")
        profile = home / ".config/oh-my-ztty/profile"
        manifest = (profile / "profile.zdot").read_bytes()
        run(cli, "config", "init")
        assert (profile / "profile.zdot").read_bytes() == manifest
        run(cli, "config", "plan", "--json")
        rejected = subprocess.run([str(cli), "config", "apply"], env=env,
                                  text=True, capture_output=True, timeout=20)
        assert rejected.returncode != 0
        assert (home / ".zshrc").read_text() == original
        run(cli, "config", "apply", "--backup")
        assert (home / ".zshrc").is_symlink()
        assert not (home / ".zdot-state").exists() and not (home / ".zdot.lock").exists()
        run(cli, "config", "apply", "--backup")
        run("zsh", "-d", "-i", "-c", '[[ -n $ZSHARD_VERSION ]] && print DIRECT_SHELL_OK')
        run(cli, "config", "status")
        marker = profile / ".omztty-profile"
        marker.write_text("damaged")
        rejected = subprocess.run([str(cli), "uninstall"], env=env,
                                  text=True, capture_output=True, timeout=20)
        assert rejected.returncode != 0 and current.exists()
        assert (home / ".zshrc").is_symlink()
        marker.write_text("omztty-profile-v1" + chr(10))
        run(cli, "config", "remove")
        assert not (home / ".zshrc").is_symlink()
        assert (home / ".zshrc").read_text() == original
        env["XDG_CONFIG_HOME"] = str(home / "custom-config")
        run(cli, "config", "init")
        run(cli, "config", "apply", "--backup")
        assert (home / "custom-config/nvim").is_symlink()
        assert (home / "custom-config/ztty").is_symlink()
        assert not (home / ".config/nvim").exists()
        run("zsh", "-d", "-i", "-c", '[[ -n $ZSHARD_VERSION ]]')
        run(cli, "config", "remove")
        env["XDG_CONFIG_HOME"] = str(home / ".config")
        run(cli, "config", "apply", "--backup")
        run(cli, "uninstall")
        assert not current.parent.exists()
        assert not (home / ".zshrc").is_symlink()
        assert (home / ".zshrc").read_text() == original
        print("PASS: actual bundle install, repeat, doctor, zsh, local AI context, component commands, boot-chain entrypoints, zdot adoption/restore and uninstall.")

if __name__ == "__main__":
    main()
