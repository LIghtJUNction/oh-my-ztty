"""Exercise explicit refresh, fingerprint changes and last-good publication."""
from pathlib import Path
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELP = """ssmcp — fixture
Usage: ssmcp [options]
       ssmcp automation [options]
  --name NAME          Display name
  --server URL         Relay
  --input MODE         Input
  --agent NAME         Recipient
  --worker N           Slots
  --context NAME       Context
  --no-browser         No browser
  --no-color           No color
  --future-option TEXT New local option
"""


@unittest.skipUnless(shutil.which("zsh"), "requires the real zsh syntax checker")
class CompletionManager(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="completion manager 中文 ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.root = self.work / "suite"
        self.home = self.work / "home"
        self.home.mkdir()
        (self.root / "bin").mkdir(parents=True)
        shutil.copy2(ROOT / "bin/omztty-completion", self.root / "bin/omztty-completion")
        shutil.copytree(ROOT / "packaging/completions", self.root / "packaging/completions")
        self.calls = self.work / "calls"
        self.binary = self.root / "bin/ssmcp"
        self.write_binary()
        self.env = {"PATH": str(self.root / "bin") + ":/usr/bin:/bin", "HOME": str(self.home),
                    "XDG_CACHE_HOME": str(self.home / "cache"),
                    "XDG_CONFIG_HOME": str(self.home / "config")}
        self.state = self.home / "cache/oh-my-ztty/completions/suite"

    def write_binary(self, version="0.10.26", help_text=HELP, fail=None):
        # An owned non-model fixture; its log verifies which exact probes ran.
        temporary = self.binary.with_suffix(".new")
        temporary.write_text(
            "#!/usr/bin/python3\nimport sys\nfrom pathlib import Path\n"
            f"with Path({str(self.calls)!r}).open('a') as f: f.write(sys.argv[1] + '\\n')\n"
            f"if sys.argv[1] == {fail!r}: raise SystemExit(17)\n"
            f"print('ssmcp {version}' if sys.argv[1] == '--version' else {help_text!r})\n")
        temporary.chmod(0o755)
        temporary.replace(self.binary)

    def run_manager(self, *args, success=True):
        result = subprocess.run([sys.executable, "-I", str(self.root / "bin/omztty-completion"),
                                 *args], env=self.env, capture_output=True, text=True, timeout=15)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def current(self):
        return (self.state / "current").read_text().strip()

    def refresh(self):
        return json.loads(self.run_manager("refresh", "ssmcp", "--json").stdout)

    def test_list_check_are_passive_and_refresh_is_explicit(self):
        listed = json.loads(self.run_manager("list", "ssmcp", "--json").stdout)
        self.assertEqual(listed["entries"][0]["state"], "not-refreshed")
        self.run_manager("check", "ssmcp", success=False)
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.state.exists())
        refreshed = self.refresh()
        self.assertEqual(self.calls.read_text().splitlines(), ["--version", "--help", "--help-full"])
        self.assertEqual(refreshed["entries"][0]["observed_version"], "ssmcp 0.10.26")
        self.assertEqual(refreshed["entries"][0]["state"], "current")
        self.run_manager("check", "ssmcp")
        same = self.refresh()
        self.assertFalse(same["refresh"]["changed"])
        self.assertEqual(len(self.calls.read_text().splitlines()), 3)

    def test_atomic_executable_upgrade_detected_and_new_flags_published(self):
        first = self.refresh()
        previous = self.current()
        old_file = Path(first["active_directory"]) / "_ssmcp"
        old_bytes = old_file.read_bytes()
        self.write_binary("0.10.27", HELP.replace("--future-option", "--new-version-option"))
        stale = json.loads(self.run_manager("check", "ssmcp", "--json", success=False).stdout)
        self.assertEqual(stale["entries"][0]["state"], "stale-binary")
        self.assertEqual(len(self.calls.read_text().splitlines()), 3, "check executed the application")
        current = self.refresh()
        self.assertNotEqual(self.current(), previous)
        self.assertIn("--new-version-option[", (Path(current["active_directory"]) / "_ssmcp").read_text())
        self.assertEqual(old_file.read_bytes(), old_bytes, "old shells lost their immutable completion")

    def test_failed_help_and_bad_source_preserve_last_good_generation(self):
        first = self.refresh()
        pointer = (self.state / "current").read_bytes()
        original = (Path(first["active_directory"]) / "_ssmcp").read_bytes()
        self.write_binary("0.10.27", fail="--help-full")
        result = self.run_manager("refresh", "ssmcp", success=False)
        self.assertIn("exited 17", result.stderr)
        self.assertEqual((self.state / "current").read_bytes(), pointer)
        self.assertEqual((Path(first["active_directory"]) / "_ssmcp").read_bytes(), original)
        self.write_binary("0.10.27")
        (self.root / "packaging/completions/_omztty").write_text("#compdef omztty\nif (\n")
        self.run_manager("refresh", "ssmcp", success=False)
        self.assertEqual((self.state / "current").read_bytes(), pointer)
        self.assertEqual(list(self.state.glob(".stage-*")), [])

    def test_same_name_source_edit_changes_generation_and_preserves_personal(self):
        personal = self.home / "config/oh-my-ztty/completions/_my_ssmcp"
        personal.parent.mkdir(parents=True)
        personal.write_text("#compdef ssmcp\ncompadd -- personal\n")
        first = self.refresh()
        before = self.current()
        source = self.root / "packaging/completions/_ssmcp"
        source.write_text(source.read_text() + "\n# reviewed source update\n")
        stale = json.loads(self.run_manager("check", "ssmcp", "--json", success=False).stdout)
        self.assertEqual(stale["entries"][0]["state"], "stale-source")
        after = self.refresh()
        self.assertNotEqual(before, self.current())
        self.assertEqual(after["entries"][0]["personal_override"], str(personal))
        self.assertEqual(personal.read_text(), "#compdef ssmcp\ncompadd -- personal\n")
        self.assertTrue(Path(first["active_directory"]).is_dir())

    def test_no_code_evaluation_from_help_and_unrecognized_help_rejected(self):
        sentinel = self.work / "should-not-exist"
        malicious = HELP + f"\n  --quoted-option TEXT  $(touch {sentinel}) '`rm -rf /`'\n"
        self.write_binary(help_text=malicious)
        result = self.refresh()
        generated = (Path(result["active_directory"]) / "_ssmcp").read_text()
        self.assertNotIn("touch", generated)
        self.assertNotIn("rm -rf", generated)
        self.assertFalse(sentinel.exists())
        pointer = self.current()
        self.write_binary(help_text="unrelated program\n")
        self.run_manager("refresh", "ssmcp", success=False)
        self.assertEqual(self.current(), pointer)

    def test_changed_managed_file_and_symlink_state_are_not_overwritten(self):
        first = self.refresh()
        path = Path(first["active_directory"]) / "_ssmcp"
        path.write_text("#compdef ssmcp\ncompadd -- manual\n")
        pointer = self.current()
        self.run_manager("refresh", "ssmcp", success=False)
        self.assertEqual(self.current(), pointer)
        self.assertEqual(path.read_text(), "#compdef ssmcp\ncompadd -- manual\n")
        self.env["XDG_CACHE_HOME"] = str(self.home / "symlink-cache")
        Path(self.env["XDG_CACHE_HOME"]).symlink_to(self.home / "cache", target_is_directory=True)
        self.run_manager("refresh", "ssmcp", success=False)
        self.assertEqual(self.current(), pointer)

    def test_concurrent_refresh_refused_and_unknown_command_never_executed(self):
        self.refresh()
        pointer = self.current()
        with (self.state / ".lock").open("r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_manager("refresh", "ssmcp", success=False)
            self.assertIn("another completion refresh", result.stderr)
        self.assertEqual(self.current(), pointer)
        count = self.calls.read_text()
        self.run_manager("refresh", "unknown-generator", success=False)
        self.run_manager("list", "ssmcp", "--binary", str(self.binary), success=False)
        self.assertEqual(self.calls.read_text(), count)


if __name__ == "__main__":
    unittest.main()
