"""Anchor mapping view with table, manual remap, and include/exclude controls."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from models.anchor_mapping import AnchorMapping
from models.anchor_record import AnchorRecord
from services.anchor_mapper import get_match_status


class MappingViewFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, on_back=None, on_continue=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._on_continue = on_continue
        self._mappings: list[AnchorMapping] = []
        self._existing_anchors: list[AnchorRecord] = []
        self._new_anchors: list[AnchorRecord] = []
        self._check_vars: dict[int, tk.BooleanVar] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Anchor Mapping", font=("TkDefaultFont", 14, "bold"))
        header.pack(pady=(10, 2))

        self._summary_var = tk.StringVar()
        ttk.Label(self, textvariable=self._summary_var, foreground="gray").pack(pady=(0, 6))

        top_btn = ttk.Frame(self)
        top_btn.pack(fill=tk.X, padx=8)
        ttk.Button(top_btn, text="Select All", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_btn, text="Select None", command=self._select_none).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_btn, text="Select Matched Only", command=self._select_matched).pack(side=tk.LEFT, padx=2)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        cols = ("include", "key", "status", "ex_slide", "ex_shape", "ex_source",
                "new_slide", "new_shape", "new_source", "notes")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)

        self._tree.heading("include", text="Test")
        self._tree.heading("key", text="Anchor Key")
        self._tree.heading("status", text="Match Status")
        self._tree.heading("ex_slide", text="Ex Slide")
        self._tree.heading("ex_shape", text="Ex Shape")
        self._tree.heading("ex_source", text="Ex Source")
        self._tree.heading("new_slide", text="New Slide")
        self._tree.heading("new_shape", text="New Shape")
        self._tree.heading("new_source", text="New Source")
        self._tree.heading("notes", text="Notes")

        self._tree.column("include", width=40, minwidth=40, anchor=tk.CENTER)
        self._tree.column("key", width=110, minwidth=80)
        self._tree.column("status", width=95, minwidth=70)
        self._tree.column("ex_slide", width=55, minwidth=40, anchor=tk.CENTER)
        self._tree.column("ex_shape", width=110, minwidth=60)
        self._tree.column("ex_source", width=80, minwidth=55)
        self._tree.column("new_slide", width=60, minwidth=40, anchor=tk.CENTER)
        self._tree.column("new_shape", width=110, minwidth=60)
        self._tree.column("new_source", width=80, minwidth=55)
        self._tree.column("notes", width=120, minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._tree.bind("<Double-1>", self._on_double_click)

        detail_frame = ttk.LabelFrame(self, text="Selected Mapping Detail / Manual Remap", padding=8)
        detail_frame.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(detail_frame, text="Anchor Key:").grid(row=0, column=0, sticky=tk.W, padx=4)
        self._detail_key_var = tk.StringVar()
        ttk.Label(detail_frame, textvariable=self._detail_key_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=1, sticky=tk.W, padx=4)

        ttk.Label(detail_frame, text="Existing Anchor:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        self._existing_combo_var = tk.StringVar()
        self._existing_combo = ttk.Combobox(detail_frame, textvariable=self._existing_combo_var,
                                             state="readonly", width=50)
        self._existing_combo.grid(row=1, column=1, sticky=tk.EW, padx=4, pady=2)

        ttk.Label(detail_frame, text="New Anchor:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        self._new_combo_var = tk.StringVar()
        self._new_combo = ttk.Combobox(detail_frame, textvariable=self._new_combo_var,
                                        state="readonly", width=50)
        self._new_combo.grid(row=2, column=1, sticky=tk.EW, padx=4, pady=2)

        self._include_var = tk.BooleanVar()
        ttk.Checkbutton(detail_frame, text="Include in test", variable=self._include_var).grid(
            row=3, column=1, sticky=tk.W, padx=4, pady=2)

        ttk.Button(detail_frame, text="Apply Changes", command=self._apply_remap).grid(
            row=4, column=1, sticky=tk.W, padx=4, pady=4)

        detail_frame.columnconfigure(1, weight=1)

        self._selected_idx: int | None = None

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Back to Detection", command=self._handle_back).pack(side=tk.LEFT, padx=4)
        self._continue_btn = ttk.Button(btn_frame, text="Continue to Testing",
                                         command=self._handle_continue, state=tk.DISABLED)
        self._continue_btn.pack(side=tk.LEFT, padx=4)

    def load_mappings(
        self,
        mappings: list[AnchorMapping],
        existing_anchors: list[AnchorRecord],
        new_anchors: list[AnchorRecord],
    ) -> None:
        self._mappings = mappings
        self._existing_anchors = existing_anchors
        self._new_anchors = new_anchors
        self._check_vars.clear()

        ex_labels = ["(none)"] + [
            f"{a.anchor_key} [slide {a.slide_index+1}, {a.shape_name}]" for a in existing_anchors
        ]
        new_labels = ["(none)"] + [
            f"{a.anchor_key} [slide {a.slide_index+1}, {a.shape_name}]" for a in new_anchors
        ]
        self._existing_combo["values"] = ex_labels
        self._new_combo["values"] = new_labels

        self._refresh_tree()
        self._update_summary()
        self._continue_btn.configure(state=tk.NORMAL)

    def _refresh_tree(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, m in enumerate(self._mappings):
            inc = "Y" if m.include_in_test else "-"
            status = get_match_status(m)
            ex_slide = str(m.existing_anchor.slide_index + 1) if m.existing_anchor else "-"
            ex_shape = m.existing_anchor.shape_name if m.existing_anchor else "-"
            ex_src = m.existing_anchor.detection_source if m.existing_anchor else "-"
            new_slide = str(m.new_anchor.slide_index + 1) if m.new_anchor else "-"
            new_shape = m.new_anchor.shape_name if m.new_anchor else "-"
            new_src = m.new_anchor.detection_source if m.new_anchor else "-"
            notes = "; ".join(m.notes)

            tag = "matched" if status == "Matched" else "unmatched"
            self._tree.insert("", tk.END, iid=str(i), values=(
                inc, m.anchor_key, status,
                ex_slide, ex_shape, ex_src,
                new_slide, new_shape, new_src,
                notes,
            ), tags=(tag,))

        self._tree.tag_configure("matched", background="#e8f5e9")
        self._tree.tag_configure("unmatched", background="#fff3e0")

    def _update_summary(self) -> None:
        matched = sum(1 for m in self._mappings if m.existing_anchor and m.new_anchor)
        ex_only = sum(1 for m in self._mappings if m.existing_anchor and not m.new_anchor)
        new_only = sum(1 for m in self._mappings if not m.existing_anchor and m.new_anchor)
        included = sum(1 for m in self._mappings if m.include_in_test)
        self._summary_var.set(
            f"Matched: {matched}  |  Existing only: {ex_only}  |  New only: {new_only}"
            f"  |  Selected for test: {included}"
        )

    def _on_double_click(self, event) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        col_region = self._tree.identify_region(event.x, event.y)
        col = self._tree.identify_column(event.x)

        if col == "#1":
            m = self._mappings[idx]
            m.include_in_test = not m.include_in_test
            self._refresh_tree()
            self._tree.selection_set(str(idx))
            self._update_summary()
            return

        self._load_detail(idx)

    def _load_detail(self, idx: int) -> None:
        self._selected_idx = idx
        m = self._mappings[idx]
        self._detail_key_var.set(m.anchor_key)
        self._include_var.set(m.include_in_test)

        if m.existing_anchor:
            label = f"{m.existing_anchor.anchor_key} [slide {m.existing_anchor.slide_index+1}, {m.existing_anchor.shape_name}]"
            self._existing_combo_var.set(label)
        else:
            self._existing_combo_var.set("(none)")

        if m.new_anchor:
            label = f"{m.new_anchor.anchor_key} [slide {m.new_anchor.slide_index+1}, {m.new_anchor.shape_name}]"
            self._new_combo_var.set(label)
        else:
            self._new_combo_var.set("(none)")

    def _apply_remap(self) -> None:
        if self._selected_idx is None:
            return
        m = self._mappings[self._selected_idx]

        ex_val = self._existing_combo_var.get()
        if ex_val == "(none)":
            m.existing_anchor = None
        else:
            for a in self._existing_anchors:
                label = f"{a.anchor_key} [slide {a.slide_index+1}, {a.shape_name}]"
                if label == ex_val:
                    m.existing_anchor = a
                    break

        new_val = self._new_combo_var.get()
        if new_val == "(none)":
            m.new_anchor = None
        else:
            for a in self._new_anchors:
                label = f"{a.anchor_key} [slide {a.slide_index+1}, {a.shape_name}]"
                if label == new_val:
                    m.new_anchor = a
                    break

        m.include_in_test = self._include_var.get()

        if "auto-matched" in m.notes:
            m.notes = [n for n in m.notes if n != "auto-matched"]
            m.notes.append("manually remapped")

        self._refresh_tree()
        self._tree.selection_set(str(self._selected_idx))
        self._update_summary()

    def _select_all(self) -> None:
        for m in self._mappings:
            m.include_in_test = True
        self._refresh_tree()
        self._update_summary()

    def _select_none(self) -> None:
        for m in self._mappings:
            m.include_in_test = False
        self._refresh_tree()
        self._update_summary()

    def _select_matched(self) -> None:
        for m in self._mappings:
            m.include_in_test = bool(m.existing_anchor and m.new_anchor)
        self._refresh_tree()
        self._update_summary()

    def get_mappings(self) -> list[AnchorMapping]:
        return self._mappings

    def _handle_back(self) -> None:
        if self._on_back:
            self._on_back()

    def _handle_continue(self) -> None:
        if self._on_continue:
            self._on_continue()
