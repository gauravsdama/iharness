import json
import tempfile
import unittest
from pathlib import Path

from iharness.report import VerificationReport
from iharness.runner import CommandResult


class ReportTests(unittest.TestCase):
    def test_reports_are_atomic_private_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report"
            report = VerificationReport(output)
            report.add_step(
                "unsafe * step",
                CommandResult(
                    command=["tool", "--token", "top-secret"],
                    returncode=1,
                    stdout="",
                    stderr=f"failure at {Path.home()}/project\nAuthorization: Bearer bearer-secret\n``` injected",
                    duration_seconds=0.1,
                ),
            )
            report.add_error("```markdown injection")
            json_path, markdown_path = report.write()
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["steps"][0]["command"][-1], "[REDACTED]")
            self.assertNotIn(str(Path.home()), json_path.read_text(encoding="utf-8"))
            self.assertNotIn(
                str(Path.home()), markdown_path.read_text(encoding="utf-8")
            )
            self.assertNotIn("bearer-secret", json_path.read_text(encoding="utf-8"))
            self.assertNotIn("- ```", markdown_path.read_text(encoding="utf-8"))
            self.assertEqual(json_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(markdown_path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
