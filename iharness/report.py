from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass
class VerificationReport:
    output_dir: Path
    status: str = "passed"
    steps: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

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

    def write(self) -> tuple[Path, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.output_dir / "report.json"
        md_path = self.output_dir / "report.md"
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
            handle.write("\n")
        with md_path.open("w", encoding="utf-8") as handle:
            handle.write(self.to_markdown())
        return json_path, md_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "steps": self.steps,
            "artifacts": self.artifacts,
            "errors": self.errors,
        }

    def to_markdown(self) -> str:
        lines = [f"# iharness Verification Report", "", f"Status: **{self.status.upper()}**", ""]
        if self.errors:
            lines.append("## Errors")
            for error in self.errors:
                lines.append(f"- {error}")
            lines.append("")
        if self.artifacts:
            lines.append("## Artifacts")
            for name, value in self.artifacts.items():
                lines.append(f"- {name}: `{value}`")
            lines.append("")
        if self.steps:
            lines.append("## Steps")
            for step in self.steps:
                marker = "PASS" if step.get("ok") else "FAIL"
                lines.append(f"- {marker} `{step.get('name')}`")
                command = step.get("command")
                if command:
                    lines.append(f"  - command: `{' '.join(command)}`")
                returncode = step.get("returncode")
                if returncode is not None:
                    lines.append(f"  - returncode: `{returncode}`")
                stderr = str(step.get("stderr") or "").strip()
                if stderr:
                    excerpt = stderr[-1200:]
                    lines.append("")
                    lines.append("  ```text")
                    lines.extend(f"  {line}" for line in excerpt.splitlines())
                    lines.append("  ```")
            lines.append("")
        return "\n".join(lines)
