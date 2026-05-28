from __future__ import annotations

from tkinter import Canvas

import customtkinter as ctk


FONT = "Segoe UI Variable"
LINE_WIDTH = 2
SIDEBAR_WIDTH = 220
CONTENT_MAX_WIDTH = 640
ROW_HEIGHT = 48
NAV_ROW_HEIGHT = 38
BUTTON_HEIGHT = 32
PAGE_TITLE_SIZE = 30
NAV_TEXT_SIZE = 15
ROW_TEXT_SIZE = 15
STATUS_TEXT_SIZE = 14
BUTTON_TEXT_SIZE = 14

COLORS = {
    "bg": "#F5F5F7",
    "sidebar": "#F5F5F7",
    "list": "#FAFAFC",
    "row_hover": "#EFEFF2",
    "nav_selected": "#EAEAEE",
    "border": "#E5E5EA",
    "button_border_subtle": "#F0F0F2",
    "divider": "#F0F0F2",
    "text": "#26262A",
    "muted": "#5F5F64",
    "muted_light": "#8E8E93",
    "nav_icon": "#9A9AA0",
    "nav_icon_selected": "#5F5F64",
    "blue": "#0071E3",
    "blue_hover": "#0066CC",
    "blue_soft": "#EAF3FF",
    "green": "#34C759",
    "orange": "#FF9F0A",
    "red": "#FF3B30",
    "red_soft": "#FFF2F1",
    "scrollbar": "#D1D1D6",
    "scrollbar_hover": "#AEAEB2",
}


class IconCanvas(ctk.CTkFrame):
    def __init__(
        self,
        master,
        icon: str,
        color: str = COLORS["muted"],
        size: int = 28,
        bg_color: str = COLORS["sidebar"],
    ) -> None:
        super().__init__(master, width=size, height=size, fg_color="transparent", corner_radius=8)
        self.grid_propagate(False)
        self.canvas_size = 15
        self.canvas = Canvas(
            self,
            width=self.canvas_size,
            height=self.canvas_size,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
        )
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        self.icon = icon
        self._draw_icon(icon, color)

    def set_background(self, color: str) -> None:
        self.canvas.configure(bg=color)

    def set_color(self, color: str) -> None:
        self.canvas.delete("all")
        self._draw_icon(self.icon, color)

    def _line(self, *points: int, color: str) -> None:
        self.canvas.create_line(*points, fill=color, width=LINE_WIDTH, capstyle="round", joinstyle="round")

    def _draw_icon(self, icon: str, color: str) -> None:
        if icon == "bell":
            self._line(4, 13, 14, 13, 13, 10, 13, 8, 11, 4, 7, 4, 5, 8, 5, 10, 4, 13, color=color)
            self.canvas.create_oval(7, 14, 11, 17, outline=color, width=LINE_WIDTH)
        elif icon == "link":
            self._line(6, 6, 9, 3, 13, 3, 15, 5, 15, 8, 12, 11, color=color)
            self._line(12, 12, 9, 15, 5, 15, 3, 13, 3, 10, 6, 7, color=color)
        elif icon == "music":
            self._line(7, 13, 7, 4, 14, 3, 14, 11, color=color)
            self.canvas.create_oval(3, 12, 7, 16, outline=color, width=LINE_WIDTH)
            self.canvas.create_oval(10, 10, 14, 14, outline=color, width=LINE_WIDTH)
        elif icon == "more":
            self.canvas.create_oval(3, 8, 5, 10, fill=color, outline=color)
            self.canvas.create_oval(8, 8, 10, 10, fill=color, outline=color)
            self.canvas.create_oval(13, 8, 15, 10, fill=color, outline=color)
        elif icon == "app":
            self.canvas.create_oval(3, 3, 15, 15, outline=color, width=LINE_WIDTH)
            self._line(6, 9, 8, 11, 12, 6, color=color)
        else:
            self.canvas.create_oval(4, 4, 14, 14, outline=color, width=LINE_WIDTH)


