# iHarness

iHarness is a small, dependency-free CLI for a repeatable iOS Simulator verification loop. It wraps `xcodebuild` and `xcrun simctl` to build an app, run tests, boot a simulator, install and launch an app, and save the evidence from a run in one place.

It is for developers and coding agents that need a readable record of what actually ran—not a collection of remembered shell commands.

## What it covers

- Xcode and Simulator environment checks
- Simulator discovery and booting
- Xcode project or workspace builds and tests
- App installation and launch by bundle identifier
- Simulator screenshots, video captures, and bounded logs
- Markdown and JSON verification reports
- Polling-based re-verification while source files change

## Requirements

- macOS with Xcode selected by `xcode-select`
- Python 3.11 or later
- An iOS Simulator runtime installed through Xcode

## Install

### Standalone installation

Use the setup script to install an isolated Python runtime and launcher under a prefix you control. The default prefix is `$HOME/.local`.

From a clone or release checkout:

```sh
cd iharness
./scripts/setup.sh --prefix "$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
iharness doctor
```

`./scripts/setup.sh --check` validates prerequisites without installing. The installer can also add the bundled Codex skill; see [Codex integration](docs/codex-integration.md).

### Development installation

```sh
python3 -m pip install -e .
python3 -m iharness doctor
```

## Quick start

From an iOS app repository, create a configuration that identifies the app and Simulator target:

```sh
iharness init \
  --workspace MyApp.xcworkspace \
  --scheme MyApp \
  --bundle-id com.example.MyApp \
  --app .iharness/DerivedData/Build/Products/Debug-iphonesimulator/MyApp.app \
  --device "iPhone 17"
iharness verify --run-tests
```

Each run writes artifacts to `.iharness/runs/<timestamp>/`:

- `report.md` — concise human-readable result
- `report.json` — machine-readable steps and return codes
- `screenshot.png` — Simulator state after launch
- `simulator.log` — bounded Simulator logs

## Operating model

The tool intentionally keeps Xcode inputs explicit. A useful verification configuration needs a `workspace` or `project`, `scheme`, `bundle_id`, and `app_path`. iHarness does not yet derive an app bundle from Xcode build settings; provide the bundle path you want installed.

A run with no project/workspace can establish that Xcode and a Simulator are healthy, but it is not application verification. Do not treat a boot-only screenshot as evidence that an app works.

## Commands

```sh
iharness doctor
iharness devices
iharness boot --device "iPhone 17" --open
iharness build --workspace MyApp.xcworkspace --scheme MyApp
iharness test --workspace MyApp.xcworkspace --scheme MyApp
iharness install --app path/to/MyApp.app
iharness launch --bundle-id com.example.MyApp
iharness screenshot --out .iharness/current.png
iharness record --seconds 8 --out .iharness/current.mp4
iharness logs --bundle-id com.example.MyApp --seconds 20
iharness verify --run-tests
iharness watch
```

## Codex integration

iHarness is a local CLI, not an MCP service. Its supported Codex integration is a reusable local skill and optional project-level `AGENTS.md` guidance. The setup script installs the skill by default; [the integration guide](docs/codex-integration.md) explains the workflow and available pathways.

## Development

```sh
python3 -m unittest discover -v
```

Contributions should preserve explicit command inputs, bounded log/video capture, and inspection-friendly run artifacts. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
