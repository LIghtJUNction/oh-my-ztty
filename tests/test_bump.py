#!/usr/bin/env python3
"""Version publication keeps current docs in sync without rewriting evidence."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VersionPublication(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omztty bump ")
        self.work = Path(self.temp.name)
        self.root = self.work / "suite"
        self.root.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_")}
        self.env.update(HOME=str(self.work / "home"), GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM="1")
        Path(self.env["HOME"]).mkdir()
        files = {
            "VERSION": "0.1.1\n",
            "install.sh": "#!/bin/sh\nVERSION=0.1.1\n",
            "site/content/index.md":
                "The current suite release is **0.1.1**, available for Linux.\n"
                "[0.1.1 evidence](../../docs/reports/release-0.1.1.md)\n",
            "site/content/installation.md":
                "[release](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.1.1)\n"
                "sh install.sh --from ./oh-my-ztty-0.1.1-linux-x86_64.tar.gz\n"
                "[audit](../../docs/reports/public-release-0.1.1.json)\n",
            "docs/installation.md":
                "[release](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.1.1)\n"
                "sh install.sh --from ./oh-my-ztty-0.1.1-linux-x86_64.tar.gz\n"
                "sh install.sh --from ./oh-my-ztty-0.1.1-linux-aarch64.tar.gz\n"
                "[audit](reports/public-release-0.1.1.json)\n",
            "Makefile": "check:\n\t@true\n",
        }
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        (self.root / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts/bump.py", self.root / "scripts/bump.py")

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *args, ok=True):
        result = subprocess.run(args, cwd=self.root, env=self.env,
                                text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def bump(self, *extra, ok=True):
        return self.command("python3", "scripts/bump.py", "patch", *extra, ok=ok)

    def assert_current_docs(self, version="0.1.2"):
        self.assertEqual((self.root / "VERSION").read_text(), version + "\n")
        self.assertIn("VERSION=" + version + "\n", (self.root / "install.sh").read_text())
        overview = (self.root / "site/content/index.md").read_text()
        self.assertIn(f"The current suite release is **{version}**", overview)
        self.assertIn("release-0.1.1.md", overview)
        for name in ("docs/installation.md", "site/content/installation.md"):
            with self.subTest(guide=name):
                guide = (self.root / name).read_text()
                self.assertIn(f"releases/tag/v{version}", guide)
                self.assertIn(f"oh-my-ztty-{version}-linux-x86_64.tar.gz", guide)
                self.assertNotIn("oh-my-ztty-0.1.1-linux-", guide)
                self.assertIn("public-release-0.1.1.json", guide)
        self.assertIn(f"oh-my-ztty-{version}-linux-aarch64.tar.gz",
                      (self.root / "docs/installation.md").read_text())

    def test_bump_updates_current_guidance_and_keeps_historical_evidence(self):
        self.bump()
        self.assert_current_docs()

    def test_source_only_bump_preserves_published_release_guidance(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.bump("--source-only")
        after = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before.keys(), after.keys())
        self.assertEqual({path.relative_to(self.root).as_posix()
                          for path in before if before[path] != after[path]},
                         {"VERSION", "install.sh"})
        self.assertEqual((self.root / "VERSION").read_text(), "0.1.2\n")
        self.assertIn("VERSION=0.1.2\n", (self.root / "install.sh").read_text())

    def test_normal_bump_after_source_only_uses_published_version(self):
        self.bump("--source-only")
        self.bump()
        self.assert_current_docs("0.1.3")

    def test_source_only_cannot_publish_a_release(self):
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result = self.bump("--source-only", "--release", ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed with argument", result.stderr)
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def test_document_mismatch_does_not_partially_bump(self):
        for name in ("docs/installation.md", "site/content/installation.md"):
            with self.subTest(guide=name):
                guide = self.root / name
                original = guide.read_text()
                guide.write_text(original.replace("releases/tag/v0.1.1", "releases/tag/v0.1.0"))
                before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
                result = self.bump(ok=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Installation guide " + name, result.stderr)
                self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
                guide.write_text(original)

    def test_release_publishes_matching_version_and_documentation(self):
        remote = self.work / "remote.git"
        self.command("git", "init", "--bare", str(remote))
        self.command("git", "init", "-b", "main")
        self.command("git", "config", "user.name", "Version fixture")
        self.command("git", "config", "user.email", "fixture@example.invalid")
        self.command("git", "config", "commit.gpgsign", "false")
        self.command("git", "config", "tag.gpgsign", "false")
        self.command("git", "add", ".")
        self.command("git", "commit", "-m", "fixture")
        self.command("git", "remote", "add", "origin", str(remote))
        self.command("git", "push", "-u", "origin", "main")
        self.bump("--release")
        self.assert_current_docs()
        head = self.command("git", "--git-dir", str(remote), "rev-parse", "refs/heads/main").stdout.strip()
        tag = self.command("git", "--git-dir", str(remote), "rev-parse", "refs/tags/v0.1.2^{commit}").stdout.strip()
        self.assertEqual(head, tag)
        for name in ("VERSION", "install.sh", "site/content/index.md", "docs/installation.md", "site/content/installation.md"):
            published = self.command("git", "--git-dir", str(remote), "show", "v0.1.2:" + name).stdout
            self.assertEqual(published, (self.root / name).read_text())
        self.assertEqual(self.command("git", "status", "--porcelain").stdout, "")


if __name__ == "__main__":
    unittest.main()
