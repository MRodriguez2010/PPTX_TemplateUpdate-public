# UI Screens

Every Tkinter frame, its widgets, callbacks, and navigation connections.

---

## MainWindow (`ui/main_window.py`)

**Not a frame** - it's a controller class that manages the root `tk.Tk` window.

### Layout
```
+----------------------------------------------+
|  (title bar: "PPTX TemplateUpdate")          |
|  +----------------------------------------+  |
|  |  _container (ttk.Frame)                |  |
|  |    [current screen frame packed here]   |  |
|  |                                         |  |
|  +----------------------------------------+  |
|  [__________status bar__________________]    |
+----------------------------------------------+
```

### Properties
- Window size: 800x540 default, 640x440 minimum
- `_frames: dict[str, ttk.Frame]` - registered frames by name
- `_current_frame` - currently visible frame
- `_status_var` / `_status_bar` - persistent status text at bottom

### Key Methods
| Method | Purpose |
|--------|---------|
| `register_frame(name, frame)` | Adds a frame to the registry |
| `show_frame(name)` | Hides current frame, packs the named frame |
| `set_status(text)` | Updates the status bar text |

### Frame Registry Names
| Name | Frame Class |
|------|-------------|
| `"selection"` | `TemplateSelectionFrame` |
| `"element_browser"` | `ElementBrowserFrame` |
| `"mapping"` | `MappingViewFrame` |
| `"testing"` | `TestingViewFrame` |
| `"results"` | `ResultsViewFrame` |

---

## Screen 1: TemplateSelectionFrame (`ui/template_selection.py`)

**Purpose:** File picker for existing and new PPTX templates.

### Layout
```
+----------------------------------------------+
|        PPTX TemplateUpdate (header)           |
|   Select templates to compare... (subtitle)   |
|                                               |
|  [Template Files LabelFrame]                  |
|    Existing Template: [___path___] [Browse..]  |
|    New Template:      [___path___] [Browse..]  |
|                                               |
|           [Load Anchors]                       |
|    (status label - gray text)                  |
+----------------------------------------------+
```

### State
| Variable | Type | Purpose |
|----------|------|---------|
| `_existing_path` | `tk.StringVar` | Existing template file path |
| `_new_path` | `tk.StringVar` | New template file path |
| `_status_var` | `tk.StringVar` | Status message below button |

### Callbacks
| Trigger | Handler | Action |
|---------|---------|--------|
| Browse (existing) | `_browse_existing()` | Opens file dialog, sets `_existing_path` |
| Browse (new) | `_browse_new()` | Opens file dialog, sets `_new_path` |
| Load Anchors | `_handle_load()` | Validates paths exist, calls `on_load_anchors(existing, new)` |

### Navigation
- **Forward:** `on_load_anchors` callback -> `app.py:_on_load_anchors()` -> shows `element_browser`
- **Back:** None (first screen)

---

## Screen 2: ElementBrowserFrame (`ui/element_browser.py`)

**Purpose:** Unified element browser and anchor assignment. Shows ALL shapes from both templates grouped by slide. Auto-detected anchors are pre-filled. Users can assign/edit anchor keys for any shape inline. Replaces the former separate `AnchorResultsFrame` and `AnchorAssignmentFrame`.

### Layout
```
+----------------------------------------------+
|  Element Browser & Anchor Assignment (header)  |
|  314 total shapes | Auto: 0/0 | Assigned: 0/0 |
|  [yellow banner if 0 auto-detected]            |
|                                               |
|  [Existing Template tab] [New Template tab]    |
|  +--Treeview (grouped by slide)-------------+  |
|  | > Slide 1 (4 shapes, 0 anchors)          |  |
|  |   | Anchor Key | Shape Name | Visible..  |  |
|  |   |            | Title 1    | Welcome..  |  |
|  |   | title      | Subtitle   | Company..  |  |
|  | > Slide 2 (9 shapes, 1 anchor)           |  |
|  |   ...                                     |  |
|  +-------------------------------------------+  |
|                                               |
|  [Assign Anchor Key]                          |
|    Selected shape: Slide 1 | Title 1 | "..."  |
|    Anchor Key: [__________] [Assign] [Clear]   |
|    2 existing + 1 new = 3 total anchor(s)      |
|                                               |
|    [Back to Selection]  [Continue to Mapping ->]|
+----------------------------------------------+
```

