import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from iharness.monitor import iter_watch_files, snapshot


class MonitorTests(unittest.TestCase):
    def test_asset_catalog_contents_are_watched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "Assets.xcassets" / "Icon.imageset" / "icon.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"png")
            self.assertIn(image, iter_watch_files(["."], [".xcassets"], cwd=root))

    def test_snapshot_tolerates_disappearing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "App.swift"
            source.write_text("", encoding="utf-8")
            with patch("iharness.monitor.Path.stat", side_effect=FileNotFoundError):
                self.assertEqual(snapshot(["."], [".swift"], cwd=root), {})


if __name__ == "__main__":
    unittest.main()
