from __future__ import annotations

import json
import os
import shutil
import subprocess
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


def ensure_shared_script(
    audio_path: Path,
    paths: AgentNotifyPaths,
    suppress_when_vscode_focused: bool = True,
) -> None:
    audio_path = audio_path.expanduser()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
    suffix = audio_path.suffix.lower()
    if suffix not in SUPPORTED_AUDIO_SUFFIXES:
        raise ValueError("Only WAV and MP3 audio files are supported.")

    paths.agent_notify_dir.mkdir(parents=True, exist_ok=True)
    for old_suffix in SUPPORTED_AUDIO_SUFFIXES:
        old_audio = paths.managed_audio_path(old_suffix)
        if old_audio.exists():
            old_audio.unlink()

    managed_audio_path = paths.managed_audio_path(suffix)
    shutil.copy2(audio_path, managed_audio_path)
    paths.notify_script_path.write_text(get_notify_script_content(), encoding="utf-8-sig")
    write_json(
        paths.config_path,
        {
            "app": MANAGED_BY,
            "notifyScript": str(paths.notify_script_path),
            "managedAudio": str(managed_audio_path),
            "originalAudio": str(audio_path),
            "suppressWhenVSCodeFocused": bool(suppress_when_vscode_focused),
            "updatedAt": datetime.now().astimezone().isoformat(),
        },
    )


def install_hooks(
    audio_path: Path,
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


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_notify_script_content() -> str:
    return r"""param(
    [ValidateSet('Codex', 'Claude')]
    [string]$Source = 'Codex',

    [string]$Event = 'Stop',

    [string]$ManagedBy = 'AgentNotifyConfigurator'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $baseDir 'config.json'

function Get-NotifyConfig {
    if (Test-Path -LiteralPath $configPath) {
        return Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    }

    return $null
}

function Get-NoticeText {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Event
    )

    switch ("$Source`:$Event") {
        'Codex:PermissionRequest' { return @('Codex 等待确认', '有权限或命令需要你处理。') }
        'Claude:Notification' { return @('Claude 等待输入', 'Claude Code 正在等待输入或确认。') }
        'Claude:Stop' { return @('Claude 已停止', '当前任务轮次已经结束。') }
        default { return @("$Source 已停止", '请回到 VS Code 查看当前状态。') }
    }
}

function Resolve-AudioPath {
    $config = Get-NotifyConfig
    if ($null -ne $config) {
        if ($config.managedAudio -and (Test-Path -LiteralPath $config.managedAudio)) {
            return [string]$config.managedAudio
        }
    }

    foreach ($name in @('completed.wav', 'completed.mp3')) {
        $candidate = Join-Path $baseDir $name
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Managed audio file does not exist."
}

function Test-SuppressWhenVSCodeFocused {
    $config = Get-NotifyConfig
    if ($null -eq $config) {
        return $true
    }

    if ($null -eq $config.PSObject.Properties['suppressWhenVSCodeFocused']) {
        return $true
    }

    return [bool]$config.suppressWhenVSCodeFocused
}

function Get-ForegroundProcessName {
    $signature = @'
[DllImport("user32.dll")]
public static extern System.IntPtr GetForegroundWindow();
[DllImport("user32.dll")]
public static extern uint GetWindowThreadProcessId(System.IntPtr hWnd, out uint processId);
'@

    if (-not ([System.Management.Automation.PSTypeName]'AgentNotify.ForegroundWindow').Type) {
        Add-Type -MemberDefinition $signature -Name "ForegroundWindow" -Namespace "AgentNotify"
    }

    $handle = [AgentNotify.ForegroundWindow]::GetForegroundWindow()
    if ($handle -eq [IntPtr]::Zero) {
        return ''
    }

    [uint32]$processId = 0
    [AgentNotify.ForegroundWindow]::GetWindowThreadProcessId($handle, [ref]$processId) | Out-Null
    if ($processId -eq 0) {
        return ''
    }

    return (Get-Process -Id ([int]$processId)).ProcessName
}

function Test-VSCodeForeground {
    $processName = Get-ForegroundProcessName
    return $processName -in @('Code', 'Code - Insiders')
}

function Play-NoticeSound {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Audio file does not exist: $Path"
    }

    $signature = @'
[DllImport("winmm.dll", CharSet = CharSet.Unicode)]
public static extern int mciSendString(string command, System.Text.StringBuilder returnValue, int returnLength, System.IntPtr winHandle);
'@

    if (-not ("WinMM" -as [type])) {
        Add-Type -MemberDefinition $signature -Name "WinMM" -Namespace "AgentNotify"
    }

    $alias = "agent_notice_" + [Guid]::NewGuid().ToString("N")
    $openResult = [AgentNotify.WinMM]::mciSendString("open `"$Path`" alias $alias", $null, 0, [IntPtr]::Zero)
    if ($openResult -ne 0) {
        throw "Failed to open audio file: $Path"
    }

    try {
        $playResult = [AgentNotify.WinMM]::mciSendString("play $alias wait", $null, 0, [IntPtr]::Zero)
        if ($playResult -ne 0) {
            throw "Failed to play audio file: $Path"
        }
    }
    finally {
        [AgentNotify.WinMM]::mciSendString("close $alias", $null, 0, [IntPtr]::Zero) | Out-Null
    }
}

function Show-BalloonNotice {
    param(
        [Parameter(Mandatory)][string]$Title,
        [Parameter(Mandatory)][string]$Message
    )

    $icon = [System.Windows.Forms.NotifyIcon]::new()
    $icon.Icon = [System.Drawing.SystemIcons]::Information
    $icon.Text = 'AI Hook 提示'
    $icon.BalloonTipTitle = $Title
    $icon.BalloonTipText = $Message
    $icon.Visible = $true
    $icon.ShowBalloonTip(5000)

    Start-Sleep -Seconds 6
    $icon.Visible = $false
    $icon.Dispose()
}

$notice = Get-NoticeText -Source $Source -Event $Event
if ((Test-SuppressWhenVSCodeFocused) -and (Test-VSCodeForeground)) {
    return
}

$audioPath = Resolve-AudioPath
Play-NoticeSound -Path $audioPath
Show-BalloonNotice -Title $notice[0] -Message $notice[1]
"""