### Treeview Structure
- **Parent nodes:** Slide groups (e.g., "Slide 1 (4 shapes, 0 anchors)") with tag `"slide_header"` (gray bg)
- **Child nodes:** Individual shapes with columns: `anchor` (key), `name`, `text`

### Tags
- `"auto"` -> light blue background (`#e3f2fd`) - auto-detected anchors
- `"assigned"` -> light green background (`#e8f5e9`) - manually assigned anchors
- `"slide_header"` -> light gray background (`#f5f5f5`) - slide group headers

### State
| Variable | Type | Purpose |
|----------|------|---------|
| `_existing_shapes` | `list[ShapeInfo]` | All shapes from existing template |
| `_new_shapes` | `list[ShapeInfo]` | All shapes from new template |
| `_existing_assignments` | `dict[(int,str), str]` | `(slide_index, shape_name) -> anchor_key` |
| `_new_assignments` | `dict[(int,str), str]` | `(slide_index, shape_name) -> anchor_key` |
| `_active_tab` | `str` | `"existing"` or `"new"` |
| `_selected_iid` | `str \| None` | Currently selected treeview item id |

### Key Methods
| Method | Purpose |
|--------|---------|
| `load(ex_shapes, nw_shapes, ex_anchors, nw_anchors, ex_assign, nw_assign)` | Loads all shapes, pre-fills auto-detected anchors, refreshes trees |
| `_prefill_from_anchors(shapes, anchors, assignments)` | Copies auto-detected anchor keys into assignments dict |
| `_refresh_tree(tree, shapes, assignments, anchors)` | Rebuilds treeview with slide grouping and color tags |
| `_apply_assignment()` | Reads key entry, updates assignments dict, refreshes tree |
| `get_assignments()` | Returns `(existing_assignments, new_assignments)` tuple |

### Interactions
| Trigger | Handler | Action |
|---------|---------|--------|
| Select shape row | `_on_select(which)` | Shows shape info, loads current key into entry |
| Enter key in entry | `_apply_assignment()` | Assigns key, refreshes tree with green tag |
| Assign button | `_apply_assignment()` | Same as Enter |
| Clear button | `_clear_assignment()` | Removes key, refreshes tree |
| Tab change | `_on_tab_change()` | Resets selection, switches active tab context |

### Navigation
- **Back:** `on_back` -> shows `selection`
- **Forward:** `on_continue` -> `app.py:_on_continue_to_mapping()` -> shows `mapping`

---

## Screen 3: MappingViewFrame (`ui/mapping_view.py`)

**Purpose:** Mapping table with auto-match results, manual remap controls, include/exclude toggles.

### Layout
```
+----------------------------------------------+
|        Anchor Mapping (header)                |
|    Matched: N | Ex only: N | New only: N ...   |
|                                               |
|  [Select All] [Select None] [Select Matched]  |
|                                               |
|  +--Treeview (10 columns)-------------------+  |
|  | Test | Key | Status | ExSlide | ExShape...|  |
|  |  Y   | cover_title | Matched | 1 | ...   |  |
|  |  -   | executive.. | Ex Only | 1 | ...   |  |
|  +------------------------------------------+  |
|                                               |
|  [Selected Mapping Detail / Manual Remap]     |
|    Anchor Key: cover_title                     |
|    Existing Anchor: [combobox_____________]    |
|    New Anchor:      [combobox_____________]    |
|    [x] Include in test                         |
|    [Apply Changes]                             |
|                                               |
|    [Back to Detection]  [Continue to Testing]  |
+----------------------------------------------+
```

### Treeview Columns
`include`, `key`, `status`, `ex_slide`, `ex_shape`, `ex_source`, `new_slide`, `new_shape`, `new_source`, `notes`

### Tags
- `"matched"` -> light green background (`#e8f5e9`)
- `"unmatched"` -> light orange background (`#fff3e0`)

