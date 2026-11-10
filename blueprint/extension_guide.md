# Extension Guide

How to add new features: anchor types, detection methods, UI screens, services, and validation rules.

---

## Adding a New Anchor Detection Method

**Example:** Detect anchors from shape hyperlinks.

### 1. Update `services/pptx_reader.py`

Add a new extraction function:
```python
def get_shape_hyperlink(shape) -> str:
    # extract hyperlink URL or tooltip from the shape
    ...
```

### 2. Update `services/anchor_detector.py`

Add a new regex or parser (if needed), then add a detection block inside `detect_anchors()`:

```python
# After the existing visible_text block (around line 69-81), add:
hyperlink = get_shape_hyperlink(shape)
key = normalize_key(hyperlink)
if key:
    dedup = (slide_index, key, "hyperlink")
    if dedup not in seen:
        seen.add(dedup)
        records.append(AnchorRecord(
            anchor_key=key,
            slide_index=slide_index,
            shape_name=shape_name,
            detection_source="hyperlink",
            visible_text=visible_text,
            left=left, top=top, width=width, height=height,
        ))
```

### 3. Update `services/test_writer.py`

In `_write_text()`, add handling for the new detection source if it needs different write behavior:
```python
if detection == "hyperlink":
    _replace_hyperlink(shape, mapping, result)
else:
    ...
```

### 4. Update UI display

The `detection_source` string automatically appears in treeview columns. No UI changes needed unless you want special formatting. The Element Browser (`ui/element_browser.py`) displays all shapes grouped by slide - new detection sources will appear automatically when shapes are loaded via `build_shape_list()`.

---

## Adding a New UI Screen

### 1. Create the frame

Create `ui/new_screen.py`:
```python
import tkinter as tk
from tkinter import ttk

class NewScreenFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, on_back=None, on_continue=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._on_continue = on_continue
        self._build_ui()

    def _build_ui(self) -> None:
        # Build widgets here
        header = ttk.Label(self, text="New Screen", font=("TkDefaultFont", 14, "bold"))
        header.pack(pady=(12, 4))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Back", command=self._handle_back).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Continue", command=self._handle_continue).pack(side=tk.LEFT, padx=4)

    def _handle_back(self) -> None:
        if self._on_back:
            self._on_back()

    def _handle_continue(self) -> None:
        if self._on_continue:
            self._on_continue()
```

### 2. Register in `app.py`

```python
from ui.new_screen import NewScreenFrame

# In App.__init__():
self.new_screen = NewScreenFrame(
    self.root,
    on_back=lambda: self.window.show_frame("previous_screen"),
    on_continue=self._on_new_screen_continue,
)
self.window.register_frame("new_screen", self.new_screen)

# Add the transition callback:
def _on_new_screen_continue(self) -> None:
    # Process data, then:
    self.window.show_frame("next_screen")
```

### 3. Wire navigation

Update the previous screen's `on_continue` to show `"new_screen"` instead of the original next screen.

Current screen flow: `selection` → `element_browser` → `mapping` → `testing` → `results`

The Element Browser (`ui/element_browser.py`) is the unified screen for viewing all shapes and assigning anchor keys. It replaced the previous `anchor_results` and `anchor_assignment` screens.

---

## Adding a New Service Module

### 1. Create the module

Create `services/new_service.py`:
```python
"""Description of what this service does."""

from __future__ import annotations

def my_function(arg: str) -> list[str]:
    # Stateless function - no class needed
    ...
```

### 2. Import in `app.py` or the UI that uses it

```python
from services.new_service import my_function
```

### 3. Conventions
- Services are **stateless functions**, not classes
- All business logic goes in `services/`, never in `ui/`
- Return plain data types (lists, dicts, dataclasses) - no Tk objects
- Raise exceptions for fatal errors, return warning lists for non-fatal issues

---

## Adding a New Validation Rule

### 1. Add to `services/validation.py`

Add a function following the existing pattern:
```python
def validate_something(data) -> list[str]:
    warnings: list[str] = []
    # Check conditions, append warning strings
    if some_problem:
        warnings.append(f"Description of the problem: {details}")
    return warnings
```

### 2. Wire into `app.py`

Call it at the appropriate pipeline stage:
- **After detection:** in `_on_load_anchors()` (runs before showing Element Browser)
- **After mapping:** in `_on_continue_to_mapping()` (merges element browser assignments with auto-detected anchors)
- **Before test:** in `_on_run_test()` (add to `pre_warnings`)
- **After test:** in `_on_run_test()` (add to `readback_warnings`)

Pattern:
```python
new_warnings = validate_something(data)
result.warnings.extend(new_warnings)  # or show in status bar
```

---

## Adding a New Data Model

### 1. Create the dataclass

Create `models/new_model.py`:
```python
from dataclasses import dataclass, field

@dataclass
class NewModel:
    required_field: str
    optional_field: int = 0
    notes: list[str] = field(default_factory=list)
```

### 2. Conventions
- Use `@dataclass` (not NamedTuple or plain class)
- Use `field(default_factory=list)` for mutable defaults
- Keep models in `models/` directory
- Models should have no business logic - just data containers
- Use `from __future__ import annotations` for forward references

---

## Adding Support for a New Shape Type

**Example:** SmartArt shapes.

### 1. Update `services/pptx_reader.py`

In `_recurse_shapes()`, add a new branch:
```python
if _is_smartart(shape):
    try:
        for child in _extract_smartart_shapes(shape):
            yield child
    except (AttributeError, TypeError):
        pass
```

### 2. Create a proxy if needed

If the child elements don't look like regular shapes, create a proxy class similar to `_CellShapeProxy`:
```python
class _SmartArtProxy:
    def __init__(self, node, parent_shape):
        self.name = f"{parent_shape.name}::smartart"
        self.has_text_frame = True
        ...
```

### 3. Update `services/test_writer.py`

Add the same traversal logic to `_iter_all_writable()` so the write path mirrors the read path.

### 4. Test

```python
from services.anchor_detector import detect_anchors
anchors = detect_anchors('file_with_smartart.pptx')
# Verify SmartArt anchors appear
```

---

## Key Patterns to Follow

1. **Stateless services** - no global state, no singletons, functions take inputs and return outputs
2. **Callbacks for navigation** - UI frames receive `on_back` and `on_continue` callables, never import `App` directly
3. **Status bar for immediate feedback** - call `self.window.set_status()` from `app.py`
4. **Warnings as string lists** - all validation returns `list[str]`, surfaced through `TestResult.warnings` or status bar
5. **Proxy pattern for non-standard shapes** - wrap unusual containers (tables, groups, SmartArt) to look like regular shapes
6. **Read path mirrors write path** - `iter_shapes` / `_recurse_shapes` and `_iter_all_writable` must traverse the same structure
