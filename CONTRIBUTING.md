# Contributing to iHarness

iHarness should remain a predictable wrapper around Apple tooling, not a second build system.

1. Keep CLI inputs explicit; do not infer project settings silently.
2. Preserve machine-readable reports, atomic failure reports, and useful bounded failure output.
3. Avoid unbounded commands, logs, recordings, captured output, or generated artifacts. New subprocesses must use the shared process-group timeout path.
4. Add focused tests for parser, config, or command-construction changes.

The two Bandit subprocess suppressions in `iharness/runner.py` are intentional and narrow. Process execution is the tool's core function; commands are passed as argument arrays with `shell=False`, bounded output, finite deadlines, and process-group termination. Do not broaden those suppressions or introduce shell command evaluation.

Run:

```sh
python3 -m unittest discover -v
./scripts/release_check.sh
```

For a real Xcode or Simulator change, include the command used and a short summary of the resulting report. Do not commit `.iharness/` artifacts unless they are intentional small fixtures.
