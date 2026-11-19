#!/usr/bin/env python3
"""Installer lifecycle tests use inert component fixtures and a temporary HOME."""
from pathlib import Path
import hashlib
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Installation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omztty test ")
        self.work = Path(self.temp.name)
        self.home = self.work / "home with spaces"
        self.home.mkdir()
        self.data = self.home / ".local/share"
        self.bindir = self.home / ".local/bin"
        self.base = self.data / "oh-my-ztty"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("XDG_", "ZSHARD_", "OMZTTY_", "ZDOTDIR"))}
        self.env.update(HOME=str(self.home), XDG_DATA_HOME=str(self.data),
                        XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_CACHE_HOME=str(self.home / ".cache"),
                        XDG_STATE_HOME=str(self.home / ".local/state"))
        (self.home / ".zshrc").write_text("print UNWANTED_USER_RC\n")
        self.archive = self.bundle("0.1.0")

    def tearDown(self):
        self.temp.cleanup()

    def bundle(self, version, warm_exit=0):
        stage = self.work / ("stage-" + version) / "oh-my-ztty"
        stage.mkdir(parents=True)
        for rel in ["install.sh", "uninstall.sh", "bin/omztty", "bin/zshard",
                    "config/zsh/.zshrc", "packaging/oh-my-ztty.svg", "packaging/omztty.1"]:
            out = stage / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, out)
        for rel in ["install.sh", "uninstall.sh", "bin/omztty", "bin/zshard"]:
            (stage / rel).chmod(0o755)
        (stage / "VERSION").write_text(version + "\n")
        (stage / "PLATFORM").write_text("linux-" + os.uname().machine + "\n")
        shard = stage / "components/zshard"
        (shard / "bin").mkdir(parents=True)
        (shard / "zshard.zsh").write_text("typeset -g ZSHARD_TEST=loaded\n")
        (shard / "bin/zshard").write_text(f"#!/bin/sh\nprintf 'zshard fixture\\n'\nexit {warm_exit}\n")
        (shard / "bin/zshard").chmod(0o755)
        for name in ["ztty", "ssmcp", "zdot"]:
            executable = stage / "bin" / name
            executable.write_text(f"#!/bin/sh\nprintf '{name} fixture\\n'\n")
            executable.chmod(0o755)
        lines = [f"{sha(p)}  {p.relative_to(stage)}" for p in sorted(stage.rglob("*")) if p.is_file()]
        (stage / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
        archive = self.work / f"oh-my-ztty-{version}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(stage, arcname="oh-my-ztty")
        archive.with_name(archive.name + ".sha256").write_text(f"{sha(archive)}  {archive.name}\n")
        return archive

    def run_command(self, args, ok=True):
        result = subprocess.run([str(arg) for arg in args], env=self.env, text=True, capture_output=True)
        if ok and result.returncode:
            self.fail(f"{args}: {result.returncode}\n{result.stdout}\n{result.stderr}")
        if not ok:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def install(self, archive=None, ok=True):
        return self.run_command(["sh", ROOT / "install.sh", "--from", archive or self.archive], ok)

    def cli(self, *args, ok=True):
        return self.run_command([self.bindir / "omztty", *args], ok)

    def test_repeat_and_shell_preserve_configuration(self):
        self.bindir.mkdir(parents=True)
        foreign = self.bindir / "ztty"
        foreign.write_text("user-owned")
        self.install()
        current_inode = (self.base / "current").lstat().st_ino
        first = (self.base / "current").resolve()
        self.install()
        self.assertEqual(current_inode, (self.base / "current").lstat().st_ino)
        self.assertEqual(first, (self.base / "current").resolve())
        self.assertEqual(foreign.read_text(), "user-owned")
        result = self.cli("shell", "-ic", "print -r -- $ZSHARD_TEST")
        self.assertIn("loaded", result.stdout)
        self.assertNotIn("UNWANTED_USER_RC", result.stdout)
        self.assertEqual((self.home / ".zshrc").read_text(), "print UNWANTED_USER_RC\n")
        desktop = self.data / "applications/oh-my-ztty.desktop"
        self.assertTrue(desktop.is_symlink())
        if shutil.which("desktop-file-validate"):
            self.run_command(["desktop-file-validate", desktop])

    def test_checksum_failure_is_non_mutating(self):
        self.archive.with_name(self.archive.name + ".sha256").write_text("0" * 64 + "  fixture\n")
        self.install(ok=False)
        self.assertFalse(self.base.exists())
        self.assertFalse(self.bindir.exists())

    def test_upgrade_atomic_pointer_and_uninstall_ownership(self):
        self.install()
        second = self.bundle("0.1.1")
        self.install(second)
        self.assertEqual(os.readlink(self.base / "current"), "releases/0.1.1-linux-" + os.uname().machine)
        self.assertIn("0.1.1", self.cli("version").stdout)
        replacement = self.bindir / "zdot"
        replacement.unlink()
        replacement.write_text("replacement")
        config = self.home / ".config/oh-my-ztty/local.zsh"
        config.parent.mkdir(parents=True)
        config.write_text("user customization")
        history = self.home / ".local/state/oh-my-ztty/history"
        history.parent.mkdir(parents=True)
        history.write_text("user history")
        self.cli("uninstall")
        self.assertFalse(self.base.exists())
        self.assertFalse((self.bindir / "omztty").exists())
        self.assertEqual(replacement.read_text(), "replacement")
        self.assertEqual(config.read_text(), "user customization")
        self.assertEqual(history.read_text(), "user history")
        self.assertFalse((self.data / "applications/oh-my-ztty.desktop").is_symlink())

    def test_failed_cache_warm_preserves_previous_version(self):
        self.install()
        previous = os.readlink(self.base / "current")
        broken = self.bundle("0.1.1", warm_exit=12)
        result = self.install(broken, ok=False)
        self.assertIn("completion cache preparation failed", result.stderr)
        self.assertEqual(os.readlink(self.base / "current"), previous)
        self.assertIn("0.1.0", self.cli("version").stdout)

    def test_modified_release_is_preserved(self):
        self.install()
        binary = self.base / "current/bin/ztty"
        binary.write_text("edited by user")
        self.install(ok=False)
        self.assertEqual(binary.read_text(), "edited by user")

    def test_unowned_root_is_preserved(self):
        self.base.mkdir(parents=True)
        sentinel = self.base / "mine"
        sentinel.write_text("keep")
        self.install(ok=False)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_foreign_launcher_rejected_before_install(self):
        self.bindir.mkdir(parents=True)
        launcher = self.bindir / "omztty"
        launcher.write_text("unrelated")
        self.install(ok=False)
        self.assertFalse(self.base.exists())
        self.assertEqual(launcher.read_text(), "unrelated")

    def test_terminal_uses_suite_socket_and_preserves_arguments(self):
        self.install()
        binary = self.base / "current/bin/ztty"
        binary.write_text('#!/bin/sh\nprintf "%s\\n" "$ZTTY_SOCKET" "$@"\n')
        self.env["ZTTY_SOCKET"] = "@unrelated-running-terminal"
        direct = self.cli("ztty", "--version").stdout.splitlines()
        self.assertEqual(direct[0], f"@oh-my-ztty-{os.getuid()}-0.1.0")
        self.env["OMZTTY_SOCKET"] = "@suite-test-explicit"
        terminal = self.cli("terminal", "--geometry", "100x28").stdout.splitlines()
        self.assertEqual(terminal[0], "@suite-test-explicit")
        self.assertEqual(terminal[1], "--config")
        self.assertEqual(terminal[3:6], ["--geometry", "100x28", "-e"])
        self.assertEqual(terminal[-1], "shell")
        self.assertIn("home with spaces", terminal[-2])

    def test_archive_symlink_rejected(self):
        bad = self.work / "bad.tar.gz"
        with tarfile.open(bad, "w:gz") as tar:
            info = tarfile.TarInfo("oh-my-ztty/bin/escape")
            info.type = tarfile.SYMTYPE
            info.linkname = "/tmp"
            tar.addfile(info)
        bad.with_name(bad.name + ".sha256").write_text(f"{sha(bad)}  {bad.name}\n")
        self.install(bad, ok=False)
        self.assertFalse(self.base.exists())

if __name__ == "__main__":
    unittest.main()
