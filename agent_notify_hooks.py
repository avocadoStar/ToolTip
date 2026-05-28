from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_notify_config import MANAGED_BY, AgentNotifyPaths, read_json


def build_hook_command(source: str, event: str, paths: AgentNotifyPaths) -> str:
    return (
        'powershell.exe -NoProfile -ExecutionPolicy Bypass '
        f'-File "{paths.notify_script_path}" '
        f'-Source "{source}" -Event "{event}" -ManagedBy "{MANAGED_BY}"'
    )


def is_managed_command(command: Any, paths: AgentNotifyPaths) -> bool:
    if not isinstance(command, str):
        return False

    return str(paths.notify_script_path) in command and MANAGED_BY in command


def make_hook_group(
    source: str,
    event: str,
    include_matcher: bool,
    paths: AgentNotifyPaths,
) -> dict[str, Any]:
    group: dict[str, Any] = {
        "hooks": [
            {
                "type": "command",
                "command": build_hook_command(source, event, paths),
                "timeout": 10000,
            }
        ]
    }
    if include_matcher:
        group = {"matcher": "", **group}
    return group


def remove_managed_hook_groups(groups: Any, paths: AgentNotifyPaths) -> list[Any]:
    kept: list[Any] = []
    for group in as_list(groups):
        if not isinstance(group, dict):
            kept.append(group)
            continue

        hooks = as_list(group.get("hooks"))
        if any(isinstance(hook, dict) and is_managed_command(hook.get("command"), paths) for hook in hooks):
            continue
        kept.append(group)
    return kept


def set_managed_hook(
    config: dict[str, Any],
    source: str,
    event: str,
    include_matcher: bool,
    paths: AgentNotifyPaths,
) -> None:
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("The hooks field is not an object, so it cannot be merged safely.")

    existing = remove_managed_hook_groups(hooks.get(event, []), paths)
    hooks[event] = [*existing, make_hook_group(source, event, include_matcher, paths)]


def remove_managed_hook(config: dict[str, Any], event: str, paths: AgentNotifyPaths) -> None:
    hooks = config.get("hooks")
    if not isinstance(hooks, dict) or event not in hooks:
        return

    remaining = remove_managed_hook_groups(hooks[event], paths)
    if remaining:
        hooks[event] = remaining
    else:
        hooks.pop(event, None)


def is_event_configured(path: Path, event: str, paths: AgentNotifyPaths) -> bool:
    try:
        config = read_json(path)
    except Exception:
        return False

    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return False

    for group in as_list(hooks.get(event)):
        if not isinstance(group, dict):
            continue
        for hook in as_list(group.get("hooks")):
            if isinstance(hook, dict) and is_managed_command(hook.get("command"), paths):
                return True
    return False


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
