"""Detect anchors in a PPTX presentation."""

from __future__ import annotations

import re

from models.anchor_record import AnchorRecord
from services.pptx_reader import (
    open_presentation,
    iter_shapes,
    get_shape_text,
    get_shape_alt_text,
    get_shape_bounds,
)

_SLOT_RE = re.compile(r"slot:(\w+)")
_CURLY_RE = re.compile(r"\{\{(\w+)\}\}")


def normalize_key(raw: str) -> str | None:
    m = _SLOT_RE.search(raw)
    if m:
        return m.group(1)
    m = _CURLY_RE.search(raw)
    if m:
        return m.group(1)
    return None


def detect_anchors(path: str) -> list[AnchorRecord]:
    prs = open_presentation(path)
    records: list[AnchorRecord] = []
    seen: set[tuple[int, str, str]] = set()

    for slide_index, shape in iter_shapes(prs):
        left, top, width, height = get_shape_bounds(shape)
        shape_name = shape.name or ""
        visible_text = get_shape_text(shape)
        alt_text = get_shape_alt_text(shape)

        key = normalize_key(shape_name)
        if key:
            dedup = (slide_index, key, "shape_name")
            if dedup not in seen:
                seen.add(dedup)
                records.append(AnchorRecord(
                    anchor_key=key,
                    slide_index=slide_index,
                    shape_name=shape_name,
                    detection_source="shape_name",
                    visible_text=visible_text,
                    left=left, top=top, width=width, height=height,
                ))

        key = normalize_key(alt_text)
        if key:
            dedup = (slide_index, key, "alt_text")
            if dedup not in seen:
                seen.add(dedup)
                records.append(AnchorRecord(
                    anchor_key=key,
                    slide_index=slide_index,
                    shape_name=shape_name,
                    detection_source="alt_text",
                    visible_text=visible_text,
                    left=left, top=top, width=width, height=height,
                ))

        for m in _CURLY_RE.finditer(visible_text):
            vkey = m.group(1)
            dedup = (slide_index, vkey, "visible_text")
            if dedup not in seen:
                seen.add(dedup)
                records.append(AnchorRecord(
                    anchor_key=vkey,
                    slide_index=slide_index,
                    shape_name=shape_name,
                    detection_source="visible_text",
                    visible_text=visible_text,
                    left=left, top=top, width=width, height=height,
                ))

    _flag_duplicates(records)
    return records


def _flag_duplicates(records: list[AnchorRecord]) -> None:
    key_counts: dict[str, int] = {}
    for r in records:
        key_counts[r.anchor_key] = key_counts.get(r.anchor_key, 0) + 1
    for r in records:
        if key_counts[r.anchor_key] > 1:
            r.notes.append(f"duplicate key ({key_counts[r.anchor_key]} occurrences)")
