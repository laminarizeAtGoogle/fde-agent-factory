# 🎨 FDE A2UI Skills: Interactive UI for Gemini Enterprise (v0.9)

Welcome to the **FDE A2UI Skills** workspace. This repository skill provides standard tooling, production patterns, and hardening guardrails for Forward Deployed Engineers (FDEs) building rich, interactive agent applications for **Gemini Enterprise (GE)** using the Google Cloud **Agent Development Kit (ADK)** and **Vertex AI Reasoning Engine**.

---

## ⚡ Overview: A2UI in Gemini Enterprise

**A2UI** (Agent-to-User Interface) enables Google Cloud agents to communicate beyond plain markdown prose. With A2UI, agents can emit:
- **Interactive Canvas Side Panels**: Resizable drawer panels with sticky action bars, collapsible accordion panels, and nested visualizations.
- **Looker Studio `RichTable` Grids**: Interactive data tables with client-side column sorting, multi-column filtering, and automatic charting inside an iframe—without incurring expensive LLM roundtrips.
- **Interactive `VegaChart` Visualizations**: Native Vega-Lite charts with browser hover tooltips, zoom, and dynamic selection, replacing heavy rasterized PNGs with ~3KB lightweight specs.
- **Action Buttons & Option Pickers**: Interactive buttons that dispatch structured intent payloads (`action.name`, `action.context`) directly back into the agent turn orchestrator.

### 🌐 Native Frontend Interception (No A2A Required)
A common misconception is that A2UI strictly requires full Agent-to-Agent (A2A) protocol negotiation or `.well-known/agent-card.json` declarations. 

**Production verified**: The Gemini Enterprise web application natively inspects the GenAI content stream and intercepts structured parts wrapped with the sentinel:
```python
Part(
    inline_data=Blob(
        mime_type="text/plain",
        data=b"<a2a_datapart_json>" + json_payload + b"</a2a_datapart_json>"
    ),
    part_metadata={"mimeType": "application/json+a2ui"}
)
```
This means **standard Vertex AI Reasoning Engine deployments and ADK agents** can immediately render interactive UIs without requiring external protocol brokers!

---

## 📁 Directory Structure

```
.agents/skills/fde-a2ui-skills/
├── SKILL.md                          # Primary agent skill instructions & trigger definitions
├── README.md                         # This comprehensive FDE engineering guide
├── scripts/
│   ├── a2ui_builder.py              # Modular Python library for generating valid A2UI v0.9 parts
│   └── validate_a2ui.py             # CLI validation utility to catch GE catalog & runtime bugs
├── examples/
│   ├── README.md                    # Examples index
│   ├── interactive_canvas.py        # Pattern: Canvas side panel with action bar, panels & table
│   ├── inline_action_card.py        # Pattern: Inline chat cards with button grids & context payloads
│   ├── rich_data_table.py           # Pattern: Looker Studio RichTable with auto-typing & charting
│   ├── interactive_vega_chart.py    # Pattern: Interactive Vega-Lite charts with title extraction
│   └── ge_turn_lifecycle.py         # Pattern: ADK callbacks, history sanitization & event dispatching
└── resources/
    ├── a2ui_reference_impl.py       # Production reference implementation from Google Health AI PQA
    ├── a2ui_v09_catalog_spec.md     # Component catalog reference (54 components, props, closed enums)
    └── ge_a2ui_pitfalls_guide.md    # Hard-won battle lessons: flex layout, typography, 500 prevention
```

---

## 🏛️ Grounding to GEAP (Gemini Enterprise Agent Platform)

This skill adheres to Google Cloud's **GEAP Best Practices**:

1. **Zero-Trust Security & PoLP**:
   - UI action payloads (`action.context`) carry identifiers (e.g. `task_id`, `table_name`), never raw credentials or secrets.
   - Server-side validation strictly verifies that any dispatched action is authorized within the user's IAM and workspace perimeter.
