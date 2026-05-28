from __future__ import annotations

import sys
import threading
from pathlib import Path
from tkinter import Canvas, filedialog, messagebox

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


APP_TITLE = "AI Hook 提示配置器"
FONT = "Microsoft YaHei UI"

COLORS = {
    "bg": "#F6FAFF",
    "card": "#FFFFFF",
    "card_soft": "#F9FBFF",
    "border": "#D9E3F0",
    "text": "#17233C",
    "muted": "#51627F",
    "muted_light": "#8492A8",
    "blue": "#2563EB",
    "blue_light": "#EAF2FF",
    "green": "#2FB36D",
    "green_light": "#E8F8EF",
    "purple": "#7C3AED",
    "purple_light": "#F1EAFE",
    "orange": "#F59E0B",
    "orange_light": "#FFF5E5",
    "red": "#EF4444",
    "red_light": "#FEEEEE",
    "cyan": "#0EA5E9",
    "cyan_light": "#E6F7FE",
    "line": "#D4DEEB",
}


class IconCanvas(ctk.CTkFrame):
    def __init__(self, master, icon: str, color: str, bg_color: str) -> None:
        super().__init__(master, width=72, height=72, fg_color=bg_color, corner_radius=18)
        self.grid_propagate(False)
        self.canvas = Canvas(self, width=44, height=44, bg=bg_color, bd=0, highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        self._draw_icon(icon, color)

    def _draw_icon(self, icon: str, color: str) -> None:
        if icon == "folder":
            self.canvas.create_rectangle(8, 14, 38, 34, fill=color, outline=color, width=0)
            self.canvas.create_rectangle(8, 10, 22, 18, fill=color, outline=color, width=0)
            self.canvas.create_line(9, 14, 37, 14, fill="#7BB0FF", width=2)
        elif icon == "code":
            self.canvas.create_polygon(12, 6, 30, 6, 38, 14, 38, 38, 12, 38, fill=color, outline=color)
            self.canvas.create_polygon(30, 6, 38, 14, 30, 14, fill="#A7F3D0", outline="#A7F3D0")
            self.canvas.create_text(25, 27, text="</>", fill="white", font=("Consolas", 14, "bold"))
        elif icon == "puzzle":
            self.canvas.create_rectangle(12, 14, 34, 34, fill=color, outline=color)
            self.canvas.create_oval(18, 6, 28, 16, fill=color, outline=color)
            self.canvas.create_oval(4, 20, 16, 32, fill=color, outline=color)
            self.canvas.create_oval(30, 20, 42, 32, fill=color, outline=color)
            self.canvas.create_oval(18, 30, 28, 42, fill=color, outline=color)
        elif icon == "speaker":
            self.canvas.create_polygon(8, 20, 18, 20, 30, 10, 30, 34, 18, 24, 8, 24, fill=color, outline=color)
            self.canvas.create_arc(28, 14, 42, 30, start=-45, extent=90, style="arc", outline=color, width=3)
            self.canvas.create_arc(25, 8, 48, 36, start=-45, extent=90, style="arc", outline=color, width=3)
        elif icon == "trash":
            self.canvas.create_rectangle(13, 15, 34, 38, fill=color, outline=color)
            self.canvas.create_rectangle(10, 11, 37, 15, fill=color, outline=color)
            self.canvas.create_rectangle(18, 6, 29, 10, fill=color, outline=color)
            for x in (18, 24, 30):
                self.canvas.create_line(x, 20, x, 34, fill="white", width=2)
        elif icon == "monitor":
            self.canvas.create_rectangle(8, 9, 38, 29, outline=color, width=3)
            self.canvas.create_rectangle(19, 30, 27, 36, fill=color, outline=color)
            self.canvas.create_rectangle(14, 36, 32, 39, fill=color, outline=color)
            self.canvas.create_oval(31, 5, 41, 15, fill=color, outline=color)


class StepCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        description: str,
        icon: str,
        icon_color: str,
        icon_bg: str,
        status_var: ctk.StringVar,
        button_text: str | None = None,
        button_color: str = COLORS["blue"],
        button_text_color: str = "#FFFFFF",
        button_border_color: str | None = None,
        command=None,
        switch_var: ctk.BooleanVar | None = None,
        switch_command=None,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=14,
        )
        self.status_var = status_var
        self.grid_columnconfigure(1, weight=1)

        IconCanvas(self, icon, icon_color, icon_bg).grid(row=0, column=0, rowspan=2, padx=(26, 22), pady=22)
        ctk.CTkLabel(
            self,
            text=title,
            font=(FONT, 19, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(26, 4))
        ctk.CTkLabel(
            self,
            text=description,
            font=(FONT, 13),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(0, 24))

        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=0, column=2, rowspan=2, sticky="e", padx=(18, 26))
        if switch_var is not None:
            ctk.CTkSwitch(
                action_frame,
                text="",
                variable=switch_var,
                command=switch_command,
                width=54,
                progress_color=button_color,
                button_color="#FFFFFF",
                button_hover_color="#EEF4FF",
            ).pack(anchor="e", pady=(0, 13))
        elif button_text:
            transparent = button_text_color != "#FFFFFF"
            ctk.CTkButton(
                action_frame,
                text=button_text,
                width=138,
                height=38,
                fg_color="transparent" if transparent else button_color,
                hover_color="#F0F5FF" if transparent else button_color,
                border_width=1 if transparent else 0,
                border_color=button_border_color or button_color,
                text_color=button_text_color,
                font=(FONT, 14),
                corner_radius=8,
                command=command,
            ).pack(anchor="e", pady=(0, 13))
        ctk.CTkLabel(
            action_frame,
            textvariable=status_var,
            font=(FONT, 12),
            text_color=COLORS["muted"],
            anchor="e",
        ).pack(anchor="e")


