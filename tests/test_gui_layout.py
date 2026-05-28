from __future__ import annotations

import inspect

import agent_notify_configurator


def test_status_panel_uses_scrollable_frame_for_overflow() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._build_main)

    assert "CTkScrollableFrame" in source
    assert "self.steps_scroll" in source


def test_gui_uses_light_stepper_layout_from_reference() -> None:
    source = inspect.getsource(agent_notify_configurator)

    assert "class StepCard" in source
    assert "class StatusRow" in source
    assert "class IconCanvas" in source
    assert "选择提示音" in source
    assert "生成共享通知脚本" in source
    assert "安装 Hook 配置" in source
    assert "测试通知" in source
    assert "撤销（可选）" in source
    assert "VS Code 前台静默（可选）" in source
    assert "当前状态" in source
    assert "配置预览" in source
    assert "#F6FAFF" in source


def test_gui_exposes_vscode_foreground_suppression_switch() -> None:
    app_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    module_source = inspect.getsource(agent_notify_configurator)

    assert "suppress_when_vscode_focused_var" in app_source
    assert "load_suppress_when_vscode_focused" in app_source
    assert "save_suppress_when_vscode_focused" in app_source
    assert "CTkSwitch" in module_source


def test_gui_passes_suppression_choice_to_script_generation_and_install() -> None:
    generate_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.generate_script)
    install_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.install)

    assert "suppress_when_vscode_focused=self.suppress_when_vscode_focused()" in generate_source
    assert "suppress_when_vscode_focused=self.suppress_when_vscode_focused()" in install_source
