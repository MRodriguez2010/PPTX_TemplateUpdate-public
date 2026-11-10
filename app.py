#!/usr/bin/env python3
"""PPTX TemplateUpdate - main entry point."""

import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui.main_window import MainWindow
from ui.template_selection import TemplateSelectionFrame
from ui.element_browser import ElementBrowserFrame
from ui.mapping_view import MappingViewFrame
from ui.testing_view import TestingViewFrame
from ui.results_view import ResultsViewFrame
from services.anchor_detector import detect_anchors
from services.anchor_mapper import build_mappings
from services.test_writer import run_test, generate_output_path
from services.validation import validate_anchors, validate_mappings, validate_pre_test, verify_readback
from services.anchor_assigner import (
    build_shape_list,
    assignments_to_anchor_records,
    bake_assignments_into_pptx,
)

OUTPUT_DIR = str(Path(__file__).resolve().parent / "outputs")


class App:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.window = MainWindow(self.root)

        self.existing_anchors = []
        self.new_anchors = []
        self.mappings = []
        self.new_template_path = ""
        self.existing_path = ""
        self._existing_assignments: dict[tuple[int, str], str] = {}
        self._new_assignments: dict[tuple[int, str], str] = {}

        self.selection = TemplateSelectionFrame(self.root, on_load_anchors=self._on_load_anchors)
        self.element_browser = ElementBrowserFrame(
            self.root,
            on_back=lambda: self.window.show_frame("selection"),
            on_continue=self._on_continue_to_mapping,
        )
        self.mapping = MappingViewFrame(
            self.root,
            on_back=lambda: self.window.show_frame("element_browser"),
            on_continue=self._on_continue_to_testing,
        )
        self.testing = TestingViewFrame(
            self.root,
            on_back=lambda: self.window.show_frame("mapping"),
            on_run_test=self._on_run_test,
        )
        self.results = ResultsViewFrame(
            self.root,
            on_back_to_testing=lambda: self.window.show_frame("testing"),
            on_start_over=lambda: self.window.show_frame("selection"),
        )

        self.window.register_frame("selection", self.selection)
        self.window.register_frame("element_browser", self.element_browser)
        self.window.register_frame("mapping", self.mapping)
        self.window.register_frame("testing", self.testing)
        self.window.register_frame("results", self.results)

        self.window.show_frame("selection")

    def _on_load_anchors(self, existing_path: str, new_path: str) -> None:
        self.existing_path = existing_path
        self.new_template_path = new_path

        self.window.set_status("Detecting anchors and loading shapes...")
        self.root.update_idletasks()

        try:
            self.existing_anchors = detect_anchors(existing_path)
            self.new_anchors = detect_anchors(new_path)
        except Exception as exc:
            messagebox.showerror("Detection Error", f"Failed to detect anchors:\n{exc}")
            self.selection._status_var.set("Detection failed.")
            return

        try:
            existing_shapes = build_shape_list(existing_path)
            new_shapes = build_shape_list(new_path)
        except Exception as exc:
            messagebox.showerror("Load Error", f"Failed to load shapes:\n{exc}")
            self.selection._status_var.set("Shape loading failed.")
            return

        anchor_warnings = validate_anchors(self.existing_anchors, "Existing")
        anchor_warnings += validate_anchors(self.new_anchors, "New")

        total_anchors = len(self.existing_anchors) + len(self.new_anchors)
        total_shapes = len(existing_shapes) + len(new_shapes)
        status = (
            f"Loaded {total_shapes} shapes. "
            f"Auto-detected {len(self.existing_anchors)} existing / {len(self.new_anchors)} new anchor(s)."
        )
        if total_anchors == 0:
            self.window.set_status(
                "No anchors auto-detected. Assign anchor keys to shapes on the Element Browser."
            )
        elif anchor_warnings:
            status += f" ({len(anchor_warnings)} warning(s))"
            self.window.set_status("; ".join(anchor_warnings))
        else:
            self.window.set_status("Shapes loaded. Auto-detected anchors are pre-filled (blue).")
        self.selection._status_var.set(status)

        self.element_browser.load(
            existing_shapes,
            new_shapes,
            self.existing_anchors,
            self.new_anchors,
            self._existing_assignments,
            self._new_assignments,
        )
        self.window.show_frame("element_browser")

    def _on_continue_to_mapping(self) -> None:
        self._existing_assignments, self._new_assignments = self.element_browser.get_assignments()

        existing_shapes = self.element_browser._existing_shapes
        new_shapes = self.element_browser._new_shapes

        assigned_existing = assignments_to_anchor_records(existing_shapes, self._existing_assignments)
        assigned_new = assignments_to_anchor_records(new_shapes, self._new_assignments)

        auto_existing_keys = {(a.slide_index, a.shape_name) for a in self.existing_anchors}
        auto_new_keys = {(a.slide_index, a.shape_name) for a in self.new_anchors}

        merged_existing = list(self.existing_anchors) + [
            a for a in assigned_existing
            if (a.slide_index, a.shape_name) not in auto_existing_keys
        ]
        merged_new = list(self.new_anchors) + [
            a for a in assigned_new
            if (a.slide_index, a.shape_name) not in auto_new_keys
        ]

        self.mappings = build_mappings(merged_existing, merged_new)
        mapping_warnings = validate_mappings(self.mappings)
        total_assigned = len(self._existing_assignments) + len(self._new_assignments)
        if mapping_warnings:
            self.window.set_status(f"{len(mapping_warnings)} mapping warning(s): {mapping_warnings[0]}")
        else:
            self.window.set_status(f"Mappings built from {total_assigned} assigned anchor(s).")
        self.mapping.load_mappings(self.mappings, merged_existing, merged_new)
        self.window.show_frame("mapping")

    def _on_continue_to_testing(self) -> None:
        self.mappings = self.mapping.get_mappings()
        selected = [m for m in self.mappings if m.include_in_test]
        if not selected:
            messagebox.showwarning("No Anchors Selected", "Select at least one anchor for testing.")
            return
        self.testing.load_mappings(self.mappings)
        self.window.show_frame("testing")

    def _on_run_test(self) -> None:
        self.mappings = self.testing.get_mappings_with_values()

        has_values = any(m.test_value.strip() for m in self.mappings)
        if not has_values:
            messagebox.showwarning("No Test Values", "Enter at least one test value before running.")
            return

        pre_warnings = validate_pre_test(self.mappings)

        Path(OUTPUT_DIR).mkdir(exist_ok=True)
        output_path = generate_output_path(self.new_template_path, OUTPUT_DIR)

        self.window.set_status("Writing test output...")
        self.root.update_idletasks()

        try:
            result = run_test(self.new_template_path, output_path, self.mappings)
        except Exception as exc:
            messagebox.showerror("Test Error", f"Failed to write test output:\n{exc}")
            self.window.set_status("Test failed.")
            return

        result.warnings.extend(pre_warnings)

        self.window.set_status("Verifying output...")
        self.root.update_idletasks()
        readback_warnings = verify_readback(output_path, self.mappings)
        result.warnings.extend(readback_warnings)

        if self._new_assignments:
            self.window.set_status("Baking anchor assignments into output...")
            self.root.update_idletasks()
            try:
                bake_assignments_into_pptx(output_path, output_path, self._new_assignments)
                result.warnings.append(
                    f"Anchor assignments baked into output: {len(self._new_assignments)} shape(s) "
                    f"tagged with slot: alt text for future auto-detection."
                )
            except Exception as exc:
                result.warnings.append(f"Anchor bake-in failed: {exc}")

        self.window.set_status(
            f"Test complete: {result.written_count} written, "
            f"{len(result.warnings)} warning(s), {len(result.failures)} failure(s)"
        )

        self.results.load_results(result)
        self.window.show_frame("results")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
