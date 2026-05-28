from __future__ import annotations

import inspect

import agent_notify_configurator
import agent_notify_ui_components


def test_settings_panel_uses_scrollable_content_for_overflow() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._build_main)

    assert "CTkScrollableFrame" in source
    assert "self.content_scroll" in source
    assert "self.sidebar" in source


def test_gui_title_uses_chinese_app_name_and_window_icon() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)

    assert agent_notify_configurator.APP_TITLE == "灵犀提醒"
    assert agent_notify_configurator.WINDOW_ICON_PATH.name == "lingxi_icon.ico"
    assert "def _apply_window_icon" in source
    assert "self.iconbitmap" in source


def test_gui_initializes_theme_before_window_creation_and_repaints_on_restore() -> None:
    init_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.__init__)
    module_source = inspect.getsource(agent_notify_configurator)

    assert "def configure_app_theme" in module_source
    assert init_source.index("configure_app_theme()") < init_source.index("super().__init__()")
    assert 'self.bind("<Map>", self._on_window_mapped, add="+")' in init_source
    assert "def _on_window_mapped" in module_source
    assert "def _refresh_window_paint" in module_source
    assert "self.after_idle(self._refresh_window_paint)" in module_source


def test_gui_uses_macos_settings_panel_layout() -> None:
    app_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    module_source = inspect.getsource(agent_notify_configurator) + inspect.getsource(agent_notify_ui_components)

    assert hasattr(agent_notify_ui_components, "SidebarItem")
    assert hasattr(agent_notify_ui_components, "SettingSection")
    assert hasattr(agent_notify_ui_components, "ActionRow")
    assert hasattr(agent_notify_ui_components, "PreviewBox")
    assert hasattr(agent_notify_ui_components, "StatusRow")
    assert hasattr(agent_notify_ui_components, "IconCanvas")
    assert agent_notify_ui_components.COLORS["bg"] == "#F5F5F7"
    assert agent_notify_ui_components.COLORS["blue"] == "#007AFF"
    assert "glass" in agent_notify_ui_components.COLORS
    assert "选择提示音" in app_source
    assert "生成共享通知脚本" in app_source
    assert "安装 Hook 配置" in app_source
    assert "测试通知" in app_source
    assert "撤销配置" in app_source
    assert "VS Code 活跃时静默（可选）" in app_source
    assert "只有当前前台窗口是 VS Code 时，才不播放声音也不显示通知。" in app_source
    assert "当前状态" in app_source
    assert "配置预览" in app_source
    assert "PreviewBox" in module_source
    assert "preview_card" not in app_source
    assert "preview_box.grid(row=1" not in app_source


def test_gui_presents_audio_as_optional() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    selected_audio_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.selected_audio)

    assert "提示音可选" in source
    assert "未选择，将静音显示通知" in source
    assert "Path | None" in selected_audio_source
    assert "return None" in selected_audio_source
    assert "raise ValueError" not in selected_audio_source


def test_icon_canvas_uses_unified_line_icon_style() -> None:
    source = inspect.getsource(agent_notify_ui_components.IconCanvas)

    assert "LINE_WIDTH" in source
    assert "create_line" in source
    assert "create_polygon" not in source
    assert "create_arc" not in source
    assert "visual_effect" not in source


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
