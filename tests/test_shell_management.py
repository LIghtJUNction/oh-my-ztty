"""Exercise real zsh management, startup and recovery in disposable homes."""
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ZSH = shutil.which("zsh")


@unittest.skipUnless(ZSH, "requires zsh")
class ShellManagement(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omztty shell ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.home = self.work / "home with spaces"
        self.home.mkdir()
        self.config = self.home / "config/oh-my-ztty"
        self.profile = self.config / "profile"
        self.profile.mkdir(parents=True)
        (self.profile / ".omztty-profile").write_text("omztty-profile-v1\n")
        self.shared = self.profile / "shell"
        self.local = self.config / "local"
        self.state = self.home / "state/oh-my-ztty"
        self.env = {
            "PATH": "/usr/bin:/bin", "HOME": str(self.home), "LC_ALL": "C.UTF-8",
            "OMZTTY_ROOT": str(ROOT), "XDG_CONFIG_HOME": str(self.home / "config"),
            "XDG_STATE_HOME": str(self.home / "state"),
            "XDG_DATA_HOME": str(self.home / "data"),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
        }

    def cli(self, *args, ok=True, extra=None):
        env = self.env | (extra or {})
        result = subprocess.run(["sh", str(ROOT / "bin/omztty"), *args],
                                env=env, capture_output=True, text=True, timeout=10)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def shell(self, script, ok=True, extra=None):
        result = subprocess.run([ZSH, "-dfc", script], env=self.env | (extra or {}),
                                capture_output=True, text=True, timeout=10)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    @property
    def load(self):
        return 'source "$OMZTTY_ROOT/config/zsh/settings.zsh"'

    def backups(self, target=None):
        records = sorted((self.state / "backups").glob("*"), key=lambda p: p.stat().st_mtime_ns)
        return [p for p in records if target is None or (p / "target").read_text() == str(target)]

    def git(self, *args, ok=True):
        result = subprocess.run(["git", "-C", str(self.profile), *args], env=self.env,
                                capture_output=True, text=True, timeout=10)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def enable_git(self):
        self.cli("rc", "init")
        self.git("init", "-q", "--initial-branch=main")
        self.git("config", "user.name", "Shell test")
        self.git("config", "user.email", "shell@example.invalid")
        self.git("add", "--", ".omztty-profile", "shell")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "Initial profile")

    def test_git_mode_records_shared_changes_without_file_backups(self):
        self.enable_git()
        self.cli("env", "set", "OMZTEST_VALUE", "first", "--shared")
        self.cli("env", "set", "OMZTEST_VALUE", "second", "--shared")
        self.assertIn("OMZTEST_VALUE\tfirst", self.git("show", "HEAD~1:shell/env.tsv").stdout)
        self.assertIn("OMZTEST_VALUE\tsecond", self.git("show", "HEAD:shell/env.tsv").stdout)
        self.assertFalse((self.state / "backups").exists())
        self.assertIn("Git manages versions", self.cli("rc", "backups").stdout)
        self.assertIn("sync restore", self.cli("rc", "restore", "old-id", ok=False).stderr)

    def test_git_mode_keeps_local_values_and_home_rc_outside_git(self):
        self.enable_git()
        head = self.git("rev-parse", "HEAD").stdout
        self.cli("env", "set", "OMZTEST_TOKEN", "private-local-value")
        self.cli("rc", "install")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)
        self.assertNotIn("private-local-value", self.git("show", "HEAD").stdout)
        self.assertFalse((self.state / "backups").exists())

    def test_git_mode_preserves_manual_version_and_unrelated_index(self):
        self.enable_git()
        self.cli("env", "set", "OMZTEST_VALUE", "first", "--shared")
        (self.shared / "env.tsv").write_text("OMZTEST_VALUE\tmanual\n")
        (self.profile / "README.md").write_text("unrelated staged change\n")
        self.git("add", "README.md")
        self.cli("env", "set", "OMZTEST_VALUE", "third", "--shared")
        self.assertIn("OMZTEST_VALUE\tmanual", self.git("show", "HEAD~1:shell/env.tsv").stdout)
        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout.strip(), "README.md")
        self.assertNotIn("README.md", self.git("ls-tree", "--name-only", "HEAD").stdout)

    def test_git_mode_checks_identity_before_changing_shared_file(self):
        self.enable_git()
        self.git("config", "--unset", "user.name")
        self.git("config", "--unset", "user.email")
        self.git("config", "user.useConfigOnly", "true")
        before = (self.shared / "env.tsv").read_bytes()
        self.cli("env", "set", "OMZTEST_VALUE", "new", "--shared", ok=False)
        self.assertEqual((self.shared / "env.tsv").read_bytes(), before)
        self.assertFalse((self.state / "backups").exists())

    def test_git_mode_versions_snippet_rename_and_deletion(self):
        self.enable_git()
        self.cli("rc", "add", "10-tools")
        self.cli("rc", "disable", "10-tools")
        files = self.git("ls-tree", "-r", "--name-only", "HEAD").stdout
        self.assertIn("shell/rc.d/10-tools.zsh.disabled", files)
        self.assertNotIn("shell/rc.d/10-tools.zsh\n", files)
        self.cli("rc", "remove", "10-tools")
        self.assertNotIn("10-tools", self.git("ls-tree", "-r", "--name-only", "HEAD").stdout)
        self.assertIn("10-tools", self.git("ls-tree", "-r", "--name-only", "HEAD~1").stdout)
        self.assertFalse((self.state / "backups").exists())

    def test_git_mode_rejects_binary_snippet_before_writing(self):
        self.enable_git()
        source = self.work / "binary.zsh"
        source.write_bytes(b"# shell comment\x00binary\n")
        before = self.git("rev-parse", "HEAD").stdout
        self.cli("rc", "add", "binary", "--from", str(source), ok=False)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)
        self.assertFalse((self.shared / "rc.d/binary.zsh").exists())
        source.write_bytes(b"# shell comment\xffbinary\n")
        self.cli("rc", "add", "binary", "--from", str(source), ok=False)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)

    def test_first_managed_git_commit_contains_profile_identity(self):
        self.git("init", "-q", "--initial-branch=main")
        self.git("config", "user.name", "Shell test")
        self.git("config", "user.email", "shell@example.invalid")
        self.cli("path", "add", "/tools/bin")
        revisions = self.git("rev-list", "HEAD").stdout.splitlines()
        for revision in revisions:
            self.assertEqual(self.git("show", revision + ":.omztty-profile").stdout,
                             "omztty-profile-v1\n")

    def test_local_variables_hidden_by_default_and_override_shared(self):
        self.cli("env", "set", "EDITOR", "nano", "--shared")
        self.cli("env", "set", "EDITOR", "my editor --flag")
        self.assertIn("<set>", self.cli("env", "list").stdout)
        self.assertNotIn("my editor", self.cli("env", "list").stdout)
        self.assertIn("my editor --flag", self.cli("env", "list", "--show").stdout)
        self.assertEqual(self.cli("env", "get", "EDITOR").stdout, "my editor --flag\n")
        self.assertEqual(self.shell(self.load + '; print -r -- "$EDITOR"').stdout, "my editor --flag\n")
        self.assertEqual((self.local / "env.tsv").stat().st_mode & 0o777, 0o600)
        self.cli("env", "unset", "EDITOR")
        self.assertEqual(self.cli("env", "get", "EDITOR").stdout, "nano\n")

    def test_empty_values_and_shell_metacharacters_remain_literal(self):
        value = "$(touch marker) `touch marker2` ' \\\" * $HOME ; # end"
        self.cli("env", "set", "OMZTEST_VALUE", value, "--shared")
        self.cli("env", "set", "OMZTEST_EMPTY", "")
        result = self.shell(self.load + '; print -rl -- "$OMZTEST_VALUE" "${+OMZTEST_EMPTY}:$OMZTEST_EMPTY"')
        self.assertEqual(result.stdout, value + "\n1:\n")
        self.assertFalse((self.home / "marker").exists())
        self.assertFalse((ROOT / "marker").exists())

    def test_value_named_like_flag_is_not_parsed_as_option(self):
        self.cli("env", "set", "OMZTEST_FLAG", "--shared")
        self.assertEqual(self.cli("env", "get", "OMZTEST_FLAG").stdout, "--shared\n")
        self.assertTrue((self.local / "env.tsv").is_file())

    def test_invalid_names_and_multiline_values_leave_no_files(self):
        for name in ("PATH", "HOME", "XDG_CONFIG_HOME", "ZDOTDIR", "OMZTTY_ROOT", "status", "RANDOM", "1BAD", "A=B", "_omztty_key"):
            with self.subTest(name=name):
                self.cli("env", "set", name, "secret", ok=False)
        for value in ("one\ntwo", "one\ttwo", "one\rtwo"):
            self.cli("env", "set", "OMZTEST_VALUE", value, ok=False)
        self.assertFalse(self.local.exists())
        self.assertFalse(self.state.exists())

    def test_environment_unset_reload_restores_inherited_value(self):
        self.cli("env", "set", "OMZTEST_VALUE", "managed")
        result = self.shell(
            'export OMZTEST_VALUE=inherited; ' + self.load + '; '
            '"$OMZTTY_ROOT/bin/omztty" env unset OMZTEST_VALUE >/dev/null 2>/dev/null; '
            + self.load + '; print -r -- "$OMZTEST_VALUE"')
        self.assertEqual(result.stdout, "inherited\n")

    def test_invalid_manual_environment_file_is_never_evaluated(self):
        self.cli("rc", "init")
        (self.shared / "env.tsv").write_text('export OMZTEST_VALUE=$(touch "$HOME/executed")\n')
        self.cli("rc", "check", ok=False)
        self.shell(self.load, ok=False)
        self.assertFalse((self.home / "executed").exists())

    def test_duplicate_manual_variable_rejected_without_printing_values(self):
        self.cli("rc", "init")
        (self.shared / "env.tsv").write_text("OMZTEST_A\tsecret1\nOMZTEST_A\tsecret2\n")
        result = self.cli("env", "list", ok=False)
        self.assertNotIn("secret", result.stdout + result.stderr)
        self.assertIn(":2", result.stderr)

    def test_path_order_home_portability_and_idempotent_reload(self):
        first = self.home / "tools with spaces/bin"
        last = self.work / "late/bin"
        self.cli("path", "add", str(first))
        self.cli("path", "add", str(last), "--append")
        self.assertIn("prepend\t~/tools with spaces/bin", (self.shared / "path.tsv").read_text())
        output = self.shell(self.load + '; ' + self.load + '; print -r -- "$PATH"').stdout.strip()
        self.assertEqual(output, f"{first}:/usr/bin:/bin:{last}")
        before = len(self.backups())
        self.cli("path", "add", str(first))
        self.assertEqual(len(self.backups()), before)

    def test_path_moves_and_removes_rules_without_changing_inherited_path(self):
        self.cli("path", "add", "/one")
        self.cli("path", "add", "/two")
        self.cli("path", "move", "/one", "last")
        self.assertEqual(self.shell(self.load + '; print -r -- "$PATH"').stdout.strip(), "/two:/usr/bin:/bin:/one")
        self.cli("path", "remove", "/two")
        self.assertEqual(self.shell(self.load + '; print -r -- "$PATH"').stdout.strip(), "/usr/bin:/bin:/one")
        self.assertIn("inherited PATH is unchanged", self.cli("path", "remove", "/usr/bin").stdout)

    def test_path_special_characters_do_not_execute_and_empty_segments_survive(self):
        directory = str(self.home / "dollar$(false) ' `false` * ")
        self.cli("path", "add", directory)
        result = self.shell('PATH=:/usr/bin::/bin:; ' + self.load + '; print -r -- "$PATH"')
        self.assertEqual(result.stdout.rstrip("\n"), directory + ":" + ":/usr/bin::/bin:")

    def test_path_removal_reload_restores_original_order(self):
        self.cli("path", "add", "/bin", "--append")
        result = self.shell(self.load + '; '
                            '"$OMZTTY_ROOT/bin/omztty" path remove /bin >/dev/null 2>/dev/null; '
                            + self.load + '; print -r -- "$PATH"')
        self.assertEqual(result.stdout, "/usr/bin:/bin\n")

    def test_path_reload_preserves_new_venv_entries(self):
        self.cli("path", "add", "/tools")
        result = self.shell(self.load + '; PATH="/venv/bin:$PATH"; ' + self.load + '; print -r -- "$PATH"')
        self.assertEqual(result.stdout, "/tools:/venv/bin:/usr/bin:/bin\n")

    def test_invalid_path_inputs_are_read_only(self):
        for directory in ("relative/bin", "/a:/b", "/a\nb", "/a\tb"):
            self.cli("path", "add", directory, ok=False)
        self.assertFalse(self.shared.exists())
        self.assertFalse(self.state.exists())

    def test_file_commands_reveal_paths_without_initializing(self):
        self.assertEqual(self.cli("env", "file").stdout.strip(), str(self.local / "env.tsv"))
        self.assertEqual(self.cli("env", "file", "--shared").stdout.strip(), str(self.shared / "env.tsv"))
        self.assertEqual(self.cli("path", "file").stdout.strip(), str(self.shared / "path.tsv"))
        self.assertFalse(self.shared.exists())
        self.assertFalse(self.local.exists())

    def test_rc_snippet_enable_disable_and_shell_options_persist(self):
        source = self.work / "personal.zsh"
        source.write_text("setopt autocd\ntypeset OMZTEST_DECL=loaded\nalias omztest_alias='print alias-ok'\n")
        self.cli("rc", "add", "10-personal", "--from", str(source))
        result = self.shell(self.load + '; print -rl -- "$options[autocd]" "$OMZTEST_DECL"; alias omztest_alias')
        self.assertIn("on\nloaded\n", result.stdout)
        self.cli("rc", "disable", "10-personal")
        self.assertTrue(self.cli("rc", "file", "10-personal").stdout.strip().endswith(".zsh.disabled"))
        self.assertIn("disabled", self.cli("rc", "list").stdout)
        self.assertEqual(self.shell(self.load + '; print -r -- "${OMZTEST_DECL:-absent}"').stdout, "absent\n")
        self.cli("rc", "enable", "10-personal")
        self.assertEqual(self.shell(self.load + '; print -r -- "$OMZTEST_DECL"').stdout, "loaded\n")

    def test_rc_check_does_not_execute_snippets(self):
        source = self.work / "check.zsh"
        source.write_text('print executed > "$HOME/ran-rc"\n')
        self.cli("rc", "add", "20-check", "--from", str(source))
        self.cli("rc", "check")
        self.assertFalse((self.home / "ran-rc").exists())

    def test_invalid_snippet_does_not_replace_or_initialize(self):
        source = self.work / "invalid.zsh"
        source.write_text("if then\n")
        self.cli("rc", "add", "bad", "--from", str(source), ok=False)
        self.assertFalse(self.shared.exists())
        self.assertFalse(self.state.exists())
        self.cli("rc", "add", "../outside", ok=False)

    def test_rc_install_dry_run_and_round_trip_preserve_bytes(self):
        rc = self.home / ".zshrc"
        original = b"# personal config without a final newline"
        rc.write_bytes(original)
        self.cli("rc", "install", "--dry-run")
        self.assertEqual(rc.read_bytes(), original)
        self.assertFalse(self.shared.exists())
        self.assertFalse(self.state.exists())
        self.cli("rc", "install")
        first = rc.read_bytes()
        backup_count = len(self.backups())
        self.cli("rc", "install")
        self.assertEqual(rc.read_bytes(), first)
        self.assertEqual(len(self.backups()), backup_count)
        self.cli("rc", "uninstall")
        self.assertEqual(rc.read_bytes(), original)

    def test_rc_install_respects_zdotdir_and_preserves_symlink(self):
        zdotdir = self.home / "custom zsh"
        zdotdir.mkdir()
        real = self.home / "tracked.zsh"
        real.write_text("# tracked original\n")
        rc = zdotdir / ".zshrc"
        rc.symlink_to(real)
        self.cli("rc", "install", extra={"ZDOTDIR": str(zdotdir)})
        self.assertTrue(rc.is_symlink())
        self.assertIn("# >>> oh-my-ztty shell >>>", real.read_text())
        self.assertFalse((self.home / ".zshrc").exists())
        self.cli("rc", "uninstall", extra={"ZDOTDIR": str(zdotdir)})
        self.assertTrue(rc.is_symlink())
        self.assertEqual(real.read_text(), "# tracked original\n")

    def test_rc_install_does_not_edit_suite_zdotdir(self):
        original = (ROOT / "config/zsh/.zshrc").read_bytes()
        self.cli("rc", "install", extra={"ZDOTDIR": str(ROOT / "config/zsh")})
        self.assertEqual((ROOT / "config/zsh/.zshrc").read_bytes(), original)
        self.assertTrue((self.home / ".zshrc").exists())

    def test_rc_broken_or_duplicate_markers_are_preserved(self):
        for text in ("# >>> oh-my-ztty shell >>>\n", "# <<< oh-my-ztty shell <<<\n",
                     "# >>> oh-my-ztty shell >>>\n# >>> oh-my-ztty shell >>>\n# <<< oh-my-ztty shell <<<\n"):
            rc = self.home / ".zshrc"
            rc.write_text(text)
            self.cli("rc", "install", ok=False)
            self.assertEqual(rc.read_text(), text)
        self.assertFalse(self.state.exists())

    def test_installed_hook_loads_real_interactive_shell(self):
        self.cli("env", "set", "OMZTEST_REAL", "loaded")
        self.cli("rc", "install")
        env = self.env | {"PATH": str(ROOT / "bin") + ":/usr/bin:/bin", "ZDOTDIR": str(self.home)}
        result = subprocess.run([ZSH, "-di", "-c", 'print -r -- "$OMZTEST_REAL"'],
                                env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "loaded\n")

    def test_backup_restore_preserves_mode_and_current_version(self):
        self.cli("env", "set", "OMZTEST_VALUE", "first")
        target = self.local / "env.tsv"
        target.chmod(0o640)
        original = target.read_bytes()
        self.cli("env", "set", "OMZTEST_VALUE", "second")
        record = self.backups(target)[-1]
        second = target.read_bytes()
        self.cli("rc", "restore", record.name)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertEqual((self.backups(target)[-1] / "content").read_bytes(), second)

    def test_backup_of_new_file_restores_absence(self):
        self.cli("env", "set", "OMZTEST_VALUE", "first")
        target = self.local / "env.tsv"
        record = self.backups(target)[0]
        self.cli("rc", "restore", record.name)
        self.assertFalse(target.exists())
        self.assertTrue((self.backups(target)[-1] / "content").is_file())

    def test_editor_with_arguments_and_spaces_validates_before_publish(self):
        editor = self.work / "my editor"
        editor.write_text('#!/bin/sh\nprintf "OMZTEST_EDIT\\tliteral value\\n" > "$2"\n')
        editor.chmod(0o755)
        self.cli("env", "edit", extra={"EDITOR": shlex.quote(str(editor)) + " --wait"})
        self.assertEqual(self.cli("env", "get", "OMZTEST_EDIT").stdout, "literal value\n")
        original = (self.local / "env.tsv").read_bytes()
        editor.write_text('#!/bin/sh\nprintf "bad shell data\\n" > "$2"\n')
        self.cli("env", "edit", extra={"EDITOR": shlex.quote(str(editor)) + " --wait"}, ok=False)
        self.assertEqual((self.local / "env.tsv").read_bytes(), original)

    def test_symlinked_data_file_is_preserved(self):
        self.cli("rc", "init")
        target = self.shared / "env.tsv"
        target.unlink()
        external = self.home / "external.env"
        external.write_text("OMZTEST_ORIGINAL\tuntouched\n")
        target.symlink_to(external)
        self.cli("env", "set", "OMZTEST_VALUE", "new", "--shared", ok=False)
        self.assertTrue(target.is_symlink())
        self.assertEqual(external.read_text(), "OMZTEST_ORIGINAL\tuntouched\n")


if __name__ == "__main__":
    unittest.main()
