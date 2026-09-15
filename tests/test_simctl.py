import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from iharness.simctl import find_device, parse_devices_json, record_video, resolve_device


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
        class FakeProcess:
            returncode = -2

            def communicate(self, timeout: int):
                if timeout == 3:
                    raise subprocess.TimeoutExpired(["simctl"], timeout)
                return "", ""

            def send_signal(self, signal_value: int) -> None:
                self.signal_value = signal_value

            def kill(self) -> None:
                raise AssertionError("recording should stop after SIGINT")

        with patch("iharness.simctl.subprocess.Popen", return_value=FakeProcess()):
            result = record_video("booted", Path("/tmp/recording.mp4"), seconds=3)
        self.assertTrue(result.ok)

    def test_record_video_rejects_non_positive_duration(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            record_video("booted", Path("/tmp/recording.mp4"), seconds=0)

    def test_parse_devices_json(self) -> None:
        devices = parse_devices_json(SAMPLE)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].name, "iPhone 17")
        self.assertEqual(devices[0].runtime, "com.apple.CoreSimulator.SimRuntime.iOS-26-2")

    def test_find_device_by_name_udid_or_partial(self) -> None:
        devices = parse_devices_json(SAMPLE)
        self.assertEqual(find_device("iPhone 17", devices).udid, "AAAA-BBBB")
        self.assertEqual(find_device("CCCC-DDDD", devices).name, "iPhone 17 Pro")
        self.assertEqual(find_device("pro", devices).udid, "CCCC-DDDD")

    def test_resolve_default_prefers_iphone_17(self) -> None:
        devices = parse_devices_json(SAMPLE)
        self.assertEqual(resolve_device(None, devices).name, "iPhone 17")


if __name__ == "__main__":
    unittest.main()
