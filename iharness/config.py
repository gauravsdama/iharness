from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(".iharness/config.json")


@dataclass
class HarnessConfig:
    workspace: str | None = None
    project: str | None = None
    scheme: str | None = None
    configuration: str = "Debug"
    device: str = "iPhone 17"
    bundle_id: str | None = None
    app_path: str | None = None
    derived_data: str = ".iharness/DerivedData"
    result_bundle: str | None = None
    run_tests: bool = False
    log_seconds: int = 10
    screenshot: bool = True
    extra_xcode_args: list[str] = field(default_factory=list)
    watch_paths: list[str] = field(default_factory=lambda: ["."])
    watch_extensions: list[str] = field(
        default_factory=lambda: [
            ".swift",
            ".m",
            ".mm",
            ".h",
            ".storyboard",
            ".xib",
            ".xcassets",
            ".plist",
            ".json",
            ".tsx",
            ".ts",
            ".js",
        ]
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HarnessConfig":
        known = {field_name for field_name in cls.__dataclass_fields__}
        filtered = {key: value for key, value in data.items() if key in known}
        return cls(**filtered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "project": self.project,
            "scheme": self.scheme,
            "configuration": self.configuration,
            "device": self.device,
            "bundle_id": self.bundle_id,
            "app_path": self.app_path,
            "derived_data": self.derived_data,
            "result_bundle": self.result_bundle,
            "run_tests": self.run_tests,
            "log_seconds": self.log_seconds,
            "screenshot": self.screenshot,
            "extra_xcode_args": self.extra_xcode_args,
            "watch_paths": self.watch_paths,
            "watch_extensions": self.watch_extensions,
        }

    def merged(self, overrides: dict[str, Any]) -> "HarnessConfig":
        data = self.to_dict()
        for key, value in overrides.items():
            if value is not None:
                data[key] = value
        return HarnessConfig.from_dict(data)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> HarnessConfig:
    if not path.exists():
        return HarnessConfig()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected config object in {path}")
    return HarnessConfig.from_dict(data)


def save_config(config: HarnessConfig, path: Path = DEFAULT_CONFIG_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2)
        handle.write("\n")
    return path


def resolve_path(value: str | None, base: Path) -> str | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return str(path)
    return str((base / path).resolve())
