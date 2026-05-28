from __future__ import annotations

from tkinter import Canvas

import customtkinter as ctk


FONT = "Microsoft YaHei UI"
LINE_WIDTH = 2

COLORS = {
    "bg": "#F5F5F7",
    "sidebar": "#ECECF1",
    "card": "#FFFFFF",
    "card_soft": "#FBFBFD",
    "glass": "#FFFFFF",
    "border": "#E5E5EA",
    "divider": "#EFEFF4",
    "text": "#1D1D1F",
    "muted": "#6E6E73",
    "muted_light": "#A1A1A6",
    "blue": "#007AFF",
    "blue_hover": "#0A84FF",
    "blue_light": "#EAF4FF",
    "green": "#34C759",
    "green_light": "#EAF8EF",
    "purple": "#AF52DE",
    "purple_light": "#F7ECFC",
    "orange": "#FF9F0A",
    "orange_light": "#FFF4E2",
    "red": "#FF3B30",
    "red_light": "#FFF0EF",
    "cyan": "#32ADE6",
    "cyan_light": "#EAF8FE",
    "line": "#D1D1D6",
    "shadow": "#E9E9EE",
}


class IconCanvas(ctk.CTkFrame):
    def __init__(self, master, icon: str, color: str, bg_color: str, size: int = 42) -> None:
        super().__init__(master, width=size, height=size, fg_color=bg_color, corner_radius=max(12, size // 3))
        self.grid_propagate(False)
        self.canvas_size = max(24, size - 16)
        self.canvas = Canvas(
            self,
            width=self.canvas_size,
            height=self.canvas_size,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
        )
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        self._draw_icon(icon, color)

    def _line(self, *points: int, color: str) -> None:
        self.canvas.create_line(*points, fill=color, width=LINE_WIDTH, capstyle="round", joinstyle="round")

    def _draw_icon(self, icon: str, color: str) -> None:
        if icon == "folder":
            self.canvas.create_rectangle(4, 9, 25, 23, outline=color, width=LINE_WIDTH)
            self._line(5, 10, 11, 10, 14, 13, 25, 13, color=color)
        elif icon == "code":
            self.canvas.create_rectangle(6, 4, 22, 26, outline=color, width=LINE_WIDTH)
            self._line(11, 13, 8, 16, 11, 19, color=color)
            self._line(18, 13, 21, 16, 18, 19, color=color)
        elif icon == "puzzle":
            self.canvas.create_rectangle(7, 8, 23, 24, outline=color, width=LINE_WIDTH)
            self.canvas.create_oval(12, 3, 18, 9, outline=color, width=LINE_WIDTH)
            self.canvas.create_oval(21, 13, 27, 19, outline=color, width=LINE_WIDTH)
        elif icon == "speaker":
            self._line(4, 12, 10, 12, 18, 7, 18, 23, 10, 18, 4, 18, 4, 12, color=color)
            self._line(21, 12, 24, 15, 21, 18, color=color)
            self._line(23, 8, 28, 15, 23, 22, color=color)
        elif icon == "trash":
            self.canvas.create_rectangle(9, 10, 21, 25, outline=color, width=LINE_WIDTH)
            self._line(7, 8, 23, 8, color=color)
            self._line(12, 5, 18, 5, color=color)
            self._line(13, 13, 13, 22, color=color)
            self._line(17, 13, 17, 22, color=color)
        elif icon == "monitor":
            self.canvas.create_rectangle(4, 5, 26, 20, outline=color, width=LINE_WIDTH)
            self._line(12, 24, 18, 24, color=color)
            self._line(15, 20, 15, 24, color=color)
        elif icon == "bell":
            self.canvas.create_oval(12, 23, 18, 28, outline=color, width=LINE_WIDTH)
            self._line(7, 22, 23, 22, 21, 18, 21, 13, 18, 8, 12, 8, 9, 13, 9, 18, 7, 22, color=color)
        elif icon == "app":
            self.canvas.create_oval(6, 6, 24, 24, outline=color, width=LINE_WIDTH)
            self._line(10, 16, 14, 20, 21, 11, color=color)
        else:
            self.canvas.create_oval(7, 7, 23, 23, outline=color, width=LINE_WIDTH)


class SidebarItem(ctk.CTkFrame):
    def __init__(self, master, title: str, subtitle: str, icon: str, color: str, bg_color: str) -> None:
        super().__init__(master, fg_color="transparent", corner_radius=14)
        self.grid_columnconfigure(1, weight=1)
        IconCanvas(self, icon, color, bg_color, size=38).grid(row=0, column=0, rowspan=2, padx=(12, 10), pady=10)
        ctk.CTkLabel(
            self,
            text=title,
            font=(FONT, 13, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", pady=(10, 1))
        ctk.CTkLabel(
            self,
            text=subtitle,
            font=(FONT, 11),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(0, 10))


class SettingSection(ctk.CTkFrame):
    def __init__(self, master, title: str, description: str, icon: str, color: str, bg_color: str) -> None:
        super().__init__(
            master,
            fg_color=COLORS["card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=18,
        )
        self.grid_columnconfigure(1, weight=1)
        IconCanvas(self, icon, color, bg_color, size=44).grid(row=0, column=0, rowspan=2, padx=(20, 14), pady=(18, 10))
        ctk.CTkLabel(
            self,
            text=title,
            font=(FONT, 18, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 20), pady=(20, 3))
        ctk.CTkLabel(
            self,
            text=description,
            font=(FONT, 13),
            text_color=COLORS["muted"],
            anchor="w",
            wraplength=650,
        ).grid(row=1, column=1, sticky="ew", padx=(0, 20), pady=(0, 12))
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 18))
        self.body.grid_columnconfigure(0, weight=1)


class ActionRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        label: str,
        detail: str,
        status_var: ctk.StringVar | None = None,
        button_text: str | None = None,
        button_color: str = COLORS["blue"],
        button_text_color: str = "#FFFFFF",
        command=None,
        switch_var: ctk.BooleanVar | None = None,
        switch_command=None,
    ) -> None:
        super().__init__(master, fg_color=COLORS["card_soft"], corner_radius=14)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self,
            text=label,
            font=(FONT, 14, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 1))
        ctk.CTkLabel(
            self,
            text=detail,
            font=(FONT, 12),
            text_color=COLORS["muted"],
            anchor="w",
            wraplength=520,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 13))
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=0, column=1, rowspan=2, sticky="e", padx=(14, 16), pady=12)
        if switch_var is not None:
            ctk.CTkSwitch(
                action_frame,
                text="",
                variable=switch_var,
                command=switch_command,
                width=54,
                progress_color=button_color,
                button_color="#FFFFFF",
                button_hover_color="#F2F2F7",
            ).pack(anchor="e", pady=(0, 7))
        elif button_text:
            transparent = button_text_color != "#FFFFFF"
            ctk.CTkButton(
                action_frame,
                text=button_text,
                width=124,
                height=34,
                fg_color="transparent" if transparent else button_color,
                hover_color="#F2F2F7" if transparent else COLORS["blue_hover"],
                border_width=1 if transparent else 0,
                border_color=button_color,
                text_color=button_text_color,
                font=(FONT, 13),
                corner_radius=12,
                command=command,
            ).pack(anchor="e", pady=(0, 7))
        if status_var is not None:
            ctk.CTkLabel(
                action_frame,
                textvariable=status_var,
                font=(FONT, 11),
                text_color=COLORS["muted"],
                anchor="e",
            ).pack(anchor="e")


