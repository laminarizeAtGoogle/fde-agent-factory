# Gemini Enterprise A2UI Production Pitfalls & Engineering Guide

This guide documents the battle-tested failure modes, edge cases, and architectural guardrails discovered when deploying **A2UI v0.9** into **Gemini Enterprise (GE)**.

---

## 1. The Equal-Share Flex Band Bug (Canvas Blank Space)

### Symptom
When opening a Canvas side panel, the content appears with massive 200px+ blank vertical bands between elements. For example, a title bar floats in the upper-middle of the screen while an expansion card appears far down at the bottom.

### Root Cause
The Gemini Enterprise frontend lays out direct children of a `Canvas` root as flex items that **grow to share the panel's full viewport height (~825px)**. If you provide two children (e.g., `["title_row", "content_card"]`), each child gets assigned ~412px of vertical height. If `title_row` is vertically centered (`align: "center"`), its single line of text floats to the middle of its 412px allocation, leaving huge voids above and below.

### The Fix
The `Canvas` root component must have **exactly ONE child**: a single `MaterialColumn` with `justify: "start"`. All other elements must be nested inside this column.

```json
{
  "id": "root",
  "component": "Canvas",
  "children": ["main_col"]
},
{
  "id": "main_col",
  "component": "MaterialColumn",
  "justify": "start",
  "style": { "padding": "16px 20px", "gap": "16px" },
  "children": ["title_row", "content_card"]
}
```

---

## 2. Typography Token Conflict & Closed Enums

### Pitfall A: Invalid `usageHint` Values
The `usageHint` property on `MaterialText` is a strict, closed enum in the GE v0.9 catalog.
- **Allowed**: `"h1"`, `"h2"`, `"h3"`, `"h4"`, `"h5"`, `"subtitle1"`, `"subtitle2"`, `"body1"`, `"body2"`, `"caption"`.
- **Forbidden**: `"h6"`, `"title"`, `"header"`, `"display"`.
- **Failure Mode**: A single invalid value like `usageHint: "h6"` fails schema validation and **blanks the entire surface tab**, displaying:
  `"This content could not be displayed. Validation failed for component 'MaterialText' ... expected undefined, received h6"`.

### Pitfall B: Markdown Headings Fight Typography Tokens
If you put markdown heading syntax (`### Section Title`) inside a `MaterialText` that also has `usageHint: "body2"` or `usageHint: "subtitle1"`, the markdown parser and typography renderer conflict. The text renders as **small, distorted bold body copy**.
- **Rule**: When using `usageHint`, keep the `text` string plain (no `#` prefixes).
- **Rule**: Separate title and subtitle into two distinct `MaterialText` components with appropriate hints (`subtitle1` and `caption`), rather than cramming them with `\n` into one.

---

## 3. History Replay & Model Imitation Loop

### Symptom
On turns following an A2UI render, the LLM starts hand-writing raw A2UI JSON into its text response (e.g. `{"createSurface": ...}`), taking 20+ seconds of extra inference time, hallucinating broken component trees, or emitting corrupted wire sentinels.

### Root Cause
ADK (Agent Development Kit) automatically copies all previous conversation turn parts into the next prompt context (`llm_flows/contents.py::_copy_content_for_request`). When the LLM sees raw `<a2a_datapart_json>` blobs in its conversation history, few-shot conditioning causes it to imitate the wire format instead of producing natural user responses.

### The Fix: `history_callback` Sanitization
In `before_model_call`, intercept all inbound content parts before they reach the model. Convert A2UI parts into plain, human-readable summaries (`[button: Submit]`, `[table: 15 rows]`), stripping the wire envelope entirely:

```python
async def before_model_call(callback_context: Any, llm_request: Any) -> Any:
    for content in getattr(llm_request, "contents", []) or []:
        parts = getattr(content, "parts", None)
        if not parts:
            continue
        rebuilt = []
        for part in parts:
            if not is_a2ui_part(part):
                rebuilt.append(part)
            else:
                prose = readable_text(part)
                if prose:
                    rebuilt.append(types.Part(text=prose))
        content.parts = rebuilt or [types.Part(text="(interactive UI action)")]
    return None
```

