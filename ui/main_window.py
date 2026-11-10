import tkinter as tk
from tkinter import ttk


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PPTX TemplateUpdate")
        self.root.geometry("800x540")
        self.root.minsize(640, 440)

        self._container = ttk.Frame(self.root)
        self._container.pack(fill=tk.BOTH, expand=True)

        sep = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, side=tk.BOTTOM)

        self._status_var = tk.StringVar(value="Ready")
        self._status_bar = ttk.Label(
            self.root,
            textvariable=self._status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(6, 2),
        )
        self._status_bar.pack(fill=tk.X, side=tk.BOTTOM, before=sep)

        self._frames: dict[str, ttk.Frame] = {}
        self._current_frame: ttk.Frame | None = None

    def register_frame(self, name: str, frame: ttk.Frame) -> None:
        self._frames[name] = frame

    def show_frame(self, name: str) -> None:
        frame = self._frames[name]
        if self._current_frame is not None:
            self._current_frame.pack_forget()
        frame.pack(in_=self._container, fill=tk.BOTH, expand=True)
        self._current_frame = frame

    def set_status(self, text: str) -> None:
        self._status_var.set(text)
