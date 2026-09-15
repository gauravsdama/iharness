# Release readiness

Status: **source-ready**. The repository is licensed under Apache-2.0, the offline installer passes, and the owned fixture application completed the local Simulator workflow. Matching-runtime XCTest is also configured in CI.

## Product and provenance

- Intended user: iOS developers who want one repeatable Simulator build, test, install, launch, screenshot, and log workflow.
- Employer-facing story: a dependency-free Python CLI that wraps Xcode and `simctl`, records every step, and makes verification artifacts easy to inspect or automate.
- Repository: `gauravsdama/iharness`, private, not a GitHub fork, with one author in the local commit history.
- Source: first-party Python code. The runtime has no third-party Python dependencies and no vendored source or generated Xcode output is tracked.
- Interface: CLI only. Simulator screenshots show the app under test, not an iHarness UI.

## Evidence recorded 2026-09-15

- `python3 -m unittest discover -s tests -v`: 17 tests passed, including bounded video termination and explicit Xcode target/SDK builds.
- `./scripts/setup.sh --check`: prerequisites passed on Python 3.14.4 and Xcode command-line tools.
- `./scripts/release_check.sh`: checks compilation, tests, CLI startup, a network-free temporary-prefix install, personal paths, and tracked artifacts.
- `python3 -m iharness verify --device "iPhone 17" --no-screenshot --log-seconds 0`: passed the doctor, Xcode-version, and iOS 26.2 Simulator boot steps with Xcode 26.5.
- `python3 -m iharness verify --project fixtures/IHarnessFixture/IHarnessFixture.xcodeproj --target IHarnessFixture --sdk iphonesimulator --bundle-id dev.iharness.fixture --app .iharness/FixtureDerivedData/Build/Products/Debug-iphonesimulator/IHarnessFixture.app --device "iPhone 17" --derived-data .iharness/FixtureDerivedData --log-seconds 2 --out .iharness/fixture-e2e-final`: passed build, install, launch, delayed screenshot, and bounded logs.
- The fixture screenshot was visually inspected and shows the expected `iHarness fixture ready` state. The verifier now waits two seconds after launch so evidence does not capture the Simulator home-screen transition.
- The `v0.1.0` CI policy is one current toolchain: the `macos-26` runner and its `OS=latest` iPhone 17 Simulator runtime. A multi-Xcode/runtime compatibility matrix is intentionally deferred until after `v0.1.0`.

## Release boundary and blockers

- Local Xcode 26.5 cannot run XCTest against the installed iOS 26.2 Simulator runtime. The fixture's shared test scheme runs in `macos-26` CI against `OS=latest`; local build/install/launch evidence uses the explicit target/SDK path. Supporting the latest working CI pairing is the `v0.1.0` contract, not a promise of compatibility across older Xcode/runtime combinations.
- `.iharness/` may contain screenshots, logs, bundle identifiers, paths, and app output. It is ignored and must be reviewed before sharing.

## Release checklist

- Run `./scripts/release_check.sh`.
- Run `iharness doctor`, `iharness devices`, and `iharness verify --run-tests` against an owned fixture app.
- Inspect `report.md`, `report.json`, the screenshot, and bounded logs; record Xcode, runtime, device, and app revision.
- Repeat `./scripts/setup.sh` in a clean macOS user account or compatible Mac.
- Run `./scripts/release_check.sh --publish` from a clean release commit.
