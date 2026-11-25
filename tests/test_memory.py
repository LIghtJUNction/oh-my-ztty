"""Exercise the memory launcher without touching the host's system services."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MemoryCommands(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="memory suite ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        shutil.copy2(ROOT / "bin/omztty", self.bin / "omztty")
        (self.bin / "omztty").chmod(0o755)
        (self.root / "VERSION").write_text("0.2.7\n")
        self.record = self.root / "arguments.json"
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        MEMORY_TEST_RECORD=str(self.record))
        self.program("zmem", f"#!{sys.executable}\n"
                     "import json,os,sys\nfrom pathlib import Path\n"
                     "Path(os.environ['MEMORY_TEST_RECORD']).write_text(json.dumps(sys.argv[1:]))\n")
        self.program("id", '#!/bin/sh\nprintf "1000\\n"\n')
        self.program("sudo", f"#!{sys.executable}\n"
                     "import json,os,sys\nfrom pathlib import Path\n"
                     "Path(os.environ['MEMORY_TEST_RECORD']).write_text(json.dumps(sys.argv[1:]))\n")

    def program(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o755)

    def command(self, *args):
        return subprocess.run([str(self.bin / "omztty"), *args], env=self.env,
                              text=True, capture_output=True, timeout=5)

    def test_default_is_unprivileged_status(self):
        result = self.command("memory")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.record.read_text()), ["status"])

    def test_managed_command_preserves_argv(self):
        args = ["run", "--class", "background", "--", "sh", "-c", 'printf "%s" "$value"', "two words"]
        result = self.command("memory", *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.record.read_text()), args)

    def test_setup_escalates_only_the_explicit_installer(self):
        result = self.command("memory", "setup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.record.read_text()),
                         ["--", str(self.bin / "zmem"), "install", "--replace", "--config",
                          str(self.root / "config/zmem/zmem.conf")])

    def test_rollback_uses_the_root_owned_system_copy(self):
        result = self.command("memory", "rollback")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.record.read_text()),
                         ["--", "/usr/local/bin/zmem", "rollback"])

    def test_setup_rejects_extra_arguments_before_escalation(self):
        result = self.command("memory", "setup", "--arbitrary")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.record.exists())

    def test_config_only_update_rejects_system_setup_options(self):
        result = self.command("update", "--config-only", "--memory-manager")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.record.exists())

    def test_doctor_without_systemd_reports_information(self):
        for name in ["ztty", "ssmcp", "zdot", "zfetch", "zmem", "zsh", "git"]:
            self.program(name, '#!/bin/sh\nprintf "fixture 0.1.0\\n"\n')
        self.program("zrun", '#!/bin/sh\n[ "$1" = --native-shell-version ] && echo 1\n')
        self.program("uname", '#!/bin/sh\nprintf "Darwin\\n"\n')
        self.program("systemctl", '#!/bin/sh\nprintf "must not be called" >&2\nexit 99\n')
        shard = self.root / "components/zshard"
        shard.mkdir(parents=True)
        (shard / "zshard.zsh").touch()
        result = self.command("doctor")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("zmem service requires Linux with systemd", result.stdout)
        self.assertNotIn("must not be called", result.stderr)


if __name__ == "__main__":
    unittest.main()
