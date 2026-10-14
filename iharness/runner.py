from __future__ import annotations

import os
import shutil
import signal
import subprocess  # nosec B404
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

DEFAULT_TIMEOUT_SECONDS = 600.0
TERMINATION_GRACE_SECONDS = 5.0
MAX_CAPTURE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": round(self.duration_seconds, 3),
            "timed_out": self.timed_out,
        }


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_command(
    command: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_capture_bytes: int = MAX_CAPTURE_BYTES,
) -> CommandResult:
    if timeout <= 0:
        raise ValueError("Command timeout must be greater than zero seconds.")
    if max_capture_bytes <= 0:
        raise ValueError("Command output limit must be greater than zero bytes.")
    start = time.monotonic()
    process, stdout_capture, stderr_capture, readers = _start_captured_process(
        list(command), cwd=cwd, env=env, limit=max_capture_bytes
    )
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop_process_group(process, signal.SIGTERM)
    except BaseException:
        stop_process_group(process, signal.SIGTERM)
        raise
    finally:
        _finish_readers(process, readers)
    stdout = stdout_capture.text()
    stderr = stderr_capture.text()
    if timed_out:
        message = f"Command timed out after {timeout:g} seconds."
        stderr = f"{stderr.rstrip()}\n{message}" if stderr.strip() else message
    return CommandResult(
        command=list(command),
        returncode=124 if timed_out else process.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=time.monotonic() - start,
        timed_out=timed_out,
    )


def run_for_duration(
    command: Sequence[str],
    *,
    seconds: float,
    stop_signal: signal.Signals,
    successful_stop_codes: tuple[int, ...],
    output_path: Path | None = None,
    max_capture_bytes: int = MAX_CAPTURE_BYTES,
) -> CommandResult:
    if seconds <= 0:
        raise ValueError("Duration must be greater than zero seconds.")
    start = time.monotonic()
    process, stdout_capture, stderr_capture, readers = _start_captured_process(
        list(command), limit=max_capture_bytes
    )
    stopped = False
    try:
        process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        stopped = True
        stop_process_group(process, stop_signal)
    except BaseException:
        stop_process_group(process, signal.SIGTERM)
        raise
    finally:
        _finish_readers(process, readers)
    stdout = stdout_capture.text()
    stderr = stderr_capture.text()
    returncode = process.returncode
    if stopped and returncode in successful_stop_codes:
        returncode = 0
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(output_path, stdout)
        stdout = str(output_path)
    return CommandResult(
        command=list(command),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=time.monotonic() - start,
    )


def stop_process_group(
    process: subprocess.Popen[bytes], stop_signal: signal.Signals
) -> None:
    try:
        os.killpg(process.pid, stop_signal)
    except (OSError, ProcessLookupError):
        if process.poll() is None:
            process.send_signal(stop_signal)
    if process.poll() is not None:
        return
    try:
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        process.kill()
    process.wait()


class _CappedCapture:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.head_limit = limit // 2
        self.tail_limit = limit - self.head_limit
        self.head = bytearray()
        self.tail = bytearray()
        self.total = 0

    def add(self, chunk: bytes) -> None:
        self.total += len(chunk)
        head_remaining = self.head_limit - len(self.head)
        if head_remaining > 0:
            self.head.extend(chunk[:head_remaining])
            chunk = chunk[head_remaining:]
        if chunk:
            self.tail.extend(chunk)
            if len(self.tail) > self.tail_limit:
                del self.tail[: len(self.tail) - self.tail_limit]

    def text(self) -> str:
        if self.total <= self.limit:
            payload = bytes(self.head + self.tail)
        else:
            omitted = self.total - self.limit
            payload = (
                bytes(self.head)
                + f"\n... [{omitted} bytes omitted] ...\n".encode()
                + bytes(self.tail)
            )
        return payload.decode("utf-8", errors="replace")


def _start_captured_process(
    command: list[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    limit: int,
) -> tuple[
    subprocess.Popen[bytes], _CappedCapture, _CappedCapture, list[threading.Thread]
]:
    stdout_capture = _CappedCapture(limit)
    stderr_capture = _CappedCapture(limit)
    # argv is passed directly with shell=False and a finite timeout.
    process = subprocess.Popen(  # nosec B603
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    readers = [
        threading.Thread(
            target=_drain_stream, args=(process.stdout, stdout_capture), daemon=True
        ),
        threading.Thread(
            target=_drain_stream, args=(process.stderr, stderr_capture), daemon=True
        ),
    ]
    for reader in readers:
        reader.start()
    return process, stdout_capture, stderr_capture, readers


def _drain_stream(stream: object, capture: _CappedCapture) -> None:
    try:
        while True:
            chunk = stream.read(65536)  # type: ignore[attr-defined]
            if not chunk:
                return
            capture.add(chunk)
    finally:
        stream.close()  # type: ignore[attr-defined]


def _finish_readers(
    process: subprocess.Popen[bytes], readers: list[threading.Thread]
) -> None:
    for reader in readers:
        reader.join(timeout=TERMINATION_GRACE_SECONDS)
        if reader.is_alive():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            reader.join(timeout=TERMINATION_GRACE_SECONDS)
        if reader.is_alive():
            raise RuntimeError(
                "Subprocess output reader did not terminate after killing its process group."
            )


def _atomic_write_text(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
