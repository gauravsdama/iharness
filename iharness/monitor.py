from __future__ import annotations

import time
from pathlib import Path
from typing import Callable


def iter_watch_files(
    paths: list[str], extensions: list[str], *, cwd: Path
) -> list[Path]:
    normalized_exts = tuple(extensions)
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = cwd / path
        try:
            if not path.exists():
                continue
            if path.is_file() and path.suffix in normalized_exts:
                files.append(path)
                continue
            if path.is_dir():
                for candidate in path.rglob("*"):
                    try:
                        if ".git" in candidate.parts or ".iharness" in candidate.parts:
                            continue
                        in_asset_catalog = any(
                            parent.suffix == ".xcassets"
                            for parent in (candidate, *candidate.parents)
                        )
                        if candidate.is_file() and (
                            candidate.suffix in normalized_exts
                            or candidate.name.endswith(normalized_exts)
                            or (".xcassets" in normalized_exts and in_asset_catalog)
                        ):
                            files.append(candidate)
                    except OSError:
                        continue
        except OSError:
            continue
    return sorted(set(files))


def snapshot(paths: list[str], extensions: list[str], *, cwd: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for path in iter_watch_files(paths, extensions, cwd=cwd):
        try:
            result[str(path)] = path.stat().st_mtime_ns
        except OSError:
            continue
    return result


def watch(
    paths: list[str],
    extensions: list[str],
    *,
    cwd: Path,
    interval: float,
    on_change: Callable[[], None],
) -> None:
    if interval <= 0:
        raise ValueError("Watch interval must be greater than zero seconds.")
    previous = snapshot(paths, extensions, cwd=cwd)
    on_change()
    while True:
        time.sleep(interval)
        current = snapshot(paths, extensions, cwd=cwd)
        if current != previous:
            previous = current
            on_change()
