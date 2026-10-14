from __future__ import annotations

import platform
import shutil
import time
from datetime import datetime
from pathlib import Path

from .config import HarnessConfig, resolve_path
from .report import VerificationReport
from .runner import run_command
from .simctl import boot_device, capture_logs, install_app, launch_app, take_screenshot
from .xcode import XcodeTarget
from .xcode import build as xcode_build
from .xcode import test as xcode_test


def run_verification(
    config: HarnessConfig, *, cwd: Path, output_dir: Path | None = None
) -> VerificationReport:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    report = VerificationReport(
        output_dir=output_dir or cwd / ".iharness" / "runs" / timestamp
    )
    application_requested = bool(
        config.workspace or config.project or config.app_path or config.bundle_id
    )

    try:
        _run_verification_steps(config, cwd=cwd, report=report)
    except KeyboardInterrupt:
        report.add_error("Verification interrupted.")
        raise
    except Exception as exc:
        report.add_error(
            f"Verification failed unexpectedly: {type(exc).__name__}: {exc}"
        )
    finally:
        if report.status != "failed" and not application_requested:
            report.mark_incomplete(
                "No application build, test, install, or launch was requested."
            )
        report.write()
    return report


def _run_verification_steps(
    config: HarnessConfig, *, cwd: Path, report: VerificationReport
) -> None:

    doctor_payload = {
        "ok": shutil.which("xcrun") is not None
        and shutil.which("xcodebuild") is not None,
        "platform": platform.platform(),
        "xcrun": shutil.which("xcrun"),
        "xcodebuild": shutil.which("xcodebuild"),
    }
    report.add_step("doctor", doctor_payload)
    if not doctor_payload["ok"]:
        report.add_error(
            "Missing xcrun or xcodebuild. Install Xcode and select it with xcode-select."
        )
        return

    xcode_version = run_command(["xcodebuild", "-version"])
    report.add_step("xcode-version", xcode_version)
    if not xcode_version.ok:
        return

    try:
        device = boot_device(config.device, open_simulator=False)
        report.add_step("boot", {"ok": True, "device": device.as_dict()})
    except Exception as exc:
        report.add_error(f"Boot failed: {exc}")
        return

    target: XcodeTarget | None = None
    if config.workspace or config.project:
        target = XcodeTarget(
            workspace=resolve_path(config.workspace, cwd),
            project=resolve_path(config.project, cwd),
            scheme=config.scheme,
            target=config.target,
            sdk=config.sdk,
            configuration=config.configuration,
            device=config.build_destination
            or (None if config.target and config.sdk else device.udid),
            derived_data=resolve_path(config.derived_data, cwd) or config.derived_data,
            result_bundle=resolve_path(config.result_bundle, cwd)
            if config.result_bundle
            else None,
            extra_args=config.extra_xcode_args,
        )
        try:
            build_result = xcode_build(target, cwd=cwd)
            report.add_step("build", build_result)
            if not build_result.ok:
                return
        except Exception as exc:
            report.add_error(f"Build failed before xcodebuild ran: {exc}")
            return

    if target is not None and config.run_tests:
        test_result = xcode_test(target, cwd=cwd)
        report.add_step("test", test_result)
        if not test_result.ok:
            return

    app_path = resolve_path(config.app_path, cwd)
    if app_path:
        install_result = install_app(device.udid, app_path)
        report.add_step("install", install_result)
        if not install_result.ok:
            return

    if config.bundle_id:
        launch_result = launch_app(
            device.udid, config.bundle_id, terminate_running=True
        )
        report.add_step("launch", launch_result)
        if not launch_result.ok:
            return
        if config.launch_wait_seconds > 0:
            time.sleep(config.launch_wait_seconds)

    if config.screenshot:
        screenshot_path = report.output_dir / "screenshot.png"
        screenshot_result = take_screenshot(device.udid, screenshot_path)
        report.add_step("screenshot", screenshot_result)
        if screenshot_result.ok:
            report.artifacts["screenshot"] = screenshot_path.name

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
            report.artifacts["logs"] = log_path.name
