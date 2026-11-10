# Services Layer

All service modules, their public functions, signatures, and internal logic.

---

## pptx_reader.py

Low-level PPTX reading. No business logic, just shape iteration and property extraction.

### Public Functions

```python
def open_presentation(path: str) -> Presentation
```
Opens a PPTX file and returns a `python-pptx` `Presentation` object.

```python
def iter_shapes(prs: Presentation) -> Generator[tuple[int, shape], None, None]
```
Yields `(slide_index, shape)` for every shape in the presentation. **Recurses into grouped shapes** (shape_type 6) and **yields `_CellShapeProxy` objects for table cells**. This means callers automatically get anchors from groups and tables without special handling.

```python
def get_shape_text(shape) -> str
```
Extracts visible text from a shape. Handles:
- Text frame shapes: joins paragraph texts with `\n`
- `_CellShapeProxy`: reads from cell's text frame
- Table shapes without text frame: concatenates all cell texts
- Shapes with `.text` attribute: returns `.text`
- Everything else: returns `""`

```python
def get_shape_alt_text(shape) -> str
```
Reads alt text (description) from a shape's XML. Traverses `cNvPr` element across multiple namespace strategies:
1. SpreadsheetDrawing namespace
2. PresentationML namespace
3. DrawingML namespace
4. Brute-force `iter()` looking for any `cNvPr` tag

