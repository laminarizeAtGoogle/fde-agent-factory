# A2UI v0.9 Catalog Specification & Component Reference

This document provides the definitive specification for **A2UI v0.9** in **Gemini Enterprise (GE)**.

Catalog URI:
`https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json`

MIME Type:
`application/json+a2ui`

---

## 1. Wire Format & Envelope

Gemini Enterprise intercepts structured A2UI parts in the content stream wrapped in the `<a2a_datapart_json>` sentinel:

```python
{
    "kind": "data",
    "metadata": {
        "mimeType": "application/json+a2ui"
    },
    "data": {
        "version": "v0.9",
        # One of: "createSurface" | "updateComponents" | "updateDataModel"
        ...
    }
}
```

Wrapped inside a GenAI `types.Part`:
```python
from google.genai import types

blob_bytes = f"<a2a_datapart_json>{json_payload}</a2a_datapart_json>".encode("utf-8")
part = types.Part(
    inline_data=types.Blob(mime_type="text/plain", data=blob_bytes),
    part_metadata={"mimeType": "application/json+a2ui"}
)
```

---

## 2. Core Protocol Messages

A complete A2UI surface lifecycle uses these messages in mandatory sequence:

### `createSurface`
Initializes the surface and binds it to a catalog.
```json
{
  "version": "v0.9",
  "createSurface": {
    "surfaceId": "unique_surface_id",
    "catalogId": "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
  }
}
```

### `updateComponents`
Supplies the flat list of components that define the UI tree.
```json
{
  "version": "v0.9",
  "updateComponents": {
    "surfaceId": "unique_surface_id",
    "components": [
      {
        "id": "root",
        "component": "Canvas",
        "children": ["main_col"]
      },
      ...
    ]
  }
}
```

### `updateDataModel` (Optional)
Supplies state values referenced by JSON Pointer (e.g., `/spec` for `VegaChart`).
```json
{
  "version": "v0.9",
  "updateDataModel": {
    "surfaceId": "unique_surface_id",
    "path": "/spec",
    "value": { ... }
  }
}
```

---

## 3. Surface Containers (Root Component)

Every surface must have an element with `"id": "root"`. The component type determines where it renders:

| Container | Render Location | Behavior |
| :--- | :--- | :--- |
| `Canvas` | Right Side Panel (Drawer/Canvas) | Collapses to an interactive launcher chip in the chat stream. Opens expandable canvas tab. |
| `MaterialCard` | Inline in Chat Stream | Renders directly in the message flow. Ideal for inline forms, pickers, buttons, and alerts. |

### `Canvas` Properties
- `id`: `"root"`
- `component`: `"Canvas"`
- `children`: Array of child component IDs (Must be a single `MaterialColumn` to avoid the flex-stretch bug!)
- `cardTitle`: String. Short title (max ~15-20 characters before the tab strip truncates with ellipsis).
- `cardDescription`: String. Secondary label shown in the chat chip (e.g., `"15 rows · Target"`).
- `cardIcon`: String. Material icon name (e.g., `"science"`, `"table_chart"`, `"bar_chart"`).
- `autoOpen`: Boolean. `False` for general chat responses (avoids jarring user context switch); `True` only when responding directly to a user's click requesting that preview.

### `MaterialCard` Properties
- `id`: `"root"` (or nested card id)
- `component`: `"MaterialCard"`
- `appearance`: `"outlined"` | `"elevated"` | `"filled"`
- `children`: Array of child component IDs.
- `style`: Optional CSS properties dictionary.

---

## 4. Layout Components

All containers reference children by **component ID** in a flat list, NEVER nested dictionaries!

### `MaterialColumn`
Vertical flex container.
- `id`: String
- `component`: `"MaterialColumn"`
- `children`: Array of child component IDs.
- `justify`: `"start"` | `"center"` | `"end"` | `"spaceBetween"` | `"spaceAround"` | `"spaceEvenly"` (Default: `"start"`)
- `align`: `"start"` | `"center"` | `"end"` | `"stretch"` (Default: `"stretch"`)
- `style`: CSS dictionary, e.g. `{"padding": "16px", "gap": "12px"}`

