# Debugging Guide

Common issues, where to look, error paths, and diagnostic strategies.

---

## Quick Diagnostic Commands

```bash
# Check all modules compile
python3 -m py_compile app.py
python3 -m py_compile services/pptx_reader.py
python3 -m py_compile services/anchor_detector.py
python3 -m py_compile services/anchor_mapper.py
python3 -m py_compile services/test_writer.py
python3 -m py_compile services/anchor_assigner.py
python3 -m py_compile services/validation.py

# Test shape loading for element browser
python3 -c "
from services.anchor_assigner import build_shape_list
shapes = build_shape_list('path/to/file.pptx')
print(f'{len(shapes)} shapes loaded')
from collections import Counter
slides = Counter(s.slide_index for s in shapes)
for si in sorted(slides): print(f'  Slide {si}: {slides[si]} shapes')
"

# Test anchor detection on a file
python3 -c "
from services.anchor_detector import detect_anchors
for a in detect_anchors('path/to/file.pptx'):
    print(f'{a.anchor_key}  slide={a.slide_index}  source={a.detection_source}  shape={a.shape_name}')
"

# Test mapping between two files
python3 -c "
from services.anchor_detector import detect_anchors
from services.anchor_mapper import build_mappings
ex = detect_anchors('existing.pptx')
nw = detect_anchors('new.pptx')
for m in build_mappings(ex, nw):
    status = 'matched' if m.existing_anchor and m.new_anchor else 'unmatched'
    print(f'{m.anchor_key}: {status}  notes={m.notes}')
"

# Test write + readback
python3 -c "
from services.anchor_detector import detect_anchors
from services.anchor_mapper import build_mappings
from services.test_writer import run_test, generate_output_path
from services.validation import verify_readback
ex = detect_anchors('existing.pptx')
nw = detect_anchors('new.pptx')
maps = build_mappings(ex, nw)
for m in maps:
    if m.new_anchor: m.include_in_test = True; m.test_value = f'TEST_{m.anchor_key}'
out = generate_output_path('new.pptx', './outputs')
r = run_test('new.pptx', out, maps)
print(f'Written: {r.written_count}  Warnings: {r.warnings}  Failures: {r.failures}')
print(f'Readback: {verify_readback(out, maps)}')
"
```

---

## Common Issues & Fixes

### 1. No anchors detected in a PPTX file

**Symptoms:** `detect_anchors()` returns empty list.

**Check:**
- Does the PPTX have shapes with names matching `slot:key` pattern?
- Does any visible text contain `{{key}}` patterns?
- Are anchors inside grouped shapes? (Should work - `_recurse_shapes` handles groups)
- Are anchors in table cells? (Should work - `_CellShapeProxy` handles tables)

**Debug:**
```python
from services.pptx_reader import open_presentation, iter_shapes, get_shape_text, get_shape_alt_text
prs = open_presentation('file.pptx')
for si, shape in iter_shapes(prs):
    print(f"Slide {si}: name='{shape.name}' text='{get_shape_text(shape)[:50]}' alt='{get_shape_alt_text(shape)}'")
```

### 2. `_NoneColor` / `AttributeError` on font color

**Symptom:** Error when capturing font properties from a run.

**Root cause:** `python-pptx` font colors can be inherited/theme-based. Accessing `.rgb` on a `_NoneColor` raises `AttributeError`.

**Fix location:** `services/test_writer.py:_capture_font()` (lines ~161-177) - already wrapped in try/except. If this recurs, check that the try/except is still in place.

### 3. Text not appearing in output PPTX

**Symptoms:** `run_test()` reports written_count > 0, but text isn't in the output file.

**Check:**
1. Is the detection source correct? `visible_text` source uses `_replace_curly_placeholders()`, others use `_replace_all_text_preserving_format()`.
2. Is the placeholder split across runs? Check `TestResult.warnings` for "split across runs" message.
3. Does `verify_readback()` report a mismatch? If so, the write method may have silently failed.

**Debug:**
```python
from pptx import Presentation
prs = Presentation('outputs/output.pptx')
for slide_idx, slide in enumerate(prs.slides):
    for shape in slide.shapes:
        if shape.has_text_frame:
            print(f"Slide {slide_idx}, '{shape.name}': {shape.text_frame.text[:80]}")
```

### 4. Shape lookup misses in test_writer

**Symptom:** `run_test()` has `selected_count > 0` but `written_count == 0`.

