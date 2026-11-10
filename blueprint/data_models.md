# Data Models

All dataclasses used in the application, their fields, types, defaults, and relationships.

---

## AnchorRecord

**File:** `models/anchor_record.py`
**Purpose:** Represents a single detected anchor in a PPTX file. One record per unique (slide_index, key, detection_source) combination.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `anchor_key` | `str` | required | Normalized anchor identifier (e.g. `"cover_title"`). Extracted from shape name, alt text, or visible text. |
| `slide_index` | `int` | required | Zero-based slide number where the anchor was found. |
| `shape_name` | `str` | required | The `shape.name` property from python-pptx. For table cell proxies, formatted as `"ParentName::cell"`. |
| `detection_source` | `str` | required | One of: `"shape_name"`, `"alt_text"`, `"visible_text"`. How the anchor key was found. |
| `visible_text` | `str` | required | The text content of the shape at detection time. May be empty for non-text shapes. |
| `left` | `int` | required | Left edge position in EMU (English Metric Units, 914400 EMU = 1 inch). |
| `top` | `int` | required | Top edge position in EMU. |
| `width` | `int` | required | Shape width in EMU. |
| `height` | `int` | required | Shape height in EMU. |
| `notes` | `list[str]` | `[]` | Mutable list of warning/info notes (e.g. `"duplicate key (2 occurrences)"`). Appended during detection. |

**Created by:** `services/anchor_detector.py:detect_anchors()`
**Consumed by:** `services/anchor_mapper.py`, all UI screens, `services/validation.py`

---

## AnchorMapping

**File:** `models/anchor_mapping.py`
**Purpose:** Links an existing-template anchor to a new-template anchor. One mapping per unique anchor key across both templates.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `anchor_key` | `str` | required | The normalized key shared between the existing and new anchor. |
| `existing_anchor` | `AnchorRecord \| None` | `None` | Reference to the existing template's anchor. `None` if new-only. |
| `new_anchor` | `AnchorRecord \| None` | `None` | Reference to the new template's anchor. `None` if existing-only. |
| `include_in_test` | `bool` | `True` | Whether this mapping is selected for test output. Toggled by user in mapping screen. |
| `test_value` | `str` | `""` | The text value to write into the new template during test. Entered by user in testing screen. |
| `notes` | `list[str]` | `[]` | Status notes: `"auto-matched"`, `"existing only"`, `"new only"`, `"manually remapped"`. |

**Created by:** `services/anchor_mapper.py:build_mappings()`
**Mutated by:** `ui/mapping_view.py` (include toggle, manual remap), `ui/testing_view.py` (test values)
**Consumed by:** `services/test_writer.py`, `services/validation.py`

---

## TestResult

**File:** `services/test_writer.py`
**Purpose:** Holds the outcome of a test run. Created by `run_test()`, displayed by `ui/results_view.py`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output_path` | `str` | `""` | Filesystem path to the generated test PPTX. |
| `selected_count` | `int` | `0` | Number of mappings that were selected and had test values. |
| `written_count` | `int` | `0` | Number of shapes successfully written to. |
| `skipped_count` | `int` | `0` | `selected_count - written_count`. |
| `warnings` | `list[str]` | `[]` | Non-fatal issues: overflow estimates, split placeholders, readback mismatches. |
| `failures` | `list[str]` | `[]` | Fatal per-anchor issues: no text frame, write exceptions. |

**Created by:** `services/test_writer.py:run_test()`
**Extended by:** `app.py` (appends pre-test and readback warnings)
**Consumed by:** `ui/results_view.py:load_results()`

---

## _CellShapeProxy

**File:** `services/pptx_reader.py`
**Purpose:** Wraps a table cell to look like a shape for uniform anchor detection and text writing.

| Attribute | Type | Source |
|-----------|------|--------|
| `name` | `str` | `"{parent_shape.name}::cell"` |
| `has_text_frame` | `bool` | Always `True` |
| `text_frame` | `TextFrame` | From `cell.text_frame` |
| `_element` | `lxml.etree._Element` | From `cell._tc` |
| `left`, `top`, `width`, `height` | `int` | Inherited from parent table shape |
| `shape_type` | `None` | Not applicable |
| `has_table` | `False` | Prevents infinite recursion |

---

## Relationships

```
AnchorRecord ----< AnchorMapping.existing_anchor
AnchorRecord ----< AnchorMapping.new_anchor

AnchorMapping ----< TestResult (selected mappings drive the test)

_CellShapeProxy wraps table cells to produce AnchorRecords
```

## Serialization

All models are plain `dataclasses`. Convert with `dataclasses.asdict()` for JSON. Only primitive types are used (str, int, bool, list, None), except for the `AnchorRecord` references in `AnchorMapping` which nest naturally.
