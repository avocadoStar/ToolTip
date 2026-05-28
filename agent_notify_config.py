from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MANAGED_BY = "AgentNotifyConfigurator"
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".mp3"}


@dataclass(frozen=True)
class AgentNotifyPaths:
    agent_notify_dir: Path
    codex_hooks_path: Path
    claude_settings_path: Path

    @property
    def notify_script_path(self) -> Path:
        return self.agent_notify_dir / "notify.ps1"

    def managed_audio_path(self, suffix: str = ".wav") -> Path:
        return self.agent_notify_dir / f"completed{suffix.lower()}"

    @property
    def config_path(self) -> Path:
        return self.agent_notify_dir / "config.json"


def default_paths() -> AgentNotifyPaths:
    home = Path.home()
    return AgentNotifyPaths(
        agent_notify_dir=home / ".agent-notify",
        codex_hooks_path=home / ".codex" / "hooks.json",
        claude_settings_path=home / ".claude" / "settings.json",
    )


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8-sig")
    if not content.strip():
        return {}

    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def backup_json(path: Path) -> Path | None:
    if not path.exists():
        return None

    backup_path = path.with_name(f"{path.name}.bak.{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(path, backup_path)
    return backup_path
