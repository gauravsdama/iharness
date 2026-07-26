from __future__ import annotations

from dataclasses import dataclass
import json
import signal
import subprocess
import time
from pathlib import Path

from .runner import CommandResult, run_command


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


def resolve_device(device: str | None, devices: list[SimulatorDevice] | None = None) -> SimulatorDevice:
    available = devices if devices is not None else list_devices()
    if not available:
        raise RuntimeError("No available iOS simulator devices were found.")

    if device in (None, "", "default"):
        preferred = ["iPhone 17", "iPhone 17 Pro", "iPhone 16", "iPhone 15"]
        for name in preferred:
            match = find_device(name, available)
            if match is not None:
                return match
        return available[0]

    match = find_device(device, available)
    if match is None:
        names = ", ".join(sorted({candidate.name for candidate in available}))
        raise RuntimeError(f"Could not find simulator '{device}'. Available devices: {names}")
    return match


def find_device(query: str, devices: list[SimulatorDevice]) -> SimulatorDevice | None:
    normalized = query.lower()
    for device in devices:
        if device.udid.lower() == normalized:
            return device
    for device in devices:
        if device.name.lower() == normalized:
            return device
    for device in devices:
        if normalized in device.name.lower():
            return device
    return None


def boot_device(device: str | None = None, *, open_simulator: bool = False, timeout: int = 120) -> SimulatorDevice:
    selected = resolve_device(device)
    if not selected.is_booted:
        result = run_command(["xcrun", "simctl", "boot", selected.udid], timeout=timeout)
        if result.returncode not in (0, 149):
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    wait = run_command(["xcrun", "simctl", "bootstatus", selected.udid, "-b"], timeout=timeout)
    if not wait.ok:
        raise RuntimeError(wait.stderr.strip() or wait.stdout.strip())
    if open_simulator:
        run_command(["open", "-a", "Simulator"])
    return resolve_device(selected.udid)


def install_app(device: str, app_path: str) -> CommandResult:
    return run_command(["xcrun", "simctl", "install", device, app_path])


def launch_app(device: str, bundle_id: str, args: list[str] | None = None) -> CommandResult:
    command = ["xcrun", "simctl", "launch", device, bundle_id]
    if args:
        command.extend(args)
    return run_command(command)


def take_screenshot(device: str, output_path: Path) -> CommandResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return run_command(["xcrun", "simctl", "io", device, "screenshot", str(output_path)])


def record_video(device: str, output_path: Path, *, seconds: int = 10) -> CommandResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["xcrun", "simctl", "io", device, "recordVideo", str(output_path)]
    start = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.send_signal(signal.SIGINT)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    returncode = process.returncode
    if timed_out and returncode in (-15, 0, 143):
        returncode = 0
    return CommandResult(
        command=command,
        returncode=returncode,
        stdout=stdout or "",
        stderr=stderr or "",
        duration_seconds=time.monotonic() - start,
    )


def capture_logs(
    device: str,
    output_path: Path,
    *,
    seconds: int = 10,
    bundle_id: str | None = None,
    predicate: str | None = None,
) -> CommandResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if predicate is None and bundle_id:
        predicate = f'process == "{bundle_id}" OR subsystem CONTAINS "{bundle_id}"'
    command = ["xcrun", "simctl", "spawn", device, "log", "stream", "--style", "compact"]
    if predicate:
        command.extend(["--predicate", predicate])

    start = time.monotonic()
    timed_out = False
    with output_path.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _, stderr = process.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                _, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                _, stderr = process.communicate()
    returncode = process.returncode
    if timed_out and returncode in (-15, 0, 143):
        returncode = 0
    return CommandResult(
        command=command,
        returncode=returncode,
        stdout=str(output_path),
        stderr=stderr or "",
        duration_seconds=time.monotonic() - start,
    )
