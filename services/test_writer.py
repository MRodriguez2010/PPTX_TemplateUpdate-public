"""Write test values into the new template and produce output PPTX."""

from __future__ import annotations

import copy
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

from models.anchor_mapping import AnchorMapping
from services.anchor_detector import normalize_key, _CURLY_RE
from services.pptx_reader import _CellShapeProxy


def _iter_all_writable(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type is not None and shape.shape_type == 6:
            try:
                for child in _iter_all_writable(shape.shapes):
                    yield child
            except (AttributeError, TypeError):
                pass
        if shape.has_table:
            try:
                for row in shape.table.rows:
                    for cell in row.cells:
                        yield _CellShapeProxy(cell, shape)
            except (AttributeError, TypeError):
                pass


@dataclass
class TestResult:
    output_path: str = ""
    selected_count: int = 0
    written_count: int = 0
    skipped_count: int = 0
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def run_test(
    new_template_path: str,
    output_path: str,
    mappings: list[AnchorMapping],
) -> TestResult:
    result = TestResult(output_path=output_path)

    selected = [m for m in mappings if m.include_in_test and m.test_value]
    result.selected_count = len(selected)

    if not selected:
        result.warnings.append("No anchors with test values to write.")
        return result

    shutil.copy2(new_template_path, output_path)
    prs = Presentation(output_path)

    lookup: dict[tuple[int, str], AnchorMapping] = {}
    for m in selected:
        if m.new_anchor:
            key = (m.new_anchor.slide_index, m.new_anchor.shape_name)
            lookup[key] = m

    for slide_index, slide in enumerate(prs.slides):
        for shape in _iter_all_writable(slide.shapes):
            key = (slide_index, shape.name or "")
            mapping = lookup.get(key)
            if mapping is None:
                continue

            if not shape.has_text_frame:
                result.failures.append(
                    f"{mapping.anchor_key}: shape '{shape.name}' on slide {slide_index+1} has no text frame"
                )
                continue

            try:
                _write_text(shape, mapping, result)
                result.written_count += 1
            except Exception as exc:
                result.failures.append(
                    f"{mapping.anchor_key}: write failed on slide {slide_index+1} - {exc}"
                )

    result.skipped_count = result.selected_count - result.written_count

    prs.save(output_path)
    return result


def _write_text(shape, mapping: AnchorMapping, result: TestResult) -> None:
    tf = shape.text_frame
    new_text = mapping.test_value
    anchor = mapping.new_anchor
    detection = anchor.detection_source if anchor else "unknown"

    if detection == "visible_text":
        _replace_curly_placeholders(tf, mapping.anchor_key, new_text, result)
    else:
        _replace_all_text_preserving_format(tf, new_text, result, mapping.anchor_key)

    _check_overflow(shape, new_text, result, mapping.anchor_key)


def _replace_all_text_preserving_format(tf, new_text: str, result: TestResult, anchor_key: str) -> None:
    if not tf.paragraphs:
        result.warnings.append(f"{anchor_key}: no paragraphs found, writing plain text")
        tf.text = new_text
        return

    rPr_elem = None
    pPr_elem = None
    for para in tf.paragraphs:
        if pPr_elem is None:
            p_pPr = para._p.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}pPr"
            )
            if p_pPr is not None:
                pPr_elem = copy.deepcopy(p_pPr)
        for run in para.runs:
            r_rPr = run._r.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
            )
            if r_rPr is not None:
                rPr_elem = copy.deepcopy(r_rPr)
                break
        if rPr_elem is not None:
            break

    for i in range(len(tf.paragraphs) - 1, 0, -1):
        p_elem = tf.paragraphs[i]._p
        p_elem.getparent().remove(p_elem)

    first_para = tf.paragraphs[0]
    for run in list(first_para.runs)[1:]:
        first_para._p.remove(run._r)

    if first_para.runs:
        first_para.runs[0].text = new_text
        if rPr_elem is not None:
            existing_rPr = first_para.runs[0]._r.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
            )
            if existing_rPr is None:
                first_para.runs[0]._r.insert(0, rPr_elem)
    else:
        first_para.text = new_text
        if first_para.runs and rPr_elem is not None:
            existing_rPr = first_para.runs[0]._r.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
            )
            if existing_rPr is not None:
                first_para.runs[0]._r.remove(existing_rPr)
            first_para.runs[0]._r.insert(0, rPr_elem)

    if pPr_elem is not None:
        existing_pPr = first_para._p.find(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}pPr"
        )
        if existing_pPr is None:
            first_para._p.insert(0, pPr_elem)


