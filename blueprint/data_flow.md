# Data Flow & State Management

End-to-end pipeline, state ownership, and screen transition map.

---

## Application State

All mutable state lives in `app.py:App`:

| Attribute | Type | Set By | Used By |
|-----------|------|--------|---------|
| `existing_anchors` | `list[AnchorRecord]` | `_on_load_anchors` | `_on_continue_to_mapping`, element_browser UI |
| `new_anchors` | `list[AnchorRecord]` | `_on_load_anchors` | `_on_continue_to_mapping`, element_browser UI |
| `mappings` | `list[AnchorMapping]` | `_on_continue_to_mapping`, `_on_continue_to_testing`, `_on_run_test` | testing UI, test_writer |
| `existing_path` | `str` | `_on_load_anchors` | bake-in step |
| `new_template_path` | `str` | `_on_load_anchors` | `_on_run_test` |
| `_existing_assignments` | `dict[(int,str), str]` | `_on_continue_to_mapping` | `_on_run_test` (bake-in) |
| `_new_assignments` | `dict[(int,str), str]` | `_on_continue_to_mapping` | `_on_run_test` (bake-in) |

**Important:** `mappings` is the same list object mutated by UI screens (include toggles, manual remap, test values). It gets reassigned at each transition to capture the latest state from the UI.

---

## Pipeline Steps

### Step 1: Template Selection -> Element Browser

```
User clicks "Load Anchors"
  -> TemplateSelectionFrame._handle_load()
    -> validates file paths exist
    -> calls on_load_anchors(existing_path, new_path)

App._on_load_anchors(existing_path, new_path):
  1. self.existing_path = existing_path
  2. self.new_template_path = new_path
  3. self.existing_anchors = detect_anchors(existing_path)
  4. self.new_anchors = detect_anchors(new_path)
  5. existing_shapes = build_shape_list(existing_path)
  6. new_shapes = build_shape_list(new_path)
  7. validate_anchors() -> warnings to status bar
  8. element_browser.load(shapes, anchors, assignments)
  9. show_frame("element_browser")
```

**detect_anchors(path)** internally:
```
open_presentation(path)
  -> iter_shapes(prs)  [recurses groups, table cells]
    -> for each shape:
      -> normalize_key(shape.name)         -> AnchorRecord(source="shape_name")
      -> normalize_key(get_shape_alt_text)  -> AnchorRecord(source="alt_text")
      -> _CURLY_RE.finditer(visible_text)  -> AnchorRecord(source="visible_text")
  -> _flag_duplicates(records)
  -> return records
```

**build_shape_list(path)** internally:
```
open_presentation(path)
  -> iter_shapes(prs)
    -> for each shape: ShapeInfo(slide_index, name, text, bounds)
  -> return flat list of all shapes
```

### Step 2: Element Browser -> Mapping

```
User assigns anchor keys to shapes, then clicks "Continue to Mapping"
  -> ElementBrowserFrame._handle_continue()
    -> calls on_continue

App._on_continue_to_mapping():
  1. (ex_assign, nw_assign) = element_browser.get_assignments()
  2. assigned_existing = assignments_to_anchor_records(shapes, ex_assign)
  3. assigned_new = assignments_to_anchor_records(shapes, nw_assign)
  4. Merge auto-detected + manually assigned (dedup by slide+shape_name)
  5. self.mappings = build_mappings(merged_existing, merged_new)
  6. validate_mappings() -> warnings to status bar
  7. mapping.load_mappings(mappings, merged_existing, merged_new)
  8. show_frame("mapping")
```

**Element Browser pre-fill logic:**
```
_prefill_from_anchors(shapes, anchors, assignments):
  For each auto-detected anchor:
    Set assignments[(slide_index, shape_name)] = anchor_key
    (only if not already manually assigned)
  -> auto-detected keys appear pre-filled in the treeview (blue)
  -> manually assigned keys appear green
```

**build_mappings()** internally:
```
Build existing_by_key (first occurrence per key)
Build new_by_key (first occurrence per key)
Collect all unique keys (existing order first, then new-only)
For each key:
  -> both present: AnchorMapping(include=True, note="auto-matched")
  -> existing only: AnchorMapping(include=False, note="existing only")
  -> new only: AnchorMapping(include=False, note="new only")
```