**Root cause:** Shape is looked up by `(slide_index, shape_name)`. If the shape name in the new template differs from what was detected (e.g., the PPTX was modified), the lookup will miss.

**Check:** Compare `m.new_anchor.shape_name` with actual shape names in the new template PPTX.

### 5. Mapping shows "existing only" for an anchor that exists in both

**Symptom:** An anchor exists in both templates but shows as unmatched.

**Root cause:** Keys are matched by normalized key (the part after `slot:` or inside `{{}}`). If the keys differ in spelling, casing (keys are case-sensitive), or whitespace, they won't match.

**Debug:**
```python
from services.anchor_detector import detect_anchors
ex = detect_anchors('existing.pptx')
nw = detect_anchors('new.pptx')
ex_keys = {a.anchor_key for a in ex}
nw_keys = {a.anchor_key for a in nw}
print("Only in existing:", ex_keys - nw_keys)
print("Only in new:", nw_keys - ex_keys)
```

### 6. Table cell anchors not detected

**Symptom:** Anchors in table cells are missed.

**Check:** `_CellShapeProxy` names are formatted as `"{parent_shape.name}::cell"`. The anchor detection looks at visible text, so `{{key}}` patterns in table cells should be found. But `slot:key` patterns in cell text won't match (that pattern is for shape names/alt text only, and cell proxies have generic names).

**Workaround:** Use `{{key}}` syntax for anchors in table cells.

### 7. Shape loading failed (build_shape_list error)

**Symptom:** Error dialog "Shape Loading Error" appears after clicking "Load Anchors".

**Root cause:** `build_shape_list()` from `anchor_assigner.py` failed to iterate shapes in one of the templates. Possible causes: corrupt PPTX, unsupported shape type, or file permission issue.

**Fix location:** `app.py:_on_load_anchors()` catches the exception and shows `messagebox.showerror`. Check the exception message for details.

**Debug:**
```python
from services.anchor_assigner import build_shape_list
shapes = build_shape_list('path/to/file.pptx')
print(f"Loaded {len(shapes)} shapes")
for s in shapes[:5]:
    print(f"  Slide {s.slide_index}: {s.shape_name}")
```

### 8. Tkinter UI freezes during anchor detection

**Symptom:** Window becomes unresponsive during "Load Anchors".

**Root cause:** `detect_anchors()` and `build_shape_list()` run on the main thread. Large PPTX files can take time.

**Status:** Not yet threaded. For large files (100+ slides), consider moving detection to a background thread with progress callback.

### 9. Output file path collision

**Symptom:** Error about file already existing.

**Fix location:** `services/test_writer.py:generate_output_path()` auto-increments `_1`, `_2`, etc. If this fails, check file permissions in the `outputs/` directory.

---

## Error Propagation Paths

### Detection errors
```
detect_anchors() raises Exception
  -> caught in App._on_load_anchors()
  -> messagebox.showerror("Detection Error", ...)
  -> selection._status_var = "Detection failed."
  -> user stays on selection screen
```

### Shape loading errors
```
build_shape_list() raises Exception
  -> caught in App._on_load_anchors()
  -> messagebox.showerror("Shape Loading Error", ...)
  -> selection._status_var = "Shape loading failed."
  -> user stays on selection screen
```

### Test write errors
```
run_test() raises Exception
  -> caught in App._on_run_test()
  -> messagebox.showerror("Test Error", ...)
  -> status bar = "Test failed."
  -> user stays on testing screen

Per-shape write failure:
  _write_text() raises Exception
  -> caught inside run_test() loop
  -> appended to result.failures
  -> user sees failure in results view log
```

### Validation warnings
```
All validation functions return list[str], never raise.
Warnings flow:
  validate_anchors()    -> status bar (immediate)
  validate_mappings()   -> status bar (immediate)
  validate_pre_test()   -> result.warnings (shown in results view)
  verify_readback()     -> result.warnings (shown in results view)
```

---

## Logging

There is no file-based logging. All diagnostics surface through:
1. **Status bar** - brief messages at bottom of window
2. **TestResult.warnings / failures** - shown in results view log
3. **AnchorRecord.notes** - shown in element browser and mapping treeviews
4. **AnchorMapping.notes** - shown in mapping treeview

To add file logging, add `import logging` and `logging.basicConfig(filename='debug.log')` at the top of `app.py`.
