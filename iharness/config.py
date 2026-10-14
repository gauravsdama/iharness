from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(".iharness/config.json")
MAX_LAUNCH_WAIT_SECONDS = 300.0
MAX_LOG_SECONDS = 3600


@dataclass
class HarnessConfig:
    workspace: str | None = None
    project: str | None = None
    scheme: str | None = None
    target: str | None = None
    sdk: str | None = None
    configuration: str = "Debug"
    device: str = "iPhone 17"
    build_destination: str | None = None
    bundle_id: str | None = None
    app_path: str | None = None
    derived_data: str = ".iharness/DerivedData"
    result_bundle: str | None = None
    run_tests: bool = False
    launch_wait_seconds: float = 2.0
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

    def __post_init__(self) -> None:
        optional_strings = (
            "workspace",
            "project",
            "scheme",
            "target",
            "sdk",
            "build_destination",
            "bundle_id",
            "app_path",
            "result_bundle",
        )
        required_strings = ("configuration", "device", "derived_data")
        for name in optional_strings:
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(
                    f"Config field '{name}' must be a non-empty string or null."
                )
        for name in required_strings:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Config field '{name}' must be a non-empty string.")
        for name in ("run_tests", "screenshot"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"Config field '{name}' must be a boolean.")
        if isinstance(self.launch_wait_seconds, bool) or not isinstance(
            self.launch_wait_seconds, (int, float)
        ):
            raise ValueError("Config field 'launch_wait_seconds' must be a number.")
        if not 0 <= self.launch_wait_seconds <= MAX_LAUNCH_WAIT_SECONDS:
            raise ValueError(
                f"Config field 'launch_wait_seconds' must be between 0 and {MAX_LAUNCH_WAIT_SECONDS:g}."
            )
        if isinstance(self.log_seconds, bool) or not isinstance(self.log_seconds, int):
            raise ValueError("Config field 'log_seconds' must be an integer.")
        if not 0 <= self.log_seconds <= MAX_LOG_SECONDS:
            raise ValueError(
                f"Config field 'log_seconds' must be between 0 and {MAX_LOG_SECONDS}."
            )
        for name in ("extra_xcode_args", "watch_paths", "watch_extensions"):
            value = getattr(self, name)
            if not isinstance(value, list) or any(
                not isinstance(item, str) or not item for item in value
            ):
                raise ValueError(
                    f"Config field '{name}' must be a list of non-empty strings."
                )
        if any(not extension.startswith(".") for extension in self.watch_extensions):
            raise ValueError(
                "Config field 'watch_extensions' entries must start with '.'."
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HarnessConfig":
        known = {field_name for field_name in cls.__dataclass_fields__}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"Unknown config field(s): {', '.join(unknown)}")
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "project": self.project,
            "scheme": self.scheme,
            "target": self.target,
            "sdk": self.sdk,
            "configuration": self.configuration,
            "device": self.device,
            "build_destination": self.build_destination,
            "bundle_id": self.bundle_id,
            "app_path": self.app_path,
            "derived_data": self.derived_data,
            "result_bundle": self.result_bundle,
            "run_tests": self.run_tests,
            "launch_wait_seconds": self.launch_wait_seconds,
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
