from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_notify_config import AgentNotifyPaths
from agent_notify_core import (
    ensure_shared_script,
    install_hooks,
    load_notifications_enabled,
    load_suppress_when_vscode_focused,
    save_notifications_enabled,
    save_suppress_when_vscode_focused,
    uninstall_hooks,
)
from agent_notify_hooks import is_event_configured, remove_managed_hook, set_managed_hook


def test_install_preserves_existing_claude_settings_and_adds_managed_hooks(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")
    paths.codex_hooks_path.parent.mkdir(parents=True)
    paths.claude_settings_path.parent.mkdir(parents=True)
    paths.claude_settings_path.write_text(
        json.dumps(
            {
                "theme": "dark",
                "env": {"ANTHROPIC_AUTH_TOKEN": "redacted"},
                "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}]},
            }
        ),
        encoding="utf-8",
    )

    install_hooks(audio, paths)

    claude = json.loads(paths.claude_settings_path.read_text(encoding="utf-8"))
    assert claude["env"]["ANTHROPIC_AUTH_TOKEN"] == "redacted"
    assert claude["theme"] == "dark"
    assert len(claude["hooks"]["Stop"]) == 2
    assert claude["hooks"]["Stop"][0]["hooks"][0]["command"] == "echo keep"
    assert claude["hooks"]["Stop"][1]["matcher"] == ""
    assert is_event_configured(paths.claude_settings_path, "Stop", paths)
    assert is_event_configured(paths.claude_settings_path, "Notification", paths)
    assert is_event_configured(paths.codex_hooks_path, "Stop", paths)
    assert is_event_configured(paths.codex_hooks_path, "PermissionRequest", paths)
    assert list(paths.claude_settings_path.parent.glob("settings.json.bak.*"))


def test_reinstall_does_not_duplicate_managed_hooks(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")
    paths.codex_hooks_path.parent.mkdir(parents=True)
    paths.claude_settings_path.parent.mkdir(parents=True)

    install_hooks(audio, paths)
    install_hooks(audio, paths)

    codex = json.loads(paths.codex_hooks_path.read_text(encoding="utf-8"))
    claude = json.loads(paths.claude_settings_path.read_text(encoding="utf-8"))
    assert len(codex["hooks"]["Stop"]) == 1
    assert len(codex["hooks"]["PermissionRequest"]) == 1
    assert len(claude["hooks"]["Stop"]) == 1
    assert len(claude["hooks"]["Notification"]) == 1


def test_uninstall_removes_only_managed_hooks_and_deletes_managed_folder(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.agent_notify_dir.mkdir(parents=True)
    (paths.agent_notify_dir / "notify.ps1").write_text("managed", encoding="utf-8")
    paths.codex_hooks_path.parent.mkdir(parents=True)
    paths.claude_settings_path.parent.mkdir(parents=True)

    codex = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}]}}
    claude = {"env": {"KEEP": "yes"}, "hooks": {"Notification": []}}
    set_managed_hook(codex, "Codex", "Stop", False, paths)
    set_managed_hook(codex, "Codex", "PermissionRequest", False, paths)
    set_managed_hook(claude, "Claude", "Notification", True, paths)
    paths.codex_hooks_path.write_text(json.dumps(codex), encoding="utf-8")
    paths.claude_settings_path.write_text(json.dumps(claude), encoding="utf-8")

    uninstall_hooks(paths)

    remaining_codex = json.loads(paths.codex_hooks_path.read_text(encoding="utf-8"))
    remaining_claude = json.loads(paths.claude_settings_path.read_text(encoding="utf-8"))
    assert remaining_codex["hooks"]["Stop"][0]["hooks"][0]["command"] == "echo keep"
    assert "PermissionRequest" not in remaining_codex["hooks"]
    assert remaining_claude["env"]["KEEP"] == "yes"
    assert "Notification" not in remaining_claude["hooks"]
    assert not paths.agent_notify_dir.exists()
    assert not list(paths.codex_hooks_path.parent.glob("hooks.json.bak.*"))
    assert not list(paths.claude_settings_path.parent.glob("settings.json.bak.*"))


