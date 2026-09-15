import unittest

from iharness.xcode import XcodeTarget, build_xcodebuild_command, destination_for_device


class XcodeTests(unittest.TestCase):
    def test_destination_for_name(self) -> None:
        self.assertEqual(destination_for_device("iPhone 17"), "platform=iOS Simulator,name=iPhone 17")

    def test_explicit_destination_is_preserved(self) -> None:
        self.assertEqual(destination_for_device("generic/platform=iOS Simulator"), "generic/platform=iOS Simulator")

    def test_destination_for_udid(self) -> None:
        udid = "156242A1-DBF9-4F13-BA88-653D8CF58714"
        self.assertEqual(destination_for_device(udid), f"platform=iOS Simulator,id={udid}")

    def test_build_command_uses_workspace(self) -> None:
        target = XcodeTarget(workspace="App.xcworkspace", scheme="App")
        command = build_xcodebuild_command(target, "build")
        self.assertIn("-workspace", command)
        self.assertIn("App.xcworkspace", command)
        self.assertEqual(command[-1], "build")

    def test_requires_project_or_workspace(self) -> None:
        with self.assertRaises(ValueError):
            build_xcodebuild_command(XcodeTarget(scheme="App"), "build")

    def test_target_sdk_build_uses_build_roots_without_destination(self) -> None:
        command = build_xcodebuild_command(
            XcodeTarget(project="App.xcodeproj", target="App", sdk="iphonesimulator", device=None),
            "build",
        )
        self.assertIn("-target", command)
        self.assertIn("-sdk", command)
        self.assertNotIn("-destination", command)
        self.assertTrue(any(item.startswith("SYMROOT=") for item in command))

    def test_rejects_scheme_and_target_together(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            build_xcodebuild_command(XcodeTarget(project="App.xcodeproj", scheme="App", target="App"), "build")


if __name__ == "__main__":
    unittest.main()
