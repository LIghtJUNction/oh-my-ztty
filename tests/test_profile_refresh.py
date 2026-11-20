#!/usr/bin/env python3
"""Exercise profile refresh through real installer upgrades in temporary homes."""
from pathlib import Path
import os
import shutil
import stat
import tarfile
import unittest

import test_install

ROOT = Path(__file__).resolve().parents[1]


class ProfileRefresh(unittest.TestCase):
    def setUp(self):
        self.fixture = test_install.Installation()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.old = self.add_profile(self.fixture.archive, "0.1.0")

    def add_profile(self, archive, version, extra=False):
        f = self.fixture
        stage = f.work / ("stage-" + version) / "oh-my-ztty"
        shutil.copy2(ROOT / "bin/omztty-config", stage / "bin/omztty-config")
        defaults = stage / "components/zrc/profiles/ink"
        nvim = defaults / "files/.config/nvim/lua/zrc"
        nvim.mkdir(parents=True)
        for name in ("context.lua", "custom.lua", "removed.lua"):
            (nvim / name).write_text("-- shipped " + version + "\n")
        if extra:
            (nvim / "added.lua").write_text("-- new module\n")
        (defaults / "profile.zdot").write_text("files/.config/nvim\t.config/nvim\n")
        for rel in ("config/home/.zshrc", "config/ztty/config"):
            path = stage / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# shipped " + version + "\n")
        manifest = [f"{test_install.sha(p)}  {p.relative_to(stage)}"
                    for p in sorted(stage.rglob("*"))
                    if p.is_file() and p.name != "MANIFEST.sha256"]
        (stage / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n")
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(stage, arcname="oh-my-ztty")
        archive.with_name(archive.name + ".sha256").write_text(
            f"{test_install.sha(archive)}  {archive.name}\n")
        return archive

    def initialize(self):
        f = self.fixture
        f.install(self.old)
        f.cli("config", "init")
        self.profile = Path(f.env["XDG_CONFIG_HOME"]) / "oh-my-ztty/profile"
        self.files = self.profile / "files"
        self.nvim = self.files / ".config/nvim/lua/zrc"
        self.baseline = (f.base / "current").resolve()

    def upgrade(self, extra=False):
        f = self.fixture
        archive = self.add_profile(f.bundle("0.1.1"), "0.1.1", extra)
        f.install(archive)

    def snapshot(self, path):
        return {str(p.relative_to(path)):
                (os.readlink(p) if p.is_symlink()
                 else p.read_bytes() if p.is_file() else None,
                 p.lstat().st_mode, p.lstat().st_mtime_ns, p.lstat().st_ino)
                for p in path.rglob("*")}

    def exercise_refresh(self):
        f = self.fixture
        self.initialize()
        manifest = self.profile / "profile.zdot"
        manifest.write_text(manifest.read_text() + "files/personal\t.personal\n")
        before_manifest = manifest.read_bytes()
        (self.files / "personal").write_text("personal additions\n")
        (self.nvim / "custom.lua").write_text("-- my custom setting\n")
        (self.nvim / "removed.lua").unlink()
        context = self.nvim / "context.lua"
        context.chmod(0o640)
        owner = context.stat().st_uid
        local = self.profile.parent / "local.zsh"
        local.write_text('print UNEXPECTED > "$HOME/refresh-executed-hook"\n')

        # Model an adopted directory and a separate zdot journal. Refresh must
        # change source bytes without replacing links or the deployment record.
        mapped = Path(f.env["XDG_CONFIG_HOME"]) / "nvim"
        mapped.symlink_to(self.files / ".config/nvim", target_is_directory=True)
        mapped_inode = mapped.lstat().st_ino
        journal = Path(f.env["XDG_STATE_HOME"]) / "zdot/oh-my-ztty/state"
        journal.parent.mkdir(parents=True)
        journal.write_text("original deployment and backups\n")
        original_journal = self.snapshot(journal.parent)
        self.upgrade()
        self.assertEqual(context.read_text(), "-- shipped 0.1.0\n")
        result = f.cli("config", "refresh")
        self.assertIn("updated   files/.config/nvim/lua/zrc/context.lua", result.stdout)
        self.assertIn("preserved files/.config/nvim/lua/zrc/custom.lua", result.stdout)
        self.assertEqual(context.read_text(), "-- shipped 0.1.1\n")
        self.assertEqual(stat.S_IMODE(context.stat().st_mode), 0o640)
        self.assertEqual(context.stat().st_uid, owner)
        self.assertEqual((self.nvim / "custom.lua").read_text(), "-- my custom setting\n")
        self.assertFalse((self.nvim / "removed.lua").exists())
        self.assertEqual((self.files / "personal").read_text(), "personal additions\n")
        self.assertEqual(manifest.read_bytes(), before_manifest)
        self.assertEqual(self.snapshot(journal.parent), original_journal)
        self.assertEqual(mapped.lstat().st_ino, mapped_inode)
        self.assertEqual((mapped / "lua/zrc/context.lua").read_text(), "-- shipped 0.1.1\n")
        self.assertEqual((self.profile / ".suite-version").read_text(), "0.1.1\n")
        self.assertFalse((f.home / "refresh-executed-hook").exists())
        baseline = self.profile / ".baseline"
        self.assertEqual((baseline / ".suite-version").read_text(), "0.1.1\n")
        self.assertEqual((baseline / "files/.config/nvim/lua/zrc/custom.lua").read_text(),
                         "-- shipped 0.1.1\n")
        self.assertEqual((baseline / "files/.config/nvim/lua/zrc/removed.lua").read_text(),
                         "-- shipped 0.1.1\n")
        self.assertFalse((baseline / "files/personal").exists())
        self.assertNotIn("personal", (baseline / "profile.zdot").read_text())
        before = self.snapshot(self.profile)
        self.assertIn("already suite", f.cli("config", "refresh").stdout)
        self.assertEqual(self.snapshot(self.profile), before)

    def test_upgrade_refresh_preserves_customization_and_deployment(self):
        self.exercise_refresh()

    def test_refresh_with_custom_xdg_directory(self):
        self.fixture.env["XDG_CONFIG_HOME"] = str(self.fixture.home / "custom config")
        self.exercise_refresh()
        self.assertFalse((self.fixture.home / ".config/nvim").exists())

    def test_missing_baseline_rejects_without_edits(self):
        self.initialize()
        shutil.rmtree(self.profile / ".baseline")
        self.upgrade()
        shutil.rmtree(self.baseline)
        before = self.snapshot(self.profile)
        result = self.fixture.cli("config", "refresh", ok=False)
        self.assertIn("baseline release 0.1.0 is unavailable", result.stderr)
        self.assertEqual(self.snapshot(self.profile), before)

    def test_modified_baseline_rejects_without_edits(self):
        self.initialize()
        shutil.rmtree(self.profile / ".baseline")
        self.upgrade()
        (self.baseline / "config/ztty/config").write_text("changed release\n")
        before = self.snapshot(self.profile)
        result = self.fixture.cli("config", "refresh", ok=False)
        self.assertIn("release defaults were modified", result.stderr)
        self.assertEqual(self.snapshot(self.profile), before)

    def test_symlinked_source_file_preserved(self):
        self.initialize()
        original = self.nvim / "context.lua"
        external = self.fixture.home / "personal context.lua"
        original.rename(external)
        original.symlink_to(external)
        link_inode = original.lstat().st_ino
        self.upgrade()
        self.fixture.cli("config", "refresh")
        self.assertEqual(original.lstat().st_ino, link_inode)
        self.assertEqual(external.read_text(), "-- shipped 0.1.0\n")

    def test_symlinked_source_directory_not_traversed(self):
        self.initialize()
        source = self.files / ".config/nvim"
        external = self.fixture.home / "personal nvim"
        source.rename(external)
        source.symlink_to(external, target_is_directory=True)
        before = self.snapshot(external)
        link_inode = source.lstat().st_ino
        self.upgrade()
        self.fixture.cli("config", "refresh")
        self.assertEqual(source.lstat().st_ino, link_inode)
        self.assertEqual(self.snapshot(external), before)

    def test_changed_default_layout_rejects_without_edits(self):
        self.initialize()
        self.upgrade(extra=True)
        before = self.snapshot(self.profile)
        result = self.fixture.cli("config", "refresh", ok=False)
        self.assertIn("default file layout changed", result.stderr)
        self.assertEqual(self.snapshot(self.profile), before)
        self.assertEqual(list(self.profile.parent.glob(".refresh.*")), [])

    def test_saved_baseline_survives_removal_of_old_release(self):
        self.initialize()
        self.upgrade()
        shutil.rmtree(self.baseline)
        self.fixture.cli("config", "refresh")
        self.assertEqual((self.nvim / "context.lua").read_text(), "-- shipped 0.1.1\n")
        self.assertEqual((self.profile / ".baseline/.suite-version").read_text(), "0.1.1\n")

    def test_legacy_release_fallback_creates_snapshot(self):
        self.initialize()
        shutil.rmtree(self.profile / ".baseline")
        self.upgrade()
        self.fixture.cli("config", "refresh")
        self.assertEqual((self.nvim / "context.lua").read_text(), "-- shipped 0.1.1\n")
        self.assertEqual((self.profile / ".baseline/.suite-version").read_text(), "0.1.1\n")
        before = self.snapshot(self.profile)
        self.fixture.cli("config", "refresh")
        self.assertEqual(self.snapshot(self.profile), before)

    def test_system_runtime_replaced_in_place(self):
        f = self.fixture
        runtime = f.work / "system/usr/lib/oh-my-ztty"
        shutil.copytree(f.work / "stage-0.1.0/oh-my-ztty", runtime)
        f.run_command(["sh", runtime / "bin/omztty", "config", "init"])
        profile = Path(f.env["XDG_CONFIG_HOME"]) / "oh-my-ztty/profile"
        context = profile / "files/.config/nvim/lua/zrc/context.lua"
        self.assertEqual(context.read_text(), "-- shipped 0.1.0\n")
        self.add_profile(f.bundle("0.1.1"), "0.1.1")
        shutil.rmtree(runtime)
        shutil.copytree(f.work / "stage-0.1.1/oh-my-ztty", runtime)
        self.assertFalse(f.base.exists(), "no versioned per-user runtime is available")
        f.run_command(["sh", runtime / "bin/omztty", "config", "refresh"])
        self.assertEqual(context.read_text(), "-- shipped 0.1.1\n")
        self.assertEqual((profile / ".baseline/.suite-version").read_text(), "0.1.1\n")

    def test_changed_saved_baseline_rejected_without_fallback(self):
        self.initialize()
        self.upgrade()
        (self.profile / ".baseline/files/.config/nvim/lua/zrc/context.lua").write_text("changed\n")
        before = self.snapshot(self.profile)
        result = self.fixture.cli("config", "refresh", ok=False)
        self.assertIn("profile baseline verification failed", result.stderr)
        self.assertEqual(self.snapshot(self.profile), before)

    def test_saved_baseline_version_must_match_profile(self):
        self.initialize()
        self.upgrade()
        (self.profile / ".baseline/.suite-version").write_text("9.9.9\n")
        before = self.snapshot(self.profile)
        result = self.fixture.cli("config", "refresh", ok=False)
        self.assertIn("profile baseline version does not match", result.stderr)
        self.assertEqual(self.snapshot(self.profile), before)

    def test_saved_baseline_symlink_rejected_even_without_upgrade(self):
        self.initialize()
        baseline = self.profile / ".baseline"
        external = self.fixture.home / "external defaults"
        baseline.rename(external)
        baseline.symlink_to(external, target_is_directory=True)
        before = self.snapshot(self.profile)
        result = self.fixture.cli("config", "refresh", ok=False)
        self.assertIn("profile baseline must be an owned directory", result.stderr)
        self.assertEqual(self.snapshot(self.profile), before)

    def test_baseline_and_version_stay_paired_after_publication_failure(self):
        f = self.fixture
        self.initialize()
        self.upgrade()
        before_baseline = self.snapshot(self.profile / ".baseline")
        fake_bin = f.work / "failing mv"
        fake_bin.mkdir()
        wrapper = fake_bin / "mv"
        wrapper.write_text(
            '#!/bin/sh\n'
            'if [ "$#" -eq 4 ] && [ "$1" = -Tf ] && '
            '[ "$4" = "$OMZTTY_TEST_VERSION_FILE" ]; then exit 23; fi\n'
            'exec "$OMZTTY_TEST_REAL_MV" "$@"\n')
        wrapper.chmod(0o755)
        previous_path = f.env["PATH"]
        f.env["OMZTTY_TEST_REAL_MV"] = shutil.which("mv", path=previous_path)
        f.env["OMZTTY_TEST_VERSION_FILE"] = str(self.profile / ".suite-version")
        f.env["PATH"] = str(fake_bin) + os.pathsep + previous_path
        f.cli("config", "refresh", ok=False)
        self.assertEqual((self.profile / ".suite-version").read_text(), "0.1.0\n")
        self.assertEqual(self.snapshot(self.profile / ".baseline"), before_baseline)
        self.assertEqual(list(self.profile.parent.glob(".refresh.*")), [])
        f.env["PATH"] = previous_path
        f.cli("config", "refresh")
        self.assertEqual((self.profile / ".suite-version").read_text(), "0.1.1\n")
        self.assertEqual((self.profile / ".baseline/.suite-version").read_text(), "0.1.1\n")

    def test_symlinked_baseline_marker_rejected(self):
        self.initialize()
        self.upgrade()
        marker = self.profile / ".suite-version"
        external = self.fixture.home / "my-version"
        marker.rename(external)
        marker.symlink_to(external)
        before = self.snapshot(self.profile)
        result = self.fixture.cli("config", "refresh", ok=False)
        self.assertIn("no regular .suite-version baseline", result.stderr)
        self.assertEqual(self.snapshot(self.profile), before)
        self.assertEqual(external.read_text(), "0.1.0\n")


if __name__ == "__main__":
    unittest.main()
