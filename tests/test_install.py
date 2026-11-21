#!/usr/bin/env python3
"""Installer lifecycle tests use inert component fixtures and a temporary HOME."""
from pathlib import Path
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Installation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omztty test ")
        self.work = Path(self.temp.name)
        self.home = self.work / "home with spaces"
        self.home.mkdir()
        self.data = self.home / ".local/share"
        self.bindir = self.home / ".local/bin"
        self.base = self.data / "oh-my-ztty"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("XDG_", "ZSHARD_", "OMZTTY_", "ZDOTDIR"))}
        self.env.update(HOME=str(self.home), XDG_DATA_HOME=str(self.data),
                        XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_CACHE_HOME=str(self.home / ".cache"),
                        XDG_STATE_HOME=str(self.home / ".local/state"))
        (self.home / ".zshrc").write_text("print UNWANTED_USER_RC\n")
        self.archive = self.bundle("0.1.0")

    def tearDown(self):
        self.temp.cleanup()

    def bundle(self, version, warm_exit=0, real_zshard=False):
        stage = self.work / ("stage-" + version) / "oh-my-ztty"
        stage.mkdir(parents=True)
        for rel in ["install.sh", "uninstall.sh", "bin/omztty", "bin/zshard",
                    "bin/omztty-config", "bin/omztty-manage", "bin/omztty-setup", "bin/omztty-sync",
                    "config/zsh/settings-lib.zsh", "config/zsh/settings.zsh",
                    "config/zmem/zmem.conf",
                    "config/zsh/.zshrc", "config/zsh/completion-paths.zsh", "config/zsh/ink.zsh", "packaging/oh-my-ztty.svg", "packaging/omztty.1"]:
            out = stage / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, out)
        for rel in ["install.sh", "uninstall.sh", "bin/omztty", "bin/zshard"]:
            (stage / rel).chmod(0o755)
        (stage / "VERSION").write_text(version + "\n")
        (stage / "PLATFORM").write_text("linux-" + os.uname().machine + "\n")
        shard = stage / "components/zshard"
        (shard / "bin").mkdir(parents=True)
        (shard / "zshard.zsh").write_text(
            "typeset -g ZSHARD_TEST=loaded\n"
            'zshard() {\n'
            '  printf "%s\\n" "$ZSHARD_CACHE_DIR" "$ZDOTDIR" > "$HOME/fixture-cache-dir"\n'
            f'  return {warm_exit}\n'
            '}\n'
        )
        (shard / "bin/zshard").write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$ZSHARD_CACHE_DIR" "$ZDOTDIR" > "$HOME/fixture-cache-dir"\n'
            f"printf 'zshard fixture\\n'\nexit {warm_exit}\n"
        )
        (shard / "bin/zshard").chmod(0o755)
        if real_zshard:
            shutil.copy2(ROOT / "components/zshard/zshard.zsh", shard / "zshard.zsh")
            for directory in ("bin", "lib", "completions"):
                shutil.copytree(ROOT / "components/zshard" / directory, shard / directory,
                                dirs_exist_ok=True)
            shutil.copytree(ROOT / "packaging/completions", stage / "packaging/completions")
        for name in ["ztty", "ssmcp", "zdot", "zfetch"]:
            executable = stage / "bin" / name
            executable.write_text(f"#!/bin/sh\nprintf '{name} fixture\\n'\n")
            executable.chmod(0o755)
        memory = stage / "bin/zmem"
        memory.write_text(
            '#!/bin/sh\n'
            'if [ "${1:-}" = install ]; then\n'
            '  printf "%s\\n" "$@" >> "$HOME/memory-setup-args"\n'
            '  exit "${OMZTTY_TEST_MEMORY_EXIT:-0}"\n'
            'fi\n'
            'printf "zmem fixture\\n"\n'
        )
        memory.chmod(0o755)
        lines = [f"{sha(p)}  {p.relative_to(stage)}" for p in sorted(stage.rglob("*")) if p.is_file()]
        (stage / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
        archive = self.work / f"oh-my-ztty-{version}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(stage, arcname="oh-my-ztty")
        archive.with_name(archive.name + ".sha256").write_text(f"{sha(archive)}  {archive.name}\n")
        return archive

    def run_command(self, args, ok=True):
        result = subprocess.run([str(arg) for arg in args], env=self.env, text=True, capture_output=True)
        if ok and result.returncode:
            self.fail(f"{args}: {result.returncode}\n{result.stdout}\n{result.stderr}")
        if not ok:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def install(self, archive=None, ok=True, desktop=None, memory_manager=False):
        args = ["sh", ROOT / "install.sh", "--from", archive or self.archive]
        if desktop is not None:
            args.append("--desktop" if desktop else "--no-desktop")
        if memory_manager is not None:
            args.append("--memory-manager" if memory_manager else "--no-memory-manager")
        return self.run_command(args, ok)

    def memory_privilege_fixture(self):
        fake = self.work / "memory-tools"
        fake.mkdir()
        (fake / "id").write_text('#!/bin/sh\nprintf "1000\\n"\n')
        (fake / "sudo").write_text(
            '#!/bin/sh\n'
            'printf "%s\\n" "$@" >> "$HOME/memory-sudo-args"\n'
            '[ "$1" != -- ] || shift\n'
            'exec "$@"\n'
        )
        for path in fake.iterdir():
            path.chmod(0o755)
        self.env["PATH"] = str(fake) + os.pathsep + self.env["PATH"]

    def test_default_install_sets_up_system_memory_from_verified_release(self):
        self.memory_privilege_fixture()
        self.install(memory_manager=None)
        release = (self.base / "current").resolve()
        self.assertEqual((self.home / "memory-setup-args").read_text().splitlines(),
                         ["install", "--replace", "--config", str(release / "config/zmem/zmem.conf")])
        self.assertEqual((self.home / "memory-sudo-args").read_text().splitlines(),
                         ["--", str(release / "bin/zmem"), "install", "--replace",
                          "--config", str(release / "config/zmem/zmem.conf")])
        self.assertEqual((self.base / ".memory-manager-enabled").read_text(), "1\n")
        self.assertEqual((self.bindir / "zmem").resolve(), release / "bin/zmem")

    def test_memory_skip_is_remembered_and_can_be_enabled(self):
        self.memory_privilege_fixture()
        self.install()
        self.install(memory_manager=None)
        self.assertFalse((self.home / "memory-setup-args").exists())
        self.assertFalse((self.home / "memory-sudo-args").exists())
        self.assertEqual((self.base / ".memory-manager-enabled").read_text(), "0\n")
        self.install(memory_manager=True)
        self.assertTrue((self.home / "memory-setup-args").exists())
        self.assertEqual((self.base / ".memory-manager-enabled").read_text(), "1\n")

    def test_failed_memory_setup_preserves_active_release_and_choice(self):
        self.memory_privilege_fixture()
        self.install()
        previous = (self.base / "current").resolve()
        self.env["OMZTTY_TEST_MEMORY_EXIT"] = "9"
        result = self.install(self.bundle("0.1.1"), memory_manager=True, ok=False)
        self.assertIn("zmem setup failed", result.stderr)
        self.assertEqual((self.base / "current").resolve(), previous)
        self.assertEqual((self.base / ".memory-manager-enabled").read_text(), "0\n")

    def test_memory_preference_symlink_is_rejected_without_privilege(self):
        self.memory_privilege_fixture()
        self.install()
        preference = self.base / ".memory-manager-enabled"
        preference.unlink()
        foreign = self.home / "foreign-memory-choice"
        foreign.write_text("1\n")
        preference.symlink_to(foreign)
        result = self.install(memory_manager=None, ok=False)
        self.assertIn("memory preference is not a regular file", result.stderr)
        self.assertFalse((self.home / "memory-sudo-args").exists())
        self.assertEqual(foreign.read_text(), "1\n")

    def test_update_preserves_memory_skip(self):
        self.memory_privilege_fixture()
        self.install()
        self.serve_update("0.1.1", self.bundle("0.1.1"))
        self.cli("update")
        self.assertFalse((self.home / "memory-sudo-args").exists())
        self.assertEqual((self.base / ".memory-manager-enabled").read_text(), "0\n")

    def test_update_can_enable_memory_manager(self):
        self.memory_privilege_fixture()
        self.install()
        self.serve_update("0.1.1", self.bundle("0.1.1"))
        self.cli("update", "--memory-manager")
        self.assertTrue((self.home / "memory-sudo-args").exists())
        self.assertEqual((self.base / ".memory-manager-enabled").read_text(), "1\n")

    def serve_update(self, version, archive):
        """Serve only the expected release URLs through a local curl stub."""
        downloads = self.work / "downloads"
        downloads.mkdir()
        installer = downloads / "install.sh"
        installer.write_text(re.sub(r"(?m)^VERSION=\S+$", "VERSION=" + version,
                                    (ROOT / "install.sh").read_text()))
        installer_digest = installer.with_name("install.sh.sha256")
        installer_digest.write_text(f"{sha(installer)}  install.sh\n")
        asset = downloads / f"oh-my-ztty-{version}-linux-{os.uname().machine}.tar.gz"
        shutil.copy2(archive, asset)
        asset_digest = asset.with_name(asset.name + ".sha256")
        asset_digest.write_text(f"{sha(asset)}  {asset.name}\n")
        release_url = "https://github.com/LIghtJUNction/oh-my-ztty/releases"
        installer_url = release_url + "/latest/download/install.sh"
        asset_url = release_url + f"/download/v{version}/{asset.name}"
        sources = {
            installer_url: str(installer),
            installer_url + ".sha256": str(installer_digest),
            asset_url: str(asset),
            asset_url + ".sha256": str(asset_digest),
        }
        mapping = downloads / "urls.json"
        mapping.write_text(json.dumps(sources))
        fake_bin = self.work / "fake-bin"
        fake_bin.mkdir()
        curl = fake_bin / "curl"
        curl.write_text(f"#!{sys.executable}\n" + """import json, os, shutil, sys
from pathlib import Path
args = sys.argv[1:]
urls = [arg for arg in args if arg.startswith("https://")]
sources = json.loads(Path(os.environ["OMZTTY_TEST_FETCH_MAP"]).read_text())
if len(urls) != 1 or urls[0] not in sources or args.count("-o") != 1:
    raise SystemExit("unexpected curl invocation: " + repr(args))
shutil.copyfile(sources[urls[0]], args[args.index("-o") + 1])
""")
        curl.chmod(0o755)
        self.env["OMZTTY_TEST_FETCH_MAP"] = str(mapping)
        self.env["PATH"] = str(fake_bin) + os.pathsep + self.env["PATH"]

    def cli(self, *args, ok=True):
        return self.run_command([self.bindir / "omztty", *args], ok)

    def test_repeat_and_shell_preserve_configuration(self):
        self.bindir.mkdir(parents=True)
        foreign = self.bindir / "ztty"
        foreign.write_text("user-owned")
        self.install()
        current_inode = (self.base / "current").lstat().st_ino
        first = (self.base / "current").resolve()
        self.install()
        self.assertEqual(current_inode, (self.base / "current").lstat().st_ino)
        self.assertEqual(first, (self.base / "current").resolve())
        self.assertEqual(foreign.read_text(), "user-owned")
        result = self.cli("shell", "-ic", 'print -rl -- "$ZSHARD_TEST" "$ZSHARD_CACHE_DIR" "$ZDOTDIR"')
        self.assertIn("loaded", result.stdout)
        expected_cache = self.home / ".cache/oh-my-ztty/zshard" / first.name
        expected_zdotdir = first / "config/zsh"
        self.assertEqual((self.home / "fixture-cache-dir").read_text().splitlines(), [str(expected_cache), str(expected_zdotdir)])
        self.assertEqual(result.stdout.strip().splitlines(), ["loaded", str(expected_cache), str(expected_zdotdir)])
        self.assertNotIn("UNWANTED_USER_RC", result.stdout)
        self.assertEqual((self.home / ".zshrc").read_text(), "print UNWANTED_USER_RC\n")
        desktop = self.data / "applications/oh-my-ztty.desktop"
        self.assertTrue(desktop.is_symlink())
        if shutil.which("desktop-file-validate"):
            self.run_command(["desktop-file-validate", desktop])

    def test_uninstall_removes_only_the_managed_shell_hook(self):
        self.install()
        profile = Path(self.env["XDG_CONFIG_HOME"]) / "oh-my-ztty/profile"
        profile.mkdir(parents=True)
        (profile / ".omztty-profile").write_text("omztty-profile-v1\n")
        original = (self.home / ".zshrc").read_bytes()
        self.cli("rc", "install")
        self.assertIn("# >>> oh-my-ztty shell >>>", (self.home / ".zshrc").read_text())
        self.cli("uninstall")
        self.assertEqual((self.home / ".zshrc").read_bytes(), original)
        self.assertFalse(self.base.exists())

    def test_uninstall_uses_the_portable_deployment_journal(self):
        self.install()
        profile = Path(self.env["XDG_CONFIG_HOME"]) / "oh-my-ztty/profile"
        profile.mkdir(parents=True)
        (profile / ".omztty-profile").write_text("omztty-profile-v1\n")
        (profile / ".config-layout").write_text("canonical-v1\n")
        journal = Path(self.env["XDG_STATE_HOME"]) / "zdot/oh-my-ztty/fixture"
        journal.mkdir(parents=True)
        (journal / "owner").write_text("fixture journal\n")
        executable = self.base / "current/bin/zdot"
        executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$HOME/remove-args"\n')
        self.cli("uninstall")
        args = (self.home / "remove-args").read_text().splitlines()
        self.assertEqual(args[args.index("--profile") + 1], ".omztty-target.zdot")

    def assert_real_completion_cache_reused(self, completion=None):
        settings = Path(self.env["XDG_CONFIG_HOME"]) / "oh-my-ztty"
        settings.mkdir(parents=True, exist_ok=True)
        for name in ("options", "local"):
            (settings / (name + ".zsh")).write_text(
                f'print -r -- {name} >> "$HOME/personal-hooks"\n')
        self.install(self.bundle("0.1.1", real_zshard=True))
        self.assertFalse((self.home / "personal-hooks").exists(),
                         "installation must not execute personal shell hooks")
        current = (self.base / "current").resolve()
        cache = self.home / ".cache/oh-my-ztty/zshard" / current.name
        def snapshot():
            return {p.name: (sha(p), p.stat().st_mtime_ns)
                    for p in cache.glob("zcompdump-*")}
        prepared = snapshot()
        self.assertTrue(prepared, "installer must prepare the audited completion dump")
        command = 'zshard complete || exit; print -r -- "$_ZSHARD_COMPLETION_READY"'
        if completion:
            command += '; print -r -- "$_comps[omztty-cache-test]"'
        result = self.cli("shell", "-ic", command)
        self.assertEqual(result.stdout.splitlines(), ["1"] + ([completion] if completion else []))
        self.assertEqual(snapshot(), prepared,
                         "first completion must reuse the prepared bytes and mtime")
        self.assertEqual((self.home / "personal-hooks").read_text().splitlines(),
                         ["options", "local"])

    def test_completion_cache_reused_with_missing_personal_directory(self):
        personal = self.home / ".config/oh-my-ztty/completions"
        self.assertFalse(personal.exists())
        self.assert_real_completion_cache_reused()
        self.assertFalse(personal.exists())

    def test_completion_cache_reused_with_custom_xdg_and_symlinked_inputs(self):
        self.env["XDG_CONFIG_HOME"] = str(self.home / "custom config")
        personal = Path(self.env["XDG_CONFIG_HOME"]) / "oh-my-ztty/completions"
        personal.parent.mkdir(parents=True)
        actual = self.home / "completion files"
        actual.mkdir()
        (actual / "_omztty_cache_test").write_text("#compdef omztty-cache-test\n_arguments '--example'\n")
        personal.symlink_to(actual, target_is_directory=True)
        self.data.mkdir(parents=True)
        alias = self.home / "data link"
        alias.symlink_to(self.data, target_is_directory=True)
        self.env["XDG_DATA_HOME"] = str(alias)
        self.assert_real_completion_cache_reused("_omztty_cache_test")

    def test_desktop_choice_survives_repeat_upgrade_and_reenable(self):
        desktop = self.data / "applications/oh-my-ztty.desktop"
        preference = self.base / ".desktop-enabled"
        self.install(desktop=False)
        self.assertFalse(desktop.is_symlink())
        self.assertEqual(preference.read_text(), "0\n")
        self.install()
        self.assertFalse(desktop.is_symlink())
        newer = self.bundle("0.1.1")
        self.install(newer)
        self.assertFalse(desktop.is_symlink())
        self.assertEqual(preference.read_text(), "0\n")
        self.install(newer, desktop=True)
        self.assertEqual(os.readlink(desktop), str(self.base / "oh-my-ztty.desktop"))
        self.assertEqual(preference.read_text(), "1\n")
        self.install(newer, desktop=False)
        self.assertFalse(desktop.is_symlink())
        self.assertFalse((self.base / ".desktop-path").exists())
        self.install(newer)
        self.assertFalse(desktop.is_symlink())
        self.assertEqual(preference.read_text(), "0\n")

    def test_update_preserves_desktop_choice_and_accepts_overrides(self):
        self.install(desktop=False)
        self.serve_update("0.1.1", self.bundle("0.1.1"))
        desktop = self.data / "applications/oh-my-ztty.desktop"
        preference = self.base / ".desktop-enabled"
        self.cli("update")
        self.assertIn("0.1.1", self.cli("version").stdout)
        self.assertFalse(desktop.is_symlink())
        self.assertEqual(preference.read_text(), "0\n")
        self.cli("update", "--desktop")
        self.assertEqual(os.readlink(desktop), str(self.base / "oh-my-ztty.desktop"))
        self.assertEqual(preference.read_text(), "1\n")
        self.cli("update", "--no-desktop")
        self.assertFalse(desktop.is_symlink())
        self.assertEqual(preference.read_text(), "0\n")
        result = self.cli("update", "--unknown", ok=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage: omztty update", result.stderr)

    def test_legacy_desktop_choice_is_migrated(self):
        newer = self.bundle("0.1.1")
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.install(desktop=enabled)
                # Old releases stored a desktop path only when the entry was enabled.
                preference = self.base / ".desktop-enabled"
                preference.unlink()
                self.install(newer)
                desktop = self.data / "applications/oh-my-ztty.desktop"
                self.assertEqual(desktop.is_symlink(), enabled)
                self.assertEqual(preference.read_text(), ("1" if enabled else "0") + "\n")
                self.cli("uninstall")

    def test_disabling_preserves_foreign_desktop_files_and_links(self):
        desktop = self.data / "applications/oh-my-ztty.desktop"
        foreign = self.home / "foreign.desktop"
        foreign.write_text("user-owned desktop entry\n")
        for kind in ("file", "symlink"):
            with self.subTest(kind=kind):
                self.install()
                desktop.unlink()
                if kind == "symlink":
                    desktop.symlink_to(foreign)
                else:
                    desktop.write_text(foreign.read_text())
                self.install(desktop=False)
                self.install()
                self.assertEqual(desktop.read_text(), foreign.read_text())
                self.assertEqual(desktop.is_symlink(), kind == "symlink")
                if kind == "symlink":
                    self.assertEqual(os.readlink(desktop), str(foreign))
                previous = os.readlink(self.base / "current")
                result = self.install(desktop=True, ok=False)
                self.assertIn("desktop entry already exists", result.stderr)
                self.assertEqual(os.readlink(self.base / "current"), previous)
                self.assertEqual((self.base / ".desktop-enabled").read_text(), "0\n")
                self.assertEqual(desktop.read_text(), "user-owned desktop entry\n")
                self.cli("uninstall")
                self.assertEqual(desktop.read_text(), foreign.read_text())
                desktop.unlink()

    def test_unreadable_desktop_record_preserves_installation(self):
        self.install()
        desktop = self.data / "applications/oh-my-ztty.desktop"
        record = self.base / ".desktop-path"
        preference = self.base / ".desktop-enabled"
        previous = os.readlink(self.base / "current")
        record_before = record.read_bytes()
        preference_before = preference.read_bytes()
        # Inject a read failure even when the test process can bypass file modes.
        fake_bin = self.work / "failing-cat-bin"
        fake_bin.mkdir()
        cat = fake_bin / "cat"
        cat.write_text(
            '#!/bin/sh\n'
            'if [ "$#" -eq 1 ] && [ "$1" = "$OMZTTY_TEST_DESKTOP_RECORD" ]; then exit 23; fi\n'
            'exec "$OMZTTY_TEST_REAL_CAT" "$@"\n'
        )
        cat.chmod(0o755)
        self.env["OMZTTY_TEST_REAL_CAT"] = shutil.which("cat", path=self.env["PATH"])
        self.env["OMZTTY_TEST_DESKTOP_RECORD"] = str(record)
        self.env["PATH"] = str(fake_bin) + os.pathsep + self.env["PATH"]
        result = self.install(desktop=False, ok=False)
        self.assertIn("cannot read recorded desktop entry path", result.stderr)
        self.assertEqual(os.readlink(self.base / "current"), previous)
        self.assertEqual(os.readlink(desktop), str(self.base / "oh-my-ztty.desktop"))
        self.assertEqual(record.read_bytes(), record_before)
        self.assertEqual(preference.read_bytes(), preference_before)

    def test_failed_preparation_preserves_desktop_preference(self):
        broken = self.bundle("0.1.1", warm_exit=12)
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.install(desktop=enabled)
                previous = os.readlink(self.base / "current")
                preference = (self.base / ".desktop-enabled").read_text()
                result = self.install(broken, desktop=not enabled, ok=False)
                self.assertIn("completion cache preparation failed", result.stderr)
                self.assertEqual(os.readlink(self.base / "current"), previous)
                self.assertEqual((self.base / ".desktop-enabled").read_text(), preference)
                self.assertEqual((self.data / "applications/oh-my-ztty.desktop").is_symlink(), enabled)
                self.cli("uninstall")

    def test_failed_first_preparation_does_not_record_desktop_choice(self):
        broken = self.bundle("0.1.1", warm_exit=12)
        self.install(broken, desktop=False, ok=False)
        self.assertFalse((self.base / ".desktop-enabled").exists())
        self.assertFalse((self.base / "current").is_symlink())
        self.install()
        self.assertTrue((self.data / "applications/oh-my-ztty.desktop").is_symlink())
        self.assertEqual((self.base / ".desktop-enabled").read_text(), "1\n")

    def test_checksum_failure_is_non_mutating(self):
        self.archive.with_name(self.archive.name + ".sha256").write_text("0" * 64 + "  fixture\n")
        self.install(ok=False)
        self.assertFalse(self.base.exists())
        self.assertFalse(self.bindir.exists())

    def test_upgrade_atomic_pointer_and_uninstall_ownership(self):
        self.install()
        second = self.bundle("0.1.1")
        self.install(second)
        self.assertEqual(os.readlink(self.base / "current"), "releases/0.1.1-linux-" + os.uname().machine)
        self.assertIn("0.1.1", self.cli("version").stdout)
        replacement = self.bindir / "zdot"
        replacement.unlink()
        replacement.write_text("replacement")
        config = self.home / ".config/oh-my-ztty/local.zsh"
        config.parent.mkdir(parents=True)
        config.write_text("user customization")
        history = self.home / ".local/state/oh-my-ztty/history"
        history.parent.mkdir(parents=True)
        history.write_text("user history")
        self.cli("uninstall")
        self.assertFalse(self.base.exists())
        self.assertFalse((self.bindir / "omztty").exists())
        self.assertEqual(replacement.read_text(), "replacement")
        self.assertEqual(config.read_text(), "user customization")
        self.assertEqual(history.read_text(), "user history")
        self.assertFalse((self.data / "applications/oh-my-ztty.desktop").is_symlink())

    def test_failed_cache_warm_preserves_previous_version(self):
        self.install()
        previous = os.readlink(self.base / "current")
        broken = self.bundle("0.1.1", warm_exit=12)
        result = self.install(broken, ok=False)
        self.assertIn("completion cache preparation failed", result.stderr)
        self.assertEqual(os.readlink(self.base / "current"), previous)
        self.assertIn("0.1.0", self.cli("version").stdout)

    def test_modified_release_is_preserved(self):
        self.install()
        binary = self.base / "current/bin/ztty"
        binary.write_text("edited by user")
        self.install(ok=False)
        self.assertEqual(binary.read_text(), "edited by user")

    def test_unowned_root_is_preserved(self):
        self.base.mkdir(parents=True)
        sentinel = self.base / "mine"
        sentinel.write_text("keep")
        self.install(ok=False)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_foreign_launcher_rejected_before_install(self):
        self.bindir.mkdir(parents=True)
        launcher = self.bindir / "omztty"
        launcher.write_text("unrelated")
        self.install(ok=False)
        self.assertFalse(self.base.exists())
        self.assertEqual(launcher.read_text(), "unrelated")

    def test_terminal_uses_suite_socket_and_preserves_arguments(self):
        self.install()
        binary = self.base / "current/bin/ztty"
        binary.write_text('#!/bin/sh\nprintf "%s\\n" "$ZTTY_SOCKET" "$@"\n')
        self.env["ZTTY_SOCKET"] = "@unrelated-running-terminal"
        direct = self.cli("ztty", "--version").stdout.splitlines()
        self.assertEqual(direct[0], f"@oh-my-ztty-{os.getuid()}-0.1.0")
        self.env["OMZTTY_SOCKET"] = "@suite-test-explicit"
        terminal = self.cli("terminal", "--geometry", "100x28").stdout.splitlines()
        self.assertEqual(terminal[0], "@suite-test-explicit")
        self.assertEqual(terminal[1], "--config")
        self.assertEqual(terminal[3:6], ["--geometry", "100x28", "-e"])
        self.assertEqual(terminal[-1], "shell")
        self.assertIn("home with spaces", terminal[-2])

    def test_archive_symlink_rejected(self):
        bad = self.work / "bad.tar.gz"
        with tarfile.open(bad, "w:gz") as tar:
            info = tarfile.TarInfo("oh-my-ztty/bin/escape")
            info.type = tarfile.SYMTYPE
            info.linkname = "/tmp"
            tar.addfile(info)
        bad.with_name(bad.name + ".sha256").write_text(f"{sha(bad)}  {bad.name}\n")
        self.install(bad, ok=False)
        self.assertFalse(self.base.exists())

if __name__ == "__main__":
    unittest.main()
