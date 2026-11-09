from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class AppEntrypointTests(unittest.TestCase):
    def test_direct_script_without_arguments_prints_help_successfully(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        app_path = project_root / "src" / "app.py"

        result = subprocess.run(
            [sys.executable, str(app_path)],
            cwd=project_root.parent,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: app.py", result.stdout)
        self.assertNotIn("error:", result.stderr)

    def test_direct_script_invocation_loads_help_outside_repository(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        app_path = project_root / "src" / "app.py"

        result = subprocess.run(
            [sys.executable, str(app_path), "route", "--help"],
            cwd=project_root.parent,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--institution", result.stdout)
        self.assertIn("--mandate", result.stdout)
        self.assertIn("institutional_analysis", result.stdout)


if __name__ == "__main__":
    unittest.main()
