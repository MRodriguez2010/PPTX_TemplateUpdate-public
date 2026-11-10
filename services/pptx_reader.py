"""Read shapes and text from PPTX files."""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Emu


def open_presentation(path: str) -> Presentation:
    return Presentation(path)


def iter_shapes(prs: Presentation):
    for slide_index, slide in enumerate(prs.slides):
        for shape in _recurse_shapes(slide.shapes):
            yield slide_index, shape


def _recurse_shapes(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type is not None and shape.shape_type == 6:
            try:
                for child in _recurse_shapes(shape.shapes):
                    yield child
            except (AttributeError, TypeError):
                pass
        if shape.has_table:
            try:
                table = shape.table
                for row in table.rows:
                    for cell in row.cells:
                        yield _CellShapeProxy(cell, shape)
            except (AttributeError, TypeError):
                pass


class _CellShapeProxy:
    def __init__(self, cell, parent_shape):
        self._cell = cell
        self._parent = parent_shape
        self.name = f"{parent_shape.name}::cell"
        self.shape_type = None
        self.has_table = False
        self.left = parent_shape.left
        self.top = parent_shape.top
        self.width = parent_shape.width
        self.height = parent_shape.height

    @property
    def has_text_frame(self):
        return True

    @property
    def text_frame(self):
        return self._cell.text_frame

    @property
    def _element(self):
        return self._cell._tc


def get_shape_text(shape) -> str:
    if isinstance(shape, _CellShapeProxy):
        try:
            parts = []
            for paragraph in shape.text_frame.paragraphs:
                parts.append(paragraph.text)
            return "\n".join(parts)
        except (AttributeError, TypeError):
            return ""
    if not shape.has_text_frame:
        if shape.has_table:
            return _get_table_text(shape)
        if hasattr(shape, "text"):
            return shape.text or ""
        return ""
    parts = []
    for paragraph in shape.text_frame.paragraphs:
        parts.append(paragraph.text)
    return "\n".join(parts)


def _get_table_text(shape) -> str:
    parts = []
    try:
        for row in shape.table.rows:
            for cell in row.cells:
                txt = cell.text.strip()
                if txt:
                    parts.append(txt)
    except (AttributeError, TypeError):
        pass
    return "\n".join(parts)


def get_shape_alt_text(shape) -> str:
    desc = ""
    if isinstance(shape, _CellShapeProxy):
        return desc
    if hasattr(shape, "name"):
        el = shape._element
        cNvPr = el.find(".//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}cNvPr")
        if cNvPr is None:
            cNvPr = el.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr")
        if cNvPr is None:
            nsmap = {
                "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
                "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            }
            for ns_prefix, ns_uri in nsmap.items():
                cNvPr = el.find(f"{{{ns_uri}}}cNvPr")
                if cNvPr is not None:
                    break
        if cNvPr is None:
            from lxml import etree
            for child in el.iter():
                if child.tag.endswith("}cNvPr") or child.tag == "cNvPr":
                    cNvPr = child
                    break
        if cNvPr is not None:
            desc = cNvPr.get("descr", "")
    return desc


def get_shape_bounds(shape) -> tuple[int, int, int, int]:
    return (
        int(shape.left) if shape.left is not None else 0,
        int(shape.top) if shape.top is not None else 0,
        int(shape.width) if shape.width is not None else 0,
        int(shape.height) if shape.height is not None else 0,
    )
