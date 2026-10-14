import os
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path

from iharness.runner import run_command


class RunnerTests(unittest.TestCase):
    def test_timeout_is_normalized_and_bounded(self) -> None:
        result = run_command(
            [
                sys.executable,
                "-c",
                "import time; print('started', flush=True); time.sleep(30)",
            ],
            timeout=0.05,
        )
        self.assertEqual(result.returncode, 124)
        self.assertTrue(result.timed_out)
        self.assertIn("started", result.stdout)
        self.assertIn("Command timed out after 0.05 seconds.", result.stderr)

    def test_output_is_capped_without_losing_tail(self) -> None:
        result = run_command(
            [sys.executable, "-c", "print('A' * 2000); print('TAIL')"],
            max_capture_bytes=128,
        )
        self.assertTrue(result.ok)
        self.assertIn("bytes omitted", result.stdout)
        self.assertIn("TAIL", result.stdout)

    def test_rejects_unbounded_timeout(self) -> None:
        with self.assertRaisesRegex(ValueError, "timeout"):
            run_command([sys.executable, "-c", "pass"], timeout=0)

    def test_timeout_terminates_descendant_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "child-survived"
            child_code = (
                f"import time; time.sleep(0.2); open({str(marker)!r}, 'w').close()"
            )
            parent_code = (
                "import subprocess, sys, time; "
                f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
                "time.sleep(30)"
            )
            result = run_command([sys.executable, "-c", parent_code], timeout=0.05)
            time.sleep(0.3)
            self.assertEqual(result.returncode, 124)
            self.assertFalse(marker.exists())

    def test_completed_parent_does_not_wait_for_detached_pipe_holder(self) -> None:
        child_code = "import time; time.sleep(30)"
        parent_code = (
            "import subprocess, sys; "
            "child = subprocess.Popen("
            f"[sys.executable, '-c', {child_code!r}], start_new_session=True"
            "); print(child.pid, flush=True)"
        )
        start = time.monotonic()
        result = run_command([sys.executable, "-c", parent_code], timeout=5)
        try:
            self.assertTrue(result.ok)
            self.assertLess(time.monotonic() - start, 2)
        finally:
            os.killpg(int(result.stdout.strip()), signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()
