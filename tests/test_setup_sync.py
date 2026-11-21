#!/usr/bin/env python3
"""Exercise profile setup/sync with real local Git and an inert GitHub stub."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ZSH = shutil.which("zsh")
GIT = shutil.which("git")


@unittest.skipUnless(ZSH and GIT, "requires zsh and git")
class SetupSync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="omztty setup sync ")
        self.work = Path(self.tmp.name)
        self.home = self.work / "home with spaces"
        self.home.mkdir()
        self.suite = self.work / "suite"
        (self.suite / "bin").mkdir(parents=True)
        for name in ("omztty-sync", "omztty-setup"):
            shutil.copy2(ROOT / "bin" / name, self.suite / "bin" / name)
        (self.suite / "config/zsh").mkdir(parents=True)
        shutil.copy2(ROOT / "config/zsh/settings-lib.zsh", self.suite / "config/zsh/settings-lib.zsh")
        self.profile = self.home / "custom config/oh-my-ztty/profile"
        self.remote = self.work / "remote.git"
        self.fake = self.work / "fake-bin"
        self.fake.mkdir()
        self.events = self.work / "events.jsonl"
        self.settings = self.work / "github.json"
        self.settings.write_text(json.dumps({"account": "alice", "private": True}))
        self.env = {
            "HOME": str(self.home), "PATH": str(self.fake) + ":/usr/bin:/bin",
            "XDG_CONFIG_HOME": str(self.home / "custom config"),
            "XDG_STATE_HOME": str(self.home / "state"),
            "OMZTTY_ROOT": str(self.suite), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "Profile fixture", "GIT_COMMITTER_NAME": "Profile fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            "TEST_GIT": str(GIT), "TEST_REMOTE": str(self.remote),
            "TEST_EVENTS": str(self.events), "TEST_GITHUB": str(self.settings),
        }
        self.script(self.suite / "bin/omztty", r'''
from pathlib import Path
import json, os, sys
args = sys.argv[1:]
with open(os.environ["TEST_EVENTS"], "a") as out:
    out.write(json.dumps(["omztty", *args]) + "\n")
p = Path(os.environ["XDG_CONFIG_HOME"]) / "oh-my-ztty/profile"
if args == ["rc", "init"]:
    if not p.exists():
        (p / "files/.config/ztty").mkdir(parents=True)
        (p / ".omztty-profile").write_text("omztty-profile-v1\n")
        (p / ".suite-version").write_text("0.2.6\n")
        (p / ".config-layout").write_text("canonical-v1\n")
        (p / "profile.zdot").write_text("files/.zshrc\t.zshrc\nfiles/.config/ztty\t.config/ztty\n")
        (p / "files/.zshrc").write_text("# fixture profile\n")
        (p / "files/.config/ztty/config").write_text("font-size = 13\n")
        (p / ".baseline").mkdir()
        (p / ".baseline/local-baseline").write_text("local\n")
    (p / "shell/rc.d").mkdir(parents=True, exist_ok=True)
    for name in ("env.tsv", "path.tsv"):
        f = p / "shell" / name
        if not f.exists():
            f.write_text("")
elif args == ["rc", "install"]:
    (Path(os.environ["HOME"]) / ".zshrc").write_text("# managed loader fixture\n")
else:
    raise SystemExit("unexpected fixture command: " + repr(args))
''')
        self.script(self.fake / "git", r'''
import json, os, sys
args = sys.argv[1:]
network = next((a for a in args if a in ("fetch", "push", "ls-remote")), None)
if network:
    with open(os.environ["TEST_EVENTS"], "a") as out:
        out.write(json.dumps(["git", *args]) + "\n")
    if "origin" in args:
        args[args.index("origin")] = os.environ["TEST_REMOTE"]
os.execv(os.environ["TEST_GIT"], [os.environ["TEST_GIT"], *args])
''')
        self.script(self.fake / "gh", r'''
from pathlib import Path
import json, os, subprocess, sys
args = sys.argv[1:]
state = json.loads(Path(os.environ["TEST_GITHUB"]).read_text())
with open(os.environ["TEST_EVENTS"], "a") as out:
    out.write(json.dumps(["gh", *args]) + "\n")
git = os.environ["TEST_GIT"]
if args[:1] == ["api"]:
    print(state["account"])
elif args[:2] == ["repo", "view"]:
    name = args[2]
    print("\t".join([state.get("repo_owner", name.split("/")[0]), str(state["private"]).lower(), name]))
elif args[:2] == ["repo", "create"]:
    assert "--private" in args and "--public" not in args
    assert args[2].split("/")[0] == state["account"]
    subprocess.run([git, "init", "--bare", "--quiet", "--initial-branch=main", os.environ["TEST_REMOTE"]], check=True)
    source = args[args.index("--source") + 1]
    subprocess.run([git, "-C", source, "remote", "add", "origin", "https://github.com/" + args[2] + ".git"], check=True)
elif args[:2] == ["repo", "clone"]:
    assert args[4:] == ["--", "--no-checkout"]
    subprocess.run([git, "clone", "--no-checkout", "--quiet", os.environ["TEST_REMOTE"], args[3]], check=True)
    subprocess.run([git, "-C", args[3], "remote", "set-url", "origin", "https://github.com/" + args[2] + ".git"], check=True)
else:
    raise SystemExit("unexpected gh invocation: " + repr(args))
''')

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def script(path, body):
        path.write_text(f"#!{sys.executable}\n" + body.lstrip())
        path.chmod(0o755)

    def run_cli(self, name, *args, ok=True, env=None):
        result = subprocess.run([ZSH, "-f", str(self.suite / "bin" / ("omztty-" + name)), *args],
                                env=env or self.env, text=True, capture_output=True, timeout=20)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def git(self, *args, cwd=None, ok=True):
        result = subprocess.run([GIT, *map(str, args)], cwd=cwd or self.profile,
                                env=self.env, text=True, capture_output=True, timeout=15)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def log(self):
        return [json.loads(line) for line in self.events.read_text().splitlines()] if self.events.exists() else []

    def init_profile(self):
        self.run_cli("setup", "--local", "--yes")
        self.run_cli("sync", "init")

    def commit_all(self, message="fixture"):
        self.git("add", "--all")
        if self.git("diff", "--cached", "--name-only"):
            self.git("-c", "commit.gpgsign=false", "commit", "-qm", message)

    def seed_remote(self):
        self.init_profile()
        self.commit_all()
        self.git("init", "--bare", "--quiet", "--initial-branch=main", self.remote)
        self.git("remote", "add", "origin", self.remote)
        self.git("push", "-qu", "origin", "main")

    def writer(self):
        writer = self.work / "other-machine"
        self.git("clone", "--quiet", self.remote, writer)
        return writer

    def use_github_remote(self):
        self.git("remote", "set-url", "origin", "https://github.com/alice/dotfiles.git")

    def test_explicit_local_initialization_never_contacts_github(self):
        self.run_cli("setup", "--local", "--yes", "--install-rc")
        self.assertTrue((self.profile / "shell/env.tsv").is_file())
        self.assertTrue((self.home / ".zshrc").is_file())
        self.assertFalse((self.profile / ".git").exists())
        self.assertEqual(self.log(), [["omztty", "rc", "init"], ["omztty", "rc", "install"]])

    def test_noninteractive_setup_requires_an_explicit_mode(self):
        for args in ((), ("--yes",), ("--repo", "dotfiles"), ("--local", "--repo", "dotfiles")):
            with self.subTest(args=args):
                self.run_cli("setup", *args, ok=False)
        self.assertFalse(self.profile.exists())
        self.assertEqual(self.log(), [])

    def test_missing_gh_keeps_local_profile_available(self):
        no_gh = self.work / "no-gh"
        no_gh.mkdir()
        for command in ("git", "touch", "grep", "iconv", "cat", "mkdir", "mktemp", "rm"):
            (no_gh / command).symlink_to(shutil.which(command))
        env = dict(self.env, PATH=str(no_gh))
        result = self.run_cli("setup", "--repo", "dotfiles", "--yes", ok=False, env=env)
        self.assertIn("gh auth login", result.stderr)
        self.assertTrue((self.profile / ".omztty-profile").is_file())
        self.assertFalse(self.remote.exists())

    def test_private_setup_commits_allowed_files_and_pushes(self):
        self.run_cli("setup", "--repo", "dotfiles", "--yes")
        names = self.git("--git-dir", self.remote, "ls-tree", "--name-only", "-r", "main").splitlines()
        self.assertIn("shell/env.tsv", names)
        self.assertIn(".config-layout", names)
        self.assertIn("files/.config/ztty/config", names)
        self.assertNotIn(".baseline/local-baseline", names)
        calls = self.log()
        create = next(x for x in calls if x[:3] == ["gh", "repo", "create"])
        self.assertIn("--private", create)
        self.assertEqual(create[3], "alice/dotfiles")
        self.assertFalse((self.home / ".zshrc").exists())

    def test_status_is_local_and_parent_repo_is_not_used(self):
        self.git("init", "--quiet", self.home, cwd=self.home)
        self.run_cli("setup", "--local")
        result = self.run_cli("sync", "status")
        self.assertIn("not initialized", result.stdout)
        self.run_cli("sync", "push", ok=False)
        self.assertFalse(any(x[0] == "gh" for x in self.log()))
        self.assertFalse((self.profile / ".git").exists())
        self.run_cli("sync", "init")
        self.assertTrue((self.profile / ".git").is_dir())
        self.assertEqual(Path(self.git("rev-parse", "--show-toplevel")), self.profile)

    def test_existing_profile_is_preserved_on_restore(self):
        self.run_cli("setup", "--local")
        original = (self.profile / "profile.zdot").read_bytes()
        self.run_cli("setup", "--from", "alice/dotfiles", "--yes", ok=False)
        self.assertEqual((self.profile / "profile.zdot").read_bytes(), original)
        self.assertFalse(any(x[0] == "gh" for x in self.log()))

    def test_public_or_other_owner_restore_is_rejected(self):
        self.settings.write_text(json.dumps({"account": "alice", "private": False}))
        self.run_cli("setup", "--from", "alice/public", "--yes", ok=False)
        self.settings.write_text(json.dumps({"account": "alice", "private": True}))
        self.run_cli("setup", "--from", "bob/private", "--yes", ok=False)
        self.assertFalse(self.profile.exists())
        self.assertFalse(any(x[:3] == ["gh", "repo", "clone"] for x in self.log()))

    def test_restore_never_sources_rc_and_keeps_branch(self):
        self.seed_remote()
        (self.profile / "shell/rc.d/probe.zsh").write_text('touch "$HOME/rc-was-run"\n')
        self.commit_all()
        self.git("push", "-q")
        shutil.rmtree(self.profile)
        self.run_cli("setup", "--from", "alice/dotfiles", "--yes")
        self.assertTrue((self.profile / "shell/rc.d/probe.zsh").is_file())
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD"), "main")
        self.assertFalse((self.home / "rc-was-run").exists())
        self.assertFalse((self.home / ".zshrc").exists())
        self.assertFalse((self.profile / ".baseline").exists())

    def test_restore_rejects_excluded_incoming_files_before_checkout(self):
        self.seed_remote()
        (self.profile / "private-secret.txt").write_text("not for sync\n")
        self.git("add", "--force", "private-secret.txt")
        self.git("commit", "-qm", "excluded incoming file")
        self.git("push", "-q")
        shutil.rmtree(self.profile)
        result = self.run_cli("setup", "--from", "alice/dotfiles", "--yes", ok=False)
        self.assertIn("excluded file", result.stderr)
        self.assertFalse(self.profile.exists())

    def test_clean_pull_fast_forwards_local_bare_remote(self):
        self.seed_remote()
        writer = self.writer()
        (writer / "shell/env.tsv").write_text("EDITOR\tvim\n")
        self.git("add", "shell/env.tsv", cwd=writer)
        self.git("commit", "-qm", "new settings", cwd=writer)
        self.git("push", "-q", cwd=writer)
        self.run_cli("sync", "pull")
        self.assertEqual((self.profile / "shell/env.tsv").read_text(), "EDITOR\tvim\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertFalse(any(x[0] == "gh" for x in self.log()))

    def test_dirty_pull_refuses_before_fetch(self):
        self.seed_remote()
        (self.profile / "shell/env.tsv").write_text("LOCAL\tyes\n")
        result = self.run_cli("sync", "pull", ok=False)
        self.assertIn("local changes", result.stderr)
        self.assertFalse(any(x[0] == "git" and "fetch" in x for x in self.log()))
        self.assertEqual((self.profile / "shell/env.tsv").read_text(), "LOCAL\tyes\n")

    def test_diverged_pull_keeps_local_commit(self):
        self.seed_remote()
        writer = self.writer()
        (writer / "shell/env.tsv").write_text("REMOTE\tyes\n")
        self.git("add", "shell/env.tsv", cwd=writer)
        self.git("commit", "-qm", "remote", cwd=writer)
        self.git("push", "-q", cwd=writer)
        (self.profile / "shell/path.tsv").write_text("prepend\t/opt/tools\n")
        self.commit_all("local")
        head = self.git("rev-parse", "HEAD")
        self.run_cli("sync", "pull", ok=False)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_pull_rejects_unsafe_tree_without_changing_working_files(self):
        self.seed_remote()
        writer = self.writer()
        (writer / "shell/rc.d").mkdir()
        (writer / "shell/rc.d/link.zsh").symlink_to("/tmp/unrelated")
        self.git("add", "shell/rc.d/link.zsh", cwd=writer)
        self.git("commit", "-qm", "symlink", cwd=writer)
        self.git("push", "-q", cwd=writer)
        head = self.git("rev-parse", "HEAD")
        self.run_cli("sync", "pull", ok=False)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertFalse((self.profile / "shell/rc.d/link.zsh").is_symlink())

    def test_push_commits_only_allowed_paths_and_preserves_local_files(self):
        self.seed_remote()
        self.use_github_remote()
        (self.profile / "notes.txt").write_text("local notes\n")
        (self.profile / ".env").write_text("TOKEN=private\n")
        (self.profile / "shell/env.tsv").write_text("EDITOR\tnvim\n")
        (self.profile / "shell/rc.d/saved.zsh.disabled").write_text("# disabled snippet\n")
        fancy = self.profile / "files/.config/tool with spaces/config"
        fancy.parent.mkdir()
        fancy.write_text("enabled\n")
        self.run_cli("sync", "push")
        names = self.git("--git-dir", self.remote, "ls-tree", "--name-only", "-r", "main").splitlines()
        self.assertIn("files/.config/tool with spaces/config", names)
        self.assertIn("shell/rc.d/saved.zsh.disabled", names)
        self.assertNotIn("notes.txt", names)
        self.assertNotIn(".env", names)
        self.assertEqual((self.profile / "notes.txt").read_text(), "local notes\n")
        self.assertEqual(self.git("--git-dir", self.remote, "show", "main:shell/env.tsv"), "EDITOR\tnvim")

    def test_push_rejects_an_excluded_staged_file(self):
        self.seed_remote()
        self.use_github_remote()
        (self.profile / ".env").write_text("TOKEN=private\n")
        self.git("add", "--force", ".env")
        head = self.git("--git-dir", self.remote, "rev-parse", "main")
        result = self.run_cli("sync", "push", ok=False)
        self.assertIn("already staged", result.stderr)
        self.assertEqual(self.git("--git-dir", self.remote, "rev-parse", "main"), head)

    def test_push_rejects_secret_deleted_from_outgoing_history(self):
        self.init_profile()
        self.commit_all()
        (self.profile / "credentials.json").write_text("private\n")
        self.git("add", "--force", "credentials.json")
        self.git("commit", "-qm", "old secret")
        self.git("rm", "credentials.json")
        self.git("commit", "-qm", "remove secret")
        self.git("init", "--bare", "--quiet", "--initial-branch=main", self.remote)
        self.git("remote", "add", "origin", "https://github.com/alice/dotfiles.git")
        result = self.run_cli("sync", "push", ok=False)
        self.assertIn("excluded file", result.stderr)
        self.assertEqual(self.git("--git-dir", self.remote, "show-ref", ok=False), "")

    def test_push_refuses_public_repo_and_mismatched_push_url(self):
        self.seed_remote()
        self.use_github_remote()
        self.settings.write_text(json.dumps({"account": "alice", "private": False}))
        self.run_cli("sync", "push", ok=False)
        self.settings.write_text(json.dumps({"account": "alice", "private": True}))
        self.git("remote", "set-url", "--push", "origin", "https://github.com/alice/another.git")
        self.run_cli("sync", "push", ok=False)
        self.assertFalse(any(x[0] == "git" and "push" in x for x in self.log()))

    def test_push_rejects_binary_and_symlinked_config(self):
        self.seed_remote()
        self.use_github_remote()
        probe = self.profile / "shell/rc.d/probe.zsh"
        probe.write_bytes(b"hello\x00world")
        self.run_cli("sync", "push", ok=False)
        probe.unlink()
        probe.symlink_to(self.profile / "shell/env.tsv")
        self.run_cli("sync", "push", ok=False)
        self.assertTrue(probe.is_symlink())

    def test_repeated_push_without_changes_succeeds(self):
        self.run_cli("setup", "--repo", "dotfiles", "--yes")
        head = self.git("rev-parse", "HEAD")
        self.run_cli("sync", "push")
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_in_progress_git_operation_is_preserved(self):
        self.seed_remote()
        self.use_github_remote()
        operation = self.profile / ".git/CHERRY_PICK_HEAD"
        head = self.git("rev-parse", "HEAD")
        operation.write_text(head + "\n")
        for action in ("push", "pull"):
            self.run_cli("sync", action, ok=False)
        self.assertEqual(operation.read_text(), head + "\n")
        self.assertFalse(any(x[0] == "gh" for x in self.log()))

    def test_secret_directory_is_not_staged(self):
        self.seed_remote()
        self.use_github_remote()
        private = self.profile / "files/secrets/token"
        private.parent.mkdir()
        private.write_text("machine private\n")
        self.run_cli("sync", "push")
        self.assertNotIn("files/secrets/token", self.git("ls-files").splitlines())
        self.assertEqual(private.read_text(), "machine private\n")

    def invalid_incoming(self, relative, content, restore=False):
        self.seed_remote()
        writer = self.writer()
        target = writer / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        self.git("add", relative, cwd=writer)
        self.git("commit", "-qm", "invalid incoming configuration", cwd=writer)
        self.git("push", "-q", cwd=writer)
        head = self.git("rev-parse", "HEAD")
        original = {p.relative_to(self.profile): p.read_bytes() for p in (self.profile / "shell").rglob("*") if p.is_file()}
        if restore:
            shutil.rmtree(self.profile)
            result = self.run_cli("setup", "--from", "alice/dotfiles", "--yes", ok=False)
            self.assertFalse(self.profile.exists())
        else:
            result = self.run_cli("sync", "pull", ok=False)
            self.assertEqual(self.git("rev-parse", "HEAD"), head)
            self.assertEqual({p.relative_to(self.profile): p.read_bytes() for p in (self.profile / "shell").rglob("*") if p.is_file()}, original)
        self.assertIn("invalid configuration", result.stderr)
        self.assertFalse((self.home / "rc-was-run").exists())

    def test_pull_rejects_malformed_environment_data_before_merge(self):
        self.invalid_incoming("shell/env.tsv", "HOME\t/another/home\n")

    def test_pull_rejects_malformed_path_data_before_merge(self):
        self.invalid_incoming("shell/path.tsv", "prepend\t/opt/a:/opt/b\n")

    def test_pull_rejects_invalid_rc_syntax_before_merge(self):
        self.invalid_incoming("shell/rc.d/broken.zsh", 'touch "$HOME/rc-was-run"\nif then\n')

    def test_clone_rejects_invalid_disabled_rc_syntax_before_checkout(self):
        self.invalid_incoming("shell/rc.d/broken.zsh.disabled", "function {\n", restore=True)

    def test_initial_commit_is_complete_and_history_is_local(self):
        self.init_profile()
        names = self.git("ls-tree", "--name-only", "-r", "HEAD").splitlines()
        self.assertIn(".omztty-profile", names)
        self.assertIn("shell/env.tsv", names)
        result = self.run_cli("sync", "history")
        self.assertIn("Update oh-my-ztty profile", result.stdout)
        self.assertFalse(any(x[0] in ("gh", "git") for x in self.log()))

    def test_restore_shell_records_new_local_commit_without_snapshot_or_push(self):
        self.init_profile()
        initial = self.git("rev-parse", "HEAD")
        (self.profile / "shell/env.tsv").write_text("EDITOR\tnvim\n")
        (self.profile / "shell/rc.d/new.zsh").write_text('touch "$HOME/rc-was-run"\n')
        (self.profile / "files/.config/ztty/config").write_text("font-size = 16\n")
        self.commit_all("new settings")
        previous = self.git("rev-parse", "HEAD")
        self.run_cli("sync", "restore", initial)
        self.assertEqual((self.profile / "shell/env.tsv").read_text(), "")
        self.assertFalse((self.profile / "shell/rc.d/new.zsh").exists())
        self.assertEqual((self.profile / "files/.config/ztty/config").read_text(), "font-size = 16\n")
        self.assertEqual(self.git("rev-parse", "HEAD^"), previous)
        self.assertFalse((self.home / "state").exists())
        self.assertFalse((self.home / "rc-was-run").exists())
        self.assertFalse(any(x[0] in ("gh", "git") for x in self.log()))

    def test_restore_single_file_and_historical_deletion(self):
        self.init_profile()
        initial = self.git("rev-parse", "HEAD")
        (self.profile / "files/.config/ztty/config").write_text("font-size = 17\n")
        (self.profile / "shell/rc.d/new.zsh").write_text("# new snippet\n")
        self.commit_all("new settings")
        self.run_cli("sync", "restore", initial, "files/.config/ztty/config")
        self.assertEqual((self.profile / "files/.config/ztty/config").read_text(), "font-size = 13\n")
        self.assertTrue((self.profile / "shell/rc.d/new.zsh").exists())
        self.run_cli("sync", "restore", initial, "shell/rc.d/new.zsh")
        self.assertFalse((self.profile / "shell/rc.d/new.zsh").exists())

    def test_restore_refuses_dirty_tree_invalid_revision_and_unowned_path(self):
        self.init_profile()
        initial = self.git("rev-parse", "HEAD")
        (self.profile / "shell/env.tsv").write_text("EDITOR\tvim\n")
        self.run_cli("sync", "restore", initial, ok=False)
        self.assertEqual((self.profile / "shell/env.tsv").read_text(), "EDITOR\tvim\n")
        self.commit_all()
        for args in (("missing-revision",), (initial, ".env"), (initial, "../outside"), (initial, "shell/rc.d/missing.zsh")):
            self.run_cli("sync", "restore", *args, ok=False)

    def test_restore_rejects_invalid_historical_data_without_changes(self):
        self.init_profile()
        (self.profile / "shell/env.tsv").write_text("PATH\t/unwanted\n")
        self.commit_all("bad old data")
        invalid = self.git("rev-parse", "HEAD")
        (self.profile / "shell/env.tsv").write_text("EDITOR\tvim\n")
        self.commit_all("correct data")
        current = self.git("rev-parse", "HEAD")
        self.run_cli("sync", "restore", invalid, ok=False)
        self.assertEqual(self.git("rev-parse", "HEAD"), current)
        self.assertEqual((self.profile / "shell/env.tsv").read_text(), "EDITOR\tvim\n")


if __name__ == "__main__":
    unittest.main()
