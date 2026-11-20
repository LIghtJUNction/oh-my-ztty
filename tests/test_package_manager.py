"""Exercise packaged lifecycle guards and shell runtime discovery."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackagedInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="packaged suite ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.package = self.runtime(self.base / "usr/lib/oh-my-ztty", "package")
        self.commands = self.base / "usr/bin"
        self.commands.mkdir(parents=True)
        (self.commands / "omztty").symlink_to(self.package / "bin/omztty")
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("OMZTTY_", "ZSHARD_", "XDG_", "ZDOTDIR"))}
        self.env.update(HOME=str(self.home),
                        XDG_DATA_HOME=str(self.home / ".local/share"),
                        PATH=str(self.commands) + os.pathsep + self.env["PATH"])
        sentinel = self.base / "unexpected-action"
        self.sentinel = sentinel
        for name in ("curl", "uninstall.sh"):
            target = self.commands / name if name == "curl" else self.package / name
            target.write_text("#!/bin/sh\ntouch \"$ACTION_SENTINEL\"\nexit 99\n")
            target.chmod(0o755)
        self.env["ACTION_SENTINEL"] = str(sentinel)

    def runtime(self, path, marker):
        (path / "bin").mkdir(parents=True)
        shutil.copy2(ROOT / "bin/omztty", path / "bin/omztty")
        (path / "VERSION").write_text("0.2.2\n")
        (path / "PACKAGE_MANAGER").write_text("pacman\n")
        (path / "config/zsh").mkdir(parents=True)
        (path / "config/zsh/.zshrc").write_text(f"typeset -g BOOT_MARKER={marker}\n")
        return path

    def test_packaged_update_and_uninstall_do_not_mutate_files(self):
        for command, hint in (("update", "yay -Syu oh-my-ztty-bin"),
                              ("uninstall", "sudo pacman -Rns oh-my-ztty-bin")):
            with self.subTest(command=command):
                result = subprocess.run([str(self.commands / "omztty"), command],
                                        env=self.env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn(hint, result.stderr)
                self.assertFalse(self.sentinel.exists())
                self.assertTrue((self.package / "VERSION").is_file())

    def boot(self):
        result = subprocess.run(
            ["zsh", "-dfc", 'source "$1"; print -r -- "$OMZTTY_ROOT"; print -r -- "$BOOT_MARKER"',
             "probe", str(ROOT / "config/home/.zshrc")],
            env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.splitlines()

    def test_system_only_profile_finds_runtime_from_command_symlink(self):
        self.assertEqual(self.boot(), [str(self.package), "package"])

    def test_per_user_runtime_keeps_precedence(self):
        user = self.runtime(self.home / ".local/share/oh-my-ztty/current", "user")
        self.assertEqual(self.boot(), [str(user), "user"])

    def test_explicit_runtime_is_preserved(self):
        explicit = self.runtime(self.base / "explicit runtime", "explicit")
        self.env["OMZTTY_ROOT"] = str(explicit)
        self.assertEqual(self.boot(), [str(explicit), "explicit"])


if __name__ == "__main__":
    unittest.main()
