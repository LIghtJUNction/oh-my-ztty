#!/usr/bin/env python3
"""Exercise actual lazy Tab completion in a private zsh PTY; never run applications."""
from pathlib import Path
import fcntl
import os
import pty
import select
import shlex
import shutil
import struct
import subprocess
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
ZSHARD = Path(os.environ.get("OMZTTY_COMPLETION_ZSHARD", str(ROOT / "components/zshard")))
ZSH = shutil.which("zsh")


@unittest.skipUnless(ZSH and shutil.which("git") and (ZSHARD / "zshard.zsh").is_file(),
                     "requires zsh, git and the initialized zshard submodule")
class InteractiveCompletion(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omztty completion ")
        self.work = Path(self.temp.name)
        self.home, self.runtime, self.project = (self.work / name for name in ("home", "suite", "project"))
        self.home.mkdir()
        self.project.mkdir()
        shutil.copytree(ROOT / "config/zsh", self.runtime / "config/zsh")
        shutil.copytree(ROOT / "packaging/completions", self.runtime / "packaging/completions")
        shutil.copytree(ZSHARD, self.runtime / "components/zshard",
                        ignore=shutil.ignore_patterns(".git", ".github", "tests", "scripts", "docs"))
        (self.runtime / "bin").mkdir()
        shutil.copy2(ROOT / "bin/omztty", self.runtime / "bin/omztty")
        for name in ("ztty", "ssmcp", "zdot", "zfetch"):
            path = self.runtime / "bin" / name
            path.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> "$PROBE_EXECUTED"\nexit 99\n')
            path.chmod(0o755)
        self.personal = self.home / "config/oh-my-ztty/completions"
        self.personal.mkdir(parents=True)
        (self.project / "file with spaces 中文.txt").write_text("fixture\n")
        (self.project / "directory with spaces 中文").mkdir()
        (self.project / "plugin with spaces 中文.so").write_text("inert fixture\n")
        self.env = {
            "PATH": "/usr/bin:/bin", "HOME": str(self.home), "ZDOTDIR": str(self.home),
            "TERM": "xterm-256color", "LC_ALL": "C.UTF-8",
            "XDG_CONFIG_HOME": str(self.home / "config"), "XDG_DATA_HOME": str(self.home / "data"),
            "XDG_CACHE_HOME": str(self.home / "cache"), "XDG_STATE_HOME": str(self.home / "state"),
            "OMZTTY_ROOT": str(self.runtime), "ZSHARD_HOME": str(self.runtime / "components/zshard"),
            "ZSHARD_CACHE_DIR": str(self.home / "cache/oh-my-ztty/zshard/suite"),
            "ZSHARD_PROMPT": "off", "ZSHARD_SUGGESTIONS": "0", "ZSHARD_HIGHLIGHT": "0",
            "HISTFILE": "/dev/null", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "PROBE_REPORT": str(self.work / "report"), "PROBE_EXECUTED": str(self.work / "executed"),
        }
        for args in [
            ["init", "-q", "--initial-branch=main"],
            ["-c", "user.name=Completion fixture", "-c", "user.email=fixture@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "fixture"],
            ["branch", "feature/补全"],
        ]:
            subprocess.run(["git", *args], cwd=self.project, env=self.env, check=True)
        self.process = self.master = None
        (self.home / ".zshrc").write_text(
            'OMZTTY_TEST_CACHE_REUSED=no\nsource "$OMZTTY_ROOT/config/zsh/.zshrc" || return\n'
            "PROMPT='__OMZTTY_READY__ '\n"
            '_omztty_probe_report() {\n'
            '  print -rl -- "$BUFFER" "$_ZSHARD_COMPLETION_READY" "$OMZTTY_TEST_CACHE_REUSED" > "$PROBE_REPORT"\n'
            "  zle -I; print -r -- '__OMZTTY_REPORT__'\n}\n"
            "_omztty_probe_reset() { BUFFER=''; CURSOR=0; zle redisplay; }\n"
            "zle -N _omztty_probe_report\nzle -N _omztty_probe_reset\n"
            "bindkey '^[[25~' _omztty_probe_report\nbindkey '^[[26~' _omztty_probe_reset\n"
        )

    def tearDown(self):
        if self.process is not None:
            if self.process.poll() is None:
                try:
                    os.write(self.master, b"\x1b[26~exit\n")
                    self.process.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    self.process.kill()
                    self.process.wait(timeout=2)
            os.close(self.master)
        self.temp.cleanup()

    def read_until(self, marker):
        output, deadline = b"", time.monotonic() + 10
        while marker not in output:
            ready, _, _ = select.select([self.master], [], [], max(0, deadline - time.monotonic()))
            self.assertTrue(ready, "PTY response timed out: " + repr(output[-2000:]))
            try:
                block = os.read(self.master, 65536)
            except OSError:
                self.fail("zsh closed the PTY: " + repr(output[-2000:]))
            self.assertTrue(block, "zsh exited: " + repr(output[-2000:]))
            output += block
        return output

    def start(self):
        # Use the installer's cache preparation, then observe its reuse on first Tab.
        result = subprocess.run(
            [ZSH, "-d", "-f", "-i", "-c",
             'source "$OMZTTY_ROOT/config/zsh/completion-paths.zsh" && '
             'source "$ZSHARD_HOME/zshard.zsh" && zshard complete'],
            cwd=self.project, env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        dump = next(Path(self.env["ZSHARD_CACHE_DIR"]).glob("zcompdump-*"))
        with dump.open("a") as stream:
            stream.write("\ntypeset -g OMZTTY_TEST_CACHE_REUSED=yes\n")
        dump.chmod(0o600)
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 100, 0, 0))
        self.process = subprocess.Popen([ZSH, "-d", "-i"], cwd=self.project, env=self.env,
                                        stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        os.close(slave)
        self.read_until(b"__OMZTTY_READY__")

    def report(self, line=None):
        data = b"\x1b[25~" if line is None else b"\x1b[26~" + line.encode() + b"\t\x1b[25~"
        os.write(self.master, data)
        self.read_until(b"__OMZTTY_REPORT__")
        return Path(self.env["PROBE_REPORT"]).read_text().splitlines()

    def complete(self, line):
        result = self.report(line)
        self.assertEqual(result[1], "1", "Tab did not initialize real completion")
        self.assertFalse(Path(self.env["PROBE_EXECUTED"]).exists(), "completion ran a bundled application")
        return shlex.split(result[0])

    def cases(self, examples):
        for line, expected in examples.items():
            with self.subTest(line=line):
                self.assertEqual(self.complete(line), shlex.split(expected))

    def test_first_tab_cache_and_config_actions(self):
        self.start()
        self.assertEqual(self.report()[1:], ["0", "no"])
        self.assertEqual(self.complete("omztty conf"), ["omztty", "config"])
        self.assertEqual(self.report()[2], "yes", "first Tab did not reuse the audited cache")
        self.cases({
            "omztty config refr": "omztty config refresh",
            "omztty config sync pul": "omztty config sync pull",
            "omztty config sync pus": "omztty config sync push",
            "omztty config plan --j": "omztty config plan --json",
            "omztty config apply --b": "omztty config apply --backup",
            "omztty config status --j": "omztty config status --j",
            "omztty config refresh --b": "omztty config refresh --b",
            "omztty update --no": "omztty update --no-desktop",
        })

    def test_terminal_options_and_command_boundaries(self):
        self.start()
        self.cases({
            "omztty terminal --back": "omztty terminal --backend",
            "omztty terminal --backend way": "omztty terminal --backend wayland",
            "omztty terminal --name -e --back": "omztty terminal --name -e --backend",
            "omztty terminal --text-pl": "omztty terminal --text-plugin",
            "omztty terminal -e git checko": "omztty terminal -e git checkout",
            "omztty terminal -- git checko": "omztty terminal -- git checkout",
            "omztty ztty shell-integration zs": "omztty ztty shell-integration zsh",
            "omztty ztty plugin ch": "omztty ztty plugin check",
        })

    def test_paths_keep_spaces_and_unicode(self):
        self.start()
        plugin = "demo=" + str(self.project / "plugin")
        for line, expected in [
            ("omztty terminal --config file", "file with spaces 中文.txt"),
            ("omztty terminal --cwd direc", "directory with spaces 中文/"),
            ("omztty terminal --text-plugin " + shlex.quote(plugin),
             "demo=" + str(self.project / "plugin with spaces 中文.so")),
            ("omztty dot apply --root direc", "directory with spaces 中文/"),
        ]:
            with self.subTest(line=line):
                self.assertEqual(self.complete(line)[-1], expected)

    def test_git_and_delegated_commands(self):
        self.start()
        self.cases({
            "git checko": "git checkout",
            "git checkout feature/补": "git checkout feature/补全",
            "omztty terminal -e git checkout feature/补": "omztty terminal -e git checkout feature/补全",
            "omztty ai conn": "omztty ai connect",
            "omztty dot sy": "omztty dot sync",
            "omztty dot sync --root . pul": "omztty dot sync --root . pull",
            "omztty info --no": "omztty info --no-color",
        })

    def test_personal_completion_priority(self):
        (self.personal / "_omztty").write_text("#compdef omztty\ncompadd -- personal-completion\n")
        self.start()
        self.assertEqual(self.complete("omztty personal"), ["omztty", "personal-completion"])

    def test_delegate_receives_shifted_words(self):
        (self.personal / "_ztty").write_text(
            "#compdef ztty\n"
            '[[ $words[1] == ztty && $CURRENT == 2 ]] && compadd -- personal-backend\n')
        self.start()
        self.assertEqual(self.complete("omztty ztty personal"), ["omztty", "ztty", "personal-backend"])
        self.assertEqual(self.complete("omztty terminal personal"), ["omztty", "terminal", "personal-backend"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
