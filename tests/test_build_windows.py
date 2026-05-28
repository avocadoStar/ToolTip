from __future__ import annotations

from build_windows import build_pyinstaller_command


def test_build_command_creates_onefile_windowed_customtkinter_exe() -> None:
    command = build_pyinstaller_command("pyinstaller.exe")

    assert "--onefile" in command
    assert "--windowed" in command
    assert "--collect-all" in command
    assert "customtkinter" in command
    assert "--hidden-import" in command
    assert "darkdetect" in command
    assert "AgentNotifyConfigurator" in command
