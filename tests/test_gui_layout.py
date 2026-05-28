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
    assert 'self.bind("<Map>", self._on_window_paint_event, add="+")' in init_source
    assert 'self.bind("<Configure>", self._on_window_paint_event, add="+")' in init_source
    assert 'self.bind("<Visibility>", self._on_window_paint_event, add="+")' in init_source
    assert "def _schedule_repaint" in module_source
    assert "self.after(24, self._refresh_window_paint)" in module_source


def test_gui_uses_true_macos_settings_navigation() -> None:
    app_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    sidebar_source = inspect.getsource(agent_notify_ui_components.SidebarItem)

    assert hasattr(agent_notify_ui_components, "SettingsList")
    assert hasattr(agent_notify_ui_components, "SettingRow")
    assert hasattr(agent_notify_ui_components, "StatusPill")
    assert hasattr(agent_notify_ui_components, "SubtleButton")
    assert not hasattr(agent_notify_ui_components, "MoreDisclosure")
    assert agent_notify_ui_components.COLORS["bg"] == "#F5F5F7"
    assert agent_notify_ui_components.COLORS["list"] == "#FFFFFF"
    assert agent_notify_ui_components.COLORS["text"] == "#1D1D1F"
    assert agent_notify_ui_components.COLORS["muted"] == "#6E6E73"
    assert agent_notify_ui_components.COLORS["blue"] == "#0071E3"
    assert "self.current_page = ctk.StringVar(value=\"notifications\")" in app_source
    assert "def show_page" in app_source
    assert "def _page_definitions" in app_source
    assert "def _build_notifications_page" in app_source
    assert "def _build_connection_page" in app_source
    assert "def _build_audio_page" in app_source
    assert "def _build_more_page" in app_source
    assert "command=lambda page_id=page_id: self.show_page(page_id)" in app_source
    assert "def set_selected" in sidebar_source
    assert "def _on_enter" in sidebar_source
    assert "def _on_leave" in sidebar_source
    assert "通知" in app_source
    assert "连接" in app_source
    assert "提示音" in app_source
    assert "更多" in app_source
    assert "配置预览" not in app_source
    assert "VS Code 活跃时静默（可选）" not in app_source
    assert "PowerShell" not in app_source
    assert "managed block" not in app_source


def test_gui_renders_only_the_selected_page_by_default() -> None:
    init_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.__init__)
    finish_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._finish_initial_render)
    show_page_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.show_page)
    clear_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._clear_content)

    assert "more_expanded_var" not in init_source
    assert "self.current_page = ctk.StringVar(value=\"notifications\")" in init_source
    assert "self.show_page(self.current_page.get())" in finish_source
    assert "builders[page_id]()" in show_page_source
    assert "for child in self.content_scroll.winfo_children()" in clear_source
    assert "_build_notifications_group" not in init_source + finish_source + show_page_source
    assert "_build_connection_group" not in init_source + finish_source + show_page_source
    assert "_build_audio_group" not in init_source + finish_source + show_page_source
    assert "_build_more_entry" not in init_source + finish_source + show_page_source


def test_gui_uses_compact_continuous_settings_metrics() -> None:
    component_source = inspect.getsource(agent_notify_ui_components)
    main_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._build_main)

    assert agent_notify_ui_components.SIDEBAR_WIDTH == 220
    assert agent_notify_ui_components.ROW_HEIGHT == 46
    assert agent_notify_ui_components.BUTTON_HEIGHT == 32
    assert "SIDEBAR_WIDTH" in main_source
    assert "height=ROW_HEIGHT" in component_source
    assert "height=BUTTON_HEIGHT" in component_source


def test_gui_presents_audio_as_optional() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    selected_audio_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.selected_audio)

    assert "未设置" in source
    assert "已设置" in source
    assert "Path | None" in selected_audio_source
    assert "return None" in selected_audio_source
    assert "raise ValueError" not in selected_audio_source


def test_icon_canvas_uses_unified_line_icon_style() -> None:
    source = inspect.getsource(agent_notify_ui_components.IconCanvas)

    assert "LINE_WIDTH" in source
    assert "create_line" in source
    assert "create_polygon" not in source
    assert "create_arc" not in source


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


def test_gui_exposes_notification_switch_instead_of_vscode_suppression() -> None:
    app_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    module_source = inspect.getsource(agent_notify_configurator) + inspect.getsource(agent_notify_ui_components)

    assert "notifications_enabled_var" in app_source
    assert "load_notifications_enabled" in app_source
    assert "save_notifications_enabled" in app_source
    assert "suppress_when_vscode_focused_var" not in app_source
    assert "CTkSwitch" in module_source


def test_gui_passes_notification_choice_to_script_generation_and_install() -> None:
    generate_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.generate_script)
    install_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp.install)

    assert "notifications_enabled=self.notifications_enabled()" in generate_source
    assert "notifications_enabled=self.notifications_enabled()" in install_source


def test_gui_hides_to_tray_and_exposes_minimal_tray_menu() -> None:
    source = inspect.getsource(agent_notify_configurator.AgentNotifyApp)
    menu_source = inspect.getsource(agent_notify_configurator.AgentNotifyApp._make_tray_menu)

    assert 'self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)' in source
    assert "def hide_to_tray" in source
    assert "def show_main_window" in source
    assert "def quit_app" in source
    assert "打开主面板" in menu_source
    assert "开启通知" in menu_source
    assert "关闭通知" in menu_source
    assert "退出程序" in menu_source
    assert "测试通知" not in menu_source