### Step 3: Mapping -> Testing

```
User adjusts include flags, manual remaps, then clicks "Continue to Testing"
  -> MappingViewFrame._handle_continue()
    -> calls on_continue

App._on_continue_to_testing():
  1. self.mappings = self.mapping.get_mappings()  # reads back from UI
  2. Check at least one selected, else show warning dialog
  3. self.testing.load_mappings(mappings)
  4. show_frame("testing")
```

### Step 4: Testing -> Test Run -> Results

```
User enters test values, clicks "Run Test"
  -> TestingViewFrame._handle_run_test()
    -> _save_test_values() -> writes tk.Text contents into mapping.test_value
    -> calls on_run_test

App._on_run_test():
  1. self.mappings = testing.get_mappings_with_values()
  2. Check at least one has a non-empty test_value
  3. pre_warnings = validate_pre_test(mappings)
  4. output_path = generate_output_path(new_template_path, OUTPUT_DIR)
  5. result = run_test(new_template_path, output_path, mappings)
  6. result.warnings += pre_warnings
  7. readback_warnings = verify_readback(output_path, mappings)
  8. result.warnings += readback_warnings
  9. If _new_assignments: bake_assignments_into_pptx(output, output, assignments)
  10. results.load_results(result)
  11. show_frame("results")
```

**run_test()** internally:
```
Filter selected mappings with test values
shutil.copy2(template, output)
Open output with python-pptx
Build lookup: (slide_index, shape_name) -> mapping
Iterate all shapes (groups, tables)
  For each match:
    if detection_source == "visible_text":
      _replace_curly_placeholders()  # preserves surrounding text
    else:
      _replace_all_text_preserving_format()  # replaces everything
    _check_overflow()
Save output
```

---

## Screen Transition Map

```
                    [selection]
                        |
                   Load Anchors
              (detect + load shapes)
                        |
                        v
                [element_browser]
                  /           \
               Back          Continue
                |          (merge anchors
                v           + build mappings)
           [selection]         |
                               v
                           [mapping]
                          /       \
                        Back     Continue
                         |          |
                         v          v
               [element_browser] [testing]
                                /       \
                              Back    Run Test
                               |     (+ bake-in)
                               v          |
                          [mapping]       v
                                      [results]
                                      /      \
                             Back to Testing  Start Over
                                  |              |
                                  v              v
                              [testing]     [selection]
```

---

## Validation Timeline

```
1. Anchor Load    -> validate_anchors(existing, "Existing")
                  -> validate_anchors(new, "New")
                  -> Status bar shows duplicate key warnings

2. Mapping Build  -> validate_mappings(mappings)
                  -> Status bar shows missing-pair warnings

3. Pre-Test       -> validate_pre_test(mappings)
                  -> Warnings added to TestResult

4. Post-Write     -> verify_readback(output_path, mappings)
                  -> Warnings added to TestResult

5. Bake-in        -> bake_assignments_into_pptx() (if _new_assignments)
                  -> Success/failure note added to TestResult

All warnings surface in ResultsViewFrame log text.
```

---

## Data Mutation Points

| Data | Where Mutated | How |
|------|---------------|-----|
| `AnchorRecord.notes` | `anchor_detector._flag_duplicates()` | Appends duplicate warning |
| Element Browser assignments | `element_browser._apply_assignment()` | User types key, assigns to shape |
| `AnchorMapping.include_in_test` | `mapping_view._on_double_click()`, `_select_*()`, `_apply_remap()` | Toggle or batch-set |
| `AnchorMapping.existing_anchor` | `mapping_view._apply_remap()` | Combobox selection |
| `AnchorMapping.new_anchor` | `mapping_view._apply_remap()` | Combobox selection |
| `AnchorMapping.notes` | `mapping_view._apply_remap()` | Replaces "auto-matched" with "manually remapped" |
| `AnchorMapping.test_value` | `testing_view._save_test_values()` | Reads from tk.Text widgets |
