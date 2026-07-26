from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import shutil
import sys

from . import __version__
from .config import DEFAULT_CONFIG_PATH, HarnessConfig, load_config, save_config
from .monitor import watch
from .runner import command_exists, run_command
from .simctl import boot_device, capture_logs, install_app, launch_app, list_devices, record_video, take_screenshot
from .verify import run_verification
from .xcode import XcodeTarget, build as xcode_build, test as xcode_test


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"iharness: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iharness",
        description="Agent-friendly iOS simulator build, monitor, and verification harness.",
    )
    parser.add_argument("--version", action="version", version=f"iharness {__version__}")
    subparsers = parser.add_subparsers(required=True)

    doctor = subparsers.add_parser("doctor", help="Check local iOS development prerequisites.")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    doctor.set_defaults(func=cmd_doctor)

    devices = subparsers.add_parser("devices", help="List available simulator devices.")
    devices.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    devices.set_defaults(func=cmd_devices)

    init = subparsers.add_parser("init", help="Create .iharness/config.json for an app workspace.")
    add_config_args(init)
    init.set_defaults(func=cmd_init)

    boot = subparsers.add_parser("boot", help="Boot an iOS simulator.")
    boot.add_argument("--device", default=None, help="Simulator name or UDID.")
    boot.add_argument("--open", action="store_true", help="Open the Simulator app.")
    boot.add_argument("--timeout", type=int, default=120)
    boot.set_defaults(func=cmd_boot)

    build = subparsers.add_parser("build", help="Run xcodebuild build.")
    add_xcode_args(build)
    build.set_defaults(func=cmd_build)

    test = subparsers.add_parser("test", help="Run xcodebuild test.")
    add_xcode_args(test)
    test.set_defaults(func=cmd_test)

    install = subparsers.add_parser("install", help="Install an .app into a simulator.")
    install.add_argument("--device", default="booted", help="Simulator UDID or 'booted'.")
    install.add_argument("--app", required=True, help="Path to .app bundle.")
    install.set_defaults(func=cmd_install)

    launch = subparsers.add_parser("launch", help="Launch an installed app.")
    launch.add_argument("--device", default="booted", help="Simulator UDID or 'booted'.")
    launch.add_argument("--bundle-id", required=True)
    launch.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the app.")
    launch.set_defaults(func=cmd_launch)

    screenshot = subparsers.add_parser("screenshot", help="Capture a simulator screenshot.")
    screenshot.add_argument("--device", default="booted", help="Simulator UDID or 'booted'.")
    screenshot.add_argument("--out", default=".iharness/screenshot.png")
    screenshot.set_defaults(func=cmd_screenshot)

    record = subparsers.add_parser("record", help="Record a bounded simulator video.")
    record.add_argument("--device", default="booted", help="Simulator UDID or 'booted'.")
    record.add_argument("--seconds", type=int, default=10)
    record.add_argument("--out", default=".iharness/simulator.mp4")
    record.set_defaults(func=cmd_record)

    logs = subparsers.add_parser("logs", help="Capture simulator logs for a bounded period.")
    logs.add_argument("--device", default="booted", help="Simulator UDID or 'booted'.")
    logs.add_argument("--bundle-id", default=None)
    logs.add_argument("--predicate", default=None)
    logs.add_argument("--seconds", type=int, default=10)
    logs.add_argument("--out", default=".iharness/simulator.log")
    logs.set_defaults(func=cmd_logs)

    verify = subparsers.add_parser("verify", help="Run an agent-friendly build/test/install/launch verification pass.")
    add_config_args(verify)
    verify.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Config JSON path.")
    verify.add_argument("--out", default=None, help="Verification output directory.")
    verify.set_defaults(func=cmd_verify)

    watch_parser = subparsers.add_parser("watch", help="Monitor files and rerun verification after changes.")
    watch_parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Config JSON path.")
    watch_parser.add_argument("--interval", type=float, default=2.0)
    watch_parser.add_argument("--out", default=None, help="Fixed verification output directory.")
    watch_parser.set_defaults(func=cmd_watch)

    return parser


def add_config_args(parser: argparse.ArgumentParser) -> None:
    add_xcode_args(parser, include_required=False)
    parser.add_argument("--bundle-id", default=None, help="App bundle identifier for launch/log filtering.")
    parser.add_argument("--app", dest="app_path", default=None, help="Path to built .app bundle.")
    parser.add_argument("--run-tests", action="store_true", default=None, help="Run xcodebuild test during verify.")
    parser.add_argument("--no-screenshot", action="store_true", help="Skip screenshot capture during verify.")
    parser.add_argument("--log-seconds", type=int, default=None)
    parser.add_argument("--watch-path", action="append", dest="watch_paths", default=None)
    parser.add_argument("--watch-extension", action="append", dest="watch_extensions", default=None)


