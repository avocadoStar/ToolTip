from __future__ import annotations

import inspect

import agent_notify_configurator
import agent_notify_ui_components


def test_status_panel_uses_scrollable_frame_for_overflow() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._build_main)

    assert "CTkScrollableFrame" in source
    assert "self.steps_scroll" in source


def test_gui_initializes_theme_before_window_creation_and_repaints_on_restore() -> None:
    init_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.__init__)
    module_source = inspect.getsource(agent_notify_configurator)

    assert "def configure_app_theme" in module_source
    assert init_source.index("configure_app_theme()") < init_source.index("super().__init__()")
    assert 'self.bind("<Map>", self._on_window_mapped, add="+")' in init_source
    assert "def _on_window_mapped" in module_source
    assert "def _refresh_window_paint" in module_source
    assert "self.after_idle(self._refresh_window_paint)" in module_source


def test_gui_uses_light_stepper_layout_from_reference() -> None:
    app_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    step_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._step_definitions)

    assert hasattr(agent_notify_ui_components, "StepCard")
    assert hasattr(agent_notify_ui_components, "StatusRow")
    assert hasattr(agent_notify_ui_components, "IconCanvas")
    assert hasattr(agent_notify_ui_components, "TimelineMarker")
    assert agent_notify_ui_components.COLORS["bg"] == "#F5F5F7"
    assert agent_notify_ui_components.COLORS["blue"] == "#007AFF"
    assert "visual_effect" in agent_notify_ui_components.COLORS
    assert "选择提示音" in step_source
    assert "生成共享通知脚本" in step_source
    assert "安装 Hook 配置" in step_source
    assert "测试通知" in step_source
    assert "撤销（可选）" in step_source
    assert "VS Code 活跃时静默（可选）" in app_source
    assert "只有当前前台窗口是 VS Code 时，才不播放声音也不显示通知。" in app_source
    assert "当前状态" in app_source
    assert "配置预览" in app_source


def test_gui_presents_audio_as_optional() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    selected_audio_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.selected_audio)

    assert "提示音可选" in source
    assert "未选择，将静音显示通知" in source
    assert "Path | None" in selected_audio_source
    assert "return None" in selected_audio_source
    assert "raise ValueError" not in selected_audio_source


def test_timeline_marker_draws_connector_lines_between_step_numbers() -> None:
    source = inspect.getsource(agent_notify_ui_components.TimelineMarker)

    assert "show_top" in source
    assert "show_bottom" in source
    assert "top_line" in source
    assert "bottom_line" in source
    assert 'COLORS["line"]' in source
    assert "CTkLabel" in source
    assert "corner_radius" in source
    assert "create_oval" not in source


def test_run_action_shows_loading_dialog_and_preserves_exception_message() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    run_action_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.run_action)
    show_success_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.show_success)
    show_error_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.show_error)

    assert "def show_loading_popup" in source
    assert "def close_loading_popup" in source
    assert "CTkToplevel" in source
    assert "CTkProgressBar" in source
    assert "self.action_running = False" in show_success_source
    assert "self.action_running = False" in show_error_source
    assert "if self.action_running:" in run_action_source
    assert "return" in run_action_source
    assert "self.action_running = True" in run_action_source
    assert "self.show_loading_popup(working)" in run_action_source
    assert "message = str(exc)" in run_action_source
    assert "lambda message=message" in run_action_source


def test_gui_exposes_vscode_foreground_suppression_switch() -> None:
    app_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    module_source = inspect.getsource(agent_notify_configurator) + inspect.getsource(agent_notify_ui_components)

    assert "suppress_when_vscode_focused_var" in app_source
    assert "load_suppress_when_vscode_focused" in app_source
    assert "save_suppress_when_vscode_focused" in app_source
    assert "CTkSwitch" in module_source


def test_gui_passes_suppression_choice_to_script_generation_and_install() -> None:
    generate_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.generate_script)
    install_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.install)

    assert "suppress_when_vscode_focused=self.suppress_when_vscode_focused()" in generate_source
    assert "suppress_when_vscode_focused=self.suppress_when_vscode_focused()" in install_source
