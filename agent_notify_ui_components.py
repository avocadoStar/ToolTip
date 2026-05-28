from __future__ import annotations

from tkinter import Canvas

import customtkinter as ctk


FONT = "Microsoft YaHei UI"

COLORS = {
    "bg": "#F5F5F7",
    "card": "#FFFFFF",
    "card_soft": "#FBFBFD",
    "visual_effect": "#FFFFFF",
    "border": "#E5E5EA",
    "text": "#1D1D1F",
    "muted": "#6E6E73",
    "muted_light": "#A1A1A6",
    "blue": "#007AFF",
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
    def __init__(self, master, icon: str, color: str, bg_color: str) -> None:
        super().__init__(master, width=58, height=58, fg_color=bg_color, corner_radius=17)
        self.grid_propagate(False)
        self.canvas = Canvas(self, width=34, height=34, bg=bg_color, bd=0, highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        self._draw_icon(icon, color)

    def _draw_icon(self, icon: str, color: str) -> None:
        if icon == "folder":
            self.canvas.create_arc(5, 11, 29, 31, start=180, extent=90, outline=color, width=3)
            self.canvas.create_line(5, 21, 5, 28, fill=color, width=3)
            self.canvas.create_line(6, 30, 29, 30, fill=color, width=3)
            self.canvas.create_line(29, 16, 29, 30, fill=color, width=3)
            self.canvas.create_line(6, 14, 14, 14, fill=color, width=3)
            self.canvas.create_line(14, 14, 18, 18, fill=color, width=3)
            self.canvas.create_line(18, 18, 29, 18, fill=color, width=3)
        elif icon == "code":
            self.canvas.create_rectangle(7, 5, 27, 29, outline=color, width=3)
            self.canvas.create_line(12, 15, 8, 18, 12, 21, fill=color, width=2)
            self.canvas.create_line(22, 15, 26, 18, 22, 21, fill=color, width=2)
            self.canvas.create_line(18, 13, 15, 23, fill=color, width=2)
        elif icon == "puzzle":
            self.canvas.create_rectangle(8, 10, 26, 28, outline=color, width=3)
            self.canvas.create_oval(13, 4, 21, 12, outline=color, width=3)
            self.canvas.create_oval(22, 15, 31, 23, outline=color, width=3)
            self.canvas.create_line(17, 10, 17, 8, fill=color, width=3)
            self.canvas.create_line(26, 19, 28, 19, fill=color, width=3)
        elif icon == "speaker":
            self.canvas.create_polygon(5, 14, 12, 14, 22, 7, 22, 27, 12, 20, 5, 20, fill=color, outline=color)
            self.canvas.create_arc(20, 12, 31, 22, start=-45, extent=90, style="arc", outline=color, width=2)
            self.canvas.create_arc(17, 7, 35, 27, start=-45, extent=90, style="arc", outline=color, width=2)
        elif icon == "trash":
            self.canvas.create_rectangle(9, 12, 25, 29, outline=color, width=3)
            self.canvas.create_line(7, 10, 27, 10, fill=color, width=3)
            self.canvas.create_line(13, 6, 21, 6, fill=color, width=3)
            for x in (14, 20):
                self.canvas.create_line(x, 16, x, 25, fill=color, width=2)
        elif icon == "monitor":
            self.canvas.create_rectangle(5, 6, 29, 22, outline=color, width=3)
            self.canvas.create_line(14, 23, 20, 23, fill=color, width=3)
            self.canvas.create_line(11, 29, 23, 29, fill=color, width=3)
            self.canvas.create_line(17, 23, 17, 29, fill=color, width=3)
            self.canvas.create_oval(23, 3, 32, 12, fill=color, outline=color)


class TimelineMarker(ctk.CTkFrame):
    def __init__(self, master, number: str, show_top: bool, show_bottom: bool) -> None:
        super().__init__(master, width=52, height=98, fg_color=COLORS["bg"], corner_radius=0)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)

        top_line = ctk.CTkFrame(self, width=1, height=14, fg_color=COLORS["line"] if show_top else COLORS["bg"])
        top_line.grid(row=0, column=0, pady=0)

        badge = ctk.CTkFrame(
            self,
            width=32,
            height=32,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=16,
        )
        badge.grid_propagate(False)
        badge.grid(row=1, column=0)
        ctk.CTkLabel(
            badge,
            text=number,
            text_color=COLORS["blue"],
            font=(FONT, 14, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

        bottom_line = ctk.CTkFrame(self, width=1, height=52, fg_color=COLORS["line"] if show_bottom else COLORS["bg"])
        bottom_line.grid(row=2, column=0, pady=0, sticky="n")


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
            corner_radius=18,
        )
        self.status_var = status_var
        self.grid_columnconfigure(1, weight=1)

        IconCanvas(self, icon, icon_color, icon_bg).grid(row=0, column=0, rowspan=2, padx=(22, 18), pady=18)
        ctk.CTkLabel(
            self,
            text=title,
            font=(FONT, 17, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(22, 4))
        ctk.CTkLabel(
            self,
            text=description,
            font=(FONT, 13),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(0, 20))

        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=0, column=2, rowspan=2, sticky="e", padx=(16, 22))
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
            ).pack(anchor="e", pady=(0, 13))
        elif button_text:
            transparent = button_text_color != "#FFFFFF"
            ctk.CTkButton(
                action_frame,
                text=button_text,
                width=132,
                height=36,
                fg_color="transparent" if transparent else button_color,
                hover_color="#F2F2F7" if transparent else "#0A84FF",
                border_width=1 if transparent else 0,
                border_color=button_border_color or button_color,
                text_color=button_text_color,
                font=(FONT, 14),
                corner_radius=14,
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
        self.dot = ctk.CTkLabel(self, text="●", width=18, font=(FONT, 13), text_color=color)
        self.dot.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=11)
        ctk.CTkLabel(
            self,
            text=label,
            font=(FONT, 13),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", pady=11)
        self.value = ctk.CTkLabel(
            self,
            text="未选择",
            font=(FONT, 13, "bold"),
            text_color=COLORS["muted"],
            anchor="e",
        )
        self.value.grid(row=0, column=2, sticky="e", pady=11)

    def set_text(self, text: str) -> None:
        self.value.configure(text=text)

