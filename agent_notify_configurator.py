from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    import pystray
    from PIL import Image
except ImportError:  # Dependencies are validated when tray mode is used.
    pystray = None
    Image = None

from agent_notify_core import (
    default_paths,
    ensure_shared_script,
    get_status,
    install_hooks,
    load_notifications_enabled,
    load_saved_audio_path,
    run_notice_test,
    save_notifications_enabled,
    uninstall_hooks,
)
from agent_notify_ui_components import (
    COLORS,
    CONTENT_MAX_WIDTH,
    FONT,
    IconCanvas,
    PAGE_TITLE_SIZE,
    SIDEBAR_WIDTH,
    SettingRow,
    SettingsList,
    SidebarItem,
    SubtleButton,
)


APP_TITLE = "灵犀提醒"
ROOT = Path(__file__).resolve().parent
WINDOW_ICON_PATH = Path(getattr(sys, "_MEIPASS", ROOT)) / "assets" / "lingxi_icon.ico"


def configure_app_theme() -> None:
    ctk.set_appearance_mode("light")


class AgentNotifyApp(ctk.CTk):
    def __init__(self) -> None:
        configure_app_theme()
        super().__init__()
        self.withdraw()
        self.paths = default_paths()
        self.audio_var = ctk.StringVar(value=load_saved_audio_path(self.paths))
        self.notifications_enabled_var = ctk.BooleanVar(value=load_notifications_enabled(self.paths))
        self.current_page = ctk.StringVar(value="notifications")
        self.status_var = ctk.StringVar(value="就绪。")
        self.notification_status_var = ctk.StringVar(value="已启用")
        self.codex_status_var = ctk.StringVar(value="未连接")
        self.claude_status_var = ctk.StringVar(value="未连接")
        self.audio_status_var = ctk.StringVar(value="未设置")
        self.script_status_var = ctk.StringVar(value="未生成")
        self.sidebar_items: dict[str, SidebarItem] = {}
        self.notice_tested = False
        self.loading_popup: ctk.CTkToplevel | None = None
        self.loading_started_at = 0.0
        self.action_running = False
        self.repaint_after_id: str | None = None
        self.content_built = False
        self.tray_icon = None
        self.tray_started = False
        self.is_quitting = False

        self.title(APP_TITLE)
        self._apply_window_icon()
        self.geometry("980x620")
        self.minsize(960, 540)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self._apply_window_background()
        self.bind("<Map>", self._on_window_paint_event, add="+")
        self.bind("<Configure>", self._on_window_paint_event, add="+")
        self.bind("<Visibility>", self._on_window_paint_event, add="+")

        self._build_ui()
        self._init_tray()
        self.after_idle(self._show_initial_window)

    def _apply_window_icon(self) -> None:
        if WINDOW_ICON_PATH.exists():
            self.iconbitmap(str(WINDOW_ICON_PATH))

    def _on_window_paint_event(self, event) -> None:
        if event.widget is self:
            self._schedule_repaint()

    def _schedule_repaint(self) -> None:
        if not self.winfo_exists():
            return
        if self.repaint_after_id is not None:
            self.after_cancel(self.repaint_after_id)
        self.repaint_after_id = self.after(24, self._refresh_window_paint)

    def _refresh_window_paint(self) -> None:
        self.repaint_after_id = None
        if self.winfo_exists():
            self._apply_window_background()

    def _apply_window_background(self) -> None:
        self.configure(fg_color=COLORS["bg"])
        if hasattr(self, "main_frame"):
            self.main_frame.configure(fg_color=COLORS["bg"])
        if hasattr(self, "content_area"):
            self.content_area.configure(fg_color=COLORS["bg"])
        if hasattr(self, "content_panel"):
            self.content_panel.configure(fg_color=COLORS["bg"])

    def _show_initial_window(self) -> None:
        self._apply_window_background()
        self.deiconify()
        self.after(35, self._finish_initial_render)

    def _finish_initial_render(self) -> None:
        if not self.content_built:
            self._build_sidebar()
            self.show_page(self.current_page.get())
            self.content_built = True
        self.refresh_status()
        self._schedule_repaint()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_main()

    def _build_main(self) -> None:
        self.main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=32, pady=(30, 26))
        self.main_frame.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_WIDTH)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self.main_frame, fg_color=COLORS["sidebar"], corner_radius=0, width=SIDEBAR_WIDTH)
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 24))
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        self.content_area = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg"],
            corner_radius=0,
        )
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_columnconfigure(0, weight=0, minsize=CONTENT_MAX_WIDTH)
        self.content_area.grid_columnconfigure(1, weight=1)
        self.content_area.grid_rowconfigure(0, weight=0)

        self.content_panel = ctk.CTkFrame(
            self.content_area,
            fg_color=COLORS["bg"],
            width=CONTENT_MAX_WIDTH,
            corner_radius=0,
        )
        self.content_panel.grid(row=0, column=0, sticky="new")
        self.content_panel.grid_columnconfigure(0, weight=1)

    def _build_sidebar(self) -> None:
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 22))
        brand.grid_columnconfigure(1, weight=1)
        IconCanvas(brand, "app", COLORS["blue"], size=26).grid(row=0, column=0, padx=(2, 8), pady=3)
        ctk.CTkLabel(
            brand,
            text=APP_TITLE,
            font=(FONT, 16, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")

        self.sidebar_items = {}
        for index, item in enumerate(self._page_definitions(), start=1):
            page_id, title, icon = item
            nav_item = SidebarItem(
                self.sidebar,
                title,
                icon,
                command=lambda page_id=page_id: self.show_page(page_id),
                selected=self.current_page.get() == page_id,
            )
            nav_item.grid(row=index, column=0, sticky="ew", padx=4, pady=(0, 4))
            self.sidebar_items[page_id] = nav_item

    def _page_definitions(self) -> list[tuple[str, str, str]]:
        return [
            ("notifications", "通知", "bell"),
            ("connections", "连接", "link"),
            ("audio", "提示音", "music"),
            ("more", "更多", "more"),
        ]

    def show_page(self, page_id: str) -> None:
        builders = {
            "notifications": self._build_notifications_page,
            "connections": self._build_connection_page,
            "audio": self._build_audio_page,
            "more": self._build_more_page,
        }
        if page_id not in builders:
            page_id = "notifications"

        self.current_page.set(page_id)
        for item_id, item in self.sidebar_items.items():
            item.set_selected(item_id == page_id)

        self._clear_content()
        builders[page_id]()
        self._schedule_repaint()

    def _clear_content(self) -> None:
        for child in self.content_panel.winfo_children():
            child.destroy()

    def _build_page_header(self, title: str) -> None:
        ctk.CTkLabel(
            self.content_panel,
            text=title,
            font=(FONT, PAGE_TITLE_SIZE, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 18))

    def _place_list(self) -> SettingsList:
        settings_list = SettingsList(self.content_panel)
        settings_list.grid(row=1, column=0, sticky="ew", padx=2, pady=(0, 12))
        return settings_list

    def _build_notifications_page(self) -> None:
        self._build_page_header("通知")
        settings_list = self._place_list()
        SettingRow(settings_list.list, "状态", status_var=self.notification_status_var).grid(row=0, column=0, sticky="ew")
        SettingRow(
            settings_list.list,
            "通知",
            control_factory=lambda parent: ctk.CTkSwitch(
                parent,
                text="",
                variable=self.notifications_enabled_var,
                command=self.save_notification_preference,
                width=48,
                progress_color=COLORS["blue"],
                button_color="#FFFFFF",
                button_hover_color="#F2F2F4",
                height=22,
                switch_width=42,
            ),
            is_last=True,
        ).grid(row=1, column=0, sticky="ew")

    def _build_connection_page(self) -> None:
        self._build_page_header("连接")
        settings_list = self._place_list()
        SettingRow(settings_list.list, "Codex", status_var=self.codex_status_var).grid(row=0, column=0, sticky="ew")
        SettingRow(settings_list.list, "Claude Code", status_var=self.claude_status_var).grid(row=1, column=0, sticky="ew")
        SettingRow(
            settings_list.list,
            "连接 Codex 与 Claude Code",
            control_factory=lambda parent: SubtleButton(
                parent,
                "连接",
                command=lambda: self.run_action("正在连接...", self.install, "连接完成。"),
                primary=True,
                width=88,
            ),
            is_last=True,
        ).grid(row=2, column=0, sticky="ew")

    def _build_audio_page(self) -> None:
        self._build_page_header("提示音")
        settings_list = self._place_list()
        SettingRow(settings_list.list, "状态", status_var=self.audio_status_var).grid(row=0, column=0, sticky="ew")
        SettingRow(
            settings_list.list,
            "提示音",
            control_factory=lambda parent: SubtleButton(parent, "选择", command=self.choose_audio, width=88),
            is_last=True,
        ).grid(row=1, column=0, sticky="ew")

    def _build_more_page(self) -> None:
        self._build_page_header("更多")
        settings_list = self._place_list()
        SettingRow(
            settings_list.list,
            "测试通知",
            control_factory=lambda parent: SubtleButton(
                parent,
                "测试",
                command=lambda: self.run_action("正在测试通知...", self.test_notice, "测试通知已发送。"),
                width=88,
            ),
        ).grid(row=0, column=0, sticky="ew")
        SettingRow(
            settings_list.list,
            "生成脚本",
            control_factory=lambda parent: SubtleButton(
                parent,
                "生成",
                command=lambda: self.run_action("正在生成脚本...", self.generate_script, "脚本已生成。"),
                width=88,
            ),
        ).grid(row=1, column=0, sticky="ew")
        SettingRow(
            settings_list.list,
            "复制配置摘要",
            control_factory=lambda parent: SubtleButton(parent, "复制", command=self.copy_summary, width=88),
        ).grid(row=2, column=0, sticky="ew")
        SettingRow(
            settings_list.list,
            "查看诊断日志",
            control_factory=lambda parent: SubtleButton(parent, "打开", command=self.open_notify_log, width=88),
        ).grid(row=3, column=0, sticky="ew")
        SettingRow(
            settings_list.list,
            "撤销配置",
            control_factory=lambda parent: SubtleButton(
                parent,
                "撤销",
                command=self.confirm_uninstall,
                danger=True,
                width=88,
            ),
            is_last=True,
        ).grid(row=4, column=0, sticky="ew")

    def _build_footer(self) -> None:
        return

    def _init_tray(self) -> None:
        if pystray is None or Image is None:
            return
        image = self._load_tray_image()
        self.tray_icon = pystray.Icon(APP_TITLE, image, APP_TITLE, self._make_tray_menu())
        self.tray_icon.run_detached()
        self.tray_started = True

    def _load_tray_image(self):
        if WINDOW_ICON_PATH.exists():
            return Image.open(WINDOW_ICON_PATH)
        return Image.new("RGBA", (64, 64), (0, 113, 227, 255))

    def _make_tray_menu(self):
        notify_text = "关闭通知" if self.notifications_enabled() else "开启通知"
        return pystray.Menu(
            pystray.MenuItem("打开主面板", lambda: self.after(0, self.show_main_window)),
            pystray.MenuItem(notify_text, lambda: self.after(0, self.toggle_notifications_from_tray)),
            pystray.MenuItem("退出程序", lambda: self.after(0, self.quit_app)),
        )

    def _refresh_tray_menu(self) -> None:
        if self.tray_icon is None:
            return
        self.tray_icon.menu = self._make_tray_menu()
        self.tray_icon.update_menu()

    def hide_to_tray(self) -> None:
        if pystray is None or Image is None:
            messagebox.showerror(APP_TITLE, "缺少系统托盘依赖，请重新安装 requirements.txt。")
            return
        self.withdraw()
        self.status_var.set("灵犀提醒已在后台运行。")

    def show_main_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        self.refresh_status()

    def quit_app(self) -> None:
        self.is_quitting = True
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.destroy()

    def destroy(self) -> None:
        if not self.is_quitting and self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        super().destroy()

    def choose_audio(self) -> None:
        path = filedialog.askopenfilename(
            title="选择提示音（可选）",
            filetypes=[("音频文件", "*.wav *.mp3"), ("WAV 文件", "*.wav"), ("MP3 文件", "*.mp3")],
        )
        if path:
            self.audio_var.set(path)
            self.status_var.set("提示音已设置。")
            self.refresh_status()

    def selected_audio(self) -> Path | None:
        value = self.audio_var.get().strip()
        if not value:
            return None
        return Path(value)

    def notifications_enabled(self) -> bool:
        return bool(self.notifications_enabled_var.get())

    def save_notification_preference(self) -> None:
        save_notifications_enabled(self.paths, self.notifications_enabled())
        self.refresh_status()
        self._refresh_tray_menu()
        self.status_var.set("通知已启用。" if self.notifications_enabled() else "通知已暂停。")

    def toggle_notifications_from_tray(self) -> None:
        self.notifications_enabled_var.set(not self.notifications_enabled())
        self.save_notification_preference()

    def generate_script(self) -> None:
        ensure_shared_script(
            self.selected_audio(),
            self.paths,
            notifications_enabled=self.notifications_enabled(),
        )

    def install(self) -> None:
        install_hooks(
            self.selected_audio(),
            self.paths,
            notifications_enabled=self.notifications_enabled(),
        )

    def test_notice(self) -> None:
        run_notice_test(self.paths)
        self.notice_tested = True

    def confirm_uninstall(self) -> None:
        if not messagebox.askokcancel(
            APP_TITLE,
            "将移除本工具写入的连接配置，并删除本地通知文件。",
            icon="warning",
        ):
            return
        self.run_action("正在撤销配置...", lambda: uninstall_hooks(self.paths), "配置已撤销。")

    def copy_summary(self) -> None:
        status = get_status(self.paths)
        summary = "\n".join(
            [
                f"Codex: {'connected' if status['codex'] else 'not connected'}",
                f"Claude Code: {'connected' if status['claude'] else 'not connected'}",
                f"Notifications: {'enabled' if self.notifications_enabled() else 'paused'}",
                f"Audio: {'set' if bool(self.audio_var.get().strip()) else 'not set'}",
            ]
        )
        self.clipboard_clear()
        self.clipboard_append(summary)
        self.status_var.set("配置摘要已复制。")

    def open_notify_log(self) -> None:
        if not self.paths.agent_notify_dir.exists():
            self.paths.agent_notify_dir.mkdir(parents=True, exist_ok=True)
        if not self.paths.notify_log_path.exists():
            self.paths.notify_log_path.write_text("", encoding="utf-8")
        os.startfile(self.paths.notify_log_path)

    def show_loading_popup(self, message: str) -> None:
        self.close_loading_popup()
        self.loading_started_at = time.monotonic()
        popup = ctk.CTkToplevel(self)
        popup.title(APP_TITLE)
        popup.geometry("280x112")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        popup.configure(fg_color=COLORS["list"])
        popup.grid_columnconfigure(0, weight=1)

        progress = self._build_loading_popup(popup, message)
        progress.start()
        popup.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - popup.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - popup.winfo_height()) // 2)
        popup.geometry(f"+{x}+{y}")
        self.loading_popup = popup

    def _build_loading_popup(self, popup: ctk.CTkToplevel, message: str) -> ctk.CTkProgressBar:
        ctk.CTkLabel(
            popup,
            text=message,
            font=(FONT, 14),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 10))
        progress = ctk.CTkProgressBar(
            popup,
            mode="indeterminate",
            height=6,
            progress_color=COLORS["blue"],
            fg_color=COLORS["blue_soft"],
        )
        progress.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 22))
        return progress

    def close_loading_popup(self) -> None:
        if self.loading_popup is None:
            return
        popup = self.loading_popup
        self.loading_popup = None
        if popup.winfo_exists():
            popup.grab_release()
            popup.destroy()

    def finish_action_after_loading(self, callback) -> None:
        elapsed_ms = int((time.monotonic() - self.loading_started_at) * 1000)
        delay_ms = max(0, 300 - elapsed_ms)
        self.after(delay_ms, callback)

    def run_action(self, working: str, action, success: str) -> None:
        if self.action_running:
            return
        self.action_running = True
        self.status_var.set(working)
        self.show_loading_popup(working)
        self.configure(cursor="watch")
        self.update_idletasks()

        def worker() -> None:
            try:
                action()
            except Exception as exc:  # UI boundary: show explicit failure to the user.
                message = str(exc)
                self.after(0, lambda message=message: self.finish_action_after_loading(lambda: self.show_error(message)))
                return
            self.after(0, lambda: self.finish_action_after_loading(lambda: self.show_success(success)))

        threading.Thread(target=worker, daemon=True).start()

    def show_success(self, message: str) -> None:
        self.action_running = False
        self.close_loading_popup()
        self.configure(cursor="")
        self.status_var.set(message)
        self.refresh_status()
        messagebox.showinfo(APP_TITLE, message)

    def show_error(self, message: str) -> None:
        self.action_running = False
        self.close_loading_popup()
        self.configure(cursor="")
        self.status_var.set(message)
        messagebox.showerror(APP_TITLE, message)

    def refresh_status(self) -> None:
        status = get_status(self.paths)
        audio_selected = bool(self.audio_var.get().strip())

        self.notification_status_var.set("已启用" if self.notifications_enabled() else "已暂停")
        self.codex_status_var.set("已连接" if status["codex"] else "未连接")
        self.claude_status_var.set("已连接" if status["claude"] else "未连接")
        self.audio_status_var.set("已设置" if audio_selected else "未设置")
        self.script_status_var.set("已生成" if status["script"] else "未生成")

        if self.status_var.get() == "就绪。":
            self.status_var.set("关闭窗口后，灵犀提醒会安静驻留在系统托盘。")


def main() -> None:
    if "--self-test" in sys.argv:
        get_status(default_paths())
        return

    app = AgentNotifyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
