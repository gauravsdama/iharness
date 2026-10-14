#!/bin/sh
set -eu

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
project_root=$(CDPATH='' cd -- "$script_dir/.." && pwd)
install_root=${RUNNER_TEMP:-${TMPDIR:-/tmp}}/iharness-installed
derived_data="$project_root/.iharness/CI-DerivedData"
evidence_dir="$project_root/.iharness/ci-evidence"
bundle_id=dev.iharness.fixture

cleanup() {
  if [ -f "$evidence_dir/report.json" ]; then
    udid=$(python3 - "$evidence_dir/report.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
for step in payload.get("steps", []):
    if step.get("name") == "boot":
        print(step.get("device", {}).get("udid", ""))
        break
PY
)
    if [ -n "$udid" ]; then
      xcrun simctl terminate "$udid" "$bundle_id" >/dev/null 2>&1 || true
      xcrun simctl uninstall "$udid" "$bundle_id" >/dev/null 2>&1 || true
      xcrun simctl shutdown "$udid" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT HUP INT TERM

cd "$project_root"
rm -rf "$install_root" "$derived_data" "$evidence_dir"
mkdir -p "$evidence_dir"

{
  sw_vers
  uname -m
  python3 --version
  xcodebuild -version
} > "$evidence_dir/toolchain.txt" 2>&1

./scripts/setup.sh --prefix "$install_root" --no-codex-skill
"$install_root/bin/iharness" --version
"$install_root/bin/iharness" verify \
  --project fixtures/IHarnessFixture/IHarnessFixture.xcodeproj \
  --scheme IHarnessFixture \
  --bundle-id "$bundle_id" \
  --app .iharness/CI-DerivedData/Build/Products/Debug-iphonesimulator/IHarnessFixture.app \
  --device default \
  --derived-data .iharness/CI-DerivedData \
  --run-tests \
  --launch-wait-seconds 2 \
  --log-seconds 2 \
  --out .iharness/ci-evidence

python3 - "$evidence_dir" <<'PY'
import json
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
report = json.loads((root / "report.json").read_text(encoding="utf-8"))
expected = {"doctor", "xcode-version", "boot", "build", "test", "install", "launch", "screenshot", "logs"}
seen = {step.get("name") for step in report.get("steps", [])}
failed = [step.get("name") for step in report.get("steps", []) if not step.get("ok")]
if report.get("status") != "passed" or failed or expected - seen:
    raise SystemExit(
        f"fixture verification incomplete: status={report.get('status')!r}, "
        f"failed={failed!r}, missing={sorted(expected - seen)!r}"
    )

limits = {
    "report.json": 2 * 1024 * 1024,
    "report.md": 512 * 1024,
    "screenshot.png": 10 * 1024 * 1024,
    "simulator.log": 2 * 1024 * 1024,
}
for name, maximum in limits.items():
    path = root / name
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing or empty fixture evidence: {name}")
    if path.stat().st_size > maximum:
        raise SystemExit(f"fixture evidence exceeds {maximum} bytes: {name}")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise SystemExit(f"fixture evidence is not owner-only: {name}")

png = (root / "screenshot.png").read_bytes()
if not png.startswith(b"\x89PNG\r\n\x1a\n"):
    raise SystemExit("fixture screenshot is not a PNG")
if "IHARNESS_FIXTURE_READY" not in (root / "simulator.log").read_text(encoding="utf-8"):
    raise SystemExit("fixture readiness marker was not captured in the bounded Simulator log")
PY
