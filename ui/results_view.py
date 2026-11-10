"""Results view. Shows test run output summary, warnings, and failures."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

from services.test_writer import TestResult


class ResultsViewFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, on_back_to_testing=None, on_start_over=None) -> None:
        super().__init__(parent)
        self._on_back_to_testing = on_back_to_testing
        self._on_start_over = on_start_over
        self._output_path = ""
        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Test Results", font=("TkDefaultFont", 14, "bold"))
        header.pack(pady=(12, 4))

        self._status_var = tk.StringVar()
        ttk.Label(self, textvariable=self._status_var, font=("TkDefaultFont", 11)).pack(pady=(0, 8))

        summary_frame = ttk.LabelFrame(self, text="Summary", padding=8)
        summary_frame.pack(fill=tk.X, padx=12, pady=4)

        self._output_path_var = tk.StringVar()
        ttk.Label(summary_frame, text="Output file:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Label(summary_frame, textvariable=self._output_path_var, foreground="blue").grid(
            row=0, column=1, sticky=tk.W, padx=4, pady=2)

        self._selected_var = tk.StringVar()
        ttk.Label(summary_frame, text="Anchors selected:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Label(summary_frame, textvariable=self._selected_var).grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)

        self._written_var = tk.StringVar()
        ttk.Label(summary_frame, text="Successfully written:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Label(summary_frame, textvariable=self._written_var).grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)

        self._skipped_var = tk.StringVar()
        ttk.Label(summary_frame, text="Skipped/Failed:").grid(row=3, column=0, sticky=tk.W, padx=4, pady=2)
        ttk.Label(summary_frame, textvariable=self._skipped_var).grid(row=3, column=1, sticky=tk.W, padx=4, pady=2)

        summary_frame.columnconfigure(1, weight=1)

        log_frame = ttk.LabelFrame(self, text="Warnings & Failures", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        self._log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        vsb = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=vsb.set)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Open Output Folder", command=self._open_folder).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Back to Testing", command=self._handle_back).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Start Over", command=self._handle_start_over).pack(side=tk.LEFT, padx=4)

    def load_results(self, result: TestResult) -> None:
        self._output_path = result.output_path

        if result.failures:
            self._status_var.set("Test completed with errors")
        elif result.warnings:
            self._status_var.set("Test completed with warnings")
        else:
            self._status_var.set("Test completed successfully")

        self._output_path_var.set(result.output_path)
        self._selected_var.set(str(result.selected_count))
        self._written_var.set(str(result.written_count))
        self._skipped_var.set(str(result.skipped_count + len(result.failures)))

        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)

        if result.warnings:
            self._log_text.insert(tk.END, "WARNINGS:\n")
            for w in result.warnings:
                self._log_text.insert(tk.END, f"  - {w}\n")
            self._log_text.insert(tk.END, "\n")

        if result.failures:
            self._log_text.insert(tk.END, "FAILURES:\n")
            for f in result.failures:
                self._log_text.insert(tk.END, f"  - {f}\n")
            self._log_text.insert(tk.END, "\n")

        if not result.warnings and not result.failures:
            self._log_text.insert(tk.END, "No warnings or failures.\n")

        self._log_text.configure(state=tk.DISABLED)

    def _open_folder(self) -> None:
        folder = os.path.dirname(os.path.abspath(self._output_path)) if self._output_path else "."
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _handle_back(self) -> None:
        if self._on_back_to_testing:
            self._on_back_to_testing()

    def _handle_start_over(self) -> None:
        if self._on_start_over:
            self._on_start_over()
