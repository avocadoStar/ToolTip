from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_notify_config import (
    MANAGED_BY,
    SUPPORTED_AUDIO_SUFFIXES,
    AgentNotifyPaths,
    backup_json,
    default_paths,
    read_json,
    write_json,
)
from agent_notify_hooks import (
    as_list,
    build_hook_command,
    is_event_configured,
    is_managed_command,
    make_hook_group,
    remove_managed_hook,
    remove_managed_hook_groups,
    set_managed_hook,
)
from agent_notify_script import get_notify_script_content


def ensure_shared_script(
    audio_path: Path | None,
    paths: AgentNotifyPaths,
    suppress_when_vscode_focused: bool = True,
) -> None:
    paths.agent_notify_dir.mkdir(parents=True, exist_ok=True)
    for old_suffix in SUPPORTED_AUDIO_SUFFIXES:
        old_audio = paths.managed_audio_path(old_suffix)
        if old_audio.exists():
            old_audio.unlink()

    config = {
        "app": MANAGED_BY,
        "notifyScript": str(paths.notify_script_path),
        "suppressWhenVSCodeFocused": bool(suppress_when_vscode_focused),
        "updatedAt": datetime.now().astimezone().isoformat(),
    }

    if audio_path is not None:
        audio_path = audio_path.expanduser()
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        suffix = audio_path.suffix.lower()
        if suffix not in SUPPORTED_AUDIO_SUFFIXES:
            raise ValueError("Only WAV and MP3 audio files are supported.")

        managed_audio_path = paths.managed_audio_path(suffix)
        shutil.copy2(audio_path, managed_audio_path)
        config["managedAudio"] = str(managed_audio_path)
        config["originalAudio"] = str(audio_path)

    paths.notify_script_path.write_text(get_notify_script_content(), encoding="utf-8-sig")
    write_json(paths.config_path, config)


def install_hooks(
    audio_path: Path | None,
    paths: AgentNotifyPaths,
    suppress_when_vscode_focused: bool = True,
) -> None:
    codex_installed = paths.codex_hooks_path.parent.exists()
    claude_installed = paths.claude_settings_path.parent.exists()
    if not codex_installed and not claude_installed:
        raise RuntimeError("Codex or Claude configuration directory was not found.")

    ensure_shared_script(audio_path, paths, suppress_when_vscode_focused=suppress_when_vscode_focused)

    if codex_installed:
        codex = read_json(paths.codex_hooks_path)
        backup_json(paths.codex_hooks_path)
        set_managed_hook(codex, "Codex", "Stop", False, paths)
        set_managed_hook(codex, "Codex", "PermissionRequest", False, paths)
        write_json(paths.codex_hooks_path, codex)

    if claude_installed:
        claude = read_json(paths.claude_settings_path)
        backup_json(paths.claude_settings_path)
        set_managed_hook(claude, "Claude", "Stop", True, paths)
        set_managed_hook(claude, "Claude", "Notification", True, paths)
        write_json(paths.claude_settings_path, claude)


def uninstall_hooks(paths: AgentNotifyPaths) -> None:
    if paths.codex_hooks_path.exists():
        codex = read_json(paths.codex_hooks_path)
        remove_managed_hook(codex, "Stop", paths)
        remove_managed_hook(codex, "PermissionRequest", paths)
        write_json(paths.codex_hooks_path, codex)

    if paths.claude_settings_path.exists():
        claude = read_json(paths.claude_settings_path)
        remove_managed_hook(claude, "Stop", paths)
        remove_managed_hook(claude, "Notification", paths)
        write_json(paths.claude_settings_path, claude)

    if paths.agent_notify_dir.exists():
        expected = paths.agent_notify_dir.resolve()
        actual = paths.agent_notify_dir.resolve()
        if actual != expected or actual.name != ".agent-notify":
            raise RuntimeError(f"Refusing to delete unexpected directory: {actual}")
        shutil.rmtree(actual)


def run_notice_test(paths: AgentNotifyPaths) -> None:
    if not paths.notify_script_path.exists():
        raise FileNotFoundError("The shared notification script does not exist. Generate it first.")

    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(paths.notify_script_path),
            "-Source",
            "Codex",
            "-Event",
            "Stop",
            "-ManagedBy",
            MANAGED_BY,
        ],
        check=True,
    )


def load_saved_audio_path(paths: AgentNotifyPaths) -> str:
    try:
        config = read_json(paths.config_path)
    except Exception:
        return ""

    original = str(config.get("originalAudio") or "")
    if original and Path(original).exists():
        return original
    return ""


def load_suppress_when_vscode_focused(paths: AgentNotifyPaths) -> bool:
    try:
        config = read_json(paths.config_path)
    except Exception:
        return True

    value = config.get("suppressWhenVSCodeFocused", True)
    if isinstance(value, bool):
        return value
    return True


def save_suppress_when_vscode_focused(paths: AgentNotifyPaths, enabled: bool) -> None:
    config = read_json(paths.config_path)
    config.setdefault("app", MANAGED_BY)
    config["suppressWhenVSCodeFocused"] = bool(enabled)
    config["updatedAt"] = datetime.now().astimezone().isoformat()
    write_json(paths.config_path, config)


def get_status(paths: AgentNotifyPaths) -> dict[str, bool]:
    return {
        "script": paths.notify_script_path.exists(),
        "audio": any(paths.managed_audio_path(suffix).exists() for suffix in SUPPORTED_AUDIO_SUFFIXES),
        "codex": is_event_configured(paths.codex_hooks_path, "Stop", paths)
        and is_event_configured(paths.codex_hooks_path, "PermissionRequest", paths),
        "claude": is_event_configured(paths.claude_settings_path, "Stop", paths)
        and is_event_configured(paths.claude_settings_path, "Notification", paths),
    }
