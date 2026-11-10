"""Testing view. Shows selected mappings with context and test value input fields."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from models.anchor_mapping import AnchorMapping


class TestingViewFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, on_back=None, on_run_test=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._on_run_test = on_run_test
        self._mappings: list[AnchorMapping] = []
        self._text_widgets: list[tk.Text] = []
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Testing", font=("TkDefaultFont", 14, "bold"))
        header.pack(pady=(10, 2))

        self._summary_var = tk.StringVar()
        ttk.Label(self, textvariable=self._summary_var, foreground="gray").pack(pady=(0, 6))

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=8)

        canvas = tk.Canvas(container, highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self._scroll_frame = ttk.Frame(canvas)

        self._scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self._scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._canvas = canvas

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_linux_scroll_up(event):
            canvas.yview_scroll(-1, "units")

        def _on_linux_scroll_down(event):
            canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_linux_scroll_up)
        canvas.bind_all("<Button-5>", _on_linux_scroll_down)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Back to Mapping", command=self._handle_back).pack(side=tk.LEFT, padx=4)
        self._run_btn = ttk.Button(btn_frame, text="Run Test", command=self._handle_run_test)
        self._run_btn.pack(side=tk.LEFT, padx=4)

    def load_mappings(self, mappings: list[AnchorMapping]) -> None:
        self._save_test_values()

        self._mappings = [m for m in mappings if m.include_in_test]
        self._text_widgets.clear()

        for child in self._scroll_frame.winfo_children():
            child.destroy()

        self._summary_var.set(f"{len(self._mappings)} anchor(s) selected for testing")

        for i, m in enumerate(self._mappings):
            card = ttk.LabelFrame(self._scroll_frame, text=f"  {m.anchor_key}  ", padding=8)
            card.pack(fill=tk.X, padx=4, pady=6)

            info_frame = ttk.Frame(card)
            info_frame.pack(fill=tk.X)

            left = ttk.LabelFrame(info_frame, text="Existing Template Context", padding=4)
            left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
            self._fill_context(left, m.existing_anchor)

            right = ttk.LabelFrame(info_frame, text="New Template Context", padding=4)
            right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
            self._fill_context(right, m.new_anchor)

            ttk.Label(card, text="Test Value:").pack(anchor=tk.W, pady=(6, 2))
            text_widget = tk.Text(card, height=3, width=80, wrap=tk.WORD)
            text_widget.pack(fill=tk.X, pady=(0, 4))
            if m.test_value:
                text_widget.insert("1.0", m.test_value)
            self._text_widgets.append(text_widget)

    def _fill_context(self, parent, anchor) -> None:
        if anchor is None:
            ttk.Label(parent, text="(no anchor)", foreground="gray").pack(anchor=tk.W)
            return

        lines = [
            f"Slide: {anchor.slide_index + 1}",
            f"Shape: {anchor.shape_name}",
            f"Source: {anchor.detection_source}",
            f"Bounds: L={anchor.left}  T={anchor.top}  W={anchor.width}  H={anchor.height}",
        ]
        for line in lines:
            ttk.Label(parent, text=line).pack(anchor=tk.W)

        text_preview = anchor.visible_text[:120].replace("\n", " ")
        ttk.Label(parent, text=f"Text: {text_preview}", wraplength=280).pack(anchor=tk.W, pady=(2, 0))

    def _save_test_values(self) -> None:
        for i, tw in enumerate(self._text_widgets):
            if i < len(self._mappings):
                self._mappings[i].test_value = tw.get("1.0", tk.END).rstrip("\n")

    def get_mappings_with_values(self) -> list[AnchorMapping]:
        self._save_test_values()
        return self._mappings

    def _handle_back(self) -> None:
        self._save_test_values()
        if self._on_back:
            self._on_back()

    def _handle_run_test(self) -> None:
        self._save_test_values()
        if self._on_run_test:
            self._on_run_test()