2. **Operational Resilience (Blast-Radius Protection)**:
   - UI component builders run inside ADK's `after_model_callback`. Unhandled exceptions in callbacks crash the ASGI pipeline with an HTTP 500 stream failure, discarding answers the model already generated.
   - All builders are wrapped with graceful degradation: if UI rendering encounters an error, the agent falls back cleanly to delivering the text response.
3. **Conversational Integrity (History Sanitization)**:
   - ADK replays past turn parts into future prompts. Leaving raw `<a2a_datapart_json>` parts in history causes the LLM to imitate the wire format and emit broken JSON.
   - `history_callback` in `before_model_call` scrubs wire syntax while preserving reader-visible summaries (`[button: Submit]`, `[table: 15 rows]`).
4. **Latency & Cost Optimization**:
   - `RichTable` sorting and filtering execute entirely in the browser iframe—saving model tokens and eliminating turn latency.
   - UI button clicks are intercepted deterministically before calling the model, preventing redundant LLM roundtrips for simple state mutations.

---

## 🚀 Quick Start for FDE Projects

### 1. Integrate Builder into your Agent Workspace
Copy `scripts/a2ui_builder.py` into your agent codebase (e.g., `app_utils/a2ui.py`):
```bash
cp .agents/skills/fde-a2ui-skills/scripts/a2ui_builder.py my_agent_project/app_utils/a2ui.py
```

### 2. Wire ADK Lifecycle Hooks in `agent.py`
```python
from my_agent_project.app_utils.a2ui import history_callback, is_a2ui_part
from my_agent_project.app_utils.canvas import build_project_canvas

async def before_model_call(callback_context: Any, llm_request: Any) -> None:
    # Scrub previous A2UI wire parts so LLM doesn't imitate raw JSON
    history_callback(callback_context, llm_request)

def after_model_callback(callback_context: Any, llm_response: Any) -> None:
    # Skip tool calls and partial streams
    if not getattr(llm_response, "content", None) or getattr(llm_response, "partial", False):
        return
    if any(getattr(p, "function_call", None) for p in llm_response.content.parts):
        return

    # Check if UI should be attached
    data = callback_context.state.get("report_data")
    if data and not any(is_a2ui_part(p) for p in llm_response.content.parts):
        try:
            parts = build_project_canvas(data)
            llm_response.content.parts.extend(parts)
        except Exception as e:
            logger.exception("A2UI generation failed; falling back to text: %s", e)
```

### 3. Intercept Inbound Button Clicks
In your turn handler or orchestrator node:
```python
from my_agent_project.app_utils.a2ui import find_a2ui_action

action = find_a2ui_action(user_turn_parts)
if action:
    event_name = action.get("name")
    context = action.get("context", {})
    if event_name == "approve_proposal":
        return execute_approval(context)
```

---

## 🛠️ Validation Utility

Run `validate_a2ui.py` to catch catastrophic failure modes prior to testing in Gemini Enterprise:

```bash
python .agents/skills/fde-a2ui-skills/scripts/validate_a2ui.py components.json
```

**Common Pitfalls Detected**:
- ❌ `usageHint: "h6"` (Closed enum violation: blanks the entire surface).
- ⚠️ Markdown `#` headings inside `MaterialText` with `usageHint` set (causes tiny bold body text).
- ⚠️ Multiple direct children under `Canvas` root (causes 200px+ vertical blank bands).
- ❌ Missing or improperly formatted `spec` in `RichTable` (must be `{}`).
- ❌ Non-JSON numbers (`NaN`, `inf`) in table rows.
- ⚠️ Expansion panel titles exceeding 62 characters (clips in fixed-height header).

---

## 📚 Deep Dive References
- [A2UI v0.9 Catalog Specification](resources/a2ui_v09_catalog_spec.md)
- [Production Pitfalls & Engineering Guide](resources/ge_a2ui_pitfalls_guide.md)
- [Production Reference Implementation (`a2ui_reference_impl.py`)](resources/a2ui_reference_impl.py)