class PreviewBox(ctk.CTkFrame):
    def __init__(self, master, text: str, copy_command) -> None:
        super().__init__(
            master,
            fg_color=COLORS["card_soft"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=14,
        )
        self.grid_columnconfigure(0, weight=1)
        self.textbox = ctk.CTkTextbox(
            self,
            height=128,
            fg_color="transparent",
            text_color=COLORS["text"],
            font=("Cascadia Code", 12),
            border_width=0,
            wrap="word",
        )
        self.textbox.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        self.textbox.insert("1.0", text)
        self.textbox.configure(state="disabled")
        ctk.CTkButton(
            self,
            text="复制配置预览",
            width=128,
            height=32,
            fg_color="#FFFFFF",
            hover_color="#EEF4FF",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["blue"],
            font=(FONT, 12),
            corner_radius=10,
            command=copy_command,
        ).grid(row=1, column=0, sticky="e", padx=14, pady=(0, 12))


class StatusRow(ctk.CTkFrame):
    def __init__(self, master, label: str, color: str) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)
        self.dot = ctk.CTkLabel(self, text="●", width=18, font=(FONT, 13), text_color=color)
        self.dot.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=9)
        ctk.CTkLabel(
            self,
            text=label,
            font=(FONT, 12),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", pady=9)
        self.value = ctk.CTkLabel(
            self,
            text="未选择",
            font=(FONT, 12, "bold"),
            text_color=COLORS["text"],
            anchor="e",
        )
        self.value.grid(row=0, column=2, sticky="e", pady=9)

    def set_text(self, text: str) -> None:
        self.value.configure(text=text)
