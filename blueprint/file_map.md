# File Map

Every source file in the project, its purpose, and approximate size.

## Root

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | ~180 | Entry point. Creates `App` class that wires all UI screens and service callbacks. Owns all application state (`existing_anchors`, `new_anchors`, `mappings`, paths, assignments). Flow: Selection -> Element Browser -> Mapping -> Testing -> Results. |
| `requirements.txt` | 1 | `python-pptx>=0.6.21` |
| `README.md` | ~100 | Quick-start, architecture overview, Revelio integration notes. |
| `PPTX_TemplateUpdate_SPEC.md` | - | Original requirements specification document. |

## models/

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 0 | Package marker. |
| `anchor_record.py` | 15 | `AnchorRecord` dataclass. One detected anchor in a PPTX file. Fields: `anchor_key`, `slide_index`, `shape_name`, `detection_source`, `visible_text`, `left`, `top`, `width`, `height`, `notes`. |
| `anchor_mapping.py` | 15 | `AnchorMapping` dataclass. Links an existing anchor to a new anchor. Fields: `anchor_key`, `existing_anchor`, `new_anchor`, `include_in_test`, `test_value`, `notes`. |

## services/

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 0 | Package marker. |
| `pptx_reader.py` | 132 | Low-level PPTX shape iteration. Handles grouped shapes (recursive), table cells (`_CellShapeProxy`), alt text via lxml, shape bounds. |
| `anchor_detector.py` | 93 | Detects anchors in a PPTX file. Uses `_SLOT_RE` (shape name / alt text) and `_CURLY_RE` (visible text). Deduplicates by `(slide, key, source)`. Flags duplicates in notes. |
| `anchor_mapper.py` | 63 | Auto-matches anchors between old and new templates by normalized key. Produces `list[AnchorMapping]` with match status. |
| `test_writer.py` | 245 | Copies new template, writes test values into shapes. Handles font preservation, curly-brace replacement, split-placeholder fallback, overflow estimation. Recurses into groups and table cells via `_iter_all_writable`. |
| `validation.py` | 97 | Validation at every stage: duplicate anchor warnings, missing-pair warnings, pre-test empty-value warnings, post-write readback verification. |
| `anchor_assigner.py` | ~100 | Builds flat shape list from PPTX for the assignment UI. Converts user assignments `(slide, shape_name) -> key` into `AnchorRecord`s. Bakes `slot:key` into shape alt text (`cNvPr descr`) for future auto-detection. |

## ui/

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 0 | Package marker. |
| `main_window.py` | 42 | `MainWindow` class. Manages root Tk window, frame registration/switching, status bar at bottom. |
| `template_selection.py` | 93 | Screen 1: Two file pickers (existing + new template), Browse buttons, Load Anchors button, status label. |
| `element_browser.py` | ~250 | Screen 2: Unified Element Browser & Anchor Assignment. Tabbed Notebook (Existing / New) with Treeview grouped by slide. All shapes listed; auto-detected anchors pre-filled (blue), manually assigned (green). Inline anchor key assignment panel. Replaces the old `anchor_results.py` and `anchor_assignment.py`. |
| `mapping_view.py` | 272 | Screen 3: Full mapping table with match status, include toggle (double-click), detail panel with Comboboxes for manual remap. Select All/None/Matched buttons. |
| `testing_view.py` | 131 | Screen 4: Scrollable canvas with per-anchor cards showing existing/new context panels and `tk.Text` input for test values. |
| `results_view.py` | 116 | Screen 5: Summary counts, warnings/failures log, Open Output Folder button, Back to Testing / Start Over navigation. |
| `anchor_results.py` | 100 | (Legacy) Old Screen 2 showing only detected anchors. Replaced by `element_browser.py`. |
| `anchor_assignment.py` | ~170 | (Legacy) Old Screen 3 for manual anchor assignment. Replaced by `element_browser.py`. |

## outputs/

Generated test PPTX files go here. Created automatically by `app.py`. Not version-controlled (except test fixtures).

## TUI PHASE PROMPTS/

Phase-by-phase prompt files used during development. Not runtime code.
