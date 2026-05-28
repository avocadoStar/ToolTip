from __future__ import annotations

from pathlib import Path

from agent_notify_config import MANAGED_BY
from build_windows import APP_NAME, ICON_PATH, build_pyinstaller_command, release_exe_paths, release_spec_paths


def test_build_command_creates_onefile_windowed_customtkinter_exe() -> None:
    command = build_pyinstaller_command("pyinstaller.exe")

    assert "--onefile" in command
    assert "--windowed" in command
    assert "--collect-all" in command
    assert "customtkinter" in command
    assert "--hidden-import" in command
    assert "darkdetect" in command
    assert "--icon" in command
    assert str(ICON_PATH) in command
    assert "--add-data" in command
    assert f"{ICON_PATH};assets" in command
    assert APP_NAME == "灵犀提醒"
    assert "灵犀提醒" in command
    assert "AgentNotifyConfigurator" not in command


def test_build_cleans_old_and_new_release_exe_names() -> None:
    paths = release_exe_paths(Path("dist"))

    assert paths == [
        Path("dist") / "AgentNotifyConfigurator.exe",
        Path("dist") / "灵犀提醒.exe",
    ]


def test_build_cleans_old_and_new_spec_names() -> None:
    paths = release_spec_paths(Path("."))

    assert paths == [
        Path(".") / "AgentNotifyConfigurator.spec",
        Path(".") / "灵犀提醒.spec",
    ]


def test_managed_hook_marker_stays_compatible() -> None:
    assert MANAGED_BY == "AgentNotifyConfigurator"
