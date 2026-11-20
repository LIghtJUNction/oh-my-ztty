"""Run the workspace check CLI against a component without a Makefile."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/workspace.py"


class WorkspaceCheckTests(unittest.TestCase):
    def fixture(self, exit_code):
        temporary = tempfile.TemporaryDirectory(prefix="workspace check ")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "scripts").mkdir()
        shutil.copy2(SCRIPT, root / "scripts/workspace.py")
        component = root / "components/zrc"
        (component / "scripts").mkdir(parents=True)
        (component / ".git").touch()
        (component / "scripts/check.py").write_text(
            "from pathlib import Path\nimport sys\n"
            "Path('checker.cwd').write_text(str(Path.cwd()))\n"
            f"sys.exit({exit_code})\n")
        return root, component

    def check_component(self, root):
        return subprocess.run(
            [sys.executable, "scripts/workspace.py", "check", "--component", "zrc"],
            cwd=root, capture_output=True, text=True)

    def test_zrc_checker_runs_without_a_makefile(self):
        root, component = self.fixture(0)
        result = self.check_component(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((component / "checker.cwd").read_text(), str(component))

    def test_zrc_checker_failure_fails_the_workspace_check(self):
        root, component = self.fixture(7)
        result = self.check_component(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue((component / "checker.cwd").is_file())
        self.assertIn("non-zero exit status 7", result.stderr)


if __name__ == "__main__":
    unittest.main()
