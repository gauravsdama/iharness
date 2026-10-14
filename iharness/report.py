from __future__ import annotations

import json
import os
import re
import shlex
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VerificationReport:
    output_dir: Path
    status: str = "passed"
    steps: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add_step(self, name: str, result: Any) -> None:
        if hasattr(result, "as_dict"):
            payload = result.as_dict()
            ok = bool(getattr(result, "ok", False))
        elif isinstance(result, dict):
            payload = result
            ok = bool(result.get("ok", True))
        else:
            payload = {"value": str(result)}
            ok = True
        self.steps.append({"name": name, "ok": ok, **payload})
        if not ok:
            self.status = "failed"

    def add_error(self, message: str) -> None:
        self.status = "failed"
        self.errors.append(message)

    def mark_incomplete(self, message: str) -> None:
        if self.status != "failed":
            self.status = "incomplete"
        self.notes.append(message)

    def write(self) -> tuple[Path, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.output_dir / "report.json"
        md_path = self.output_dir / "report.md"
        json_payload = json.dumps(self.to_dict(), indent=2) + "\n"
        markdown_payload = self.to_markdown()
        _atomic_write_private(json_path, json_payload)
        _atomic_write_private(md_path, markdown_payload)
        return json_path, md_path

    def to_dict(self) -> dict[str, Any]:
        return _sanitize(
            {
                "status": self.status,
                "steps": self.steps,
                "artifacts": self.artifacts,
                "errors": self.errors,
                "notes": self.notes,
            }
        )

    def to_markdown(self) -> str:
        payload = self.to_dict()
        lines = [
            "# iharness Verification Report",
            "",
            f"Status: **{self.status.upper()}**",
            "",
        ]
        if payload["notes"]:
            lines.append("## Notes")
            for note in payload["notes"]:
                lines.append(f"- {_markdown_text(str(note))}")
            lines.append("")
        if payload["errors"]:
            lines.append("## Errors")
            for error in payload["errors"]:
                lines.append(f"- {_markdown_text(str(error))}")
            lines.append("")
        if payload["artifacts"]:
            lines.append("## Artifacts")
            for name, value in payload["artifacts"].items():
                lines.append(
                    f"- {_markdown_text(str(name))}: {_markdown_text(str(value))}"
                )
            lines.append("")
        if payload["steps"]:
            lines.append("## Steps")
            for step in payload["steps"]:
                marker = "PASS" if step.get("ok") else "FAIL"
                lines.append(f"- {marker} {_markdown_text(str(step.get('name')))}")
                command = step.get("command")
                if command:
                    lines.append("  - command:")
                    lines.append("")
                    safe_command = (
                        str(item).replace("\r", "\\r").replace("\n", "\\n")
                        for item in command
                    )
                    lines.append(f"        {shlex.join(safe_command)}")
                returncode = step.get("returncode")
                if returncode is not None:
                    lines.append(f"  - returncode: {returncode}")
                stderr = str(step.get("stderr") or "").strip()
                if stderr:
                    excerpt = stderr[-1200:]
                    lines.append("")
                    lines.extend(f"      {line}" for line in excerpt.splitlines())
            lines.append("")
        return "\n".join(lines)


_SECRET_PATTERN = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key)(\s*[=:]\s*)([^\s]+)"
)
_URL_CREDENTIAL_PATTERN = re.compile(r"(https?://)[^/@\s]+@", re.IGNORECASE)
_BEARER_PATTERN = re.compile(
    r"(?i)(authorization\s*[:=]\s*bearer\s+|\bbearer\s+)([^\s]+)"
)
_SENSITIVE_FLAGS = {
    "--password",
    "--passwd",
    "--secret",
    "--token",
    "--api-key",
    "--apikey",
}


def _redact_text(value: str) -> str:
    home = str(Path.home())
    redacted = value.replace(home, "~") if home and home != "/" else value
    redacted = _SECRET_PATTERN.sub(r"\1\2[REDACTED]", redacted)
    redacted = _URL_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]@", redacted)
    return _BEARER_PATTERN.sub(r"\1[REDACTED]", redacted)


def _sanitize(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        sanitized = [_sanitize(item) for item in value]
        if key == "command":
            for index, item in enumerate(sanitized[:-1]):
                if str(item).casefold() in _SENSITIVE_FLAGS:
                    sanitized[index + 1] = "[REDACTED]"
        return sanitized
    if isinstance(value, dict):
        return {
            str(item_key): _sanitize(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    return value


def _markdown_text(value: str) -> str:
    escaped = (
        _redact_text(value).replace("\r", " ").replace("\n", " ").replace("\\", "\\\\")
    )
    for character in "`*_{}[]()#+!|>":
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _atomic_write_private(path: Path, payload: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        os.chmod(temporary, 0o600)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
