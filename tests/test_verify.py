import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from iharness.config import HarnessConfig
from iharness.runner import CommandResult
from iharness.simctl import SimulatorDevice
from iharness.verify import run_verification

SUCCESS = CommandResult(["tool"], 0, "", "", 0.01)
DEVICE = SimulatorDevice("iPhone 17", "DEVICE", "iOS-26-2", "Booted")


class VerifyTests(unittest.TestCase):
    @patch("iharness.verify.shutil.which", return_value="/usr/bin/tool")
    @patch("iharness.verify.run_command", return_value=SUCCESS)
    @patch("iharness.verify.boot_device", return_value=DEVICE)
    def test_infrastructure_only_run_is_incomplete(self, _boot, _run, _which) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_verification(
                HarnessConfig(screenshot=False, log_seconds=0),
                cwd=Path(tmp),
                output_dir=Path(tmp) / "run",
            )
            self.assertEqual(report.status, "incomplete")
            self.assertTrue(report.notes)

    @patch("iharness.verify.shutil.which", return_value="/usr/bin/tool")
    @patch("iharness.verify.run_command", return_value=SUCCESS)
    @patch("iharness.verify.boot_device", return_value=DEVICE)
    @patch("iharness.verify.install_app", side_effect=RuntimeError("install exploded"))
    def test_unexpected_failure_still_writes_report(
        self, _install, _boot, _run, _which
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            report = run_verification(
                HarnessConfig(app_path="App.app", screenshot=False, log_seconds=0),
                cwd=Path(tmp),
                output_dir=output,
            )
            self.assertEqual(report.status, "failed")
            self.assertTrue((output / "report.md").is_file())
            payload = json.loads((output / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "failed")
            self.assertIn("install exploded", payload["errors"][0])


if __name__ == "__main__":
    unittest.main()
