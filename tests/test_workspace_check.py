"""Exercise direct component checks and optional Cargo background routing."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/workspace.py"


class WorkspaceCheckTests(unittest.TestCase):
    def fixture(self, exit_code):
        temporary = tempfile.TemporaryDirectory(prefix="workspace check ")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "scripts").mkdir()
        shutil.copy2(SCRIPT, root / "scripts/workspace.py")
        shutil.copy2(SCRIPT.with_name("managed_build.py"), root / "scripts/managed_build.py")
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

    def cargo_fixture(self, exit_code):
        root, _ = self.fixture(0)
        component = root / "components/zmem"
        component.mkdir()
        (component / ".git").touch()
        binaries = root / "bin"
        binaries.mkdir()
        cargo = binaries / "cargo"
        cargo.write_text("#!" + sys.executable + "\n" +
            "import json,sys\nfrom pathlib import Path\n"
            "payload=sys.stdin.read() if sys.argv[1]=='test' else ''\n"
            "with Path('cargo.calls').open('a') as log:\n"
            " log.write(json.dumps({'argv':sys.argv[1:],'cwd':str(Path.cwd()),'stdin':payload})+'\\n')\n"
            "print('cargo '+sys.argv[1]+' stdout')\n"
            "print('cargo '+sys.argv[1]+' stderr',file=sys.stderr)\n"
            f"sys.exit({exit_code})\n")
        launcher = binaries / "zmem"
        launcher.write_text("#!" + sys.executable + "\n" +
            "import json,os,sys\nfrom pathlib import Path\n"
            "with Path('route.calls').open('a') as log: log.write(json.dumps(sys.argv[1:5])+'\\n')\n"
            "os.execvp(sys.argv[5],sys.argv[5:])\n")
        cargo.chmod(0o755)
        launcher.chmod(0o755)
        environment = {**os.environ, "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
                       "ZMEM_BUILD_BACKGROUND": "1"}
        # Select a fixture launcher without probing or using the host manager.
        driver = ("import runpy,sys\nfrom pathlib import Path\n"
                  "sys.path.insert(0,str(Path('scripts').resolve()))\n"
                  "import managed_build\n"
                  "managed_build._selection=lambda:(str(Path('bin/zmem').resolve()),'fixture')\n"
                  "runpy.run_path('scripts/workspace.py',run_name='__main__')\n")
        result = subprocess.run([sys.executable, "-c", driver, "check", "--component", "zmem"],
                                cwd=root, env=environment, input="workspace stdin", text=True,
                                capture_output=True)
        calls = [json.loads(line) for line in (component / "cargo.calls").read_text().splitlines()]
        routes = [json.loads(line) for line in (component / "route.calls").read_text().splitlines()]
        return component, result, calls, routes

    def test_zmem_cargo_checks_use_background_scope_with_original_io_and_workdir(self):
        component, result, calls, routes = self.cargo_fixture(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call["argv"] for call in calls], [
            ["test", "--locked"], ["check", "--locked", "--no-default-features", "--lib"]])
        self.assertEqual([call["cwd"] for call in calls], [str(component)] * 2)
        self.assertEqual([call["stdin"] for call in calls], ["workspace stdin", ""])
        self.assertEqual(routes, [["run", "--class", "background", "--"]] * 2)
        self.assertEqual(result.stdout, "cargo test stdout\ncargo check stdout\n")
        self.assertIn("cargo test stderr", result.stderr)
        self.assertIn("cargo check stderr", result.stderr)

    def test_failed_routed_cargo_check_stops_once_with_original_exit_diagnostic(self):
        _, result, calls, routes = self.cargo_fixture(23)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(routes), 1)
        self.assertEqual(result.stdout, "cargo test stdout\n")
        self.assertIn("non-zero exit status 23", result.stderr)
        self.assertNotIn("cargo check", result.stdout + result.stderr)

    def test_git_commands_keep_capture_behavior_without_consulting_memory_router(self):
        root, _ = self.fixture(0)
        sys.path.insert(0, str(SCRIPT.parent))
        self.addCleanup(sys.path.pop, 0)
        spec = importlib.util.spec_from_file_location("suite_workspace_check", SCRIPT)
        workspace = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workspace)
        with patch.object(workspace, "background_command", side_effect=AssertionError("unexpected routing")):
            output = workspace.run("git", "--version", cwd=root, capture=True)
        self.assertTrue(output.startswith("git version "))
        self.assertNotIn("\n", output)


if __name__ == "__main__":
    unittest.main()
