"""Anchor Assignment screen.

Shown after AnchorResults. Lets the user manually assign anchor keys to
shapes in either template. Assignments are merged with auto-detected anchors
before the Mapping screen.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from services.anchor_assigner import ShapeInfo


class AnchorAssignmentFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, on_back=None, on_continue=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._on_continue = on_continue

        self._existing_shapes: list[ShapeInfo] = []
        self._new_shapes: list[ShapeInfo] = []

        # (slide_index, shape_name) -> anchor_key
        self._existing_assignments: dict[tuple[int, str], str] = {}
        self._new_assignments: dict[tuple[int, str], str] = {}

        self._active_tab = "existing"
        self._selected_row: int | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Assign Anchors", font=("TkDefaultFont", 14, "bold"))
        header.pack(pady=(10, 2))

        desc = ttk.Label(
            self,
            text="Select a shape and type an anchor key to assign. Assignments are saved into the output file.",
            foreground="gray",
        )
        desc.pack(pady=(0, 6))

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._existing_tab = ttk.Frame(self._notebook)
        self._new_tab = ttk.Frame(self._notebook)
        self._notebook.add(self._existing_tab, text="Existing Template")
        self._notebook.add(self._new_tab, text="New Template")

        self._existing_tree = self._build_tab(self._existing_tab, "existing")
        self._new_tree = self._build_tab(self._new_tab, "new")

        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        assign_frame = ttk.LabelFrame(self, text="Assign Anchor Key", padding=8)
        assign_frame.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(assign_frame, text="Selected shape:").grid(row=0, column=0, sticky=tk.W, padx=4)
        self._selected_label = ttk.Label(assign_frame, text="(none)", foreground="gray")
        self._selected_label.grid(row=0, column=1, sticky=tk.W, padx=4)

        ttk.Label(assign_frame, text="Anchor Key:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self._key_var = tk.StringVar()
        self._key_entry = ttk.Entry(assign_frame, textvariable=self._key_var, width=40)
        self._key_entry.grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)
        self._key_entry.bind("<Return>", lambda e: self._apply_assignment())

        ttk.Button(assign_frame, text="Assign", command=self._apply_assignment).grid(
            row=1, column=2, padx=6, pady=4)
        ttk.Button(assign_frame, text="Clear", command=self._clear_assignment).grid(
            row=1, column=3, padx=2, pady=4)

        self._count_var = tk.StringVar(value="0 existing / 0 new anchors assigned")
        ttk.Label(assign_frame, textvariable=self._count_var, foreground="gray").grid(
            row=2, column=0, columnspan=4, sticky=tk.W, padx=4)

        assign_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Back", command=self._handle_back).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Skip (no assignments)", command=self._handle_continue).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Save & Continue to Mapping", command=self._handle_continue,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=4)

    def _build_tab(self, parent: ttk.Frame, which: str) -> ttk.Treeview:
        cols = ("anchor", "slide", "name", "text")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)

        tree.heading("anchor", text="Anchor Key")
        tree.heading("slide", text="Slide")
        tree.heading("name", text="Shape Name")
        tree.heading("text", text="Visible Text")

        tree.column("anchor", width=130, minwidth=80)
        tree.column("slide", width=45, minwidth=35, anchor=tk.CENTER)
        tree.column("name", width=180, minwidth=80)
        tree.column("text", width=340, minwidth=100)

        vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        tree.bind("<<TreeviewSelect>>", lambda e: self._on_select(which))
        tree.tag_configure("assigned", background="#e8f5e9")

        return tree

    def load_shapes(
        self,
        existing_shapes: list[ShapeInfo],
        new_shapes: list[ShapeInfo],
        existing_assignments: dict[tuple[int, str], str] | None = None,
        new_assignments: dict[tuple[int, str], str] | None = None,
    ) -> None:
        self._existing_shapes = existing_shapes
        self._new_shapes = new_shapes
        self._existing_assignments = existing_assignments or {}
        self._new_assignments = new_assignments or {}
        self._selected_row = None
        self._selected_label.configure(text="(none)")
        self._key_var.set("")
        self._refresh_tree(self._existing_tree, existing_shapes, self._existing_assignments)
        self._refresh_tree(self._new_tree, new_shapes, self._new_assignments)
        self._update_count()

    def _refresh_tree(
        self,
        tree: ttk.Treeview,
        shapes: list[ShapeInfo],
        assignments: dict[tuple[int, str], str],
    ) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for i, info in enumerate(shapes):
            ak = assignments.get((info.slide_index, info.shape_name), "")
            text_preview = info.visible_text[:80].replace("\n", " ")
            tag = "assigned" if ak else ""
            tree.insert("", tk.END, iid=str(i), values=(
                ak,
                info.slide_index + 1,
                info.shape_name,
                text_preview,
            ), tags=(tag,) if tag else ())

    def _on_tab_change(self, event) -> None:
        idx = self._notebook.index("current")
        self._active_tab = "existing" if idx == 0 else "new"
        self._selected_row = None
        self._selected_label.configure(text="(none)")
        self._key_var.set("")

    def _on_select(self, which: str) -> None:
        tree = self._existing_tree if which == "existing" else self._new_tree
        shapes = self._existing_shapes if which == "existing" else self._new_shapes
        assignments = self._existing_assignments if which == "existing" else self._new_assignments

        sel = tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self._selected_row = idx
        self._active_tab = which

        info = shapes[idx]
        label = f"Slide {info.slide_index+1} | {info.shape_name}"
        if info.visible_text:
            label += f" | \"{info.visible_text[:50].replace(chr(10), ' ')}\""
        self._selected_label.configure(text=label)

        current_key = assignments.get((info.slide_index, info.shape_name), "")
        self._key_var.set(current_key)
        self._key_entry.focus_set()
        self._key_entry.selection_range(0, tk.END)

    def _apply_assignment(self) -> None:
        if self._selected_row is None:
            return
        shapes = self._existing_shapes if self._active_tab == "existing" else self._new_shapes
        assignments = self._existing_assignments if self._active_tab == "existing" else self._new_assignments
        tree = self._existing_tree if self._active_tab == "existing" else self._new_tree

        info = shapes[self._selected_row]
        key_raw = self._key_var.get().strip()
        key = _normalize_input_key(key_raw)

        shape_key = (info.slide_index, info.shape_name)
        if key:
            assignments[shape_key] = key
        else:
            assignments.pop(shape_key, None)

        self._refresh_tree(tree, shapes, assignments)
        tree.selection_set(str(self._selected_row))
        tree.see(str(self._selected_row))
        self._update_count()

    def _clear_assignment(self) -> None:
        self._key_var.set("")
        self._apply_assignment()

    def _update_count(self) -> None:
        ex = len(self._existing_assignments)
        nw = len(self._new_assignments)
        self._count_var.set(f"{ex} existing / {nw} new anchor(s) assigned")

    def get_assignments(self) -> tuple[
        dict[tuple[int, str], str],
        dict[tuple[int, str], str],
    ]:
        return self._existing_assignments, self._new_assignments

    def _handle_back(self) -> None:
        if self._on_back:
            self._on_back()

    def _handle_continue(self) -> None:
        if self._on_continue:
            self._on_continue()


def _normalize_input_key(raw: str) -> str:
    import re
    return re.sub(r"[^\w]", "_", raw).strip("_")
