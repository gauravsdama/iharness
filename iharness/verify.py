from __future__ import annotations

from datetime import datetime
from pathlib import Path
import platform
import shutil
import time

from .config import HarnessConfig, resolve_path
from .report import VerificationReport
from .runner import run_command
from .simctl import boot_device, capture_logs, install_app, launch_app, take_screenshot
from .xcode import XcodeTarget, build as xcode_build, test as xcode_test


def run_verification(config: HarnessConfig, *, cwd: Path, output_dir: Path | None = None) -> VerificationReport:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report = VerificationReport(output_dir=output_dir or cwd / ".iharness" / "runs" / timestamp)

    doctor_payload = {
        "ok": shutil.which("xcrun") is not None and shutil.which("xcodebuild") is not None,
        "platform": platform.platform(),
        "xcrun": shutil.which("xcrun"),
        "xcodebuild": shutil.which("xcodebuild"),
    }
    report.add_step("doctor", doctor_payload)
    if not doctor_payload["ok"]:
        report.add_error("Missing xcrun or xcodebuild. Install Xcode and select it with xcode-select.")
        report.write()
        return report

    xcode_version = run_command(["xcodebuild", "-version"])
    report.add_step("xcode-version", xcode_version)

    try:
        device = boot_device(config.device, open_simulator=False)
        report.add_step("boot", {"ok": True, "device": device.as_dict()})
    except Exception as exc:
        report.add_error(f"Boot failed: {exc}")
        report.write()
        return report

    target: XcodeTarget | None = None
    if config.workspace or config.project:
        target = XcodeTarget(
            workspace=resolve_path(config.workspace, cwd),
            project=resolve_path(config.project, cwd),
            scheme=config.scheme,
            target=config.target,
            sdk=config.sdk,
            configuration=config.configuration,
            device=config.build_destination or (None if config.target and config.sdk else device.udid),
            derived_data=resolve_path(config.derived_data, cwd) or config.derived_data,
            result_bundle=resolve_path(config.result_bundle, cwd) if config.result_bundle else None,
            extra_args=config.extra_xcode_args,
        )
        try:
            build_result = xcode_build(target, cwd=cwd)
            report.add_step("build", build_result)
            if not build_result.ok:
                report.write()
                return report
        except Exception as exc:
            report.add_error(f"Build failed before xcodebuild ran: {exc}")
            report.write()
            return report

    if target is not None and config.run_tests:
        test_result = xcode_test(target, cwd=cwd)
        report.add_step("test", test_result)
        if not test_result.ok:
            report.write()
            return report

    app_path = resolve_path(config.app_path, cwd)
    if app_path:
        install_result = install_app(device.udid, app_path)
        report.add_step("install", install_result)
        if not install_result.ok:
            report.write()
            return report

    if config.bundle_id:
        launch_result = launch_app(device.udid, config.bundle_id)
        report.add_step("launch", launch_result)
        if not launch_result.ok:
            report.write()
            return report
        if config.launch_wait_seconds > 0:
            time.sleep(config.launch_wait_seconds)

    if config.screenshot:
        screenshot_path = report.output_dir / "screenshot.png"
        screenshot_result = take_screenshot(device.udid, screenshot_path)
        report.add_step("screenshot", screenshot_result)
        if screenshot_result.ok:
            report.artifacts["screenshot"] = str(screenshot_path)

    if config.log_seconds > 0:
        log_path = report.output_dir / "simulator.log"
        log_result = capture_logs(
            device.udid,
            log_path,
            seconds=config.log_seconds,
            bundle_id=config.bundle_id,
        )
        report.add_step("logs", log_result)
        if log_path.exists():
            report.artifacts["logs"] = str(log_path)

    report.write()
    return report
