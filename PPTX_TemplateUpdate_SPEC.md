# PPTX TemplateUpdate — Product Specification

## Objective
Build a standalone local utility named **PPTX TemplateUpdate** that validates and tests anchor-based PowerPoint template updates before any integration into the Revelio production app.

The utility must let a user compare an **existing PPTX template** and a **new PPTX template**, inspect detected anchors, correct mappings if needed, choose which anchors to test, enter sample replacement text, and generate a **test PPTX output** based on the new template while preserving the template design.

This project is a **safe proving ground**. It is not the Revelio production app and it should not attempt full product integration yet.

---

## In Scope
Version 1 should support:

- Local desktop UI
- File selection for an existing template and a new template
- Anchor detection in both PPTX files
- Auto-matching anchors by normalized key
- Manual adjustment of anchor mappings
- Selecting which anchors to include in testing
- Per-anchor test text input
- Writing test text into the **new** template
- Outputting a test PPTX file
- Preserving template formatting and non-target content as much as possible
- Clear result reporting and warnings

---

## Out of Scope
Version 1 should **not** attempt to support:

- Revelio production integration
- Charts, tables, images, or advanced object mapping
- Full content generation workflows
- LLM integration
- Master slide editing
- Rebuilding slide layouts from scratch
- Broad template authoring automation

This first version is **text-anchor validation only**.

---

## Primary User Workflow
The app must support this exact flow:

1. Open the **PPTX TemplateUpdate** app
2. Browse for the **new template PPTX**
3. Browse for the **existing template PPTX**
4. Click **Load Anchors**
5. The app scans both templates and opens an **anchor mapping tool**
6. In the mapping tool:
   - show detected anchors from both templates
   - attempt auto-detection / auto-pairing
   - if auto-detection is wrong or incomplete, allow manual adjustment
   - let the user choose which anchors to include in testing
7. After mapping, go to a **Testing** screen
8. In Testing:
   - only show anchors selected for test
   - show preview/context from both old and new template
   - provide an open text field for each selected anchor
   - this field is the expected test content that should be written into the output using the **new** template
9. Click **Run Test**
10. The app writes those test values into the **new template**
11. Output a new PPTX test file
12. Preserve all template styling and non-target content as much as possible

---

## Functional Requirements

### 1. File Selection UI
Provide file pickers for:
- Existing template PPTX
- New template PPTX

Display selected file paths clearly.

### 2. Anchor Detection
Support anchor detection using this priority order:
1. Shape name contains anchor token
2. Alt text / description contains anchor token
3. Visible text contains marker token such as `{{anchor_name}}`

Supported anchor token styles:
- `slot:cover_title`
- `slot:company_name`
- `{{cover_title}}`
- `{{company_name}}`

Normalize all supported patterns to a canonical key, for example:
- `slot:cover_title` -> `cover_title`
- `{{cover_title}}` -> `cover_title`

For each detected anchor, capture:
- anchor key
- slide index
- shape name
- detection source: `shape_name`, `alt_text`, or `visible_text`
- current visible text
- shape bounds: left, top, width, height
- notes/warnings if needed

### 3. Auto-Mapping Between Old and New Templates
When the user clicks **Load Anchors**, attempt to match anchors between templates by normalized anchor key.

Create three groups:
- matched anchors
- anchors only in existing template
- anchors only in new template

### 4. Manual Mapping UI
Allow the user to correct mappings if auto-detection fails.

The UI should support:
- selecting an anchor from the existing template
- selecting the corresponding anchor from the new template
- overriding or correcting auto-matches
- excluding anchors from testing
- marking anchors for test

Suggested mapping columns:
- Include in test checkbox
- Anchor key
- Existing template anchor
- New template anchor
- Match status
- Existing slide #
- New slide #
- Detection source
- Notes / warnings

### 5. Testing Screen
After mapping, move to a testing interface that shows **only** anchors selected for testing.

For each selected anchor show:
- anchor key
- existing template preview/context
- new template preview/context
- slide number(s)
- open text field for test value

The user-entered text is what should be written to the new template output.

### 6. Preview / Context Behavior
At minimum show:
- slide number
- shape name
- original text found in anchor region
- shape bounds

If easy to implement later, add slide thumbnails with the anchored shape highlighted, but this is **not required** for v1.

### 7. Run Test Behavior
When the user clicks **Run Test**:
- duplicate the new template into an output file
- write the entered test values into the mapped new-template anchor shapes
- preserve original formatting where possible
- preserve template background and master content
- do not modify shapes that are not mapped and selected for test

### 8. Output File Naming
Generate a test output name such as:
- `NewTemplate_TEST_OUTPUT.pptx`
- or `<original_new_template_name>_anchor_test.pptx`

### 9. Validation / Reporting
After a test run, show a result summary including:
- output file path
- number of anchors selected for test
- number successfully written
- warnings
- failures

Warnings should include cases like:
- anchor detected but shape not writable
- duplicate anchor keys
- missing anchor pair
- likely overflow risk
- formatting preserved only partially

---

## Technical Design Requirements

### A. Standalone Utility
This must remain a separate small app/project. Do not integrate it into Revelio in this project.

### B. Python Desktop UI
Use a simple local Python desktop UI framework.

Preferred order:
1. **PySide6**
2. **Tkinter** if PySide6 adds too much complexity for this prototype

Choose the simplest reliable option for:
- local file browsing
- table-based mapping UI
- form-based testing UI
- future packaging

### C. PPTX Handling
Use `python-pptx` to read and write PPTX text content.

