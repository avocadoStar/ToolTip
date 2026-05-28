from __future__ import annotations

import threading
import sys
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


APP_TITLE = "AI Hook 提示配置器"
FONT = "Microsoft YaHei UI"

COLORS = {
    "bg": "#0F172A",
    "surface": "#111827",
    "surface2": "#172033",
    "border": "#334155",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "green": "#22C55E",
    "green_dark": "#15803D",
    "red": "#EF4444",
    "red_dark": "#991B1B",
    "amber": "#F59E0B",
    "slate": "#475569",
}


class StatusCard(ctk.CTkFrame):
    def __init__(self, master, title: str) -> None:
        super().__init__(
            master,
            fg_color=COLORS["surface2"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
        )
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self,
            text=title,
            font=(FONT, 12),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        self.value = ctk.CTkLabel(
            self,
            text="缺失",
            font=(FONT, 14, "bold"),
            text_color=COLORS["text"],
            fg_color=COLORS["slate"],
            corner_radius=6,
        )
        self.value.grid(row=1, column=0, sticky="ew", padx=14, pady=(8, 12))

    def set_ready(self, ready: bool) -> None:
        self.value.configure(
            text="就绪" if ready else "缺失",
            fg_color=COLORS["green_dark"] if ready else COLORS["slate"],
        )


class AgentNotifyApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.paths = default_paths()
        self.audio_var = ctk.StringVar(value=load_saved_audio_path(self.paths))
        self.suppress_when_vscode_focused_var = ctk.BooleanVar(
            value=load_suppress_when_vscode_focused(self.paths)
        )
        self.status_var = ctk.StringVar(value="就绪。")

        self.title(APP_TITLE)
        self.geometry("900x620")
        self.minsize(860, 580)
        ctk.set_appearance_mode("dark")
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
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="AI Hook 提示",
            font=(FONT, 26, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="一键配置 Codex 和 Claude Code 的完成提示音、等待确认提示和右下角通知。",
            font=(FONT, 14),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=28, pady=12)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(
            main,
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="提示音和共享脚本",
            font=(FONT, 18, "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(22, 0))
        ctk.CTkLabel(
            left,
            text="选择一个 WAV 或 MP3 文件，程序会复制到托管通知目录并生成通知脚本。",
            font=(FONT, 13),
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(8, 0))

        audio_row = ctk.CTkFrame(left, fg_color="transparent")
        audio_row.grid(row=2, column=0, sticky="ew", padx=24, pady=(28, 0))
        audio_row.grid_columnconfigure(0, weight=1)
        self.audio_entry = ctk.CTkEntry(
            audio_row,
            textvariable=self.audio_var,
            height=38,
            fg_color=COLORS["bg"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            placeholder_text="选择 .wav 或 .mp3 提示音文件",
        )
        self.audio_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        ctk.CTkButton(
            audio_row,
            text="浏览",
            width=96,
            height=38,
            fg_color=COLORS["surface2"],
            hover_color=COLORS["border"],
            command=self.choose_audio,
        ).grid(row=0, column=1)

        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=24, pady=(26, 0))
        ctk.CTkButton(
            actions,
            text="生成脚本",
            height=40,
            fg_color=COLORS["surface2"],
            hover_color=COLORS["border"],
            command=lambda: self.run_action("正在生成共享脚本...", self.generate_script, "共享脚本已生成。"),
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="测试提示",
            height=40,
            fg_color=COLORS["surface2"],
            hover_color=COLORS["border"],
            command=lambda: self.run_action("正在测试提示...", self.test_notice, "测试提示已完成。"),
        ).pack(side="left", padx=(12, 0))
        ctk.CTkButton(
            actions,
            text="刷新状态",
            height=40,
            fg_color=COLORS["surface2"],
            hover_color=COLORS["border"],
            command=self.refresh_status,
        ).pack(side="left", padx=(12, 0))

        preferences = ctk.CTkFrame(left, fg_color="transparent")
        preferences.grid(row=4, column=0, sticky="ew", padx=24, pady=(24, 0))
        preferences.grid_columnconfigure(0, weight=1)
        ctk.CTkSwitch(
            preferences,
            text="VS Code 前台时静默",
            variable=self.suppress_when_vscode_focused_var,
            command=self.save_suppression_preference,
            font=(FONT, 13),
            text_color=COLORS["text"],
            progress_color=COLORS["green_dark"],
            button_color=COLORS["text"],
            button_hover_color=COLORS["muted"],
        ).grid(row=0, column=0, sticky="w")

        paths = ctk.CTkTextbox(
            left,
            height=120,
            fg_color=COLORS["bg"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["muted"],
            font=("Cascadia Code", 11),
        )
        paths.grid(row=5, column=0, sticky="ew", padx=24, pady=(24, 0))
        paths.insert(
            "1.0",
            "\n".join(
                [
                    f"Codex config: {self.paths.codex_hooks_path}",
                    f"Claude config: {self.paths.claude_settings_path}",
                    f"Shared dir: {self.paths.agent_notify_dir}",
                ]
            ),
        )
        paths.configure(state="disabled")

        notice = ctk.CTkLabel(
            left,
            text="安装会先备份再合并 JSON。取消配置只移除本工具写入的 Hook，然后删除托管目录。",
            font=(FONT, 12),
            text_color=COLORS["muted"],
            wraplength=480,
            justify="left",
        )
        notice.grid(row=6, column=0, sticky="w", padx=24, pady=(24, 22))

        right = ctk.CTkFrame(
            main,
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
        )
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            right,
            text="当前状态",
            font=(FONT, 18, "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(22, 0))
        ctk.CTkLabel(
            right,
            text="这里只显示本工具托管的脚本、音频和 Hook 状态。",
            font=(FONT, 12),
            text_color=COLORS["muted"],
            wraplength=260,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(8, 14))

        self.status_scroll = ctk.CTkScrollableFrame(
            right,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["slate"],
        )
        self.status_scroll.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.status_scroll.grid_columnconfigure(0, weight=1)

        self.status_cards = {
            "script": StatusCard(self.status_scroll, "共享脚本"),
            "audio": StatusCard(self.status_scroll, "托管音频"),
            "codex": StatusCard(self.status_scroll, "Codex Hooks"),
            "claude": StatusCard(self.status_scroll, "Claude Hooks"),
        }
        for index, card in enumerate(self.status_cards.values()):
            card.grid(row=index, column=0, sticky="ew", padx=10, pady=(0, 12))

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer,
            textvariable=self.status_var,
            font=(FONT, 12),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=28, pady=18)

        ctk.CTkButton(
            footer,
            text="一键配置",
            height=42,
            width=128,
            fg_color=COLORS["green_dark"],
            hover_color=COLORS["green"],
            command=lambda: self.run_action("正在写入 Hook...", self.install, "Hook 配置完成。"),
        ).grid(row=0, column=1, padx=(0, 12), pady=14)
        ctk.CTkButton(
            footer,
            text="取消配置",
            height=42,
            width=112,
            fg_color=COLORS["red_dark"],
            hover_color=COLORS["red"],
            command=self.confirm_uninstall,
        ).grid(row=0, column=2, padx=(0, 28), pady=14)

    def choose_audio(self) -> None:
        path = filedialog.askopenfilename(
            title="选择提示音",
            filetypes=[("音频文件", "*.wav *.mp3"), ("WAV 文件", "*.wav"), ("MP3 文件", "*.mp3")],
        )
        if path:
            self.audio_var.set(path)

    def selected_audio(self) -> Path:
        value = self.audio_var.get().strip()
        if not value:
            raise ValueError("请先选择一个 WAV 或 MP3 提示音文件。")
        return Path(value)

    def suppress_when_vscode_focused(self) -> bool:
        return bool(self.suppress_when_vscode_focused_var.get())

    def save_suppression_preference(self) -> None:
        save_suppress_when_vscode_focused(self.paths, self.suppress_when_vscode_focused())

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

    def confirm_uninstall(self) -> None:
        if not messagebox.askokcancel(
            "Confirm uninstall",
            f"将移除本工具写入的 Hook，并删除：\n{self.paths.agent_notify_dir}",
            icon="warning",
        ):
            return
        self.run_action("正在移除 Hook 和托管目录...", lambda: uninstall_hooks(self.paths), "Hook 已移除。")

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
        for key, ready in status.items():
            self.status_cards[key].set_ready(ready)
        if self.status_var.get() in {"就绪。", "状态已刷新。"}:
            self.status_var.set("状态已刷新。")


def main() -> None:
    if "--self-test" in sys.argv:
        get_status(default_paths())
        return

    app = AgentNotifyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
