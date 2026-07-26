from __future__ import annotations

from pathlib import Path
import time
from typing import Callable


def iter_watch_files(paths: list[str], extensions: list[str], *, cwd: Path) -> list[Path]:
    normalized_exts = tuple(extensions)
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = cwd / path
        if not path.exists():
            continue
        if path.is_file() and path.suffix in normalized_exts:
            files.append(path)
            continue
        if path.is_dir():
            for candidate in path.rglob("*"):
                if ".git" in candidate.parts or ".iharness" in candidate.parts:
                    continue
                if candidate.is_file() and (
                    candidate.suffix in normalized_exts or candidate.name.endswith(normalized_exts)
                ):
                    files.append(candidate)
    return files


def snapshot(paths: list[str], extensions: list[str], *, cwd: Path) -> dict[str, float]:
    return {str(path): path.stat().st_mtime for path in iter_watch_files(paths, extensions, cwd=cwd)}


def watch(
    paths: list[str],
    extensions: list[str],
    *,
    cwd: Path,
    interval: float,
    on_change: Callable[[], None],
) -> None:
    previous = snapshot(paths, extensions, cwd=cwd)
    on_change()
    while True:
        time.sleep(interval)
        current = snapshot(paths, extensions, cwd=cwd)
        if current != previous:
            previous = current
            on_change()