### `MaterialRow`
Horizontal flex container.
- `id`: String
- `component`: `"MaterialRow"`
- `children`: Array of child component IDs.
- `justify`: `"start"` | `"center"` | `"end"` | `"spaceBetween"` | `"spaceAround"` | `"spaceEvenly"`
- `align`: `"start"` | `"center"` | `"end"` | `"stretch"` (Default: `"center"`)
- `style`: CSS dictionary. Note: `MaterialRow` does NOT auto-wrap; manually chunk into rows of 2-3 items.

### `MaterialDivider`
Horizontal rule.
- `id`: String
- `component`: `"MaterialDivider"`

### `MaterialExpansionPanel`
Collapsible accordion panel.
- `id`: String
- `component`: `"MaterialExpansionPanel"`
- `title`: String. Header title (truncate at 62 characters to avoid wrapping/overflowing the fixed-height header strip).
- `expanded`: Boolean. Initial expanded state.
- `children`: Array of child component IDs.
- `style`: CSS dictionary.

---

## 5. Typography & Text Components

### `MaterialText`
The primary text rendering component.
- `id`: String
- `component`: `"MaterialText"`
- `text`: String. Plain text or markdown.
- `usageHint`: **CLOSED ENUM**. Must be one of:
  - `"h1"`, `"h2"`, `"h3"`, `"h4"`, `"h5"` (Note: **NO `"h6"`!** Specifying `"h6"` crashes validation and blanks the surface!)
  - `"subtitle1"`, `"subtitle2"`
  - `"body1"`, `"body2"`
  - `"caption"`
- **Critical Rule**: When using `usageHint`, DO NOT include markdown heading symbols (`#`, `##`, `###`) inside `text`. Markdown headings fight typography tokens, causing text to render as small, bold body copy. Keep text clean and plain.

---

## 6. Interactive Components & Buttons

### `MaterialButton`
Clickable button that triggers backend events.
- `id`: String
- `component`: `"MaterialButton"`
- `label`: String. Button text.
- `variant`: `"raised"` (solid) | `"basic"` (text link style) | `"outlined"` (bordered)
- `color`: `"primary"` | `"secondary"`
- `leadingIcon`: Optional Material icon name (e.g. `"send"`, `"table_chart"`, `"check"`)
- `disabled`: Boolean.
- `action`:
  ```json
  {
    "event": {
      "name": "your_action_event_name",
      "context": {
        "key": "value"
      }
    }
  }
  ```
  `context` round-trips back to the backend in the synthetic turn.

---

## 7. Data Display Components

### `RichTable` (Looker Studio Interactive Table)
The standard interactive data grid in Gemini Enterprise. Sorts, filters, and auto-charts in-place inside an iframe.
- `id`: String
- `component`: `"RichTable"`
- `tableData`:
  - `schema`: Array of `{"name": str, "dataType": "STRING" | "DOUBLE"}`
  - `data`: Array of row dictionaries keyed by column name
  - `spec`: **MUST be `{}`** (empty dictionary). Do NOT omit `spec`, and do NOT pass partial specifications like `{"table": {}}` or the Looker renderer will encounter a permanent loading spinner (`ERROR lg_SU`).
- Cell Values: Numbers must be numeric types (`int`, `float`), not pre-formatted strings (`"1,234.50"`), so Looker can sort and chart them. Floats should be rounded (e.g. `round(val, 4)`). `NaN` and `inf` are forbidden.

### `VegaChart` (Interactive Vega-Lite Visualizations)
Renders high-fidelity, interactive charts with hover tooltips, zooming, and selections.
- `id`: String
- `component`: `"VegaChart"`
- `spec`: JSON Pointer binding `{"path": "/spec"}`
- `height`: Integer height in pixels (recommended: 350-450).
- Data Model: The Vega-Lite JSON specification is sent in the `updateDataModel` message at `/spec`.
- Note: GE frontend does not render the Vega-Lite `title` block. Always extract the chart title into a `MaterialText` (`usageHint: "subtitle1"`) component placed above the chart.
