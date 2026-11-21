"""Exercise default-branch synchronization with real repositories and fixture-only file remotes."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workspace.py"


class WorkspaceFixture:
    def __init__(self, component="ztty"):
        cache = SCRIPT.parent.parent / ".cache" / "workspace-tests"
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="sync fixture ", dir=cache)
        self.base = Path(self.temp.name)
        self.component = component
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_")}
        empty_config = self.base / "empty.gitconfig"
        empty_config.write_text("")
        self.env.update({
            "GIT_CONFIG_GLOBAL": str(empty_config),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "3",
            "GIT_CONFIG_KEY_0": "protocol.file.allow",
            "GIT_CONFIG_VALUE_0": "always",
            "GIT_CONFIG_KEY_1": "commit.gpgsign",
            "GIT_CONFIG_VALUE_1": "false",
            "GIT_CONFIG_KEY_2": "submodule.recurse",
            "GIT_CONFIG_VALUE_2": "false",
            "GIT_AUTHOR_NAME": "Workspace fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Workspace fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        })
        self.leaf_remote = self.repo("leaf remote")
        (self.leaf_remote / "value").write_text("old leaf\n")
        self.leaf_old = self.commit(self.leaf_remote, "Old leaf")
        self.nested_remote = self.repo("nested remote")
        (self.nested_remote / ".gitignore").write_text("cache/\n")
        self.git(self.nested_remote, "submodule", "add", str(self.leaf_remote), "deps/leaf")
        self.nested_old = self.commit(self.nested_remote, "Old nested module")
        self.upstream = self.repo("component remote")
        (self.upstream / ".gitignore").write_text("cache/\n")
        (self.upstream / "value").write_text("old component\n")
        inline = self.upstream / "vendor/extracted"
        inline.mkdir(parents=True)
        (inline / "value").write_text("previously inline source\n")
        self.git(self.upstream, "submodule", "add", str(self.nested_remote), "deps/existing")
        self.old_head = self.commit(self.upstream, "Old component")
        self.git(self.upstream, "tag", "v1.0.0")
        self.root = self.repo("suite with spaces")
        (self.root / "scripts").mkdir()
        shutil.copy2(SCRIPT, self.root / "scripts/workspace.py")
        (self.root / ".gitignore").write_text(".cache/\n")
        self.lock_path = self.root / "dependencies.lock.json"
        lock = {"schema": 2, "updated_at": "2026-11-21T00:00:00+00:00",
                "components": {component: {
                    "repository": f"https://github.com/LIghtJUNction/{component}.git",
                    "branch": "main", "commit": self.old_head}}}
        self.lock_path.write_text(json.dumps(lock, indent=2) + "\n")
        self.commit(self.root, "Suite files")
        self.git(self.root, "submodule", "add", str(self.upstream), "components/" + component)
        self.commit(self.root, "Old source pin")
        self.git(self.root, "submodule", "update", "--init", "--recursive")
        self.path = self.root / "components" / component
        self.nested = self.path / "deps/existing"
        self.leaf = self.nested / "deps/leaf"
        self.git(self.nested, "checkout", "-b", "kept-nested")
        self.git(self.leaf, "checkout", "-b", "kept-leaf")
        self.original_lock = self.lock_path.read_bytes()
        self.original_branch = self.git(self.path, "symbolic-ref", "--short", "HEAD")
        self.env["GIT_CONFIG_COUNT"] = "4"
        self.env["GIT_CONFIG_KEY_3"] = f"url.{self.upstream}.insteadOf"
        self.env["GIT_CONFIG_VALUE_3"] = f"https://github.com/LIghtJUNction/{component}.git"

    def close(self):
        self.temp.cleanup()

    def command(self, args, cwd, check=True):
        result = subprocess.run(args, cwd=cwd, env=self.env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and result.returncode:
            raise AssertionError(f"{args!r}\n{result.stdout}\n{result.stderr}")
        return result

    def git(self, cwd, *args):
        return self.command(["git", *args], cwd).stdout.strip()

    def repo(self, name):
        path = self.base / name
        path.mkdir()
        self.git(path, "init", "--quiet", "--initial-branch=main")
        return path

    def commit(self, path, message):
        self.git(path, "add", "--all")
        self.git(path, "commit", "--quiet", "-m", message)
        return self.git(path, "rev-parse", "HEAD")

    def new_release(self, broken=False, extracted=False, cache_collision=False):
        (self.leaf_remote / "value").write_text("new leaf\n")
        self.leaf_new = self.commit(self.leaf_remote, "New leaf")
        nested_leaf = self.nested_remote / "deps/leaf"
        self.git(nested_leaf, "fetch", "origin")
        self.git(nested_leaf, "checkout", "--detach", self.leaf_new)
        if broken:
            self.git(self.nested_remote, "config", "-f", ".gitmodules",
                     "submodule.broken.path", "deps/broken")
            self.git(self.nested_remote, "config", "-f", ".gitmodules",
                     "submodule.broken.url", str(self.base / "missing remote"))
            self.git(self.nested_remote, "update-index", "--add", "--cacheinfo",
                     "160000," + self.leaf_new + ",deps/broken")
        # Keep the deliberately missing gitlink in the index for failure tests.
        self.git(self.nested_remote, "add", ".gitmodules", "deps/leaf")
        self.git(self.nested_remote, "commit", "--quiet", "-m", "New nested module")
        self.nested_new = self.git(self.nested_remote, "rev-parse", "HEAD")
        self.new_remote = self.repo("new module remote")
        self.git(self.new_remote, "submodule", "add", str(self.leaf_remote), "deeper/leaf")
        self.new_module_head = self.commit(self.new_remote, "New recursive module")
        upstream_nested = self.upstream / "deps/existing"
        self.git(upstream_nested, "fetch", "origin")
        self.git(upstream_nested, "checkout", "--detach", self.nested_new)
        self.git(self.upstream, "submodule", "add", str(self.new_remote), "deps/new")
        if extracted:
            self.git(self.upstream, "rm", "-r", "vendor/extracted")
            self.git(self.upstream, "submodule", "add", str(self.new_remote), "vendor/extracted")
        if cache_collision:
            (self.upstream / "cache").mkdir()
            (self.upstream / "cache/keep").write_text("new tracked source\n")
            self.git(self.upstream, "add", "--force", "cache/keep")
        (self.upstream / "value").write_text("new component\n")
        self.new_head = self.commit(self.upstream, "New component release")
        self.git(self.upstream, "tag", "v1.1.0")
        return self.new_head

    def hook(self, content):
        location = Path(self.git(self.path, "rev-parse", "--git-path", "hooks/post-checkout"))
        if not location.is_absolute():
            location = self.path / location
        location.write_text("#!/bin/sh\n" + content)
        location.chmod(0o755)

    def sync(self):
        return self.command([sys.executable, "scripts/workspace.py", "sync",
                             self.component], self.root, check=False)

    def add_suite_components(self):
        components = {self.component: {"upstream": self.upstream,
                                      "path": self.path,
                                      "old_head": self.old_head,
                                      "branch": self.original_branch}}
        for name in ("ssmcp", "zshard", "zdot", "zrc", "zfetch", "zmem"):
            upstream = self.repo(name + " remote")
            (upstream / "value").write_text("old " + name + "\n")
            old_head = self.commit(upstream, "Old " + name)
            self.git(self.root, "submodule", "add", str(upstream), "components/" + name)
            path = self.root / "components" / name
            components[name] = {"upstream": upstream, "path": path,
                                "old_head": old_head,
                                "branch": self.git(path, "symbolic-ref", "--short", "HEAD")}
            index = int(self.env["GIT_CONFIG_COUNT"])
            self.env["GIT_CONFIG_COUNT"] = str(index + 1)
            self.env[f"GIT_CONFIG_KEY_{index}"] = f"url.{upstream}.insteadOf"
            self.env[f"GIT_CONFIG_VALUE_{index}"] = f"https://github.com/LIghtJUNction/{name}.git"
        self.commit(self.root, "Add remaining suite components")
        return components

    def sync_all(self):
        return self.command([sys.executable, "scripts/workspace.py", "sync"],
                            self.root, check=False)

    def assert_old(self, test, expected_lock=None):
        test.assertEqual(self.git(self.path, "rev-parse", "HEAD"), self.old_head)
        test.assertEqual(self.git(self.path, "symbolic-ref", "--short", "HEAD"),
                         self.original_branch)
        test.assertEqual(self.git(self.nested, "rev-parse", "HEAD"), self.nested_old)
        test.assertEqual(self.git(self.nested, "symbolic-ref", "--short", "HEAD"), "kept-nested")
        test.assertEqual(self.git(self.leaf, "rev-parse", "HEAD"), self.leaf_old)
        test.assertEqual(self.git(self.leaf, "symbolic-ref", "--short", "HEAD"), "kept-leaf")
        test.assertEqual(self.lock_path.read_bytes(),
                         self.original_lock if expected_lock is None else expected_lock)


class WorkspaceSyncTests(unittest.TestCase):
    def fixture(self, component="ztty"):
        fixture = WorkspaceFixture(component)
        self.addCleanup(fixture.close)
        return fixture

    def test_initializes_new_recursive_modules_and_keeps_top_level_cache(self):
        f = self.fixture()
        f.new_release()
        (f.path / "cache").mkdir()
        (f.path / "cache/keep").write_text("top-level build cache\n")
        temporary_name = f.root / "dependencies.lock.json.new"
        temporary_name.write_text("unrelated file\n")
        result = f.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(f.git(f.path, "rev-parse", "HEAD"), f.new_head)
        self.assertEqual(f.git(f.nested, "rev-parse", "HEAD"), f.nested_new)
        self.assertEqual(f.git(f.leaf, "rev-parse", "HEAD"), f.leaf_new)
        fresh = f.path / "deps/new"
        self.assertEqual(f.git(fresh, "rev-parse", "HEAD"), f.new_module_head)
        self.assertEqual(f.git(fresh / "deeper/leaf", "rev-parse", "HEAD"), f.leaf_new)
        self.assertEqual((f.path / "cache/keep").read_text(), "top-level build cache\n")
        self.assertEqual(temporary_name.read_text(), "unrelated file\n")
        self.assertEqual(json.loads(f.lock_path.read_text())["components"]["ztty"]["commit"], f.new_head)
        self.assertEqual(f.git(f.path, "status", "--porcelain", "--ignore-submodules=none"), "")


    def test_extracts_inline_directory_into_recursive_submodule(self):
        f = self.fixture()
        f.new_release(extracted=True)
        result = f.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        extracted = f.path / "vendor/extracted"
        self.assertEqual(f.git(extracted, "rev-parse", "HEAD"), f.new_module_head)
        self.assertEqual(f.git(extracted / "deeper/leaf", "rev-parse", "HEAD"), f.leaf_new)
        self.assertFalse((extracted / "value").exists())
        self.assertEqual(f.git(f.path, "status", "--porcelain", "--ignore-submodules=none"), "")

    def test_top_level_ignored_file_collision_preserves_cache_and_old_state(self):
        f = self.fixture()
        f.new_release(cache_collision=True)
        (f.path / "cache").mkdir()
        (f.path / "cache/keep").write_text("local build cache\n")
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("would be overwritten by checkout", result.stderr)
        self.assertEqual((f.path / "cache/keep").read_text(), "local build cache\n")
        f.assert_old(self)

    def test_new_submodule_path_does_not_take_over_ignored_directory(self):
        f = self.fixture()
        f.new_release()
        exclude = Path(f.git(f.path, "rev-parse", "--git-path", "info/exclude"))
        if not exclude.is_absolute():
            exclude = f.path / exclude
        exclude.write_text(exclude.read_text() + "\ndeps/new/\n")
        (f.path / "deps/new").mkdir()
        (f.path / "deps/new/keep").write_text("pre-existing ignored contents\n")
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("New submodule directory is not empty", result.stderr)
        self.assertIn("Additional submodule directories retained for inspection", result.stderr)
        self.assertEqual((f.path / "deps/new/keep").read_text(), "pre-existing ignored contents\n")
        f.assert_old(self)


    def test_new_submodule_path_does_not_take_over_ignored_repository(self):
        f = self.fixture()
        f.new_release()
        exclude = Path(f.git(f.path, "rev-parse", "--git-path", "info/exclude"))
        if not exclude.is_absolute():
            exclude = f.path / exclude
        exclude.write_text(exclude.read_text() + "\ndeps/new/\n")
        target = f.path / "deps/new"
        f.git(f.path, "clone", str(f.leaf_remote), str(target))
        f.git(target, "checkout", "-b", "local-work")
        local_head = f.git(target, "rev-parse", "HEAD")
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("New submodule directory is not empty", result.stderr)
        self.assertEqual(f.git(target, "rev-parse", "HEAD"), local_head)
        self.assertEqual(f.git(target, "symbolic-ref", "--short", "HEAD"), "local-work")
        self.assertEqual((target / "value").read_text(), "new leaf\n")
        f.assert_old(self)

    def test_default_branch_sync_for_shell_component(self):
        f = self.fixture("zshard")
        f.new_release()
        result = f.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((f.path / "deps/new/deeper/leaf/.git").exists())
        self.assertEqual(json.loads(f.lock_path.read_text())["components"]["zshard"]["commit"], f.new_head)

    def test_nested_source_changes_are_not_hidden_by_ignore_configuration(self):
        f = self.fixture()
        f.new_release()
        f.git(f.path, "config", "submodule.deps/existing.ignore", "all")
        f.git(f.nested, "config", "submodule.deps/leaf.ignore", "all")
        (f.leaf / "value").write_text("local source edit\n")
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source changes", result.stderr)
        self.assertEqual((f.leaf / "value").read_text(), "local source edit\n")
        f.assert_old(self)

    def test_ignored_nested_cache_is_preserved_with_precise_error(self):
        f = self.fixture()
        f.new_release()
        (f.nested / "cache").mkdir()
        (f.nested / "cache/keep").write_text("nested build cache\n")
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ignored paths (possibly build caches)", result.stderr)
        self.assertIn("cache/", result.stderr)
        self.assertEqual((f.nested / "cache/keep").read_text(), "nested build cache\n")
        f.assert_old(self)

    def test_uninitialized_nonempty_submodule_directory_is_preserved(self):
        f = self.fixture()
        f.new_release()
        f.git(f.path, "submodule", "deinit", "--", "deps/existing")
        (f.nested / "keep").write_text("pre-existing data\n")
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Uninitialized submodule directory is not empty", result.stderr)
        self.assertEqual((f.nested / "keep").read_text(), "pre-existing data\n")
        self.assertEqual(f.git(f.path, "rev-parse", "HEAD"), f.old_head)
        self.assertEqual(f.lock_path.read_bytes(), f.original_lock)

    def test_dirty_dependency_lock_is_not_overwritten(self):
        f = self.fixture()
        f.new_release()
        edited = f.original_lock + b"\n"
        f.lock_path.write_bytes(edited)
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dependencies.lock.json changes first", result.stderr)
        f.assert_old(self, edited)

    def test_recursive_failure_restores_old_heads_branches_urls_and_lock(self):
        f = self.fixture()
        f.new_release(broken=True)
        configured_url = str(f.base / "custom mirror retained")
        f.git(f.path, "config", "submodule.deps/existing.url", configured_url)
        f.git(f.nested, "config", "remote.origin.url", configured_url)
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Sync ztty failed", result.stderr)
        self.assertIn("Previous source commits and checkout branches restored", result.stderr)
        self.assertIn("Additional submodule directories retained for inspection", result.stderr)
        self.assertTrue((f.path / "deps/new/.git").exists())
        self.assertEqual(f.git(f.path, "config", "submodule.deps/existing.url"), configured_url)
        self.assertEqual(f.git(f.nested, "config", "remote.origin.url"), configured_url)
        f.assert_old(self)

    def test_lock_changed_during_sync_is_preserved_and_sources_are_restored(self):
        f = self.fixture()
        f.new_release()
        edited = b"concurrent lock edit\n"
        f.hook(f'if [ "$2" = {shlex.quote(f.new_head)} ]; then\n'
               f"  printf 'concurrent lock edit\\n' > {shlex.quote(str(f.lock_path))}\n"
               "fi\n")
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("changed during sync; it was preserved", result.stderr)
        f.assert_old(self, edited)

    def test_rollback_failure_reports_both_errors_and_keeps_conflicting_edit(self):
        f = self.fixture()
        f.new_release()
        f.hook(f'if [ "$2" = {shlex.quote(f.new_head)} ]; then\n'
               "  printf 'concurrent source edit\\n' > value\n"
               "fi\n")
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("selected source tree is not clean", result.stderr)
        self.assertIn("Rollback incomplete", result.stderr)
        self.assertEqual((f.path / "value").read_text(), "concurrent source edit\n")
        self.assertEqual(f.lock_path.read_bytes(), f.original_lock)

    def test_remote_default_branch_overrides_stale_origin_head(self):
        f = self.fixture()
        f.new_release()
        f.git(f.upstream, "branch", "-m", "trunk")
        result = f.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads(f.lock_path.read_text())["components"]["ztty"]
        self.assertEqual(record["branch"], "trunk")
        self.assertEqual(record["commit"], f.new_head)
        self.assertIn("observed_at", record)
        self.assertNotIn("assets", record)
        self.assertNotIn("tag", record)

    def test_next_sync_refreshes_the_default_branch_instead_of_reusing_lock(self):
        f = self.fixture()
        f.new_release()
        result = f.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        f.commit(f.root, "Record source sync")
        (f.upstream / "value").write_text("latest source without a release tag\n")
        newest = f.commit(f.upstream, "Move default branch")
        result = f.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(f.git(f.path, "rev-parse", "HEAD"), newest)
        self.assertEqual(json.loads(f.lock_path.read_text())["components"]["ztty"]["commit"], newest)

    def test_partial_migration_does_not_invent_unobserved_component_sources(self):
        f = self.fixture()
        legacy = {"schema": 1, "components": {"ztty": {"tag": "v1.0.0"}}}
        f.lock_path.write_text(json.dumps(legacy) + "\n")
        f.commit(f.root, "Legacy release lock")
        previous = f.lock_path.read_bytes()
        result = f.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("without a component", result.stderr)
        self.assertEqual(f.lock_path.read_bytes(), previous)
        self.assertEqual(f.git(f.path, "rev-parse", "HEAD"), f.old_head)

    def test_all_components_are_checked_before_the_first_checkout(self):
        f = self.fixture()
        components = f.add_suite_components()
        f.new_release()
        marker = f.base / "first checkout"
        f.hook(f"printf '%s\\n' \"$2\" >> {shlex.quote(str(marker))}\n")
        last = components["zmem"]
        (last["path"] / "value").write_text("uncommitted zmem work\n")
        result = f.sync_all()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source changes in components/zmem", result.stderr)
        self.assertFalse(marker.exists(), "A component was checked out before preflight finished")
        self.assertEqual((last["path"] / "value").read_text(), "uncommitted zmem work\n")
        f.assert_old(self)
        for component in components.values():
            self.assertEqual(f.git(component["path"], "rev-parse", "HEAD"), component["old_head"])
            self.assertEqual(f.git(component["path"], "symbolic-ref", "--short", "HEAD"),
                             component["branch"])

    def test_second_component_recursive_failure_restores_the_whole_sync(self):
        f = self.fixture()
        components = f.add_suite_components()
        f.new_release()
        marker = f.base / "first checkout"
        f.hook(f"printf '%s\\n' \"$2\" >> {shlex.quote(str(marker))}\n")
        second = components["ssmcp"]
        remote = second["upstream"]
        (remote / "value").write_text("new ssmcp\n")
        f.git(remote, "config", "-f", ".gitmodules", "submodule.broken.path", "deps/broken")
        f.git(remote, "config", "-f", ".gitmodules", "submodule.broken.url",
              str(f.base / "missing second component remote"))
        f.git(remote, "update-index", "--add", "--cacheinfo",
              "160000," + f.leaf_new + ",deps/broken")
        f.git(remote, "add", ".gitmodules", "value")
        f.git(remote, "commit", "--quiet", "-m", "Add unavailable recursive dependency")
        result = f.sync_all()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing second component remote", result.stderr)
        self.assertIn("Previous source commits and checkout branches restored", result.stderr)
        visited = marker.read_text().splitlines()
        self.assertIn(f.new_head, visited)
        self.assertEqual(visited[-1], f.old_head)
        f.assert_old(self)
        for component in components.values():
            self.assertEqual(f.git(component["path"], "rev-parse", "HEAD"), component["old_head"])
            self.assertEqual(f.git(component["path"], "symbolic-ref", "--short", "HEAD"),
                             component["branch"])
        self.assertEqual((second["path"] / "value").read_text(), "old ssmcp\n")
        self.assertFalse((second["path"] / ".gitmodules").exists())

    def test_full_sync_migrates_legacy_assets_to_all_seven_source_records(self):
        f = self.fixture()
        components = f.add_suite_components()
        legacy = {"schema": 1, "components": {
            name: {"tag": "v1.0.0", "assets": {"x86_64": {"url": "legacy asset"}}}
            for name in ("ztty", "ssmcp")}}
        f.lock_path.write_text(json.dumps(legacy) + "\n")
        f.commit(f.root, "Use legacy release asset lock")
        f.new_release()
        expected = {"ztty": f.new_head}
        for name, component in components.items():
            if name != "ztty":
                (component["upstream"] / "value").write_text("latest " + name + "\n")
                expected[name] = f.commit(component["upstream"], "Advance " + name)
        result = f.sync_all()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lock = json.loads(f.lock_path.read_text())
        self.assertEqual(lock["schema"], 2)
        self.assertIn("updated_at", lock)
        self.assertEqual(set(lock["components"]), set(components))
        for name, component in components.items():
            record = lock["components"][name]
            self.assertEqual(record["repository"], f"https://github.com/LIghtJUNction/{name}.git")
            self.assertEqual(record["branch"], "main")
            self.assertEqual(record["commit"], expected[name])
            self.assertEqual(f.git(component["path"], "rev-parse", "HEAD"), expected[name])
            self.assertIn("observed_at", record)
            self.assertNotIn("tag", record)
            self.assertNotIn("assets", record)


if __name__ == "__main__":
    unittest.main()
