from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .runner import CommandResult, run_command


@dataclass
class XcodeTarget:
    workspace: str | None = None
    project: str | None = None
    scheme: str | None = None
    target: str | None = None
    sdk: str | None = None
    configuration: str = "Debug"
    device: str | None = "iPhone 17"
    derived_data: str = ".iharness/DerivedData"
    result_bundle: str | None = None
    extra_args: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.workspace and self.project:
            raise ValueError("Use either workspace or project, not both.")
        if not self.workspace and not self.project:
            raise ValueError("An Xcode workspace or project is required.")
        if bool(self.scheme) == bool(self.target):
            raise ValueError("Use exactly one Xcode scheme or target.")
        if self.target and self.workspace:
            raise ValueError("Target builds require an Xcode project, not a workspace.")


def destination_for_device(device: str) -> str:
    if device.startswith("generic/") or device.startswith("platform="):
        return device
    if "-" in device and len(device) >= 32:
        return f"platform=iOS Simulator,id={device}"
    return f"platform=iOS Simulator,name={device}"


def build_xcodebuild_command(target: XcodeTarget, action: str) -> list[str]:
    target.validate()
    command = ["xcodebuild"]
    if target.workspace:
        command.extend(["-workspace", target.workspace])
    if target.project:
        command.extend(["-project", target.project])
    if target.scheme:
        command.extend(["-scheme", target.scheme])
    else:
        command.extend(["-target", target.target or ""])
    command.extend(["-configuration", target.configuration])
    if target.sdk:
        command.extend(["-sdk", target.sdk])
    if target.device:
        command.extend(["-destination", destination_for_device(target.device)])
    if target.target:
        derived = Path(target.derived_data)
        command.extend([f"SYMROOT={derived / 'Build' / 'Products'}", f"OBJROOT={derived / 'Build' / 'Intermediates.noindex'}"])
    else:
        command.extend(["-derivedDataPath", target.derived_data])
    if target.result_bundle:
        command.extend(["-resultBundlePath", target.result_bundle])
    command.extend(target.extra_args)
    command.append(action)
    return command


def build(target: XcodeTarget, *, cwd: Path) -> CommandResult:
    return run_command(build_xcodebuild_command(target, "build"), cwd=str(cwd))


def test(target: XcodeTarget, *, cwd: Path) -> CommandResult:
    return run_command(build_xcodebuild_command(target, "test"), cwd=str(cwd))
