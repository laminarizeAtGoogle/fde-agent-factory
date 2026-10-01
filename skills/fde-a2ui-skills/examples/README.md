# A2UI v0.9 Golden Pattern Examples

This directory contains battle-tested, production-ready implementation examples for building interactive A2UI components in Gemini Enterprise.

---

## Example Catalog

| File | Pattern | Key Capabilities Demonstrated |
| :--- | :--- | :--- |
| [`interactive_canvas.py`](interactive_canvas.py) | **Canvas Side Panel** | Full multi-tab side panel with anti-flex-stretch single column wrapper, action bar, collapsible `MaterialExpansionPanels`, and embedded `RichTable`. |
| [`inline_action_card.py`](inline_action_card.py) | **Inline Action Card** | Chat stream card with 2-column `MaterialButton` grid and structured round-trip event `context`. |
| [`rich_data_table.py`](rich_data_table.py) | **Looker Studio RichTable** | Dynamic data grid with automatic Looker FieldDataType inference (`DOUBLE` vs `STRING`), float rounding, and client-side sorting/filtering/auto-charting. |
| [`interactive_vega_chart.py`](interactive_vega_chart.py) | **Interactive VegaChart** | Replaces heavy ~250KB rasterized PNGs with lightweight ~3KB interactive Vega-Lite specs with hover tooltips, zoom, and extracted titles. |
| [`ge_turn_lifecycle.py`](ge_turn_lifecycle.py) | **ADK Turn Lifecycle** | Complete ADK integration: `before_model_call` history sanitization (stops LLM JSON format imitation), synthetic turn click parsing, and `after_model_callback` safe attachment (stops HTTP 500 stream failures). |

---

## How to Test Examples

You can test generating component trees and validating them with `scripts/validate_a2ui.py`:

```bash
# Validate that components adhere to Gemini Enterprise constraints
python ../scripts/validate_a2ui.py --inline '[{"id": "root", "component": "Canvas", "children": ["c1"]}, {"id": "c1", "component": "MaterialColumn", "children": []}]'
```
