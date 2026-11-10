"""Anchor detection results view. Shows detected anchors from both templates."""

import tkinter as tk
from tkinter import ttk

from models.anchor_record import AnchorRecord


class AnchorResultsFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, on_back=None, on_continue=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._on_continue = on_continue
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Detected Anchors", font=("TkDefaultFont", 14, "bold"))
        header.pack(pady=(12, 4))

        self._summary_var = tk.StringVar()
        ttk.Label(self, textvariable=self._summary_var, foreground="gray").pack(pady=(0, 8))

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left_frame = ttk.LabelFrame(paned, text="Existing Template", padding=4)
        paned.add(left_frame, weight=1)
        self._existing_tree = self._make_tree(left_frame)

        right_frame = ttk.LabelFrame(paned, text="New Template", padding=4)
        paned.add(right_frame, weight=1)
        self._new_tree = self._make_tree(right_frame)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Back to Selection", command=self._handle_back).pack(side=tk.LEFT, padx=4)
        self._continue_btn = ttk.Button(btn_frame, text="Continue to Anchor Assignment", command=self._handle_continue)
        self._continue_btn.pack(side=tk.LEFT, padx=4)

    def _make_tree(self, parent) -> ttk.Treeview:
        cols = ("key", "slide", "shape", "source", "text", "notes")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=12)
        tree.heading("key", text="Anchor Key")
        tree.heading("slide", text="Slide")
        tree.heading("shape", text="Shape Name")
        tree.heading("source", text="Source")
        tree.heading("text", text="Visible Text")
        tree.heading("notes", text="Notes")

        tree.column("key", width=120, minwidth=80)
        tree.column("slide", width=45, minwidth=35, anchor=tk.CENTER)
        tree.column("shape", width=120, minwidth=60)
        tree.column("source", width=85, minwidth=60)
        tree.column("text", width=140, minwidth=60)
        tree.column("notes", width=120, minwidth=60)

        vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def load_results(
        self,
        existing_anchors: list[AnchorRecord],
        new_anchors: list[AnchorRecord],
        existing_path: str,
        new_path: str,
    ) -> None:
        self._populate_tree(self._existing_tree, existing_anchors)
        self._populate_tree(self._new_tree, new_anchors)
        total = len(existing_anchors) + len(new_anchors)
        summary = f"Existing: {len(existing_anchors)} anchor(s)  |  New: {len(new_anchors)} anchor(s)"
        if total == 0:
            summary += "  —  No anchors detected. Use 'Assign Anchors' on the next screen to tag shapes manually."
        self._summary_var.set(summary)

    def _populate_tree(self, tree: ttk.Treeview, anchors: list[AnchorRecord]) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for a in anchors:
            text_preview = a.visible_text[:60].replace("\n", " ")
            notes_str = "; ".join(a.notes) if a.notes else ""
            tree.insert("", tk.END, values=(
                a.anchor_key,
                a.slide_index + 1,
                a.shape_name,
                a.detection_source,
                text_preview,
                notes_str,
            ))

    def _handle_back(self) -> None:
        if self._on_back:
            self._on_back()

    def _handle_continue(self) -> None:
        if self._on_continue:
            self._on_continue()
