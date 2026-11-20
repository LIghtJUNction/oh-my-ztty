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
        for name in ("ztty", "ssmcp", "zdot", "zfetch", "codex", "claude", "gemini",
                     "opencode", "pi", "amp", "go", "npx", "yarn", "rustc", "node", "cmake"):
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
            "omztty dot --root . sync pul": "omztty dot --root . sync pull",
            "omztty dot --root . plan --b": "omztty dot --root . plan --backup",
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

    def test_native_component_commands(self):
        self.start()
        self.cases({
            "ztty --back": "ztty --backend",
            "ztty --backend way": "ztty --backend wayland",
            "ztty --name -e --back": "ztty --name -e --backend",
            "ztty -e git checko": "ztty -e git checkout",
            "ztty -- git checkout feature/补": "ztty -- git checkout feature/补全",
            "ztty shell-integration zs": "ztty shell-integration zsh",
            "ztty mcp --http-response ss": "ztty mcp --http-response sse",
            "zdot --ro": "zdot --root",
            "zdot --root . sync pul": "zdot --root . sync pull",
            "zdot plan --b": "zdot plan --backup",
            "zfetch --no": "zfetch --no-color",
            "ztty --cwd file": "ztty --cwd file",
            "omztty terminal --cwd file": "omztty terminal --cwd file",
            "zdot --root file": "zdot --root file",
            "zdot apply --target file": "zdot apply --target file",
            "omztty dot apply --state-dir file": "omztty dot apply --state-dir file",
        })

    def test_ssmcp_commands_and_option_arity(self):
        self.start()
        self.cases({
            "ssmcp sess": "ssmcp sessions",
            "ssmcp inv": "ssmcp invite",
            "ssmcp invite --shell pow": "ssmcp invite --shell powershell",
            "ssmcp joi": "ssmcp join",
            "ssmcp loc": "ssmcp loc",
            "ssmcp --account-co": "ssmcp --account-co",
            "ssmcp config set git-fetch": "ssmcp config set git-fetch",
            "ssmcp 007 upg": "ssmcp 007 upg",
            "ssmcp sessions create fixture --the": "ssmcp sessions create fixture --theme",
            "ssmcp sessions create fixture --json --the":
                "ssmcp sessions create fixture --json --theme",
            "ssmcp --th": "ssmcp --theme",
            "ssmcp --theme nor": "ssmcp --theme nord",
            "ssmcp --log-format pretty-v": "ssmcp --log-format pretty-verbose",
            "ssmcp --name sessions --th": "ssmcp --name sessions --theme",
            "ssmcp --title -e --th": "ssmcp --title -e --theme",
            "ssmcp --server https://example.invalid list --ter":
                "ssmcp --server https://example.invalid list --terminal",
            "ssmcp config se": "ssmcp config set",
            "ssmcp config set ser": "ssmcp config set server",
            "ssmcp trust add --pub": "ssmcp trust add --public-key",
            "ssmcp setup bro": "ssmcp setup browser",
            "ssmcp setup browser --play": "ssmcp setup browser --playwright-mcp",
            "ssmcp ui prev": "ssmcp ui preview",
            "ssmcp ui preview --theme min": "ssmcp ui preview --theme minimal",
            "ssmcp sessions lo": "ssmcp sessions logs",
            "ssmcp sessions --json lo": "ssmcp sessions --json logs",
            "ssmcp sessions logs fixture --li": "ssmcp sessions logs fixture --lines",
            "ssmcp attach --read": "ssmcp attach --read-only",
            "ssmcp service inst": "ssmcp service install",
            "ssmcp service install --state": "ssmcp service install --state-dir",
            "ssmcp 007 sessions rest": "ssmcp 007 sessions restart",
            "ssmcp update --ch": "ssmcp update --check",
        })
        self.assertEqual(self.report()[2], "yes")

    def test_ssmcp_files_directories_and_free_text(self):
        self.start()
        for line, expected in [
            ("ssmcp --context-root direc", "directory with spaces 中文/"),
            ("ssmcp --ui-config file", "file with spaces 中文.txt"),
            ("ssmcp trust add --public-key file", "file with spaces 中文.txt"),
            ("ssmcp setup browser --playwright-mcp file", "file with spaces 中文.txt"),
            ("ssmcp sessions create fixture --cwd direc", "directory with spaces 中文/"),
            ("ssmcp service install --state-dir direc", "directory with spaces 中文/"),
        ]:
            with self.subTest(line=line):
                self.assertEqual(self.complete(line)[-1], expected)
        self.cases({
            "ssmcp --context-root file": "ssmcp --context-root file",
            "ssmcp --name file": "ssmcp --name file",
            "ssmcp --server file": "ssmcp --server file",
            "ssmcp sessions logs file": "ssmcp sessions logs file",
        })

    def test_ssmcp_through_suite_and_ai_entrypoints(self):
        self.start()
        for prefix in ("omztty ssmcp", "omztty ai connect", "zai connect",
                       "zshard ai connect", "omztty zshard ai connect"):
            with self.subTest(prefix=prefix):
                self.assertEqual(self.complete(prefix + " --theme nor"),
                                 shlex.split(prefix + " --theme nord"))
                self.assertEqual(self.complete(prefix + " sessions lo"),
                                 shlex.split(prefix + " sessions logs"))

    def test_framework_nested_arguments(self):
        plugins = Path(self.env["XDG_DATA_HOME"]) / "zshard/plugins"
        plugins.mkdir(parents=True)
        (plugins / "local-fixture.lock").write_text("completion only; never evaluated\n")
        self.start()
        self.cases({
            "zshard plugin ver": "zshard plugin verify",
            "zshard plugin rest": "zshard plugin restore",
            "zshard plugin remove local-fi": "zshard plugin remove local-fixture",
            "zshard use local-fi": "zshard use local-fixture",
            "zshard cache wa": "zshard cache warm",
            "zshard hook precm": "zshard hook precmd",
            "zshard ai conn": "zshard ai connect",
            "omztty zshard plugin ver": "omztty zshard plugin verify",
            "zai conn": "zai connect",
            "zai ask file": "zai ask file",
            "zshard ai ask file": "zshard ai ask file",
            "zshard plugin export file": "zshard plugin export file",
            "zshard completions file": "zshard completions file",
            "zshard cache warm file": "zshard cache warm file",
            "omztty zshard completions file": "omztty zshard completions file",
        })
        for line, expected in [
            ("zshard plugin restore file", "file with spaces 中文.txt"),
            ("zshard completions direc", "directory with spaces 中文/"),
            ("zshard cache warm direc", "directory with spaces 中文/"),
        ]:
            with self.subTest(line=line):
                self.assertEqual(self.complete(line)[-1], expected)


    def test_native_codex_claude_and_gemini(self):
        self.start()
        self.cases({
            "codex exec --sand": "codex exec --sandbox=",
            "codex exec --sandbox work": "codex exec --sandbox workspace-write",
            "codex --model mcp --cd direc":
                "codex --model mcp --cd 'directory with spaces 中文/'",
            "codex exec check file": "codex exec check file",
            "claude mcp add demo --transport ht": "claude mcp add demo --transport http",
            "claude --output-format str": "claude --output-format stream-json",
            "claude --add-dir . direc": "claude --add-dir . 'directory with spaces 中文/'",
            "claude -p file": "claude -p file",
            "gemini extensions up": "gemini extensions update",
            "gemini --output-format str": "gemini --output-format stream-json",
            "gemini extensions link direc": "gemini extensions link 'directory with spaces 中文/'",
            "gemini -p file": "gemini -p file",
            "codex exec --cd file": "codex exec --cd file",
            "claude --add-dir file": "claude --add-dir file",
            "gemini --include-directories file": "gemini --include-directories file",
        })

    def test_native_opencode_pi_and_amp(self):
        self.start()
        self.cases({
            "opencode auth logi": "opencode auth login",
            "opencode session list --format j": "opencode session list --format json",
            "opencode --server https://example.invalid run --format j":
                "opencode --server https://example.invalid run --format json",
            "opencode session import --directory direc":
                "opencode session import --directory 'directory with spaces 中文/'",
            "pi --thinking x": "pi --thinking xhigh",
            "pi auth print-bear": "pi auth print-bearer-token",
            "pi mcp add demo --oauth-client-registration c":
                "pi mcp add demo --oauth-client-registration cimd",
            "pi @file": "pi '@file with spaces 中文.txt'",
            "amp t li": "amp t list",
            "amp plugins add --target w": "amp plugins add --target workspace",
            "amp config model-providers add-github":
                "amp config model-providers add-github-copilot-subscription",
            "amp runner dirs add direc": "amp runner dirs add 'directory with spaces 中文/'",
            "opencode session import --directory file": "opencode session import --directory file",
            "pi --session-dir file": "pi --session-dir file",
            "amp runner dirs add file": "amp runner dirs add file",
        })
        for command in ("opencode", "pi", "amp"):
            self.assertEqual(self.complete(command + " mcp add demo -- git checko"),
                             [command, "mcp", "add", "demo", "--", "git", "checkout"])

    def test_native_developer_options_and_boundaries(self):
        self.start()
        self.cases({
            "go mod ti": "go mod tidy",
            "npx fixture --offl": "npx fixture --offl",
            "yarn cache cl": "yarn cache clean",
            "yarn --cwd . cache cl": "yarn --cwd . cache clean",
            "rustc -C panic=ab": "rustc -C panic=abort",
            "node --input-type mod": "node --input-type module",
            "node fixture.js --wat": "node fixture.js --wat",
            "cmake --build . --config Deb": "cmake --build . --config Debug",
        })

    def test_native_developer_paths_and_quoting(self):
        (self.project / "directory with spaces 中文/nested.go").write_text("package fixture\n")
        self.start()
        self.cases({
            'go -C "directory with spaces 中文" build nest':
                'go -C "directory with spaces 中文" build nested.go',
            "npx --cache direc": "npx --cache 'directory with spaces 中文/'",
            "rustc -L native=direc": "rustc -L 'native=directory with spaces 中文/'",
            "cmake --install . --prefix direc":
                "cmake --install . --prefix 'directory with spaces 中文/'",
            "npx --cache file": "npx --cache file",
            "cmake --install . --prefix file": "cmake --install . --prefix file",
        })

    def test_personal_ai_and_developer_completion_priority(self):
        for name in ("codex", "go"):
            (self.personal / ("_" + name)).write_text(
                f"#compdef {name}\ncompadd -- personal-{name}\n")
        self.start()
        self.cases({"codex personal": "codex personal-codex", "go personal": "go personal-go"})


    def personal_component_completions(self):
        for name in ("zshard", "zai", "ssmcp"):
            (self.personal / ("_" + name)).write_text(
                f"#compdef {name}\ncompadd -- personal-{name}\n")
        self.start()
        self.cases({
            "zshard personal": "zshard personal-zshard",
            "zai personal": "zai personal-zai",
            "ssmcp personal": "ssmcp personal-ssmcp",
            "omztty zshard personal": "omztty zshard personal-zshard",
            "omztty ssmcp personal": "omztty ssmcp personal-ssmcp",
            "omztty ai connect personal": "omztty ai connect personal-ssmcp",
        })

    def test_personal_component_completion_priority(self):
        self.personal_component_completions()

    def test_eager_personal_component_completion_priority(self):
        self.env["ZSHARD_COMPLETION"] = "eager"
        self.personal_component_completions()


if __name__ == "__main__":
    unittest.main(verbosity=2)
