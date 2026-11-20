"""Verify source-locked builds and the contents of a complete suite archive."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/build_bundle.py"
SPEC = importlib.util.spec_from_file_location("suite_build_bundle", SCRIPT)
BUNDLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUNDLE)


def executable(path, arch="x86_64", label=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    header[18:20] = BUNDLE.ARCHES[arch].to_bytes(2, "little")
    path.write_bytes(header + label.encode())
    path.chmod(0o755)
    return path


def artifact(name, path, manifest):
    return {"reason": "compiler-artifact", "target": {"name": name, "kind": ["bin"]},
            "manifest_path": str(manifest), "executable": str(path), "fresh": True}


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="suite source build ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "suite"
        self.root.mkdir()
        self.root_patch = patch.object(BUNDLE, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def git(self, path, *args):
        return subprocess.check_output(
            ["git", "-c", "user.name=Suite Test", "-c", "user.email=suite@example.invalid",
             *args], cwd=path, text=True, stderr=subprocess.PIPE).strip()

    def source_fixture(self):
        lock = {"schema": 2, "updated_at": "2026-11-21T00:00:00Z", "components": {}}
        for name in BUNDLE.COMPONENTS:
            source = self.root / "components" / name
            source.mkdir(parents=True)
            self.git(source, "init", "-b", "main")
            (source / "LICENSE").write_text(f"{name} license\n")
            (source / "Cargo.toml").write_text(f"[package]\nname = '{name}'\nversion = '1.0.0'\n")
            (source / "VERSION").write_text("1.0.0\n")
            if name == "ssmcp":
                (source / "src").mkdir()
                (source / "src/code_mode.js").write_text("// source-matched code mode\n")
            self.git(source, "add", ".")
            self.git(source, "commit", "-m", "Fixture source")
            lock["components"][name] = {
                "repository": f"https://github.com/LIghtJUNction/{name}.git",
                "branch": "main", "commit": self.git(source, "rev-parse", "HEAD")}
        (self.root / "dependencies.lock.json").write_text(json.dumps(lock) + "\n")
        return lock

    def nested_source_fixture(self):
        lock = self.source_fixture()
        leaf_remote = self.base / "leaf remote"
        leaf_remote.mkdir()
        self.git(leaf_remote, "init", "-b", "main")
        (leaf_remote / "value").write_text("original leaf\n")
        self.git(leaf_remote, "add", ".")
        self.git(leaf_remote, "commit", "-m", "Leaf source")

        nested_remote = self.base / "nested remote"
        nested_remote.mkdir()
        self.git(nested_remote, "init", "-b", "main")
        self.git(nested_remote, "-c", "protocol.file.allow=always", "submodule",
                 "add", str(leaf_remote), "deps/leaf source")
        self.git(nested_remote, "commit", "-m", "Nested source")

        source = self.root / "components/ztty"
        self.git(source, "-c", "protocol.file.allow=always", "submodule",
                 "add", str(nested_remote), "deps/nested source")
        self.git(source, "commit", "-m", "Recursive source dependency")
        self.git(source, "-c", "protocol.file.allow=always", "submodule",
                 "update", "--init", "--recursive")
        lock["components"]["ztty"]["commit"] = self.git(source, "rev-parse", "HEAD")
        (self.root / "dependencies.lock.json").write_text(json.dumps(lock) + "\n")
        nested = source / "deps/nested source"
        return lock, source, nested, nested / "deps/leaf source"

    def suite_fixture(self):
        lock = self.source_fixture()
        for name in ["install.sh", "uninstall.sh", "LICENSE", "bin/omztty",
                     "bin/omztty-config", "bin/zshard", "config/ztty/config",
                     "packaging/omztty.1"]:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture " + name + "\n")
        (self.root / "VERSION").write_text("0.3.0\n")
        return lock

    def test_rejects_old_asset_lock_before_reading_sources(self):
        with self.assertRaisesRegex(RuntimeError, "workspace.py sync"):
            BUNDLE.verify_sources({"schema": 1, "components": {}})

    def test_source_lock_requires_all_six_components(self):
        with self.assertRaisesRegex(RuntimeError, "all six"):
            BUNDLE.verify_sources({"schema": 2, "components": {"ztty": {}}})

    def test_verifies_exact_clean_source_heads(self):
        lock = self.source_fixture()
        self.assertEqual(BUNDLE.verify_sources(lock),
                         {name: spec["commit"] for name, spec in lock["components"].items()})

    def test_rejects_a_source_head_outside_the_lock(self):
        lock = self.source_fixture()
        lock["components"]["ssmcp"]["commit"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "ssmcp source HEAD.*sync"):
            BUNDLE.verify_sources(lock)

    def test_rejects_tracked_and_untracked_source_edits(self):
        lock = self.source_fixture()
        source = self.root / "components/ztty"
        (source / "VERSION").write_text("uncommitted\n")
        with self.assertRaisesRegex(RuntimeError, "ztty source tree.*uncommitted"):
            BUNDLE.verify_sources(lock)
        (source / "VERSION").write_text("1.0.0\n")
        (source / "untracked.rs").write_text("uncommitted\n")
        with self.assertRaisesRegex(RuntimeError, "ztty source tree.*uncommitted"):
            BUNDLE.verify_sources(lock)

    def test_verifies_clean_recursive_sources_with_spaces_in_paths(self):
        lock, _, _, _ = self.nested_source_fixture()
        self.assertEqual(BUNDLE.verify_sources(lock),
                         {name: spec["commit"] for name, spec in lock["components"].items()})

    def test_rejects_leaf_edits_hidden_by_nested_ignore_configuration(self):
        lock, source, nested, leaf = self.nested_source_fixture()
        self.git(nested, "config", "submodule.deps/leaf source.ignore", "all")
        (leaf / "value").write_text("uncommitted leaf source\n")
        self.assertEqual(self.git(source, "status", "--porcelain",
                                  "--untracked-files=all", "--ignore-submodules=none"), "")
        with self.assertRaisesRegex(RuntimeError, "ztty source tree has uncommitted changes"):
            BUNDLE.verify_sources(lock)

    def test_rejects_uninitialized_nested_source(self):
        lock, source, _, _ = self.nested_source_fixture()
        self.git(source, "submodule", "deinit", "--", "deps/nested source")
        with self.assertRaisesRegex(RuntimeError, "ztty source tree has unresolved submodule commits"):
            BUNDLE.verify_sources(lock)

    def test_rejects_uninitialized_leaf_source(self):
        lock, _, nested, _ = self.nested_source_fixture()
        self.git(nested, "submodule", "deinit", "--", "deps/leaf source")
        with self.assertRaisesRegex(RuntimeError, "ztty source tree has unresolved submodule commits"):
            BUNDLE.verify_sources(lock)

    def test_rejects_leaf_commit_outside_the_recursive_pin(self):
        lock, _, nested, leaf = self.nested_source_fixture()
        self.git(nested, "config", "submodule.deps/leaf source.ignore", "all")
        (leaf / "value").write_text("different committed leaf source\n")
        self.git(leaf, "add", "value")
        self.git(leaf, "commit", "-m", "Move leaf beyond recorded pin")
        with self.assertRaisesRegex(RuntimeError, "ztty source tree has unresolved submodule commits"):
            BUNDLE.verify_sources(lock)

    def test_rejects_noncanonical_repository_and_invalid_commit(self):
        lock = self.source_fixture()
        lock["components"]["ztty"]["repository"] = "https://github.com/LIghtJUNction/ztty"
        with self.assertRaisesRegex(RuntimeError, "Invalid.*ztty"):
            BUNDLE.verify_sources(lock)
        lock["components"]["ztty"]["repository"] += ".git"
        lock["components"]["ztty"]["commit"] = 123
        with self.assertRaisesRegex(RuntimeError, "Invalid.*ztty"):
            BUNDLE.verify_sources(lock)

    def test_uses_cargo_reported_native_path_and_wayland_feature(self):
        binary = executable(self.base / "shared cargo output/release/ztty")
        manifest = self.root / "components/ztty/Cargo.toml"
        messages = [artifact("ztty", self.base / "wrong-ztty", manifest.parent / "other/Cargo.toml"),
                    {"reason": "compiler-artifact", "target": {"name": "ztty", "kind": ["lib"]}},
                    artifact("ztty", binary, manifest), {"reason": "build-finished", "success": True}]
        result = subprocess.CompletedProcess([], 0, "\n".join(map(json.dumps, messages)))
        with patch.object(BUNDLE.platform, "machine", return_value="x86_64"), \
                patch.object(BUNDLE.subprocess, "run", return_value=result) as cargo:
            self.assertEqual(BUNDLE.build_component("ztty", "x86_64"), binary)
        command = cargo.call_args.args[0]
        self.assertNotIn("--target", command)
        self.assertIn("--locked", command)
        self.assertEqual(command[command.index("--features") + 1], "wayland")
        self.assertNotIn("env", cargo.call_args.kwargs)

    def test_cross_build_selects_target_and_validates_elf(self):
        binary = executable(self.base / "shared/release/zdot", "aarch64")
        manifest = self.root / "components/zdot/Cargo.toml"
        result = subprocess.CompletedProcess([], 0, json.dumps(artifact("zdot", binary, manifest)))
        with patch.object(BUNDLE.platform, "machine", return_value="x86_64"), \
                patch.object(BUNDLE.subprocess, "run", return_value=result) as cargo:
            self.assertEqual(BUNDLE.build_component("zdot", "aarch64"), binary)
        command = cargo.call_args.args[0]
        self.assertEqual(command[command.index("--target") + 1], "aarch64-unknown-linux-gnu")
        self.assertNotIn("--features", command)
        executable(binary, "x86_64")
        with patch.object(BUNDLE.subprocess, "run", return_value=result), \
                self.assertRaisesRegex(RuntimeError, "wrong executable architecture"):
            BUNDLE.build_component("zdot", "aarch64")

    def test_missing_cargo_artifact_is_a_build_failure(self):
        result = subprocess.CompletedProcess([], 0, json.dumps({"reason": "build-finished", "success": True}))
        with patch.object(BUNDLE.subprocess, "run", return_value=result), \
                self.assertRaisesRegex(RuntimeError, "exactly one ssmcp executable"):
            BUNDLE.build_component("ssmcp", "x86_64")

    def fake_cargo(self, calls):
        real_run = subprocess.run

        def run(command, **kwargs):
            if command[0] != "cargo":
                return real_run(command, **kwargs)
            name = command[command.index("--bin") + 1]
            calls.append(name)
            manifest = Path(command[command.index("--manifest-path") + 1])
            binary = executable(self.base / "shared/release" / name, label=name + " source binary")
            return subprocess.CompletedProcess(command, 0, json.dumps(artifact(name, binary, manifest)))

        return run

    def test_archive_contains_source_built_programs_and_exact_provenance(self):
        lock = self.suite_fixture()
        calls = []
        fake = self.fake_cargo(calls)
        with patch.object(BUNDLE.platform, "machine", return_value="x86_64"), \
                patch.object(BUNDLE.subprocess, "run", side_effect=fake), redirect_stdout(io.StringIO()):
            BUNDLE.main(["--arch", "x86_64"])
        self.assertEqual(calls, list(BUNDLE.BINARIES))
        archive = self.root / "dist/oh-my-ztty-0.3.0-linux-x86_64.tar.gz"
        first_digest = BUNDLE.digest(archive)
        with tarfile.open(archive, "r:gz") as stream:
            metadata = json.load(stream.extractfile("oh-my-ztty/BUILD.json"))
            self.assertEqual(metadata["schema"], 2)
            self.assertEqual(metadata["sources_updated_at"], lock["updated_at"])
            self.assertEqual(metadata["source_commits"],
                             {name: spec["commit"] for name, spec in lock["components"].items()})
            self.assertEqual(metadata["source_branches"], {name: "main" for name in BUNDLE.COMPONENTS})
            for name in BUNDLE.BINARIES:
                contents = stream.extractfile("oh-my-ztty/bin/" + name).read()
                self.assertTrue(contents.endswith((name + " source binary").encode()))
            self.assertEqual(stream.extractfile("oh-my-ztty/bin/code-mode.js").read(),
                             b"// source-matched code mode\n")
            for name in BUNDLE.COMPONENTS:
                self.assertEqual(stream.extractfile(f"oh-my-ztty/licenses/{name}.txt").read(),
                                 f"{name} license\n".encode())
        with patch.object(BUNDLE.platform, "machine", return_value="x86_64"), \
                patch.object(BUNDLE.subprocess, "run", side_effect=fake), redirect_stdout(io.StringIO()):
            BUNDLE.main(["--arch", "x86_64"])
        self.assertEqual(BUNDLE.digest(archive), first_digest)

    def test_changed_lock_aborts_before_publishing_archive(self):
        self.suite_fixture()

        def build(name, arch):
            if name == "zfetch":
                path = self.root / "dependencies.lock.json"
                path.write_text(path.read_text() + "\n")
            return executable(self.base / "shared" / name, arch)

        with patch.object(BUNDLE, "build_component", side_effect=build), \
                self.assertRaisesRegex(RuntimeError, "changed during the build"):
            BUNDLE.main(["--arch", "x86_64"])
        self.assertEqual(list((self.root / "dist").glob("*.tar.gz")), [])


if __name__ == "__main__":
    unittest.main()
