"""A synchronized profile keeps canonical destinations across XDG layouts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConfigPortability(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omztty portable ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.suite = self.base / "suite"
        for relative in ("bin/omztty", "bin/omztty-config", "config/home/.zshrc", "VERSION"):
            destination = self.suite / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        (self.suite / "config/ztty").mkdir(parents=True)
        (self.suite / "config/ztty/config").write_text("font_size = 12\n")
        defaults = self.suite / "components/zrc/profiles/ink"
        (defaults / "files/.config/nvim").mkdir(parents=True)
        (defaults / "files/.config/nvim/init.lua").write_text("-- fixture\n")
        (defaults / "profile.zdot").write_text("files/.config/nvim\t.config/nvim\n")
        zdot = self.suite / "bin/zdot"
        zdot.write_text(f"#!{sys.executable}\n" +
                        "import json,pathlib,sys\nargs=sys.argv[1:]\n"
                        "root=pathlib.Path(args[args.index('--root')+1])\n"
                        "manifest=args[args.index('--profile')+1]\n"
                        "print(json.dumps({'args':args,'manifest':(root/manifest).read_text()}))\n")
        zdot.chmod(0o755)
        self.home = self.base / "first home"
        self.home.mkdir()
        self.config = self.home / "custom/config"
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin",
                    "XDG_CONFIG_HOME": str(self.config), "XDG_STATE_HOME": str(self.home / "state")}

    def cli(self, *args):
        result = subprocess.run(["sh", str(self.suite / "bin/omztty"), "config", *args],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_new_profile_is_portable_and_resolves_local_targets(self):
        self.cli("init")
        profile = self.config / "oh-my-ztty/profile"
        canonical = (profile / "profile.zdot").read_bytes()
        self.assertIn(b"files/.config/nvim\t.config/nvim", canonical)
        self.assertEqual((profile / ".config-layout").read_text(), "canonical-v1\n")
        plan = json.loads(self.cli("plan", "--json").stdout)
        self.assertIn("files/.config/nvim\tcustom/config/nvim", plan["manifest"])
        self.assertIn("files/.config/ztty\tcustom/config/ztty", plan["manifest"])
        self.assertEqual((profile / "profile.zdot").read_bytes(), canonical)
        for action in ("status", "apply", "remove"):
            result = json.loads(self.cli(action).stdout)
            self.assertEqual(result["args"][result["args"].index("--profile") + 1], ".omztty-target.zdot")

    def test_cloned_profile_uses_second_machine_xdg_without_git_diff(self):
        self.cli("init")
        original = self.config / "oh-my-ztty/profile"
        second_home = self.base / "second home"
        second_home.mkdir()
        second_config = second_home / "settings"
        restored = second_config / "oh-my-ztty/profile"
        shutil.copytree(original, restored)
        canonical = (restored / "profile.zdot").read_bytes()
        self.env.update(HOME=str(second_home), XDG_CONFIG_HOME=str(second_config),
                        XDG_STATE_HOME=str(second_home / "state"))
        result = json.loads(self.cli("plan").stdout)
        self.assertIn("files/.config/nvim\tsettings/nvim", result["manifest"])
        self.assertNotIn("custom/config", result["manifest"])
        self.assertEqual((restored / "profile.zdot").read_bytes(), canonical)

    def test_legacy_profile_keeps_existing_manifest_and_journal_namespace(self):
        self.cli("init")
        profile = self.config / "oh-my-ztty/profile"
        (profile / ".config-layout").unlink()
        manifest = profile / "profile.zdot"
        manifest.write_text("files/.config/nvim\tcustom/config/nvim\n")
        result = json.loads(self.cli("plan").stdout)
        self.assertEqual(result["args"][result["args"].index("--profile") + 1], "profile.zdot")
        self.assertEqual(result["manifest"], manifest.read_text())


if __name__ == "__main__":
    unittest.main()
