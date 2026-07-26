---
name: iharness
description: Build, test, launch, and verify iOS Simulator apps with the locally installed iharness CLI. Use for iOS or React Native iOS verification when an Xcode project/workspace is available.
---

# iHarness

Use this skill to run a repeatable iOS Simulator verification loop. `iharness`
is a local CLI, not an MCP service: it has no external-account connector or
remote data access.

## Preconditions

Run these from the target app repository:

```sh
iharness doctor
iharness devices
```

Before `verify`, create or inspect `.iharness/config.json`. A meaningful app
verification must set all of the following:

- `workspace` or `project`
- `scheme`
- `bundle_id`
- `app_path` for the built `.app`

Do not treat a report containing only `doctor`, `boot`, a screenshot, or logs
as app verification. In the current CLI, an empty configuration can pass after
booting a simulator.

## Standard pathway

1. Run `iharness doctor` and `iharness devices`.
2. Inspect the app's Xcode workspace/project and scheme; create configuration
   with `iharness init` or edit `.iharness/config.json`.
3. Make the requested app change.
4. Run `iharness verify --run-tests`.
5. Inspect `.iharness/runs/<timestamp>/report.md`, `report.json`,
   `screenshot.png`, and `simulator.log`.
6. Report success only when build/test/install/launch steps and the relevant
   visual or log evidence passed.

## Available functionality

- `doctor`: local Xcode and Simulator prerequisites
- `devices`, `boot`: discover and start iOS Simulators
- `build`, `test`: run `xcodebuild` for a project/workspace and scheme
- `install`, `launch`: put an app on a Simulator and start it
- `screenshot`, `record`, `logs`: capture debugging artifacts
- `verify`, `watch`: build/test/install/launch workflow and repeated runs

## Constraints

- Keep generated `.iharness/` artifacts out of commits.
- Prefer one explicit target Simulator over relying on a name when multiple
  runtimes are installed.
- Never report a screenshot alone as proof of the requested UI behavior.
