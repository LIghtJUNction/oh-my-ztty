#!/usr/bin/env python3
"""Check terminal forwarding with an inert ztty and a temporary bundle."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TerminalExec(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omztty terminal ")
        self.work = Path(self.temp.name)
        self.home = self.work / "home with spaces"
        self.home.mkdir()
        self.runtime = self.work / "suite runtime"
        (self.runtime / "bin").mkdir(parents=True)
        shutil.copy2(ROOT / "bin/omztty", self.runtime / "bin/omztty")
        (self.runtime / "VERSION").write_text("test-version\n")
        (self.runtime / "config/ztty").mkdir(parents=True)
        (self.runtime / "config/ztty/config").write_text("# inert fixture\n")
        ztty = self.work / "system-ztty"
        ztty.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "print(json.dumps(sys.argv[1:]))\n"
        )
        ztty.chmod(0o755)
        fake_bin = self.work / "fake bin"
        fake_bin.mkdir()
        zsh = fake_bin / "zsh"
        zsh.write_text("#!/bin/sh\nexit 99\n")
        zsh.chmod(0o755)
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("XDG_", "ZSHARD_", "OMZTTY_", "ZDOTDIR", "ZTTY_"))
        }
        self.env.update(
            HOME=str(self.home),
            OMZTTY_ZTTY=str(ztty),
            PATH=str(fake_bin) + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin"),
            XDG_CONFIG_HOME=str(self.home / ".config"),
            XDG_CACHE_HOME=str(self.home / ".cache"),
            XDG_STATE_HOME=str(self.home / ".local/state"),
        )
        self.prefix = ["--config", str(self.runtime / "config/ztty/config")]
        self.native = self.home / ".local/bin/zrun"
        self.native.parent.mkdir(parents=True)
        self.make_native(self.native)
        self.default = ["-e", str(self.native)]
        self.sentinel = self.work / "MUST_NOT_EXECUTE"

    @staticmethod
    def make_native(path):
        path.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "if sys.argv[1:] == ['--native-shell-version']: print('1')\n"
            "else: print(json.dumps([sys.argv[0], sys.argv[1:], os.getenv('ZDOTDIR')]))\n"
        )
        path.chmod(0o755)

    def test_shell_uses_native_executable_preserves_argv_and_user_environment(self):
        self.env["ZDOTDIR"] = "/original shell setting"
        args = ["-c", "literal; input", "two words", ""]
        result = subprocess.run([str(self.runtime / "bin/omztty"), "shell", *args], env=self.env,
                                text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), [str(self.native), args, "/original shell setting"])
        self.assertFalse((self.home / ".local/state/oh-my-ztty").exists())

    def test_legacy_zrun_is_skipped_even_when_it_precedes_native_zrun_in_path(self):
        self.native.write_text("#!/bin/sh\nprintf 'usage: enter the configured shell\\n'\n")
        another = self.work / "other directory"
        another.mkdir()
        self.make_native(another / "zrun")
        self.env["PATH"] = os.pathsep.join([str(self.native.parent), str(another), self.env["PATH"]])
        self.assertEqual(self.forwarded(), self.prefix + ["-e", str(another / "zrun")])

    def test_first_native_revision_supports_help_capability_fallback(self):
        self.native.write_text("#!/bin/sh\n[ \"$1\" = --help ] && echo '  zrun     Enter the native Linux terminal shell'\n")
        self.assertEqual(self.forwarded(), self.prefix + self.default)

    def test_explicit_compatibility_uses_preset_only_on_request(self):
        self.env["OMZTTY_ZRUN"] = "/not-installed"
        self.assertEqual(self.forwarded("--zsh", "--geometry", "80x24"), self.prefix + [
            "--geometry", "80x24", "-e", str(self.runtime / "bin/omztty"), "shell", "--zsh"])
        self.env["OMZTTY_SHELL"] = "zsh"
        self.assertEqual(self.forwarded(), self.prefix + [
            "-e", str(self.runtime / "bin/omztty"), "shell", "--zsh"])
        self.assertEqual(self.forwarded("-e", "/bin/true"), self.prefix + ["-e", "/bin/true"])

    def test_bad_explicit_zrun_fails_before_opening_terminal_and_leaves_command_passthrough(self):
        self.env["OMZTTY_ZRUN"] = "relative path"
        for mode in ("shell", "terminal"):
            p = subprocess.run([str(self.runtime / "bin/omztty"), mode], env=self.env,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 126)
            self.assertIn("OMZTTY_ZRUN", p.stderr)
        self.assertEqual(self.forwarded("-e", "/bin/true"), self.prefix + ["-e", "/bin/true"])

    def test_missing_native_shell_is_actionable_and_explicit_commands_still_run(self):
        self.native.unlink()
        only = self.work / "minimal path"
        only.mkdir()
        for name in ("readlink", "id", "python3"):
            (only / name).symlink_to(shutil.which(name))
        self.env["PATH"] = str(only)
        for mode in ("shell", "terminal"):
            result = subprocess.run([str(self.runtime / "bin/omztty"), mode], env=self.env,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 127, result.stderr)
            self.assertIn("omztty shell --zsh", result.stderr)
        self.assertEqual(self.forwarded("-e", "/bin/true"), self.prefix + ["-e", "/bin/true"])

    def test_explicit_absolute_native_binary_takes_precedence(self):
        selected = self.work / "selected executable"
        self.make_native(selected)
        self.env["OMZTTY_ZRUN"] = str(selected)
        self.assertEqual(self.forwarded(), self.prefix + ["-e", str(selected)])

    def tearDown(self):
        self.temp.cleanup()

    def forwarded(self, *args):
        result = subprocess.run(
            [str(self.runtime / "bin/omztty"), "terminal", *args],
            env=self.env, cwd=self.work, text=True, capture_output=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_option_only_invocations_open_the_native_shell(self):
        cases = [
            [],
            ["--observe"],
            ["--backend", "x11"],
            ["--backend", "wayland", "--text-plugin", "one=/absolute/plugin one.so",
             "--text-plugin", "two=/absolute/plugin-two.so"],
            ["--name", "named session", "--cwd", "directory with spaces",
             "--font", "monospace:size=12", "--geometry", "80x24",
             "--scrollback", "0", "--config", "custom appearance", "--tab", "target"],
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.forwarded(*args), self.prefix + args + self.default)

    def test_explicit_command_preserves_every_argument_without_a_shell_suffix(self):
        payload = [
            "/usr/bin/printf", "", "argument with spaces", "line one\nline two",
            "'quotes' and ; semicolon", f"$(touch '{self.sentinel}')",
            "-e", "--name", "--",
        ]
        for boundary in ("-e", "--"):
            args = ["--backend", "wayland", "--text-plugin", "one=/absolute/plugin one.so",
                    "--name", "command session", boundary, *payload]
            with self.subTest(boundary=boundary):
                self.assertEqual(self.forwarded(*args), self.prefix + args)
                self.assertFalse(self.sentinel.exists())

    def test_marker_shaped_option_values_are_not_commands(self):
        options = ("--name", "--cwd", "--font", "--config",
                   "--tab", "--split-right", "--split-down", "--backend", "--text-plugin")
        for option in options:
            for value in ("-e", "--"):
                args = [option, value]
                with self.subTest(option=option, value=value):
                    self.assertEqual(self.forwarded(*args), self.prefix + args + self.default)

    def test_real_command_boundary_after_a_marker_shaped_value(self):
        for boundary in ("-e", "--"):
            args = ["--name", "-e", "--font", "--", boundary, "program", "-e", ""]
            with self.subTest(boundary=boundary):
                self.assertEqual(self.forwarded(*args), self.prefix + args)

    def test_incomplete_or_unknown_native_arguments_are_not_filled_in(self):
        cases = [
            ["-e"], ["--"], ["--unknown", "value"], ["unmarked-command", "argument"],
            *[[option] for option in (
                "--config", "--name", "--cwd", "--font", "--geometry",
                "--scrollback", "--tab", "--split-right", "--split-down", "--backend", "--text-plugin",
            )],
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.forwarded(*args), self.prefix + args)

    def test_help_and_version_reach_ztty_without_a_default_command(self):
        for flag in ("--help", "-h", "--version", "-V"):
            with self.subTest(flag=flag):
                self.assertEqual(self.forwarded(flag), self.prefix + [flag])


if __name__ == "__main__":
    unittest.main(verbosity=2)
