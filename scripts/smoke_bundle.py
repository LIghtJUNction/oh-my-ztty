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
            result = subprocess.run([str(x) for x in argv], env=env, text=True, capture_output=True, check=True, timeout=45)
            print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="")
            return result.stdout
        install = ["sh", ROOT / "install.sh", "--from", archive]
        run(*install)
        current = home / ".local/share/oh-my-ztty/current"
        first_target = current.resolve()
        first_inode = current.lstat().st_ino
        run(*install)
        assert current.resolve() == first_target and current.lstat().st_ino == first_inode
        cli = home / ".local/bin/omztty"
        run(cli, "doctor")
        run(cli, "shell", "-ic", "print -r -- OMZTTY_SHELL_OK")
        context = json.loads(run(cli, "ai", "context"))
        assert context["schema"] == "zshard.context.v1"
        assert context["history_included"] is False and context["environment_included"] is False
        run(cli, "dot", "--help")
        run(cli, "ssmcp", "--help")
        run(cli, "ztty", "--version")
        run(cli, "uninstall")
        assert not current.parent.exists()
        print("PASS: actual bundle install, repeat, doctor, zsh, local AI context, component commands and uninstall.")

if __name__ == "__main__":
    main()
