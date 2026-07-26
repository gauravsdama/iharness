from pathlib import Path
import tempfile
import unittest

from iharness.config import HarnessConfig, load_config, resolve_path, save_config


class ConfigTests(unittest.TestCase):
    def test_defaults_are_agent_friendly(self) -> None:
        config = HarnessConfig()
        self.assertEqual(config.configuration, "Debug")
        self.assertIn(".swift", config.watch_extensions)
        self.assertTrue(config.screenshot)

    def test_merge_ignores_none(self) -> None:
        config = HarnessConfig(scheme="App")
        merged = config.merged({"scheme": None, "device": "iPhone 17 Pro"})
        self.assertEqual(merged.scheme, "App")
        self.assertEqual(merged.device, "iPhone 17 Pro")

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            save_config(HarnessConfig(scheme="Example"), path)
            self.assertEqual(load_config(path).scheme, "Example")

    def test_resolve_path(self) -> None:
        base = Path("/tmp/example")
        self.assertEqual(resolve_path("App.xcodeproj", base), str((base / "App.xcodeproj").resolve()))
        self.assertEqual(resolve_path("/Applications", base), "/Applications")
        self.assertIsNone(resolve_path(None, base))


if __name__ == "__main__":
    unittest.main()
