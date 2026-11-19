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
        ztty = self.runtime / "bin/ztty"
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
            PATH=str(fake_bin) + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin"),
            XDG_CONFIG_HOME=str(self.home / ".config"),
            XDG_CACHE_HOME=str(self.home / ".cache"),
            XDG_STATE_HOME=str(self.home / ".local/state"),
        )
        self.prefix = ["--config", str(self.runtime / "config/ztty/config")]
        self.default = ["-e", str(self.runtime / "bin/omztty"), "shell"]
        self.sentinel = self.work / "MUST_NOT_EXECUTE"

    def tearDown(self):
        self.temp.cleanup()

    def forwarded(self, *args):
        result = subprocess.run(
            [str(self.runtime / "bin/omztty"), "terminal", *args],
            env=self.env, cwd=self.work, text=True, capture_output=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_option_only_invocations_keep_the_preset_shell(self):
        cases = [
            [],
            ["--observe"],
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
            args = ["--name", "command session", boundary, *payload]
            with self.subTest(boundary=boundary):
                self.assertEqual(self.forwarded(*args), self.prefix + args)
                self.assertFalse(self.sentinel.exists())

    def test_marker_shaped_option_values_are_not_commands(self):
        options = ("--name", "--cwd", "--font", "--config",
                   "--tab", "--split-right", "--split-down")
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
                "--scrollback", "--tab", "--split-right", "--split-down",
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
