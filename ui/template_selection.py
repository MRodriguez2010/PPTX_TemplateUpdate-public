import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path


class TemplateSelectionFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, on_load_anchors=None) -> None:
        super().__init__(parent)
        self._on_load_anchors = on_load_anchors

        self._existing_path = tk.StringVar()
        self._new_path = tk.StringVar()

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        header = ttk.Label(self, text="PPTX TemplateUpdate", font=("TkDefaultFont", 16, "bold"))
        header.pack(pady=(24, 4))

        subtitle = ttk.Label(self, text="Select templates to compare and test anchor mappings.")
        subtitle.pack(pady=(0, 20))

        file_frame = ttk.LabelFrame(self, text="Template Files", padding=12)
        file_frame.pack(fill=tk.X, **pad)

        ttk.Label(file_frame, text="Existing Template:").grid(row=0, column=0, sticky=tk.W, pady=4)
        existing_entry = ttk.Entry(file_frame, textvariable=self._existing_path, width=60)
        existing_entry.grid(row=0, column=1, sticky=tk.EW, padx=(8, 4), pady=4)
        ttk.Button(file_frame, text="Browse...", command=self._browse_existing).grid(row=0, column=2, pady=4)

        ttk.Label(file_frame, text="New Template:").grid(row=1, column=0, sticky=tk.W, pady=4)
        new_entry = ttk.Entry(file_frame, textvariable=self._new_path, width=60)
        new_entry.grid(row=1, column=1, sticky=tk.EW, padx=(8, 4), pady=4)
        ttk.Button(file_frame, text="Browse...", command=self._browse_new).grid(row=1, column=2, pady=4)

        file_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        self._load_btn = ttk.Button(btn_frame, text="Load Anchors", command=self._handle_load)
        self._load_btn.pack()

        self._status_var = tk.StringVar()
        ttk.Label(self, textvariable=self._status_var, foreground="gray").pack(pady=(0, 12))

    def _browse_existing(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Existing Template",
            filetypes=[("PowerPoint files", "*.pptx"), ("All files", "*.*")],
        )
        if path:
            self._existing_path.set(path)

    def _browse_new(self) -> None:
        path = filedialog.askopenfilename(
            title="Select New Template",
            filetypes=[("PowerPoint files", "*.pptx"), ("All files", "*.*")],
        )
        if path:
            self._new_path.set(path)

    def _handle_load(self) -> None:
        existing = self._existing_path.get().strip()
        new = self._new_path.get().strip()

        if not existing or not new:
            messagebox.showwarning("Missing file", "Please select both an existing and a new template.")
            return

        if not Path(existing).is_file():
            messagebox.showerror("File not found", f"Existing template not found:\n{existing}")
            return

        if not Path(new).is_file():
            messagebox.showerror("File not found", f"New template not found:\n{new}")
            return

        self._status_var.set("Loading anchors...")

        if self._on_load_anchors:
            self._on_load_anchors(existing, new)
        else:
            self._status_var.set("Anchor detection not yet implemented (Phase 2).")

    @property
    def existing_path(self) -> str:
        return self._existing_path.get().strip()

    @property
    def new_path(self) -> str:
        return self._new_path.get().strip()
