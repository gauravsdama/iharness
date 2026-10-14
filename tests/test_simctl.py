import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from iharness.runner import CommandResult
from iharness.simctl import (
    capture_logs,
    find_device,
    launch_app,
    parse_devices_json,
    record_video,
    resolve_device,
    take_screenshot,
)

SAMPLE = json.dumps(
    {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-2": [
                {
                    "name": "iPhone 17",
                    "udid": "AAAA-BBBB",
                    "state": "Shutdown",
                    "isAvailable": True,
                },
                {
                    "name": "iPhone 17 Pro",
                    "udid": "CCCC-DDDD",
                    "state": "Booted",
                    "isAvailable": True,
                },
            ]
        }
    }
)


class SimctlTests(unittest.TestCase):
    def test_record_video_treats_expected_sigint_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "recording.mp4"
            output.write_bytes(b"video")
            success = CommandResult(["simctl"], 0, "", "", 3.0)
            with patch("iharness.simctl.run_for_duration", return_value=success) as run:
                result = record_video("booted", output, seconds=3)
            self.assertTrue(result.ok)
            self.assertEqual(run.call_args.kwargs["seconds"], 3)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_screenshot_requires_an_output_artifact(self) -> None:
        success = CommandResult(["simctl"], 0, "", "", 0.1)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "missing.png"
            with patch("iharness.simctl.run_command", return_value=success):
                result = take_screenshot("booted", output)
            self.assertFalse(result.ok)
            self.assertIn("did not create", result.stderr)

    def test_log_predicate_escapes_bundle_identifier(self) -> None:
        success = CommandResult(["simctl"], 0, "", "", 0.1)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "simulator.log"
            with patch("iharness.simctl.run_for_duration", return_value=success) as run:
                capture_logs(
                    "booted",
                    output,
                    seconds=1,
                    bundle_id='example" OR TRUEPREDICATE OR "',
                )
            predicate = run.call_args.args[0][-1]
            self.assertIn('example\\" OR TRUEPREDICATE', predicate)
            self.assertNotIn('example" OR TRUEPREDICATE', predicate)

    def test_launch_can_force_a_fresh_process(self) -> None:
        success = CommandResult(["simctl"], 0, "", "", 0.1)
        with patch("iharness.simctl.run_command", return_value=success) as run:
            result = launch_app(
                "DEVICE", "dev.iharness.fixture", terminate_running=True
            )
        self.assertTrue(result.ok)
        self.assertEqual(
            run.call_args.args[0],
            [
                "xcrun",
                "simctl",
                "launch",
                "--terminate-running-process",
                "DEVICE",
                "dev.iharness.fixture",
            ],
        )

    def test_record_video_rejects_non_positive_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            record_video("booted", Path("/tmp/recording.mp4"), seconds=0)

    def test_parse_devices_json(self) -> None:
        devices = parse_devices_json(SAMPLE)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].name, "iPhone 17")
        self.assertEqual(
            devices[0].runtime, "com.apple.CoreSimulator.SimRuntime.iOS-26-2"
        )

    def test_find_device_by_name_udid_or_partial(self) -> None:
        devices = parse_devices_json(SAMPLE)
        self.assertEqual(find_device("iPhone 17", devices).udid, "AAAA-BBBB")
        self.assertEqual(find_device("CCCC-DDDD", devices).name, "iPhone 17 Pro")
        self.assertEqual(find_device("pro", devices).udid, "CCCC-DDDD")

    def test_resolve_default_prefers_iphone_17(self) -> None:
        devices = parse_devices_json(SAMPLE)
        self.assertEqual(resolve_device(None, devices).name, "iPhone 17")

    def test_duplicate_names_choose_booted_then_newest_runtime_deterministically(
        self,
    ) -> None:
        devices = parse_devices_json(
            json.dumps(
                {
                    "devices": {
                        "com.apple.CoreSimulator.SimRuntime.iOS-25-4": [
                            {"name": "iPhone 17", "udid": "OLD", "state": "Shutdown"}
                        ],
                        "com.apple.CoreSimulator.SimRuntime.iOS-26-2": [
                            {"name": "iPhone 17", "udid": "NEW", "state": "Booted"}
                        ],
                    }
                }
            )
        )
        self.assertEqual(find_device("iPhone 17", list(reversed(devices))).udid, "NEW")

    def test_patch_runtime_version_sorts_newest_first(self) -> None:
        devices = parse_devices_json(
            json.dumps(
                {
                    "devices": {
                        "com.apple.CoreSimulator.SimRuntime.iOS-26-2": [
                            {"name": "iPhone 17", "udid": "BASE", "state": "Shutdown"}
                        ],
                        "com.apple.CoreSimulator.SimRuntime.iOS-26-2-1": [
                            {"name": "iPhone 17", "udid": "PATCH", "state": "Shutdown"}
                        ],
                    }
                }
            )
        )
        self.assertEqual(find_device("iPhone 17", devices).udid, "PATCH")


if __name__ == "__main__":
    unittest.main()