def _replace_curly_placeholders(tf, anchor_key: str, new_text: str, result: TestResult) -> None:
    pattern = re.compile(r"\{\{" + re.escape(anchor_key) + r"\}\}")
    replaced = False

    for paragraph in tf.paragraphs:
        for run in paragraph.runs:
            if pattern.search(run.text):
                run.text = pattern.sub(new_text, run.text)
                replaced = True

    if not replaced:
        full_text = "".join(run.text for p in tf.paragraphs for run in p.runs)
        if pattern.search(full_text):
            result.warnings.append(
                f"{anchor_key}: placeholder split across runs, falling back to full-text replace"
            )
            _replace_split_placeholder(tf, anchor_key, new_text)
            replaced = True

    if not replaced:
        result.warnings.append(
            f"{anchor_key}: placeholder '{{{{' + anchor_key + '}}}}' not found in runs, replacing all text"
        )
        _replace_all_text_preserving_format(tf, new_text, result, anchor_key)


def _replace_split_placeholder(tf, anchor_key: str, new_text: str) -> None:
    placeholder = "{{" + anchor_key + "}}"
    for paragraph in tf.paragraphs:
        runs = paragraph.runs
        if not runs:
            continue
        combined = "".join(r.text for r in runs)
        if placeholder not in combined:
            continue
        new_combined = combined.replace(placeholder, new_text)
        rPr_elem = None
        for r in runs:
            rPr = r._r.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
            )
            if rPr is not None:
                rPr_elem = copy.deepcopy(rPr)
                break
        runs[0].text = new_combined
        if rPr_elem is not None:
            existing = runs[0]._r.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
            )
            if existing is None:
                runs[0]._r.insert(0, rPr_elem)
        for r in runs[1:]:
            r.text = ""


def _capture_font(run) -> dict:
    font = run.font
    props = {}
    if font.name is not None:
        props["name"] = font.name
    if font.size is not None:
        props["size"] = font.size
    if font.bold is not None:
        props["bold"] = font.bold
    if font.italic is not None:
        props["italic"] = font.italic
    try:
        if font.color and font.color.type is not None and font.color.rgb is not None:
            props["color_rgb"] = font.color.rgb
    except (AttributeError, TypeError):
        pass
    return props


def _apply_font(run, props: dict) -> None:
    font = run.font
    if "name" in props:
        font.name = props["name"]
    if "size" in props:
        font.size = props["size"]
    if "bold" in props:
        font.bold = props["bold"]
    if "italic" in props:
        font.italic = props["italic"]
    if "color_rgb" in props:
        font.color.rgb = props["color_rgb"]


def _check_overflow(shape, new_text: str, result: TestResult, anchor_key: str) -> None:
    width_emu = shape.width if shape.width else 0
    height_emu = shape.height if shape.height else 0

    width_in = width_emu / 914400 if width_emu else 0
    height_in = height_emu / 914400 if height_emu else 0

    if width_in > 0 and height_in > 0:
        avg_char_width_in = 0.08
        chars_per_line = max(1, int(width_in / avg_char_width_in))
        line_height_in = 0.22
        max_lines = max(1, int(height_in / line_height_in))

        text_lines = new_text.count("\n") + 1
        wrapped_lines = 0
        for line in new_text.split("\n"):
            wrapped_lines += max(1, -(-len(line) // chars_per_line))

        if wrapped_lines > max_lines:
            result.warnings.append(
                f"{anchor_key}: text may overflow shape "
                f"(~{wrapped_lines} lines vs ~{max_lines} max in {width_in:.1f}x{height_in:.1f} in)"
            )


def generate_output_path(new_template_path: str, output_dir: str) -> str:
    stem = Path(new_template_path).stem
    output = Path(output_dir) / f"{stem}_TEST_OUTPUT.pptx"
    counter = 1
    while output.exists():
        output = Path(output_dir) / f"{stem}_TEST_OUTPUT_{counter}.pptx"
        counter += 1
    return str(output)