Important:
- preserve existing slide/theme/template structure as much as possible
- update only target text shapes
- do not rebuild slides from scratch

### D. Master Slides / Backgrounds
Do not edit slide masters.
Do not replace or redraw static branded background elements.

### E. Internal Data Models
Recommended model shapes:

```python
class AnchorRecord:
    anchor_key: str
    slide_index: int
    shape_name: str
    detection_source: str
    visible_text: str
    left: int
    top: int
    width: int
    height: int
    notes: list[str]
```

```python
class AnchorMapping:
    anchor_key: str
    existing_anchor: AnchorRecord | None
    new_anchor: AnchorRecord | None
    include_in_test: bool
    test_value: str
    notes: list[str]
```

### F. Suggested Project Structure

```text
PPTX_TemplateUpdate/
├── PPTX_TemplateUpdate_SPEC.md
├── README.md
├── requirements.txt
├── app.py
├── outputs/
├── models/
│   ├── anchor_record.py
│   └── anchor_mapping.py
├── services/
│   ├── pptx_reader.py
│   ├── anchor_detector.py
│   ├── anchor_mapper.py
│   ├── test_writer.py
│   └── validation.py
└── ui/
    ├── main_window.py
    ├── template_selection.py
    ├── mapping_view.py
    ├── testing_view.py
    └── results_view.py
```

### G. Session Export / Import
Optional for v1:
- save/load mapping session as JSON

This is nice to have, not required.

---

## Supported Anchor Patterns

### Shape name
Examples:
- `slot:cover_title`
- `slot:company_name`

### Alt text / description
Examples:
- `slot:cover_title`
- `slot:executive_summary`

### Visible placeholder text
Examples:
- `{{cover_title}}`
- `{{company_name}}`

All should normalize to a plain anchor key such as:
- `cover_title`
- `company_name`

Malformed anchors should be flagged with warnings.

---

## Text Writing Behavior
When writing test values into the new template:
- replace only anchor placeholder content
- preserve font styling where possible
- preserve paragraph alignment where possible
- preserve original shape position and dimensions
- do not resize shapes in v1 unless there is a compelling and safe reason

For overflow handling in v1:
- enable word wrap where practical
- preserve shape bounds
- report likely overflow as a warning when possible
- avoid aggressive font shrinking in v1 unless it is simple and reliable

The utility is primarily for validation, so warning the user is acceptable.

---

## UI Screens

### Screen 1: Template Selection
Fields:
- Existing Template file picker
- New Template file picker
- Load Anchors button

### Screen 2: Anchor Mapping
Display:
- existing template detected anchors
- new template detected anchors
- auto-match results
- manual mapping controls
- include-in-test checkboxes
- continue to testing button

### Screen 3: Testing
Display only selected mappings.
For each mapping show:
- anchor key
- existing context
- new context
- test input field

Buttons:
- Run Test
- Back to Mapping

### Screen 4: Results
Show:
- output file location
- success/failure summary
- warnings list
- open output folder button if convenient

---

## Acceptance Criteria
The project is complete only if:

1. The user can browse to an existing PPTX template and a new PPTX template.
2. The app detects anchors from both files.
3. The app shows matched and unmatched anchors.
4. The user can manually adjust mappings.
5. The user can choose which anchors to test.
6. The user can enter custom text values per selected anchor.
7. Clicking **Run Test** creates a new PPTX from the new template.
8. The output preserves template design and only updates selected anchored text fields.
9. The app reports warnings and failures clearly.
10. The code is clean enough to later serve as the reference for Revelio integration.

---

## Build Phases
Because each OpenClaw TUI session may be new, the work should be executed in discrete phases. Each phase prompt must explicitly tell OpenClaw to read this spec first, do only the requested phase, stop, and report status.

### Phase 1 — Project Scaffold + Initial UI
Goals:
- create project structure
- choose UI framework
- implement initial template selection screen
- add README and requirements

### Phase 2 — Anchor Detection Services
Goals:
- implement PPTX reading
- implement anchor detection and normalization
- load anchors from both files
- surface results into the UI

### Phase 3 — Anchor Mapping Screen
Goals:
- implement auto-matching by anchor key
- display matched/unmatched anchors
- enable manual mapping edits
- allow include/exclude for test

### Phase 4 — Testing Screen
Goals:
- show only selected mappings
- display existing/new context
- allow open-ended test text per anchor
- persist test input in app state

### Phase 5 — Test Writer + Output Generation
Goals:
- write selected test values into the new template
- produce output PPTX
- preserve style and non-target content
- show results summary and warnings

### Phase 6 — Validation + Cleanup + Integration Handoff Prep
Goals:
- strengthen validation and warnings
- polish README
- document architecture and future Revelio integration notes
- ensure project is understandable as a reference implementation

---

## Guidance for New TUI Sessions
Every phase prompt should assume a **fresh session** and therefore include these instructions:

- Read `PPTX_TemplateUpdate_SPEC.md` first and use it as the primary requirements document.
- Work only inside the project folder where the spec lives.
- Execute only the named phase.
- Do not jump ahead to future phases.
- Stop after the phase is complete and report:
  - files created or changed
  - what was implemented
  - how to run or test it
  - known limitations
  - what the next phase should do

---

## Nice-to-Haves (Later)
If time permits after core phases are stable, consider:
- slide thumbnails with highlighted anchor shapes
- save/load mapping sessions
- duplicate-anchor diagnostics
- export validation report to JSON
- packaging instructions for a Windows executable

These are not required for the first working version.