### Interactions
| Trigger | Handler | Action |
|---------|---------|--------|
| Double-click column 1 (Test) | `_on_double_click` | Toggles `include_in_test`, refreshes tree |
| Double-click other columns | `_on_double_click` | Loads mapping detail in remap panel |
| Apply Changes | `_apply_remap()` | Reads combobox values, updates mapping, refreshes |
| Select All/None/Matched | `_select_*()` | Batch-sets `include_in_test`, refreshes |

### Key Methods
| Method | Purpose |
|--------|---------|
| `load_mappings(mappings, existing, new)` | Populates comboboxes and tree |
| `get_mappings()` | Returns current `_mappings` list |

### Navigation
- **Back:** `on_back` -> shows `element_browser`
- **Forward:** `on_continue` -> `app.py:_on_continue_to_testing()` -> shows `testing`

---

## Screen 4: TestingViewFrame (`ui/testing_view.py`)


**Purpose:** Per-anchor test value entry with existing/new context display.

### Layout
```
+----------------------------------------------+
|        Testing (header)                       |
|    N anchor(s) selected for testing            |
|                                               |
|  [Scrollable Canvas]                           |
|  +--Card: cover_title-------------------------+|
|  | [Existing Context] | [New Template Context]||
|  | Slide: 1           | Slide: 1              ||
|  | Shape: slot:cover   | Shape: slot:cover     ||
|  | Source: shape_name  | Source: shape_name     ||
|  | Bounds: L=..        | Bounds: L=..           ||
|  | Text: ...           | Text: ...              ||
|  |                                             ||
|  | Test Value:                                  ||
|  | [________________________text_widget_______]||
|  +---------------------------------------------+|
|  +--Card: company_name-----------------------+ |
|  | ...                                        | |
|  +--------------------------------------------+ |
|                                               |
|    [Back to Mapping]  [Run Test]               |
+----------------------------------------------+
```

### Scroll Implementation
- `tk.Canvas` with embedded `ttk.Frame` (`_scroll_frame`)
- `ttk.Scrollbar` vertical
- Mouse wheel bound for Windows (`<MouseWheel>`) and Linux (`<Button-4>`, `<Button-5>`)
- Cards are `ttk.LabelFrame` packed into `_scroll_frame`

### State
| Variable | Type | Purpose |
|----------|------|---------|
| `_mappings` | `list[AnchorMapping]` | Only included mappings (filtered from full list) |
| `_text_widgets` | `list[tk.Text]` | One per mapping, indexed same as `_mappings` |

### Key Methods
| Method | Purpose |
|--------|---------|
| `load_mappings(mappings)` | Filters to included, builds cards, restores existing test values |
| `_save_test_values()` | Reads all text widgets back into `_mappings[i].test_value` |
| `get_mappings_with_values()` | Saves then returns mappings |
| `_fill_context(parent, anchor)` | Populates a context LabelFrame with anchor details |

### Navigation
- **Back:** `on_back` -> saves values, shows `mapping`
- **Forward:** `on_run_test` -> saves values, calls `app.py:_on_run_test()`

---

## Screen 5: ResultsViewFrame (`ui/results_view.py`)

**Purpose:** Summary of test run, warnings/failures log, output file access.

### Layout
```
+----------------------------------------------+
|        Test Results (header)                  |
|    Test completed successfully / with errors   |
|                                               |
|  [Summary LabelFrame]                         |
|    Output file: /path/to/output.pptx          |
|    Anchors selected: 4                         |
|    Successfully written: 4                     |
|    Skipped/Failed: 0                           |
|                                               |
|  [Warnings & Failures LabelFrame]             |
|  +--tk.Text (read-only)---------------------+  |
|  | WARNINGS:                                  |  |
|  |   - anchor1: text may overflow shape...    |  |
|  | FAILURES:                                  |  |
|  |   - (none)                                 |  |
|  +--------------------------------------------+ |
|                                               |
|  [Open Output Folder] [Back to Testing] [Start Over] |
+----------------------------------------------+
```

### Key Methods
| Method | Purpose |
|--------|---------|
| `load_results(result: TestResult)` | Populates all summary vars and log text |
| `_open_folder()` | Platform-specific folder open (Windows/macOS/Linux) |

### Navigation
- **Back:** `on_back_to_testing` -> shows `testing`
- **Start Over:** `on_start_over` -> shows `selection`