def add_xcode_args(parser: argparse.ArgumentParser, *, include_required: bool = True) -> None:
    parser.add_argument("--workspace", default=None, help="Path to .xcworkspace.")
    parser.add_argument("--project", default=None, help="Path to .xcodeproj.")
    parser.add_argument("--scheme", default=None, required=False if not include_required else False)
    parser.add_argument("--configuration", default=None)
    parser.add_argument("--device", default=None, help="Simulator name or UDID.")
    parser.add_argument("--derived-data", default=None)
    parser.add_argument("--result-bundle", default=None)
    parser.add_argument("--extra-xcode-arg", action="append", default=None)


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = {
        "platform": platform.platform(),
        "xcodebuild": shutil.which("xcodebuild"),
        "xcrun": shutil.which("xcrun"),
        "simctl": None,
    }
    checks["simctl"] = "available" if checks["xcrun"] else None
    result = run_command(["xcodebuild", "-version"]) if command_exists("xcodebuild") else None
    payload = {
        "ok": bool(checks["xcodebuild"] and checks["xcrun"]),
        "checks": checks,
        "xcode_version": result.stdout.strip() if result and result.ok else None,
        "xcode_error": result.stderr.strip() if result and not result.ok else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"iharness {__version__}")
        print(f"platform: {payload['checks']['platform']}")
        print(f"xcodebuild: {checks['xcodebuild'] or 'missing'}")
        print(f"xcrun: {checks['xcrun'] or 'missing'}")
        if payload["xcode_version"]:
            print(payload["xcode_version"])
        print("status: OK" if payload["ok"] else "status: missing prerequisites")
    return 0 if payload["ok"] else 1


def cmd_devices(args: argparse.Namespace) -> int:
    devices = list_devices()
    if args.json:
        print(json.dumps([device.as_dict() for device in devices], indent=2))
    else:
        for device in devices:
            print(f"{device.name}\t{device.udid}\t{device.state}\t{device.runtime}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    config = HarnessConfig().merged(config_overrides(args))
    path = save_config(config)
    print(f"Wrote {path}")
    return 0


def cmd_boot(args: argparse.Namespace) -> int:
    device = boot_device(args.device, open_simulator=args.open, timeout=args.timeout)
    print(f"Booted {device.name} ({device.udid})")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    config = load_config().merged(config_overrides(args))
    target = target_from_config(config)
    result = xcode_build(target, cwd=Path.cwd())
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def cmd_test(args: argparse.Namespace) -> int:
    config = load_config().merged(config_overrides(args))
    target = target_from_config(config)
    result = xcode_test(target, cwd=Path.cwd())
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def cmd_install(args: argparse.Namespace) -> int:
    result = install_app(args.device, args.app)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def cmd_launch(args: argparse.Namespace) -> int:
    app_args = args.args
    if app_args and app_args[0] == "--":
        app_args = app_args[1:]
    result = launch_app(args.device, args.bundle_id, app_args)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def cmd_screenshot(args: argparse.Namespace) -> int:
    output = Path(args.out)
    result = take_screenshot(args.device, output)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    if result.ok:
        print(str(output.resolve()))
    return result.returncode


def cmd_record(args: argparse.Namespace) -> int:
    output = Path(args.out)
    result = record_video(args.device, output, seconds=args.seconds)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    if result.ok:
        print(str(output.resolve()))
    return result.returncode


def cmd_logs(args: argparse.Namespace) -> int:
    output = Path(args.out)
    result = capture_logs(
        args.device,
        output,
        seconds=args.seconds,
        bundle_id=args.bundle_id,
        predicate=args.predicate,
    )
    print(result.stderr, end="", file=sys.stderr)
    print(str(output.resolve()))
    return result.returncode


def cmd_verify(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config)).merged(config_overrides(args))
    report = run_verification(config, cwd=Path.cwd(), output_dir=Path(args.out).resolve() if args.out else None)
    print(f"{report.status.upper()} {report.output_dir / 'report.md'}")
    return 0 if report.status == "passed" else 1


def cmd_watch(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config = load_config(config_path)

    def run_once() -> None:
        latest = load_config(config_path)
        report = run_verification(latest, cwd=Path.cwd(), output_dir=Path(args.out).resolve() if args.out else None)
        print(f"{report.status.upper()} {report.output_dir / 'report.md'}", flush=True)

    watch(
        config.watch_paths,
        config.watch_extensions,
        cwd=Path.cwd(),
        interval=args.interval,
        on_change=run_once,
    )
    return 0


def config_overrides(args: argparse.Namespace) -> dict[str, object]:
    overrides = {
        "workspace": getattr(args, "workspace", None),
        "project": getattr(args, "project", None),
        "scheme": getattr(args, "scheme", None),
        "configuration": getattr(args, "configuration", None),
        "device": getattr(args, "device", None),
        "bundle_id": getattr(args, "bundle_id", None),
        "app_path": getattr(args, "app_path", None),
        "derived_data": getattr(args, "derived_data", None),
        "result_bundle": getattr(args, "result_bundle", None),
        "extra_xcode_args": getattr(args, "extra_xcode_arg", None),
        "watch_paths": getattr(args, "watch_paths", None),
        "watch_extensions": getattr(args, "watch_extensions", None),
        "log_seconds": getattr(args, "log_seconds", None),
    }
    run_tests = getattr(args, "run_tests", None)
    if run_tests is not None:
        overrides["run_tests"] = run_tests
    if getattr(args, "no_screenshot", False):
        overrides["screenshot"] = False
    return overrides


def target_from_config(config: HarnessConfig) -> XcodeTarget:
    return XcodeTarget(
        workspace=config.workspace,
        project=config.project,
        scheme=config.scheme,
        configuration=config.configuration,
        device=config.device,
        derived_data=config.derived_data,
        result_bundle=config.result_bundle,
        extra_args=config.extra_xcode_args,
    )