Returns `""` for `_CellShapeProxy` (cells don't have alt text).

```python
def get_shape_bounds(shape) -> tuple[int, int, int, int]
```
Returns `(left, top, width, height)` in EMU. Defaults to 0 for None values.

### Internal

```python
def _recurse_shapes(shapes) -> Generator
```
Recursive generator. For each shape, yields it, then:
- If `shape_type == 6` (group): recurses into `shape.shapes`
- If `shape.has_table`: yields `_CellShapeProxy` for each cell

```python
class _CellShapeProxy
```
Wraps a `pptx.table.Cell` to look like a shape. See `data_models.md` for details.

```python
def _get_table_text(shape) -> str
```
Concatenates all non-empty cell texts from a table shape.

---

## anchor_detector.py

Detects anchors in a PPTX presentation.

### Constants

```python
_SLOT_RE = re.compile(r"slot:(\w+)")    # matches "slot:key" in shape names / alt text
_CURLY_RE = re.compile(r"\{\{(\w+)\}\}")  # matches "{{key}}" in visible text
```

### Public Functions

```python
def normalize_key(raw: str) -> str | None
```
Extracts an anchor key from a raw string. Tries `_SLOT_RE` first, then `_CURLY_RE`. Returns `None` if no match.

```python
def detect_anchors(path: str) -> list[AnchorRecord]
```
Main detection function. Opens the PPTX, iterates all shapes (including groups and table cells via `iter_shapes`), checks three sources in order:
1. **Shape name** against `_SLOT_RE`
2. **Alt text** against `_SLOT_RE`
3. **Visible text** against `_CURLY_RE` (can match multiple keys in one shape)

Deduplicates by `(slide_index, key, detection_source)`. Calls `_flag_duplicates()` before returning.

### Internal

```python
def _flag_duplicates(records: list[AnchorRecord]) -> None
```
Counts occurrences of each `anchor_key`. If count > 1, appends a warning note to each record with that key.

---

## anchor_assigner.py

Shape listing, manual anchor assignment, and bake-in service. Powers the Element Browser screen by providing the full shape list for both templates.

### Data Model

```python
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
```

### Public Functions

```python
def build_shape_list(path: str) -> list[ShapeInfo]
```
**Used by:** `app.py:_on_load_anchors()` for both templates before showing the Element Browser.
Opens a PPTX, iterates all shapes via `iter_shapes()`, and returns a flat `ShapeInfo` list. This is the primary data source for the Element Browser treeviews.

```python
def assignments_to_anchor_records(
    shape_list: list[ShapeInfo],
    assignments: dict[tuple[int, str], str],
) -> list[AnchorRecord]
```
Converts the user's manual assignments (from the Element Browser) into `AnchorRecord` objects with `detection_source="assigned"`. Used in `app.py:_on_continue_to_mapping()` to merge manual assignments with auto-detected anchors.

```python
def bake_assignments_into_pptx(
    pptx_path: str,
    output_path: str,
    assignments: dict[tuple[int, str], str],
) -> None
```
Writes `slot:<key>` into the alt text (`cNvPr descr`) of assigned shapes. Creates a copy at `output_path` (or modifies in place if paths match). This ensures future runs of `detect_anchors()` will auto-detect the manually assigned anchors.

### Internal

```python
def _set_shape_alt_text(shape, text: str) -> None
```
Sets the `descr` attribute on the shape's `cNvPr` element via `lxml` traversal.

---

## anchor_mapper.py

Auto-matches anchors between existing and new templates.

### Public Functions

```python
def build_mappings(
    existing_anchors: list[AnchorRecord],
    new_anchors: list[AnchorRecord],
) -> list[AnchorMapping]
```
Creates one `AnchorMapping` per unique key across both templates:
- **Matched**: key exists in both -> `include_in_test = True`, note `"auto-matched"`
- **Existing-only**: key only in old -> `include_in_test = False`, note `"existing only"`
- **New-only**: key only in new -> `include_in_test = False`, note `"new only"`

Uses first occurrence per key (if duplicates exist). Preserves order: existing keys first, then new-only keys.

```python
def get_match_status(mapping: AnchorMapping) -> str
```
Returns `"Matched"`, `"Existing Only"`, or `"New Only"` based on which anchors are present.

---

## test_writer.py

Writes test values into the new template and produces output PPTX.

### Public Functions

```python
def run_test(
    new_template_path: str,
    output_path: str,
    mappings: list[AnchorMapping],
) -> TestResult
```
1. Filters to selected mappings with test values
2. Copies template with `shutil.copy2`
3. Opens copy with `python-pptx`
4. Builds lookup: `(slide_index, shape_name) -> AnchorMapping`
5. Iterates all shapes (including groups/tables via `_iter_all_writable`)
6. For each matching shape, calls `_write_text()`
7. Saves and returns `TestResult`

```python
def generate_output_path(new_template_path: str, output_dir: str) -> str
```
Creates path like `{stem}_TEST_OUTPUT.pptx`. Auto-increments suffix if file exists.

### Internal - Text Writing

```python
def _write_text(shape, mapping, result) -> None
```
Dispatches based on `detection_source`:
- `"visible_text"` -> `_replace_curly_placeholders()` (preserves surrounding text)
- Otherwise -> `_replace_all_text_preserving_format()` (replaces entire shape text)

Then calls `_check_overflow()`.

```python
def _replace_all_text_preserving_format(tf, new_text, result, anchor_key) -> None
```
Captures font from first run, removes all paragraphs except first, removes extra runs, sets text on first run. Preserves font name, size, bold, italic, color.

```python
def _replace_curly_placeholders(tf, anchor_key, new_text, result) -> None
```
Regex-replaces `{{key}}` in individual runs. Falls back to:
1. `_replace_split_placeholder()` if placeholder spans runs
2. `_replace_all_text_preserving_format()` if not found at all

```python
def _replace_split_placeholder(tf, anchor_key, new_text) -> None
```
When `{{key}}` is split across multiple runs: combines all run text, replaces, puts result in first run, empties the rest.

### Internal - Font Handling

```python
def _capture_font(run) -> dict
```
Captures `name`, `size`, `bold`, `italic`, `color_rgb` from a run's font. Wraps color access in try/except for `_NoneColor` safety.

```python
def _apply_font(run, props: dict) -> None
```
Applies captured font properties back to a run.

### Internal - Overflow Detection

```python
def _check_overflow(shape, new_text, result, anchor_key) -> None
```
Estimates text overflow by computing approximate character capacity from shape dimensions:
- `avg_char_width_in = 0.08`
- `line_height_in = 0.22`
- Computes `chars_per_line` and `max_lines` from shape width/height
- Accounts for newlines and word wrapping
- Adds warning if estimated lines exceed capacity

### Internal - Shape Iteration

```python
def _iter_all_writable(shapes) -> Generator
```
Mirrors `pptx_reader._recurse_shapes()` for the write path. Yields shapes, recurses into groups, yields `_CellShapeProxy` for table cells.

---

## validation.py

Validation and verification at every pipeline stage.

### Public Functions

```python
def validate_anchors(anchors: list[AnchorRecord], label: str) -> list[str]
```
**When:** After anchor detection (called in `app.py:_on_load_anchors`)
Checks for duplicate anchor keys within a single template. Returns warnings like `"[Existing] Duplicate anchor key 'title' found 3 times"`.

```python
def validate_mappings(mappings: list[AnchorMapping]) -> list[str]
```
**When:** After mapping build (called in `app.py:_on_continue_to_mapping`)
Checks for:
- Missing pairs (existing-only or new-only anchors)
- Duplicate keys in the mapping list itself
- Selected anchors with no new-template target

```python
def validate_pre_test(mappings: list[AnchorMapping]) -> list[str]
```
**When:** Before test run (called in `app.py:_on_run_test`)
Warns about selected anchors with empty test values.

```python
def verify_readback(output_path: str, mappings: list[AnchorMapping]) -> list[str]
```
**When:** After test run (called in `app.py:_on_run_test`)
Re-opens the output PPTX with `python-pptx`, reads text from each target shape, checks that the expected test value substring is present. Reports mismatches.
