#!/usr/bin/env python3
"""Exercise the suite AI bridge with real zshard and an inert local provider."""
from pathlib import Path
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AIBridge(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omztty ai ")
        self.work = Path(self.temp.name)
        self.home = self.work / "home with spaces"
        self.home.mkdir()
        self.runtime = self.work / "suite runtime"
        for rel in ("bin/omztty", "bin/zshard", "VERSION", "config/zsh/.zshrc", "config/zsh/completion-paths.zsh", "config/zsh/ink.zsh"):
            target = self.runtime / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
        shutil.copytree(
            ROOT / "components/zshard",
            self.runtime / "components/zshard",
            ignore=shutil.ignore_patterns(".git", ".github", "tests", "docs"),
        )
        self.cwd = self.work / "working directory"
        self.cwd.mkdir()
        self.env = {
            k: v for k, v in os.environ.items()
            if not k.startswith(("XDG_", "ZSHARD_", "OMZTTY_", "ZDOTDIR"))
        }
        self.env.update(
            HOME=str(self.home),
            XDG_CONFIG_HOME=str(self.home / ".config"),
            XDG_CACHE_HOME=str(self.home / ".cache"),
            XDG_STATE_HOME=str(self.home / ".local/state"),
        )
        self.provider = self.work / "provider with spaces"
        self.provider.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "print(json.dumps({'argv': sys.argv[1:], 'stdin': sys.stdin.read(), 'cwd': os.getcwd()}))\n"
        )
        self.provider.chmod(0o755)
        ssmcp = self.runtime / "bin/ssmcp"
        ssmcp.write_text("#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n")
        ssmcp.chmod(0o755)
        self.sentinel = self.work / "MUST_NOT_EXECUTE"
        self.provider_args = [
            "argument with spaces",
            "$(touch " + shlex.quote(str(self.sentinel)) + ")",
            "literal 'quote' and ; semicolon",
            "--flag=value with spaces",
        ]
        config = self.home / ".config/oh-my-ztty/local.zsh"
        config.parent.mkdir(parents=True)
        config.write_text(
            'print -r -- loaded > "$HOME/local-loaded"\n'
            "typeset -ga ZSHARD_AI_COMMAND=("
            + " ".join(shlex.quote(arg) for arg in [str(self.provider), *self.provider_args])
            + ")\n"
        )
        (self.home / ".zshrc").write_text("print USER_RC_MUST_NOT_LOAD\n")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args):
        result = subprocess.run(
            [str(self.runtime / "bin/omztty"), *args],
            env=self.env, cwd=self.cwd, text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_ask_loads_configured_array_and_preserves_request(self):
        request = "Explain $(touch " + shlex.quote(str(self.sentinel)) + ")\n"
        request += "and `touch " + shlex.quote(str(self.sentinel)) + "`; keep 'quotes' and \\slashes"
        result = json.loads(self.run_cli("ai", "ask", request, "final argument with spaces"))
        self.assertEqual(result["argv"], self.provider_args)
        self.assertEqual(result["cwd"], str(self.cwd))
        context_line, forwarded_request = result["stdin"].split("\n", 1)
        context = json.loads(context_line)
        self.assertEqual(context["schema"], "zshard.context.v1")
        self.assertEqual(context["cwd"], str(self.cwd))
        self.assertFalse(context["history_included"])
        self.assertFalse(context["environment_included"])
        self.assertEqual(forwarded_request, request + " final argument with spaces\n")
        self.assertEqual((self.home / "local-loaded").read_text(), "loaded\n")
        self.assertFalse(self.sentinel.exists())

    def test_context_and_connect_do_not_load_user_customization(self):
        context = json.loads(self.run_cli("ai", "context"))
        self.assertEqual(context["schema"], "zshard.context.v1")
        self.assertEqual(context["cwd"], str(self.cwd))
        self.assertFalse(context["history_included"])
        self.assertFalse(context["environment_included"])
        self.assertFalse((self.home / "local-loaded").exists())
        self.assertEqual(
            json.loads(self.run_cli("ai", "connect", "--help", "literal ; $(not-executed)")),
            ["--help", "literal ; $(not-executed)"],
        )
        self.assertFalse((self.home / "local-loaded").exists())


if __name__ == "__main__":
    unittest.main()