class StatusRow(ctk.CTkFrame):
    def __init__(self, master, label: str, color: str) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)
        self.dot = ctk.CTkLabel(self, text="●", width=18, font=(FONT, 16), text_color=color)
        self.dot.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=11)
        ctk.CTkLabel(
            self,
            text=label,
            font=(FONT, 14),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", pady=11)
        self.value = ctk.CTkLabel(
            self,
            text="未选择",
            font=(FONT, 14),
            text_color=COLORS["muted"],
            anchor="e",
        )
        self.value.grid(row=0, column=2, sticky="e", pady=11)

    def set_text(self, text: str) -> None:
        self.value.configure(text=text)


class AgentNotifyApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.paths = default_paths()
        self.audio_var = ctk.StringVar(value=load_saved_audio_path(self.paths))
        self.suppress_when_vscode_focused_var = ctk.BooleanVar(
            value=load_suppress_when_vscode_focused(self.paths)
        )
        self.status_var = ctk.StringVar(value="就绪。")
        self.audio_status_var = ctk.StringVar(value="未选择文件")
        self.script_status_var = ctk.StringVar(value="尚未生成")
        self.hook_status_var = ctk.StringVar(value="尚未安装")
        self.test_status_var = ctk.StringVar(value="尚未测试")
        self.uninstall_status_var = ctk.StringVar(value="尚未安装")
        self.suppress_status_var = ctk.StringVar(value="已开启" if self.suppress_when_vscode_focused_var.get() else "已关闭")
        self.notice_tested = False

        self.title(APP_TITLE)
        self.geometry("1280x820")
        self.minsize(1180, 760)
        ctk.set_appearance_mode("light")
        self.configure(fg_color=COLORS["bg"])

        self._build_ui()
        self.refresh_status()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_main()
        self._build_footer()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=50, pady=(34, 14))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=APP_TITLE,
            font=(FONT, 30, "bold"),
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
        main.grid(row=1, column=0, sticky="nsew", padx=50, pady=(0, 12))
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(main, fg_color=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        self.steps_scroll = ctk.CTkScrollableFrame(
            left,
            fg_color=COLORS["bg"],
            scrollbar_button_color="#D6E2F1",
            scrollbar_button_hover_color="#B9CAE1",
        )
        self.steps_scroll.grid(row=0, column=0, sticky="nsew")
        self.steps_scroll.grid_columnconfigure(1, weight=1)

        self._build_timeline_steps()
        self._build_side_panel(main)

    def _build_timeline_steps(self) -> None:
        line = ctk.CTkFrame(self.steps_scroll, fg_color=COLORS["line"], width=1)
        line.grid(row=0, column=0, rowspan=6, sticky="ns", padx=(22, 20), pady=(38, 60))

        steps = [
            (
                "1",
                "选择提示音",
                "选择一个 .wav 或 .mp3 文件作为提示音。",
                "folder",
                COLORS["blue"],
                COLORS["blue_light"],
                self.audio_status_var,
                "Browse",
                COLORS["blue"],
                COLORS["blue"],
                self.choose_audio,
            ),
            (
                "2",
                "生成共享通知脚本",
                "根据当前设置生成通知脚本。",
                "code",
                COLORS["green"],
                COLORS["green_light"],
                self.script_status_var,
                "Generate script",
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
                "Install hooks",
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
                "Test notice",
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
                "Uninstall",
                COLORS["red"],
                COLORS["red"],
                self.confirm_uninstall,
            ),
        ]

        for index, step in enumerate(steps):
            number, title, description, icon, icon_color, icon_bg, status, button, color, text_color, command = step
            self._timeline_number(index, number)
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

        self._timeline_number(5, "6")
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

    def _timeline_number(self, row: int, number: str) -> None:
        badge = ctk.CTkLabel(
            self.steps_scroll,
            text=number,
            width=34,
            height=34,
            fg_color=COLORS["blue"],
            text_color="#FFFFFF",
            font=(FONT, 15, "bold"),
            corner_radius=17,
        )
        badge.grid(row=row, column=0, padx=(5, 20), pady=(28, 0), sticky="n")

    def _build_side_panel(self, master) -> None:
        side = ctk.CTkFrame(master, fg_color=COLORS["bg"], width=310)
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_columnconfigure(0, weight=1)

        status_card = ctk.CTkFrame(
            side,
            fg_color=COLORS["card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=14,
        )
        status_card.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        status_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            status_card,
            text="当前状态",
            font=(FONT, 19, "bold"),
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
            corner_radius=14,
        )
        preview_card.grid(row=1, column=0, sticky="ew")
        preview_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            preview_card,
            text="配置预览",
            font=(FONT, 19, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(26, 16))

        preview_box = ctk.CTkFrame(
            preview_card,
            fg_color=COLORS["card_soft"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=10,
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
        footer.grid(row=2, column=0, sticky="ew", padx=50, pady=(0, 22))
        footer.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            footer,
            text="●",
            font=(FONT, 18),
            text_color="#91A0B8",
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
            title="选择提示音",
            filetypes=[("音频文件", "*.wav *.mp3"), ("WAV 文件", "*.wav"), ("MP3 文件", "*.mp3")],
        )
        if path:
            self.audio_var.set(path)
            self.audio_status_var.set("已选择文件")
            self.status_var.set("已选择提示音文件。")
            self.refresh_status()

    def selected_audio(self) -> Path:
        value = self.audio_var.get().strip()
        if not value:
            raise ValueError("请先选择一个 WAV 或 MP3 提示音文件。")
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

    def run_action(self, working: str, action, success: str) -> None:
        self.status_var.set(working)
        self.configure(cursor="watch")
        self.update_idletasks()

        def worker() -> None:
            try:
                action()
            except Exception as exc:  # UI boundary: show explicit failure to the user.
                self.after(0, lambda: self.show_error(str(exc)))
                return
            self.after(0, lambda: self.show_success(success))

        threading.Thread(target=worker, daemon=True).start()

    def show_success(self, message: str) -> None:
        self.configure(cursor="")
        self.status_var.set(message)
        self.refresh_status()
        messagebox.showinfo(APP_TITLE, message)

    def show_error(self, message: str) -> None:
        self.configure(cursor="")
        self.status_var.set(message)
        messagebox.showerror(APP_TITLE, message)

    def refresh_status(self) -> None:
        status = get_status(self.paths)
        audio_selected = bool(self.audio_var.get().strip())
        hook_ready = status["codex"] or status["claude"]

        self.audio_status_var.set("已选择文件" if audio_selected else "未选择文件")
        self.script_status_var.set("已生成" if status["script"] else "尚未生成")
        self.hook_status_var.set("已安装" if hook_ready else "尚未安装")
        self.uninstall_status_var.set("可撤销" if hook_ready else "尚未安装")
        self.test_status_var.set("已测试" if self.notice_tested else "尚未测试")
        self.suppress_status_var.set("已开启" if self.suppress_when_vscode_focused() else "已关闭")

        self.status_rows["audio"].set_text("已选择" if audio_selected else "未选择")
        self.status_rows["script"].set_text("已生成" if status["script"] else "未生成")
        self.status_rows["hook"].set_text("已安装" if hook_ready else "未安装")
        self.status_rows["test"].set_text("已测试" if self.notice_tested else "未测试")

        if self.status_var.get() in {"就绪。", "状态已刷新。"}:
            self.status_var.set("提示：安装后，当 Codex 或 Claude Code 需要您操作时，将播放提示音并显示右下角通知。")


def main() -> None:
    if "--self-test" in sys.argv:
        get_status(default_paths())
        return

    app = AgentNotifyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
