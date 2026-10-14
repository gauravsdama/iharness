# Release readiness

Status: **source-ready**. The repository is licensed under Apache-2.0, the offline installer passes, and the owned fixture application completed the local Simulator workflow. Matching-runtime XCTest is also configured in CI.

## Product and provenance

- Intended user: iOS developers who want one repeatable Simulator build, test, install, launch, screenshot, and log workflow.
- Employer-facing story: a dependency-free Python CLI that wraps Xcode and `simctl`, records every step, and makes verification artifacts easy to inspect or automate.
- Repository: `gauravsdama/iharness`, public, not a GitHub fork, with one author in the local commit history.
- Source: first-party Python code. The runtime has no third-party Python dependencies and no vendored source or generated Xcode output is tracked.
- Interface: CLI only. Simulator screenshots show the app under test, not an iHarness UI.

## Evidence recorded 2026-09-15

- `python3 -m unittest discover -s tests -v`: 31 tests passed, including subprocess timeout/output bounds and descendant termination, atomic redacted reports, private artifact handling, asset-catalog watching, deterministic Simulator selection, config validation, bounded video termination, and explicit Xcode target/SDK builds.
- `./scripts/setup.sh --check`: prerequisites passed on Python 3.14.4 and Xcode command-line tools.
- `./scripts/release_check.sh`: checks compilation, tests, CLI startup, a network-free temporary-prefix install, personal paths, and tracked artifacts.
- `python3 -m iharness verify --device "iPhone 17" --no-screenshot --log-seconds 0`: completed the doctor, Xcode-version, and iOS 26.2 Simulator boot steps with Xcode 26.5. Under the tightened status model this infrastructure-only scope is `INCOMPLETE`, not application verification.
- `python3 -m iharness verify --project fixtures/IHarnessFixture/IHarnessFixture.xcodeproj --target IHarnessFixture --sdk iphonesimulator --bundle-id dev.iharness.fixture --app .iharness/FixtureDerivedData/Build/Products/Debug-iphonesimulator/IHarnessFixture.app --device "iPhone 17" --derived-data .iharness/FixtureDerivedData --log-seconds 2 --out .iharness/fixture-e2e-final`: passed build, install, launch, delayed screenshot, and bounded logs.
- The fixture screenshot was visually inspected and shows the expected `iHarness fixture ready` state. The verifier now waits two seconds after launch so evidence does not capture the Simulator home-screen transition.
- GitHub Actions run `35034516771` passed both the clean-checkout offline install and the fixture XCTest workflow on the `macos-26` runner with an iPhone 17 and `OS=latest`.
- The current CI definition additionally builds and installs the wheel, invokes its `iharness` entry point, checks dependency/license metadata, and runs the repository-owned fixture through build, test, install, launch, screenshot, bounded-log capture, assertions, and cleanup using the documented standalone installer. This strengthened workflow must pass on the release commit before publishing.
- The required release lane uses GitHub's `macos-26` Apple Silicon runner and current bundled Xcode. The `macos-15` Apple Silicon lane runs the same lifecycle as informational compatibility coverage. Every run records its actual OS, architecture, Python, Xcode, and Simulator runtime inventory; the project does not claim fixed Xcode combinations that GitHub's rolling images no longer provide.
- CI evidence contains only the owned fixture report, screenshot, bounded log, and toolchain record. It is capped by assertions and retained for seven days. Derived data and the built application are neither uploaded nor committed.
- A separate pinned Gitleaks job scans the repository's complete Git history. The local release gate rejects generated artifacts, credentials, provisioning files, personal IDE state, local environment files, and personal home paths.

## Release boundary and blockers

- Local Xcode 26.5 cannot run XCTest against the installed iOS 26.2 Simulator runtime. The fixture's shared test scheme runs in `macos-26` CI against `OS=latest`; local build/install/launch evidence uses the explicit target/SDK path. Supporting the latest working CI pairing is the `v0.1.0` contract, not a promise of compatibility across older Xcode/runtime combinations.
- `.iharness/` may contain screenshots, logs, bundle identifiers, paths, and app output. It is ignored and must be reviewed before sharing.
- Infrastructure-only `verify` runs are `INCOMPLETE`; only a requested application build, test, install, or launch can produce `PASSED`.

## Release checklist

- Run `./scripts/release_check.sh`.
- Run `iharness doctor`, `iharness devices`, and `iharness verify --run-tests` against an owned fixture app.
- Inspect `report.md`, `report.json`, the screenshot, and bounded logs; record Xcode, runtime, device, and app revision.
- Repeat `./scripts/setup.sh` in a clean macOS user account or compatible Mac.
- Run `./scripts/release_check.sh --publish` from a clean release commit.
