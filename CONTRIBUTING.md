# Contributing to iHarness

iHarness should remain a predictable wrapper around Apple tooling, not a second build system.

1. Keep CLI inputs explicit; do not infer project settings silently.
2. Preserve machine-readable reports and useful failure output.
3. Avoid unbounded commands, logs, recordings, or generated artifacts.
4. Add focused tests for parser, config, or command-construction changes.

Run:

```sh
python3 -m unittest discover -v
```

For a real Xcode or Simulator change, include the command used and a short summary of the resulting report. Do not commit `.iharness/` artifacts unless they are intentional small fixtures.
