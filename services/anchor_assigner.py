"""Anchor assignment service.

Handles:
  - Building a flat shape list from a PPTX for display in the assignment UI
  - Converting user assignments (slide_index, shape_name) -> anchor_key into AnchorRecords
  - Writing slot:<key> into shape alt text (cNvPr descr) so future loads auto-detect
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from pptx import Presentation

from models.anchor_record import AnchorRecord
from services.pptx_reader import open_presentation, iter_shapes, get_shape_text


@dataclass
class ShapeInfo:
    slide_index: int
    shape_name: str
    visible_text: str
    left: int
    top: int
    width: int
    height: int
    current_anchor_key: str = ""


def build_shape_list(path: str) -> list[ShapeInfo]:
    """Return a flat list of all shapes in the PPTX, suitable for assignment UI."""
    prs = open_presentation(path)
    shapes: list[ShapeInfo] = []
    for slide_index, shape in iter_shapes(prs):
        text = get_shape_text(shape)
        left = int(shape.left) if shape.left is not None else 0
        top = int(shape.top) if shape.top is not None else 0
        width = int(shape.width) if shape.width is not None else 0
        height = int(shape.height) if shape.height is not None else 0
        shapes.append(ShapeInfo(
            slide_index=slide_index,
            shape_name=shape.name or "",
            visible_text=text,
            left=left, top=top, width=width, height=height,
        ))
    return shapes


def assignments_to_anchor_records(
    shape_list: list[ShapeInfo],
    assignments: dict[tuple[int, str], str],
) -> list[AnchorRecord]:
    """Convert user assignments dict into AnchorRecord objects."""
    records: list[AnchorRecord] = []
    for info in shape_list:
        key = assignments.get((info.slide_index, info.shape_name))
        if not key:
            continue
        records.append(AnchorRecord(
            anchor_key=key,
            slide_index=info.slide_index,
            shape_name=info.shape_name,
            detection_source="assigned",
            visible_text=info.visible_text,
            left=info.left,
            top=info.top,
            width=info.width,
            height=info.height,
            notes=["manually assigned"],
        ))
    return records


def bake_assignments_into_pptx(
    pptx_path: str,
    output_path: str,
    assignments: dict[tuple[int, str], str],
) -> None:
    """Write slot:<key> into the alt text (cNvPr descr) of assigned shapes.

    Creates a copy at output_path with the annotations embedded so future
    runs of detect_anchors() will auto-detect them without manual assignment.
    If pptx_path == output_path the file is modified in place.
    """
    if pptx_path != output_path:
        shutil.copy2(pptx_path, output_path)

    prs = Presentation(output_path)

    for slide_index, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            anchor_key = assignments.get((slide_index, shape.name or ""))
            if not anchor_key:
                continue
            _set_shape_alt_text(shape, f"slot:{anchor_key}")

    prs.save(output_path)


def _set_shape_alt_text(shape, text: str) -> None:
    """Set the cNvPr descr attribute on a shape element."""
    el = shape._element
    for child in el.iter():
        tag = child.tag
        if tag.endswith("}cNvPr") or tag == "cNvPr":
            child.set("descr", text)
            return
