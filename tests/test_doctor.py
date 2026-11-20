import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DoctorDiagnosticsTest(unittest.TestCase):
    def test_failed_bundled_program_reports_its_loader_error(self):
        with tempfile.TemporaryDirectory(prefix="omztty doctor ") as temp:
            root = Path(temp)
            bindir = root / "bin"
            bindir.mkdir()
            shutil.copy2(ROOT / "bin/omztty", bindir / "omztty")
            (root / "VERSION").write_text("0.0.0\n")
            component = root / "components/zshard"
            component.mkdir(parents=True)
            (component / "zshard.zsh").touch()
            error = "ztty: error while loading shared libraries: libwayland-client.so.0: cannot open shared object file"
            for name in ("ztty", "ssmcp", "zdot", "zfetch", "zsh", "git"):
                program = bindir / name
                if name == "ztty":
                    program.write_text("#!/bin/sh\nprintf '%s\\n' '" + error + "' >&2\nexit 127\n")
                else:
                    program.write_text("#!/bin/sh\nprintf '%s\\n' '" + name + " 0.0.0'\n")
                program.chmod(0o755)
            env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ.get("PATH", ""))
            result = subprocess.run([str(bindir / "omztty"), "doctor"],
                                    env=env, text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("fail bundled ztty\n" + error, result.stdout)
            self.assertIn("ok   ssmcp 0.0.0", result.stdout)
            self.assertIn("ok   zdot 0.0.0", result.stdout)
            self.assertIn("No connection or background service was started.", result.stdout)


if __name__ == "__main__":
    unittest.main()
