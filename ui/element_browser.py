"""Element Browser screen.

Shown after Load Anchors. Displays ALL shapes from both templates grouped by
slide. Auto-detected anchors are pre-filled. Users can assign/edit anchor keys
for any shape. Continue goes directly to Mapping.
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from models.anchor_record import AnchorRecord
from services.anchor_assigner import ShapeInfo


class ElementBrowserFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, on_back=None, on_continue=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._on_continue = on_continue

        self._existing_shapes: list[ShapeInfo] = []
        self._new_shapes: list[ShapeInfo] = []

        self._existing_assignments: dict[tuple[int, str], str] = {}
        self._new_assignments: dict[tuple[int, str], str] = {}

        self._active_tab = "existing"
        self._selected_iid: str | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Label(
            self, text="Element Browser & Anchor Assignment",
            font=("TkDefaultFont", 14, "bold"),
        )
        header.pack(pady=(10, 2))

        self._summary_var = tk.StringVar()
        ttk.Label(self, textvariable=self._summary_var, foreground="gray").pack(pady=(0, 4))

        self._banner_var = tk.StringVar()
        self._banner_label = tk.Label(
            self,
            textvariable=self._banner_var,
            bg="#fff3cd",
            fg="#856404",
            font=("TkDefaultFont", 10, "bold"),
            wraplength=700,
            justify=tk.LEFT,
            anchor=tk.W,
            relief=tk.FLAT,
            padx=12,
            pady=6,
        )
        self._banner_label.pack(fill=tk.X, padx=8, pady=(0, 2))

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
        self._selected_label.grid(row=0, column=1, columnspan=4, sticky=tk.W, padx=4)

        ttk.Label(assign_frame, text="Anchor Key:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self._key_var = tk.StringVar()
        self._key_entry = ttk.Entry(assign_frame, textvariable=self._key_var, width=40)
        self._key_entry.grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)
        self._key_entry.bind("<Return>", lambda e: self._apply_assignment())

        ttk.Button(assign_frame, text="Assign", command=self._apply_assignment).grid(
            row=1, column=2, padx=6, pady=4)
        ttk.Button(assign_frame, text="Anchor from Shape", command=self._anchor_from_shape).grid(
            row=1, column=3, padx=6, pady=4)
        ttk.Button(assign_frame, text="Clear", command=self._clear_assignment).grid(
            row=1, column=4, padx=2, pady=4)

        ttk.Button(assign_frame, text="Anchor All from Shape", command=self._anchor_all_from_shape).grid(
            row=2, column=3, padx=6, pady=2)

        self._count_var = tk.StringVar(value="0 anchors assigned")
        ttk.Label(assign_frame, textvariable=self._count_var, foreground="gray").grid(
            row=3, column=0, columnspan=5, sticky=tk.W, padx=4)

        assign_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Back to Selection", command=self._handle_back).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(
            btn_frame, text="Continue to Mapping \u2192", command=self._handle_continue,
        ).pack(side=tk.LEFT, padx=4)

    def _build_tab(self, parent: ttk.Frame, which: str) -> ttk.Treeview:
        cols = ("anchor", "name", "text")
        tree = ttk.Treeview(parent, columns=cols, show="tree headings", height=16,
                            selectmode="extended")

        tree.heading("#0", text="Slide / Shape")
        tree.heading("anchor", text="Anchor Key")
        tree.heading("name", text="Shape Name")
        tree.heading("text", text="Visible Text")

        tree.column("#0", width=180, minwidth=120)
        tree.column("anchor", width=130, minwidth=80)
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
        tree.tag_configure("auto", background="#e3f2fd")
        tree.tag_configure("slide_header", background="#f5f5f5")

        return tree

    def load(
        self,
        existing_shapes: list[ShapeInfo],
        new_shapes: list[ShapeInfo],
        existing_anchors: list[AnchorRecord],
        new_anchors: list[AnchorRecord],
        existing_assignments: dict[tuple[int, str], str] | None = None,
        new_assignments: dict[tuple[int, str], str] | None = None,
    ) -> None:
        self._existing_shapes = existing_shapes
        self._new_shapes = new_shapes

        self._existing_assignments = dict(existing_assignments) if existing_assignments else {}
        self._new_assignments = dict(new_assignments) if new_assignments else {}

        self._prefill_from_anchors(existing_shapes, existing_anchors, self._existing_assignments)
        self._prefill_from_anchors(new_shapes, new_anchors, self._new_assignments)

        self._selected_iid = None
        self._selected_label.configure(text="(none)")
        self._key_var.set("")

        self._refresh_tree(self._existing_tree, existing_shapes, self._existing_assignments, existing_anchors)
        self._refresh_tree(self._new_tree, new_shapes, self._new_assignments, new_anchors)
        self._update_counts(existing_anchors, new_anchors)

    def _prefill_from_anchors(
        self,
        shapes: list[ShapeInfo],
        anchors: list[AnchorRecord],
        assignments: dict[tuple[int, str], str],
    ) -> None:
        anchor_lookup: dict[tuple[int, str], str] = {}
        for a in anchors:
            anchor_lookup[(a.slide_index, a.shape_name)] = a.anchor_key
        for info in shapes:
            key = (info.slide_index, info.shape_name)
            if key in anchor_lookup and key not in assignments:
                assignments[key] = anchor_lookup[key]

    def _refresh_tree(
        self,
        tree: ttk.Treeview,
        shapes: list[ShapeInfo],
        assignments: dict[tuple[int, str], str],
        anchors: list[AnchorRecord],
    ) -> None:
        for item in tree.get_children():
            tree.delete(item)

        auto_keys = {(a.slide_index, a.shape_name) for a in anchors}

        slides: dict[int, list[int]] = {}
        for i, info in enumerate(shapes):
            slides.setdefault(info.slide_index, []).append(i)

        for slide_idx in sorted(slides):
            slide_iid = f"slide_{slide_idx}"
            shape_indices = slides[slide_idx]
            assigned_on_slide = sum(
                1 for idx in shape_indices
                if assignments.get((shapes[idx].slide_index, shapes[idx].shape_name))
            )
            slide_label = f"Slide {slide_idx + 1}  ({len(shape_indices)} shapes, {assigned_on_slide} anchors)"
            tree.insert("", tk.END, iid=slide_iid, text=slide_label, open=True,
                        values=("", "", ""), tags=("slide_header",))

            for idx in shape_indices:
                info = shapes[idx]
                shape_key = (info.slide_index, info.shape_name)
                ak = assignments.get(shape_key, "")
                text_preview = info.visible_text[:80].replace("\n", " ")

                if ak and shape_key in auto_keys:
                    tag = "auto"
                elif ak:
                    tag = "assigned"
                else:
                    tag = ""

                tree.insert(
                    slide_iid, tk.END,
                    iid=str(idx),
                    text="",
                    values=(ak, info.shape_name, text_preview),
                    tags=(tag,) if tag else (),
                )

    def _update_counts(
        self,
        existing_anchors: list[AnchorRecord],
        new_anchors: list[AnchorRecord],
    ) -> None:
        ex_assigned = len(self._existing_assignments)
        nw_assigned = len(self._new_assignments)
        auto_ex = len(existing_anchors)
        auto_nw = len(new_anchors)
        total_shapes = len(self._existing_shapes) + len(self._new_shapes)

        self._summary_var.set(
            f"{total_shapes} total shapes  |  "
            f"Auto-detected: {auto_ex} existing / {auto_nw} new  |  "
            f"Assigned: {ex_assigned} existing / {nw_assigned} new"
        )

        self._count_var.set(
            f"{ex_assigned} existing + {nw_assigned} new = {ex_assigned + nw_assigned} total anchor(s) assigned"
        )

        if auto_ex + auto_nw == 0:
            self._banner_var.set(
                "\u26a0\ufe0f  No anchors were auto-detected. Select any shape below and "
                "type an anchor key to assign it. Blue = auto-detected, Green = manually assigned."
            )
        else:
            self._banner_var.set("")

    def _on_tab_change(self, event) -> None:
        idx = self._notebook.index("current")
        self._active_tab = "existing" if idx == 0 else "new"
        self._selected_iid = None
        self._selected_label.configure(text="(none)")
        self._key_var.set("")

    def _on_select(self, which: str) -> None:
        tree = self._existing_tree if which == "existing" else self._new_tree
        shapes = self._existing_shapes if which == "existing" else self._new_shapes
        assignments = self._existing_assignments if which == "existing" else self._new_assignments

        sel = tree.selection()
        if not sel:
            return

        shape_iids = [s for s in sel if not s.startswith("slide_")]
        if not shape_iids:
            self._selected_iid = None
            self._selected_label.configure(text="(slide group — select a shape)")
            self._key_var.set("")
            return

        self._active_tab = which

        if len(shape_iids) == 1:
            iid = shape_iids[0]
            try:
                idx = int(iid)
            except ValueError:
                return
            self._selected_iid = iid
            info = shapes[idx]
            label = f"Slide {info.slide_index + 1} | {info.shape_name}"
            if info.visible_text:
                label += f' | "{info.visible_text[:50].replace(chr(10), " ")}"'
            self._selected_label.configure(text=label)
            current_key = assignments.get((info.slide_index, info.shape_name), "")
            self._key_var.set(current_key)
            self._key_entry.focus_set()
            self._key_entry.selection_range(0, tk.END)
        else:
            self._selected_iid = shape_iids[0]
            self._selected_label.configure(text=f"{len(shape_iids)} shapes selected")
            self._key_var.set("")

    def _apply_assignment(self) -> None:
        if self._selected_iid is None:
            return
        try:
            idx = int(self._selected_iid)
        except ValueError:
            return

        shapes = self._existing_shapes if self._active_tab == "existing" else self._new_shapes
        assignments = self._existing_assignments if self._active_tab == "existing" else self._new_assignments
        tree = self._existing_tree if self._active_tab == "existing" else self._new_tree

        info = shapes[idx]
        key_raw = self._key_var.get().strip()
        key = _normalize_input_key(key_raw)

        shape_key = (info.slide_index, info.shape_name)
        if key:
            assignments[shape_key] = key
        else:
            assignments.pop(shape_key, None)

        self._refresh_tree(tree, shapes, assignments, [])
        tree.selection_set(self._selected_iid)
        tree.see(self._selected_iid)
        self._update_count_label()

    def _clear_assignment(self) -> None:
        self._key_var.set("")
        self._apply_assignment()

    def _anchor_from_shape(self) -> None:
        tree = self._existing_tree if self._active_tab == "existing" else self._new_tree
        shapes = self._existing_shapes if self._active_tab == "existing" else self._new_shapes
        assignments = self._existing_assignments if self._active_tab == "existing" else self._new_assignments

        sel = tree.selection()
        shape_iids = [s for s in sel if not s.startswith("slide_")]
        if not shape_iids:
            return

        for iid in shape_iids:
            try:
                idx = int(iid)
            except ValueError:
                continue
            info = shapes[idx]
            key = _normalize_input_key(info.shape_name)
            if key:
                assignments[(info.slide_index, info.shape_name)] = key

        self._refresh_tree(tree, shapes, assignments, [])
        tree.selection_set(shape_iids)
        tree.see(shape_iids[0])
        self._update_count_label()
        if len(shape_iids) == 1:
            idx = int(shape_iids[0])
            self._key_var.set(assignments.get(
                (shapes[idx].slide_index, shapes[idx].shape_name), ""))

    def _anchor_all_from_shape(self) -> None:
        shapes = self._existing_shapes if self._active_tab == "existing" else self._new_shapes
        assignments = self._existing_assignments if self._active_tab == "existing" else self._new_assignments
        tree = self._existing_tree if self._active_tab == "existing" else self._new_tree

        for info in shapes:
            key = _normalize_input_key(info.shape_name)
            if key:
                assignments[(info.slide_index, info.shape_name)] = key

        self._refresh_tree(tree, shapes, assignments, [])
        self._update_count_label()

    def _update_count_label(self) -> None:
        ex = len(self._existing_assignments)
        nw = len(self._new_assignments)
        self._count_var.set(f"{ex} existing + {nw} new = {ex + nw} total anchor(s) assigned")

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
    return re.sub(r"[^\w]", "_", raw).strip("_")
