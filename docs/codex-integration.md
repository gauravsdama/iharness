# Codex integration

`iharness` is a local command-line verification tool. It is intentionally not
an MCP connector: it does not expose external data or authorize an account.
The supported Codex integration is a reusable local skill plus project-scoped
guidance.

## One-time setup

```sh
git clone <your-iharness-repository> iharness
cd iharness
./scripts/setup.sh --prefix "$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
```

The setup script installs the `iharness` executable and copies the bundled
skill to `$CODEX_HOME/skills/iharness` (or `$HOME/.codex/skills/iharness`).
Start a new Codex task after installation so the skill is discovered.

Use `./scripts/setup.sh --check` to validate Xcode, `xcrun`, Python, and pip
without making changes. Use `--no-codex-skill` if only the CLI is wanted.

## Project guidance

Add this to the target iOS repository's `AGENTS.md` when iHarness should be
the normal verification path:

```md
## iOS verification

Use the `iharness` skill for iOS Simulator work. Before reporting success, run
`iharness verify --run-tests` with an explicit workspace/project, scheme,
bundle id, and app path. Inspect the generated report, screenshot, and logs.
Do not call boot-only or screenshot-only output a successful app verification.
```

## Functional pathways

| Need | Command |
| --- | --- |
| Prerequisites | `iharness doctor` |
| Select a Simulator | `iharness devices`, then `iharness boot --device "iPhone 17"` |
| Build or test | `iharness build ...`, `iharness test ...` |
| Inspect UI/runtime | `iharness screenshot`, `iharness logs`, `iharness record` |
| Full loop | `iharness verify --run-tests` |
| Re-run while editing | `iharness watch` |

## Current verification boundary

The current version requires `app_path` to install a build artifact; it does
not derive one from Xcode automatically. A config missing an app target can
still create a passing boot/screenshot report, so treat that as environment
health only, not application verification.