class SidebarItem(ctk.CTkFrame):
    def __init__(self, master, title: str, icon: str, command=None, selected: bool = False) -> None:
        self.selected = selected
        self.command = command
        super().__init__(
            master,
            fg_color=self._background(),
            corner_radius=8,
            height=NAV_ROW_HEIGHT,
        )
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        self.icon_view = IconCanvas(self, icon, self._icon_color(), size=21, bg_color=self._background())
        self.icon_view.grid(row=0, column=0, padx=(9, 7), pady=5)
        self.label = ctk.CTkLabel(
            self,
            text=title,
            font=(FONT, NAV_TEXT_SIZE, "bold"),
            text_color=self._text_color(),
            anchor="w",
        )
        self.label.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)
        self._bind_pointer_events(self)

    def _bind_pointer_events(self, widget) -> None:
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<Button-1>", self._on_click, add="+")
        for child in widget.winfo_children():
            self._bind_pointer_events(child)

    def _background(self) -> str:
        return COLORS["nav_selected"] if self.selected else COLORS["sidebar"]

    def _text_color(self) -> str:
        return COLORS["text"] if self.selected else COLORS["muted"]

    def _icon_color(self) -> str:
        return COLORS["nav_icon_selected"] if self.selected else COLORS["nav_icon"]

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._apply_state(self._background())

    def _apply_state(self, bg_color: str) -> None:
        text_color = self._text_color()
        self.configure(fg_color=bg_color)
        self.icon_view.set_background(bg_color)
        self.icon_view.set_color(self._icon_color())
        self.label.configure(text_color=text_color)

    def _on_enter(self, _event=None) -> None:
        self._apply_state(COLORS["row_hover"])

    def _on_leave(self, _event=None) -> None:
        self._apply_state(self._background())

    def _on_click(self, _event=None) -> None:
        if self.command is not None:
            self.command()


class SettingsList(ctk.CTkFrame):
    def __init__(self, master, title: str | None = None) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.list = ctk.CTkFrame(
            self,
            fg_color=COLORS["list"],
            border_color=COLORS["button_border_subtle"],
            border_width=0,
            corner_radius=10,
        )
        self.list.grid(row=0, column=0, sticky="ew")
        self.list.grid_columnconfigure(0, weight=1)


SettingsGroup = SettingsList


class SettingRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        control_factory=None,
        status_var: ctk.StringVar | None = None,
        is_last: bool = False,
    ) -> None:
        super().__init__(master, fg_color="transparent", height=ROW_HEIGHT)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self,
            text=title,
            font=(FONT, ROW_TEXT_SIZE, "bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(16, 12), pady=10)

        control = control_factory(self) if control_factory is not None else None
        if control is not None:
            control.grid(row=0, column=1, sticky="e", padx=(12, 16), pady=8)
        elif status_var is not None:
            StatusPill(self, status_var).grid(row=0, column=1, sticky="e", padx=(12, 16), pady=8)

        if not is_last:
            ctk.CTkFrame(self, fg_color=COLORS["divider"], height=1).grid(
                row=1, column=0, columnspan=2, sticky="ew", padx=(16, 0)
            )


class StatusPill(ctk.CTkFrame):
    def __init__(self, master, text_var: ctk.StringVar, color: str = COLORS["muted_light"]) -> None:
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text="●", font=(FONT, 8), text_color=color, width=10).grid(
            row=0, column=0, padx=(0, 5)
        )
        ctk.CTkLabel(
            self,
            textvariable=text_var,
            font=(FONT, STATUS_TEXT_SIZE, "bold"),
            text_color=COLORS["muted"],
        ).grid(row=0, column=1)


class SubtleButton(ctk.CTkButton):
    def __init__(
        self,
        master,
        text: str,
        command=None,
        primary: bool = False,
        danger: bool = False,
        width: int = 112,
    ) -> None:
        if primary:
            fg_color = COLORS["blue"]
            hover_color = COLORS["blue_hover"]
            border_width = 0
            text_color = "#FFFFFF"
        elif danger:
            fg_color = "transparent"
            hover_color = COLORS["row_hover"]
            border_width = 0
            text_color = COLORS["red"]
        else:
            fg_color = "#FFFFFF"
            hover_color = COLORS["row_hover"]
            border_width = 1
            text_color = COLORS["text"]

        super().__init__(
            master,
            text=text,
            command=command,
            width=width,
            height=BUTTON_HEIGHT,
            fg_color=fg_color,
            hover_color=hover_color,
            border_width=border_width,
            border_color=COLORS["button_border_subtle"],
            text_color=text_color,
            font=(FONT, BUTTON_TEXT_SIZE, "bold"),
            corner_radius=8,
        )
