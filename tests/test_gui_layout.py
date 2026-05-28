from __future__ import annotations

import inspect

import agent_notify_configurator


def test_status_panel_uses_scrollable_frame_for_overflow() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._build_main)

    assert "CTkScrollableFrame" in source
    assert "self.status_scroll" in source


def test_gui_exposes_vscode_foreground_suppression_switch() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)

    assert "suppress_when_vscode_focused_var" in source
    assert "load_suppress_when_vscode_focused" in source
    assert "save_suppress_when_vscode_focused" in source
    assert "CTkSwitch" in source


def test_gui_passes_suppression_choice_to_script_generation_and_install() -> None:
    generate_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.generate_script)
    install_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.install)

    assert "suppress_when_vscode_focused=self.suppress_when_vscode_focused()" in generate_source
    assert "suppress_when_vscode_focused=self.suppress_when_vscode_focused()" in install_source