def test_ensure_shared_script_accepts_mp3_audio(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.mp3"
    audio.write_bytes(b"ID3")

    ensure_shared_script(audio, paths)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert paths.managed_audio_path(".mp3").exists()
    assert config["managedAudio"].endswith("completed.mp3")
    assert config["suppressWhenVSCodeFocused"] is True
    assert config["notificationsEnabled"] is True


def test_ensure_shared_script_allows_no_audio(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)

    ensure_shared_script(None, paths)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert paths.notify_script_path.exists()
    assert "managedAudio" not in config
    assert "originalAudio" not in config
    assert config["suppressWhenVSCodeFocused"] is True
    assert config["notificationsEnabled"] is True
    assert not paths.managed_audio_path(".wav").exists()
    assert not paths.managed_audio_path(".mp3").exists()


def test_ensure_shared_script_without_audio_removes_old_managed_audio(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")

    ensure_shared_script(audio, paths)
    assert paths.managed_audio_path(".wav").exists()

    ensure_shared_script(None, paths)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert "managedAudio" not in config
    assert not paths.managed_audio_path(".wav").exists()


def test_ensure_shared_script_can_disable_vscode_foreground_suppression(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")

    ensure_shared_script(audio, paths, suppress_when_vscode_focused=False)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert config["suppressWhenVSCodeFocused"] is False


def test_install_hooks_allows_no_audio(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.codex_hooks_path.parent.mkdir(parents=True)

    install_hooks(None, paths)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert paths.notify_script_path.exists()
    assert "managedAudio" not in config
    assert is_event_configured(paths.codex_hooks_path, "Stop", paths)
    assert is_event_configured(paths.codex_hooks_path, "PermissionRequest", paths)


def test_install_hooks_persists_vscode_foreground_suppression_choice(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")
    paths.codex_hooks_path.parent.mkdir(parents=True)

    install_hooks(audio, paths, suppress_when_vscode_focused=False)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert config["suppressWhenVSCodeFocused"] is False


def test_install_hooks_persists_notifications_enabled_choice(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.codex_hooks_path.parent.mkdir(parents=True)

    install_hooks(None, paths, notifications_enabled=False)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert config["notificationsEnabled"] is False


def test_install_hooks_configures_only_codex_when_only_codex_is_installed(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")
    paths.codex_hooks_path.parent.mkdir(parents=True)

    install_hooks(audio, paths)

    assert paths.codex_hooks_path.exists()
    assert not paths.claude_settings_path.exists()
    assert is_event_configured(paths.codex_hooks_path, "Stop", paths)
    assert is_event_configured(paths.codex_hooks_path, "PermissionRequest", paths)


def test_install_hooks_configures_only_claude_when_only_claude_is_installed(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")
    paths.claude_settings_path.parent.mkdir(parents=True)

    install_hooks(audio, paths)

    assert not paths.codex_hooks_path.exists()
    assert paths.claude_settings_path.exists()
    assert is_event_configured(paths.claude_settings_path, "Stop", paths)
    assert is_event_configured(paths.claude_settings_path, "Notification", paths)


def test_install_hooks_fails_without_installed_agent(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")

    with pytest.raises(RuntimeError, match="Codex or Claude"):
        install_hooks(audio, paths)

    assert not paths.agent_notify_dir.exists()
    assert not paths.codex_hooks_path.exists()
    assert not paths.claude_settings_path.exists()


def test_load_suppress_when_vscode_focused_defaults_to_enabled(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)

    assert load_suppress_when_vscode_focused(paths) is True

    paths.config_path.parent.mkdir(parents=True)
    paths.config_path.write_text("{not json", encoding="utf-8")
    assert load_suppress_when_vscode_focused(paths) is True


def test_save_suppress_when_vscode_focused_preserves_existing_config(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.config_path.parent.mkdir(parents=True)
    paths.config_path.write_text(
        json.dumps({"originalAudio": "sound.wav", "suppressWhenVSCodeFocused": True}),
        encoding="utf-8",
    )

    save_suppress_when_vscode_focused(paths, False)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert config["originalAudio"] == "sound.wav"
    assert config["suppressWhenVSCodeFocused"] is False


def test_load_notifications_enabled_defaults_to_enabled(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)

    assert load_notifications_enabled(paths) is True

    paths.config_path.parent.mkdir(parents=True)
    paths.config_path.write_text("{not json", encoding="utf-8")
    assert load_notifications_enabled(paths) is True


def test_save_notifications_enabled_preserves_existing_config(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.config_path.parent.mkdir(parents=True)
    paths.config_path.write_text(
        json.dumps(
            {
                "originalAudio": "sound.wav",
                "suppressWhenVSCodeFocused": False,
                "notificationsEnabled": True,
            }
        ),
        encoding="utf-8",
    )

    save_notifications_enabled(paths, False)

    config = json.loads(paths.config_path.read_text(encoding="utf-8"))
    assert config["originalAudio"] == "sound.wav"
    assert config["suppressWhenVSCodeFocused"] is False
    assert config["notificationsEnabled"] is False


def test_ensure_shared_script_rejects_unsupported_audio(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.flac"
    audio.write_bytes(b"not supported")

    with pytest.raises(ValueError, match="Only WAV and MP3"):
        ensure_shared_script(audio, paths)


def test_generated_notify_script_is_valid_powershell(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")

    ensure_shared_script(audio, paths)

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                "$tokens=$null; $errors=$null; "
                "[System.Management.Automation.Language.Parser]::ParseFile("
                f"'{paths.notify_script_path}', [ref]$tokens, [ref]$errors) | Out-Null; "
                "if ($errors.Count -gt 0) { exit 1 }"
            ),
        ],
        check=False,
    )
    assert result.returncode == 0


def test_generated_notify_script_uses_chinese_toast_text(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.mp3"
    audio.write_bytes(b"ID3")

    ensure_shared_script(audio, paths)

    script = paths.notify_script_path.read_text(encoding="utf-8-sig")
    assert "Codex 等待确认" in script
    assert "Claude 等待输入" in script
    assert "AI Hook 提示" in script


def test_remove_managed_hook_keeps_unrelated_event_when_no_managed_command(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    config = {"hooks": {"Stop": [{"hooks": [{"command": "echo keep"}]}]}}

    remove_managed_hook(config, "Stop", paths)

    assert config["hooks"]["Stop"][0]["hooks"][0]["command"] == "echo keep"


def test_generated_notify_script_reads_runtime_notification_switch(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")

    ensure_shared_script(audio, paths)

    script = paths.notify_script_path.read_text(encoding="utf-8-sig")
    assert "function Get-NotifyConfig" in script
    assert "function Test-NotificationsEnabled" in script
    assert "function Write-NotifyLog" in script
    assert "notificationsEnabled" in script
    assert "skipped-disabled" in script
    assert "shown" in script
    assert "Test-VSCodeForeground" not in script
    assert "GetForegroundWindow" not in script
    assert "return" in script


def test_generated_notify_script_uses_custom_card_toast_instead_of_balloon_tip(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    audio = tmp_path / "source.wav"
    audio.write_bytes(b"RIFF....WAVEfmt ")

    ensure_shared_script(audio, paths)

    script = paths.notify_script_path.read_text(encoding="utf-8-sig")
    assert "function Show-ToastNotice" in script
    assert "PresentationFramework" in script
    assert "PresentationCore" in script
    assert "WindowsBase" in script
    assert "XamlReader" in script
    assert "NotifyIcon" not in script
    assert "ShowBalloonTip" not in script
    assert "FormBorderStyle" not in script
    assert "Get-RoundedRectanglePath" not in script
    assert "打开 VS Code" not in script
    assert "Open VS Code" not in script
    assert 'Width="340"' in script
    assert 'Height="92"' in script
    assert '<ColumnDefinition Width="38" />' in script
    assert 'Width="24"' in script
    assert 'Width="22"' in script
    assert 'WindowStyle="None"' in script
    assert 'AllowsTransparency="True"' in script
    assert 'CornerRadius="18"' in script
    assert "DropShadowEffect" in script
    assert "TopMost = $true" in script
    assert 'VerticalAlignment="Top"' in script
    assert "closeButton" in script
    assert "#FAFBFD" in script
    assert "#1D1D1F" in script
    assert "macOSNoticeCard" in script
    assert "Show-ToastNotice -Title $notice[0] -Message $notice[1]" in script


def test_generated_notify_script_skips_sound_when_audio_is_not_configured(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)

    ensure_shared_script(None, paths)

    script = paths.notify_script_path.read_text(encoding="utf-8-sig")
    assert "return $null" in script
    assert "PSObject.Properties['managedAudio']" in script
    assert "$audioPath = Resolve-AudioPath" in script
    assert "if ($null -ne $audioPath)" in script
    assert "Play-NoticeSound -Path $audioPath" in script


def make_paths(root: Path) -> AgentNotifyPaths:
    return AgentNotifyPaths(
        agent_notify_dir=root / ".agent-notify",
        codex_hooks_path=root / ".codex" / "hooks.json",
        claude_settings_path=root / ".claude" / "settings.json",
    )
