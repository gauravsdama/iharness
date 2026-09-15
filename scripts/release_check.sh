#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
mode=${1:-technical}
case "$mode" in
  technical|--publish) ;;
  *) echo "Usage: ./scripts/release_check.sh [--publish]" >&2; exit 64 ;;
esac
install_root=$(mktemp -d "${TMPDIR:-/tmp}/iharness-release.XXXXXX")
trap 'rm -rf "$install_root"' EXIT HUP INT TERM

cd "$project_root"
git diff --check
python3 -m compileall -q iharness tests
python3 -m unittest discover -s tests -v
python3 -m iharness --help >/dev/null
./scripts/setup.sh --prefix "$install_root" --no-codex-skill
"$install_root/bin/iharness" --version

if git grep -n '/Users/' -- . ':!scripts/release_check.sh'; then
  echo "Release check failed: a tracked personal home path was found." >&2
  exit 1
fi

if git ls-files | grep -Eq '(^|/)(\.iharness|DerivedData|build|dist|[^/]+\.egg-info)(/|$)'; then
  echo "Release check failed: generated output is tracked." >&2
  exit 1
fi

if [ "$mode" = "--publish" ] && [ ! -f LICENSE ]; then
  echo "Publish check failed: the repository owner has not selected a LICENSE." >&2
  exit 1
fi
if [ "$mode" = "--publish" ] && [ -n "$(git status --porcelain --untracked-files=all)" ]; then
  echo "Publish check failed: the working tree is not clean." >&2
  exit 1
fi

echo "iHarness technical release checks passed."
