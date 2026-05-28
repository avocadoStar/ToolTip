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
from agent_notify_ui_components import COLORS, FONT, StatusRow, StepCard, TimelineMarker


APP_TITLE = "AI Hook 提示配置器"


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

        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(1080, 700)
        self.configure(fg_color=COLORS["bg"])
        self.bind("<Map>", self._on_window_mapped, add="+")

        self._build_ui()
        self.refresh_status()
        self.after_idle(self.deiconify)

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
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_main()
        self._build_footer()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=42, pady=(28, 14))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=APP_TITLE,
            font=(FONT, 28, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="为 Codex 和 Claude Code 配置提示音与右下角通知。",
            font=(FONT, 15),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        main.grid(row=1, column=0, sticky="nsew", padx=42, pady=(0, 12))
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(main, fg_color=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        self.steps_scroll = ctk.CTkScrollableFrame(
            left,
            fg_color=COLORS["bg"],
            scrollbar_button_color="#D1D1D6",
            scrollbar_button_hover_color="#AEAEB2",
        )
        self.steps_scroll.grid(row=0, column=0, sticky="nsew")
        self.steps_scroll.grid_columnconfigure(1, weight=1)

        self._build_timeline_steps()
        self._build_side_panel(main)

    def _build_timeline_steps(self) -> None:
        for index, step in enumerate(self._step_definitions()):
            number, title, description, icon, icon_color, icon_bg, status, button, color, text_color, command = step
            TimelineMarker(
                self.steps_scroll,
                number,
                show_top=index > 0,
                show_bottom=True,
            ).grid(row=index, column=0, padx=(0, 18), pady=(0, 16), sticky="n")
            StepCard(
                self.steps_scroll,
                title=title,
                description=description,
                icon=icon,
                icon_color=icon_color,
                icon_bg=icon_bg,
                status_var=status,
                button_text=button,
                button_color=color,
                button_text_color=text_color,
                button_border_color=color,
                command=command,
            ).grid(row=index, column=1, sticky="ew", pady=(0, 16))

        TimelineMarker(
            self.steps_scroll,
            "6",
            show_top=True,
            show_bottom=False,
        ).grid(row=5, column=0, padx=(0, 18), pady=(0, 0), sticky="n")
        StepCard(
            self.steps_scroll,
            title="VS Code 前台静默（可选）",
            description="当 VS Code 位于前台时，不播放声音也不显示通知。",
            icon="monitor",
            icon_color=COLORS["cyan"],
            icon_bg=COLORS["cyan_light"],
            status_var=self.suppress_status_var,
            button_color=COLORS["blue"],
            switch_var=self.suppress_when_vscode_focused_var,
            switch_command=self.save_suppression_preference,
        ).grid(row=5, column=1, sticky="ew", pady=(0, 0))

    def _step_definitions(self):
        return [
            (
                "1",
                "选择提示音",
                "提示音可选；不选择时，通知将静音显示。",
                "folder",
                COLORS["blue"],
                COLORS["blue_light"],
                self.audio_status_var,
                "选择文件",
                COLORS["blue"],
                COLORS["blue"],
                self.choose_audio,
            ),
            (
                "2",
                "生成共享通知脚本",
                "根据当前设置生成通知脚本，可不配置提示音。",
                "code",
                COLORS["green"],
                COLORS["green_light"],
                self.script_status_var,
                "生成脚本",
                COLORS["green"],
                "#FFFFFF",
                lambda: self.run_action("正在生成共享通知脚本...", self.generate_script, "共享通知脚本已生成。"),
            ),
            (
                "3",
                "安装 Hook 配置",
                "将脚本写入 Codex 和 Claude Code 的用户级 Hook 配置。",
                "puzzle",
                COLORS["purple"],
                COLORS["purple_light"],
                self.hook_status_var,
                "安装 Hook",
                COLORS["blue"],
                "#FFFFFF",
                lambda: self.run_action("正在写入 Hook...", self.install, "Hook 配置完成。"),
            ),
            (
                "4",
                "测试通知",
                "测试提示音播放与右下角通知是否正常。",
                "speaker",
                COLORS["orange"],
                COLORS["orange_light"],
                self.test_status_var,
                "测试通知",
                COLORS["muted"],
                COLORS["text"],
                lambda: self.run_action("正在测试提示...", self.test_notice, "测试提示已完成。"),
            ),
            (
                "5",
                "撤销（可选）",
                "移除已写入的 Hook 配置，恢复到未安装状态。",
                "trash",
                COLORS["red"],
                COLORS["red_light"],
                self.uninstall_status_var,
                "撤销配置",
                COLORS["red"],
                COLORS["red"],
                self.confirm_uninstall,
            ),
        ]

    def _build_side_panel(self, master) -> None:
        side = ctk.CTkFrame(master, fg_color=COLORS["bg"], width=330)
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_columnconfigure(0, weight=1)

        status_card = ctk.CTkFrame(
            side,
            fg_color=COLORS["card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=18,
        )
        status_card.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        status_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            status_card,
            text="当前状态",
            font=(FONT, 17, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(26, 12))

        rows = ctk.CTkFrame(status_card, fg_color="transparent")
        rows.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 22))
        rows.grid_columnconfigure(0, weight=1)
        self.status_rows = {
            "audio": StatusRow(rows, "提示音文件", COLORS["blue"]),
            "script": StatusRow(rows, "脚本生成", COLORS["green"]),
            "hook": StatusRow(rows, "Hook 安装", COLORS["purple"]),
            "test": StatusRow(rows, "通知测试", COLORS["orange"]),
        }
        for index, row in enumerate(self.status_rows.values()):
            row.grid(row=index, column=0, sticky="ew")

        preview_card = ctk.CTkFrame(
            side,
            fg_color=COLORS["card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=18,
        )
        preview_card.grid(row=1, column=0, sticky="ew")
        preview_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            preview_card,
            text="配置预览",
            font=(FONT, 17, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(26, 16))

        preview_box = ctk.CTkFrame(
            preview_card,
            fg_color=COLORS["card_soft"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=14,
        )
        preview_box.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 24))
        preview_box.grid_columnconfigure(0, weight=1)
        self.preview_text = (
            "Codex config:\n"
            "~/.codex/hooks.json\n\n"
            "Claude config:\n"
            "~/.claude/settings.json\n\n"
            "Shared dir:\n"
            "~/.agent-notify"
        )
        ctk.CTkLabel(
            preview_box,
            text=self.preview_text,
            font=("Cascadia Code", 12),
            text_color=COLORS["text"],
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=16)
        ctk.CTkButton(
            preview_box,
            text="⧉",
            width=34,
            height=30,
            fg_color="#FFFFFF",
            hover_color="#EEF4FF",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["muted"],
            font=(FONT, 16),
            corner_radius=8,
            command=self.copy_preview,
        ).grid(row=1, column=0, sticky="e", padx=16, pady=(0, 14))

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=42, pady=(0, 22))
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
        self.status_var.set("VS Code 前台静默设置已保存。")

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
        self.close_loading_popup()
        self.configure(cursor="")
        self.status_var.set(message)
        self.refresh_status()
        messagebox.showinfo(APP_TITLE, message)

    def show_error(self, message: str) -> None:
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
            self.status_var.set("提示：提示音可选；未选择时，当 Codex 或 Claude Code 需要您操作会静音显示右下角通知。")

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
