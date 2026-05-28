from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from agent_notify_core import (
    default_paths,
    ensure_shared_script,
    get_status,
    install_hooks,
    load_saved_audio_path,
    load_suppress_when_vscode_focused,
    run_notice_test,
    save_suppress_when_vscode_focused,
    uninstall_hooks,
)
from agent_notify_ui_components import (
    COLORS,
    FONT,
    ActionRow,
    IconCanvas,
    PreviewBox,
    SettingSection,
    SidebarItem,
    StatusRow,
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
        self.suppress_when_vscode_focused_var = ctk.BooleanVar(
            value=load_suppress_when_vscode_focused(self.paths)
        )
        self.status_var = ctk.StringVar(value="就绪。")
        self.audio_status_var = ctk.StringVar(value="未选择，将静音显示通知")
        self.script_status_var = ctk.StringVar(value="尚未生成")
        self.hook_status_var = ctk.StringVar(value="尚未安装")
        self.test_status_var = ctk.StringVar(value="尚未测试")
        self.uninstall_status_var = ctk.StringVar(value="尚未安装")
        self.suppress_status_var = ctk.StringVar(value="已开启" if self.suppress_when_vscode_focused_var.get() else "已关闭")
        self.notice_tested = False
        self.loading_popup: ctk.CTkToplevel | None = None
        self.loading_started_at = 0.0
        self.action_running = False
        self.status_rows: dict[str, StatusRow] = {}

        self.title(APP_TITLE)
        self._apply_window_icon()
        self.geometry("1180x760")
        self.minsize(980, 680)
        self.configure(fg_color=COLORS["bg"])
        self.bind("<Map>", self._on_window_mapped, add="+")

        self._build_ui()
        self.refresh_status()
        self.after_idle(self.deiconify)

    def _apply_window_icon(self) -> None:
        if WINDOW_ICON_PATH.exists():
            self.iconbitmap(str(WINDOW_ICON_PATH))

    def _on_window_mapped(self, event) -> None:
        if event.widget is self:
            self.after_idle(self._refresh_window_paint)

    def _refresh_window_paint(self) -> None:
        if not self.winfo_exists():
            return
        self.configure(fg_color=COLORS["bg"])
        self.update_idletasks()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._build_main()
        self._build_footer()

    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        main.grid(row=0, column=0, sticky="nsew", padx=24, pady=(24, 10))
        main.grid_columnconfigure(0, weight=0, minsize=280)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            main,
            fg_color=COLORS["sidebar"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=22,
            width=280,
        )
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 18))
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        self.content_scroll = ctk.CTkScrollableFrame(
            main,
            fg_color=COLORS["bg"],
            scrollbar_button_color="#D1D1D6",
            scrollbar_button_hover_color="#AEAEB2",
        )
        self.content_scroll.grid(row=0, column=1, sticky="nsew")
        self.content_scroll.grid_columnconfigure(0, weight=1)

        self._build_sidebar()
        self._build_settings_content()

    def _build_sidebar(self) -> None:
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 18))
        brand.grid_columnconfigure(1, weight=1)
        IconCanvas(brand, "app", COLORS["blue"], COLORS["blue_light"], size=54).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ctk.CTkLabel(
            brand,
            text=APP_TITLE,
            font=(FONT, 21, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(
            brand,
            text="AI Hook 通知设置",
            font=(FONT, 12),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(3, 0))

        status_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=COLORS["glass"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=18,
        )
        status_card.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 18))
        status_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            status_card,
            text="当前状态",
            font=(FONT, 15, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))
        rows = ctk.CTkFrame(status_card, fg_color="transparent")
        rows.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        rows.grid_columnconfigure(0, weight=1)
        self.status_rows = {
            "audio": StatusRow(rows, "提示音文件", COLORS["blue"]),
            "script": StatusRow(rows, "脚本生成", COLORS["green"]),
            "hook": StatusRow(rows, "Hook 安装", COLORS["purple"]),
            "test": StatusRow(rows, "通知测试", COLORS["orange"]),
        }
        for index, row in enumerate(self.status_rows.values()):
            row.grid(row=index, column=0, sticky="ew")

        nav_items = [
            ("选择提示音", "可选声音，也可静音显示", "folder", COLORS["blue"], COLORS["blue_light"]),
            ("生成共享通知脚本", "写入 notify.ps1 与配置", "code", COLORS["green"], COLORS["green_light"]),
            ("安装 Hook 配置", "只配置已安装工具", "puzzle", COLORS["purple"], COLORS["purple_light"]),
            ("测试通知", "验证声音与横幅", "speaker", COLORS["orange"], COLORS["orange_light"]),
            ("VS Code 活跃时静默", "离开 VS Code 后提醒", "monitor", COLORS["cyan"], COLORS["cyan_light"]),
            ("撤销配置", "移除托管 Hook", "trash", COLORS["red"], COLORS["red_light"]),
        ]
        for index, item in enumerate(nav_items, start=2):
            title, subtitle, icon, color, bg = item
            SidebarItem(self.sidebar, title, subtitle, icon, color, bg).grid(row=index, column=0, sticky="ew", padx=12, pady=(0, 4))

    def _build_settings_content(self) -> None:
        ctk.CTkLabel(
            self.content_scroll,
            text="配置面板",
            font=(FONT, 30, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=4, pady=(2, 4))
        ctk.CTkLabel(
            self.content_scroll,
            text="为 Codex 和 Claude Code 配置提示音与右下角通知。所有设置都会写入本机用户级配置。",
            font=(FONT, 14),
            text_color=COLORS["muted"],
            anchor="w",
            wraplength=760,
        ).grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 18))

        sections = [
            self._build_audio_section,
            self._build_script_section,
            self._build_hook_section,
            self._build_test_section,
            self._build_suppression_section,
            self._build_uninstall_section,
            self._build_preview_section,
        ]
        for index, builder in enumerate(sections, start=2):
            builder(index)

    def _add_section(self, row: int, title: str, description: str, icon: str, color: str, bg_color: str) -> SettingSection:
        section = SettingSection(self.content_scroll, title, description, icon, color, bg_color)
        section.grid(row=row, column=0, sticky="ew", padx=4, pady=(0, 14))
        return section

    def _build_audio_section(self, row: int) -> None:
        section = self._add_section(
            row,
            "选择提示音",
            "提示音可选；不选择时，通知会以静音横幅显示。",
            "folder",
            COLORS["blue"],
            COLORS["blue_light"],
        )
        ActionRow(
            section.body,
            "提示音文件",
            "支持 WAV 和 MP3。留空时不会阻止生成脚本或安装 Hook。",
            status_var=self.audio_status_var,
            button_text="选择文件",
            button_color=COLORS["blue"],
            command=self.choose_audio,
        ).grid(row=0, column=0, sticky="ew")

    def _build_script_section(self, row: int) -> None:
        section = self._add_section(
            row,
            "生成共享通知脚本",
            "根据当前偏好生成共享 PowerShell 通知脚本。",
            "code",
            COLORS["green"],
            COLORS["green_light"],
        )
        ActionRow(
            section.body,
            "共享脚本",
            "写入 ~/.agent-notify/notify.ps1 和 config.json。",
            status_var=self.script_status_var,
            button_text="生成脚本",
            button_color=COLORS["green"],
            command=lambda: self.run_action("正在生成共享通知脚本...", self.generate_script, "共享通知脚本已生成。"),
        ).grid(row=0, column=0, sticky="ew")

    def _build_hook_section(self, row: int) -> None:
        section = self._add_section(
            row,
            "安装 Hook 配置",
            "将共享脚本写入 Codex 和 Claude Code 的用户级 Hook 配置。",
            "puzzle",
            COLORS["purple"],
            COLORS["purple_light"],
        )
        ActionRow(
            section.body,
            "用户级 Hook",
            "只配置已安装的工具，重复安装不会重复追加 Hook。",
            status_var=self.hook_status_var,
            button_text="安装 Hook",
            button_color=COLORS["blue"],
            command=lambda: self.run_action("正在写入 Hook...", self.install, "Hook 配置完成。"),
        ).grid(row=0, column=0, sticky="ew")

    def _build_test_section(self, row: int) -> None:
        section = self._add_section(
            row,
            "测试通知",
            "立即触发一次通知，确认声音和右下角横幅是否正常。",
            "speaker",
            COLORS["orange"],
            COLORS["orange_light"],
        )
        ActionRow(
            section.body,
            "通知测试",
            "会复用当前共享脚本和提示音设置。",
            status_var=self.test_status_var,
            button_text="测试通知",
            button_color=COLORS["orange"],
            button_text_color=COLORS["text"],
            command=lambda: self.run_action("正在测试提示...", self.test_notice, "测试提示已完成。"),
        ).grid(row=0, column=0, sticky="ew")

    def _build_suppression_section(self, row: int) -> None:
        section = self._add_section(
            row,
            "VS Code 活跃时静默（可选）",
            "只有当前前台窗口是 VS Code 时，才不播放声音也不显示通知。",
            "monitor",
            COLORS["cyan"],
            COLORS["cyan_light"],
        )
        ActionRow(
            section.body,
            "活跃窗口静默",
            "离开 VS Code 后，Codex 或 Claude Code 需要您操作时会正常显示通知。",
            status_var=self.suppress_status_var,
            button_color=COLORS["blue"],
            switch_var=self.suppress_when_vscode_focused_var,
            switch_command=self.save_suppression_preference,
        ).grid(row=0, column=0, sticky="ew")

    def _build_uninstall_section(self, row: int) -> None:
        section = self._add_section(
            row,
            "撤销配置",
            "移除本工具写入的 Hook，并删除托管通知目录。",
            "trash",
            COLORS["red"],
            COLORS["red_light"],
        )
        ActionRow(
            section.body,
            "托管配置",
            "只移除带 AgentNotifyConfigurator 标记的 Hook。",
            status_var=self.uninstall_status_var,
            button_text="撤销配置",
            button_color=COLORS["red"],
            button_text_color=COLORS["red"],
            command=self.confirm_uninstall,
        ).grid(row=0, column=0, sticky="ew")

    def _build_preview_section(self, row: int) -> None:
        section = self._add_section(
            row,
            "配置预览",
            "这些路径用于定位 Codex、Claude Code 和共享通知脚本。",
            "app",
            COLORS["blue"],
            COLORS["blue_light"],
        )
        self.preview_text = (
            "Codex config:\n"
            "~/.codex/hooks.json\n\n"
            "Claude config:\n"
            "~/.claude/settings.json\n\n"
            "Shared dir:\n"
            "~/.agent-notify"
        )
        PreviewBox(section.body, self.preview_text, self.copy_preview).grid(row=0, column=0, sticky="ew")

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        footer.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 18))
        footer.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            footer,
            text="●",
            font=(FONT, 13),
            text_color=COLORS["blue"],
        ).grid(row=0, column=0, padx=(0, 12))
        ctk.CTkLabel(
            footer,
            textvariable=self.status_var,
            font=(FONT, 12),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")

    def choose_audio(self) -> None:
        path = filedialog.askopenfilename(
            title="选择提示音（可选）",
            filetypes=[("音频文件", "*.wav *.mp3"), ("WAV 文件", "*.wav"), ("MP3 文件", "*.mp3")],
        )
        if path:
            self.audio_var.set(path)
            self.audio_status_var.set("已选择文件")
            self.status_var.set("已选择提示音文件。")
            self.refresh_status()

    def selected_audio(self) -> Path | None:
        value = self.audio_var.get().strip()
        if not value:
            return None
        return Path(value)

    def suppress_when_vscode_focused(self) -> bool:
        return bool(self.suppress_when_vscode_focused_var.get())

    def save_suppression_preference(self) -> None:
        save_suppress_when_vscode_focused(self.paths, self.suppress_when_vscode_focused())
        self.suppress_status_var.set("已开启" if self.suppress_when_vscode_focused() else "已关闭")
        self.status_var.set("VS Code 活跃时静默设置已保存；离开 VS Code 后通知会正常显示。")

    def generate_script(self) -> None:
        ensure_shared_script(
            self.selected_audio(),
            self.paths,
            suppress_when_vscode_focused=self.suppress_when_vscode_focused(),
        )

    def install(self) -> None:
        install_hooks(
            self.selected_audio(),
            self.paths,
            suppress_when_vscode_focused=self.suppress_when_vscode_focused(),
        )

    def test_notice(self) -> None:
        run_notice_test(self.paths)
        self.notice_tested = True

    def confirm_uninstall(self) -> None:
        if not messagebox.askokcancel(
            "Confirm uninstall",
            f"将移除本工具写入的 Hook，并删除：\n{self.paths.agent_notify_dir}",
            icon="warning",
        ):
            return
        self.run_action("正在移除 Hook 和托管目录...", lambda: uninstall_hooks(self.paths), "Hook 已移除。")

    def copy_preview(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.preview_text)
        self.status_var.set("配置预览已复制。")

    def show_loading_popup(self, message: str) -> None:
        self.close_loading_popup()
        self.loading_started_at = time.monotonic()
        popup = ctk.CTkToplevel(self)
        popup.title(APP_TITLE)
        popup.geometry("300x132")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        popup.configure(fg_color=COLORS["card"])
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
            font=(FONT, 15, "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 10))
        ctk.CTkProgressBar(
            popup,
            mode="indeterminate",
            height=8,
            progress_color=COLORS["blue"],
            fg_color=COLORS["blue_light"],
        ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        ctk.CTkLabel(
            popup,
            text="请稍候，正在处理当前步骤。",
            font=(FONT, 12),
            text_color=COLORS["muted"],
        ).grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 20))

        return popup.grid_slaves(row=1, column=0)[0]

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
        delay_ms = max(0, 350 - elapsed_ms)
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
        hook_ready = status["codex"] or status["claude"]

        self._update_status_rows(status, audio_selected, hook_ready)

        if self.status_var.get() in {"就绪。", "状态已刷新。"}:
            self.status_var.set("提示：提示音可选；离开 VS Code 后，Codex 或 Claude Code 需要您操作时会正常显示右下角通知。")

    def _update_status_rows(self, status: dict, audio_selected: bool, hook_ready: bool) -> None:
        self.audio_status_var.set("已选择文件" if audio_selected else "未选择，将静音显示通知")
        self.script_status_var.set("已生成" if status["script"] else "尚未生成")
        self.hook_status_var.set("已安装" if hook_ready else "尚未安装")
        self.uninstall_status_var.set("可撤销" if hook_ready else "尚未安装")
        self.test_status_var.set("已测试" if self.notice_tested else "尚未测试")
        self.suppress_status_var.set("已开启" if self.suppress_when_vscode_focused() else "已关闭")

        self.status_rows["audio"].set_text("已选择" if audio_selected else "静音显示")
        self.status_rows["script"].set_text("已生成" if status["script"] else "未生成")
        self.status_rows["hook"].set_text("已安装" if hook_ready else "未安装")
        self.status_rows["test"].set_text("已测试" if self.notice_tested else "未测试")


def main() -> None:
    if "--self-test" in sys.argv:
        get_status(default_paths())
        return

    app = AgentNotifyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
