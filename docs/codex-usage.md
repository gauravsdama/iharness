# Codex Usage Notes

Use `iharness` as the repeatable verification layer for iOS work.

## Standard loop

```bash
iharness doctor
iharness devices
iharness verify --run-tests
```

After a code change:

```bash
iharness verify --run-tests
```

For longer sessions:

```bash
iharness watch
```

## What the agent should inspect

- `report.md` for pass/fail state and failing command excerpts.
- `report.json` for machine-readable status.
- `screenshot.png` for visual regressions.
- `simulator.log` for launch/runtime errors.

## Minimum useful app config

```json
{
  "workspace": "MyApp.xcworkspace",
  "scheme": "MyApp",
  "bundle_id": "com.example.MyApp",
  "device": "iPhone 17",
  "run_tests": true
}
```

Use `project` instead of `workspace` for simple Xcode projects.