---

## 4. Synthetic User Turn & Button Click Dispatches

### Symptom
When a user clicks a button (e.g. "Submit Analysis"), the agent responds with a generic greeting ("Hello! How can I help you today?") and nothing is executed.

### Root Cause
Gemini Enterprise delivers a button click as a **synthetic user turn** consisting of two parts:
1. A generic text bubble: `"User action triggered."` (or `"User action"`).
2. An `inline_data` part containing the `<a2a_datapart_json>` payload with `action.name`, `action.context`, `action.surfaceId`, and `action.sourceComponentId`.

If your agent inspects only `text`, it sees a generic prompt with zero domain keywords, which triggers default greetings or confusion.

### The Fix
Deterministically intercept synthetic UI dispatches before passing them to the LLM:
```python
def read_inbound_action(turn_parts: list[Any]) -> dict[str, Any] | None:
    for part in turn_parts:
        action = parse_a2ui_action(part)
        if action:
            return action
    return None

# In turn orchestrator:
action = read_inbound_action(user_turn_parts)
if action and action.get("name") == "submit_analysis":
    return handle_submission(action.get("context"))
```

---

## 5. Looker Studio `RichTable` Configuration (`spec: {}`)

### Pitfall A: Half-Populated `spec`
The Looker Studio interactive chart engine (`RichTable`) uses this internal logic:
```typescript
if (spec && this.hasChartSpec(spec)) builder.withSpecChartConfig(spec);
else                                 builder.withAutoChartConfig();
```
- Passing `spec: {"table": {}}` satisfies `hasChartSpec`, taking the explicit config branch with unbound metrics. This causes the Looker bundle to crash with `ERROR lg_SU`, leaving a **permanent loading spinner**.
- **Rule**: `spec` must be an **empty dictionary `{}`**. It is truthy, but bypasses `hasChartSpec`, allowing Looker's `withAutoChartConfig()` to infer column layout and sorting automatically.

### Pitfall B: Pre-Formatted Strings vs Coerced Numbers
`RichTable` sorts, filters, and auto-charts values client-side.
- If you pass `"1,234.50"` or `"$99.00"`, Looker infers `STRING`. The column cannot be sorted numerically, nor can it be visualized on a chart axis.
- **Rule**: Coerce numeric cells to raw `int` or `float` (rounded to 4 decimal places). Convert `NaN` and `+/-inf` to `None` (valid JSON `null`).

---

## 6. Canvas Tab Strip Ellipsis & Labeling

### Symptom
In Gemini Enterprise, when multiple Canvas tabs are opened, all tab headers display `"Data preview: …"` or `"Candidate Hyp…"` and cannot be distinguished.

### Root Cause
The GE tab strip is a fixed-width horizontal bar. It truncates tab headers with an ellipsis at approximately **15 to 20 characters**.

### The Fix
- Use **terse, distinctive nouns** for `cardTitle`: `"Target data"`, `"Exploratory"`, `"Hypotheses (6)"`.
- Place descriptive context in `cardDescription` (e.g. `"15 rows · claims_table"`), which renders in the chat stream chip where there is ample room.

---

## 7. Blast Radius Protection in `after_model_callback`

### Symptom
A user asks a complex question. The model finishes generating a comprehensive textual answer. Suddenly, the user gets an HTTP 500 stream failure and the entire answer disappears.

### Root Cause
If component builders run inside `after_model_callback` and throw an unhandled exception (e.g. `AttributeError` from unexpected state shape, `KeyError`, or database timeout), ADK propagates the exception out of the ASGI pipeline, terminating the HTTP response with a 500.

### The Fix: Never Fail the Turn
The side panel is an enhancement; it must never kill the primary conversation. Always wrap A2UI construction in a try/except block:
```python
def safe_canvas_parts(data: Any) -> list[types.Part]:
    try:
        return build_canvas_parts(data)
    except Exception as e:
        logger.exception("Failed to build A2UI canvas; falling back to text-only turn: %s", e)
        return []
```
If UI generation fails, the agent cleanly delivers the model's text response without crashing.
