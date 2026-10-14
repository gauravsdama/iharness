from __future__ import annotations

import json
import signal
from dataclasses import dataclass, replace
from pathlib import Path

from .runner import CommandResult, run_command, run_for_duration

MAX_CAPTURE_SECONDS = 3600


@dataclass(frozen=True)
class SimulatorDevice:
    name: str
    udid: str
    runtime: str
    state: str
    is_available: bool = True

    @property
    def is_booted(self) -> bool:
        return self.state.lower() == "booted"

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "udid": self.udid,
            "runtime": self.runtime,
            "state": self.state,
            "is_available": self.is_available,
        }


def list_devices() -> list[SimulatorDevice]:
    result = run_command(["xcrun", "simctl", "list", "devices", "available", "--json"])
    if not result.ok:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return parse_devices_json(result.stdout)


def parse_devices_json(payload: str) -> list[SimulatorDevice]:
    data = json.loads(payload)
    devices: list[SimulatorDevice] = []
    for runtime, runtime_devices in data.get("devices", {}).items():
        for item in runtime_devices:
            devices.append(
                SimulatorDevice(
                    name=item.get("name", ""),
                    udid=item.get("udid", ""),
                    runtime=runtime,
                    state=item.get("state", ""),
                    is_available=bool(item.get("isAvailable", True)),
                )
            )
    return devices


def resolve_device(
    device: str | None, devices: list[SimulatorDevice] | None = None
) -> SimulatorDevice:
    available = devices if devices is not None else list_devices()
    if not available:
        raise RuntimeError("No available iOS simulator devices were found.")

    if device in (None, "", "default"):
        preferred = ["iPhone 17", "iPhone 17 Pro", "iPhone 16", "iPhone 15"]
        for name in preferred:
            match = find_device(name, available)
            if match is not None:
                return match
        return sorted(available, key=_device_sort_key)[0]

    match = find_device(device, available)
    if match is None:
        names = ", ".join(sorted({candidate.name for candidate in available}))
        raise RuntimeError(
            f"Could not find simulator '{device}'. Available devices: {names}"
        )
    return match


def find_device(query: str, devices: list[SimulatorDevice]) -> SimulatorDevice | None:
    normalized = query.lower()
    ordered = sorted(devices, key=_device_sort_key)
    for device in ordered:
        if device.udid.lower() == normalized:
            return device
    for device in ordered:
        if device.name.lower() == normalized:
            return device
    for device in ordered:
        if normalized in device.name.lower():
            return device
    return None


def _device_sort_key(device: SimulatorDevice) -> tuple[object, ...]:
    version_parts = [
        int(part)
        for part in device.runtime.rsplit(".", 1)[-1].replace("-", ".").split(".")
        if part.isdigit()
    ]
    runtime_version = tuple(-part for part in (version_parts + [0, 0, 0, 0])[:4])
    return (
        not device.is_booted,
        runtime_version,
        device.name.casefold(),
        device.udid.casefold(),
    )


def boot_device(
    device: str | None = None, *, open_simulator: bool = False, timeout: int = 120
) -> SimulatorDevice:
    selected = resolve_device(device)
    if not selected.is_booted:
        result = run_command(
            ["xcrun", "simctl", "boot", selected.udid], timeout=timeout
        )
        if result.returncode not in (0, 149):
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    wait = run_command(
        ["xcrun", "simctl", "bootstatus", selected.udid, "-b"], timeout=timeout
    )
    if not wait.ok:
        raise RuntimeError(wait.stderr.strip() or wait.stdout.strip())
    if open_simulator:
        run_command(["open", "-a", "Simulator"])
    return resolve_device(selected.udid)


def install_app(device: str, app_path: str) -> CommandResult:
    return run_command(["xcrun", "simctl", "install", device, app_path])


def launch_app(
    device: str,
    bundle_id: str,
    args: list[str] | None = None,
    *,
    terminate_running: bool = False,
) -> CommandResult:
    command = ["xcrun", "simctl", "launch"]
    if terminate_running:
        command.append("--terminate-running-process")
    command.extend([device, bundle_id])
    if args:
        command.extend(args)
    return run_command(command)


def take_screenshot(device: str, output_path: Path) -> CommandResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(
        ["xcrun", "simctl", "io", device, "screenshot", str(output_path)]
    )
    return _finalize_private_artifact(result, output_path, "Screenshot")


def record_video(device: str, output_path: Path, *, seconds: int = 10) -> CommandResult:
    _validate_capture_seconds(seconds, "Video")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["xcrun", "simctl", "io", device, "recordVideo", str(output_path)]
    result = run_for_duration(
        command,
        seconds=seconds,
        stop_signal=signal.SIGINT,
        successful_stop_codes=(-signal.SIGINT, 0, 128 + signal.SIGINT),
    )
    return _finalize_private_artifact(result, output_path, "Video")


def capture_logs(
    device: str,
    output_path: Path,
    *,
    seconds: int = 10,
    bundle_id: str | None = None,
    predicate: str | None = None,
) -> CommandResult:
    _validate_capture_seconds(seconds, "Log")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if predicate is None and bundle_id:
        predicate_value = bundle_id.replace("\\", "\\\\").replace('"', '\\"')
        predicate = (
            f'process == "{predicate_value}" OR subsystem CONTAINS "{predicate_value}"'
        )
    command = [
        "xcrun",
        "simctl",
        "spawn",
        device,
        "log",
        "stream",
        "--style",
        "compact",
    ]
    if predicate:
        command.extend(["--predicate", predicate])

    return run_for_duration(
        command,
        seconds=seconds,
        stop_signal=signal.SIGTERM,
        successful_stop_codes=(-signal.SIGTERM, 0, 128 + signal.SIGTERM),
        output_path=output_path,
    )


def _validate_capture_seconds(seconds: int, label: str) -> None:
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise ValueError(f"{label} duration must be an integer number of seconds.")
    if seconds <= 0:
        raise ValueError(f"{label} duration must be greater than zero seconds.")
    if seconds > MAX_CAPTURE_SECONDS:
        raise ValueError(
            f"{label} duration must not exceed {MAX_CAPTURE_SECONDS} seconds."
        )


def _finalize_private_artifact(
    result: CommandResult, output_path: Path, label: str
) -> CommandResult:
    if not result.ok:
        return result
    if not output_path.is_file():
        message = f"{label} command succeeded but did not create {output_path}."
        stderr = (
            f"{result.stderr.rstrip()}\n{message}" if result.stderr.strip() else message
        )
        return replace(result, returncode=1, stderr=stderr)
    output_path.chmod(0o600)
    return result
