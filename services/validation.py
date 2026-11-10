"""Validation helpers and warning generation."""

from __future__ import annotations

from models.anchor_mapping import AnchorMapping
from models.anchor_record import AnchorRecord


def validate_anchors(anchors: list[AnchorRecord], label: str) -> list[str]:
    warnings: list[str] = []
    key_counts: dict[str, int] = {}
    for a in anchors:
        key_counts[a.anchor_key] = key_counts.get(a.anchor_key, 0) + 1
    for key, count in key_counts.items():
        if count > 1:
            warnings.append(
                f"[{label}] Duplicate anchor key '{key}' found {count} times"
            )
    return warnings


def validate_mappings(mappings: list[AnchorMapping]) -> list[str]:
    warnings: list[str] = []

    for m in mappings:
        if m.existing_anchor and not m.new_anchor:
            warnings.append(
                f"Anchor '{m.anchor_key}' exists in old template but has no match in new template"
            )
        elif m.new_anchor and not m.existing_anchor:
            warnings.append(
                f"Anchor '{m.anchor_key}' exists in new template but has no match in old template"
            )

    key_counts: dict[str, int] = {}
    for m in mappings:
        key_counts[m.anchor_key] = key_counts.get(m.anchor_key, 0) + 1
    for key, count in key_counts.items():
        if count > 1:
            warnings.append(
                f"Duplicate mapping key '{key}' appears {count} times in mapping list"
            )

    selected = [m for m in mappings if m.include_in_test]
    no_new = [m for m in selected if not m.new_anchor]
    for m in no_new:
        warnings.append(
            f"Anchor '{m.anchor_key}' is selected for test but has no new-template target"
        )

    return warnings


def validate_pre_test(mappings: list[AnchorMapping]) -> list[str]:
    warnings: list[str] = []
    selected = [m for m in mappings if m.include_in_test]
    empty_vals = [m for m in selected if not m.test_value.strip()]
    if empty_vals:
        keys = ", ".join(m.anchor_key for m in empty_vals[:5])
        suffix = f" and {len(empty_vals) - 5} more" if len(empty_vals) > 5 else ""
        warnings.append(f"Selected anchors with empty test values: {keys}{suffix}")
    return warnings


def verify_readback(output_path: str, mappings: list[AnchorMapping]) -> list[str]:
    from pptx import Presentation

    warnings: list[str] = []
    selected = [m for m in mappings if m.include_in_test and m.test_value.strip() and m.new_anchor]

    if not selected:
        return warnings

    try:
        prs = Presentation(output_path)
    except Exception as exc:
        warnings.append(f"Readback verification failed: could not open output file - {exc}")
        return warnings

    shape_texts: dict[tuple[int, str], str] = {}
    for slide_index, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.has_text_frame:
                shape_texts[(slide_index, shape.name or "")] = shape.text_frame.text

    for m in selected:
        anchor = m.new_anchor
        key = (anchor.slide_index, anchor.shape_name)
        actual = shape_texts.get(key, "")
        expected = m.test_value.strip()
        if expected not in actual:
            warnings.append(
                f"Readback mismatch for '{m.anchor_key}': "
                f"expected '{expected[:40]}' not found in shape text"
            )

    return warnings
