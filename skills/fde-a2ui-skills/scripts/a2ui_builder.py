# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A2UI v0.9 Component Builder Library for Gemini Enterprise.

Provides robust, production-tested helpers to construct valid A2UI v0.9 GenAI Parts,
parse inbound UI events, and manage conversation state safely.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from google.genai import types

logger = logging.getLogger(__name__)

# Protocol Constants
VERSION = "v0.9"
CATALOG_ID = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
)
MIME = "application/json+a2ui"

SENTINEL_OPEN = "<a2a_datapart_json>"
SENTINEL_CLOSE = "</a2a_datapart_json>"

# Typography allowed usageHint enum values
ALLOWED_USAGE_HINTS = {
    "h1", "h2", "h3", "h4", "h5",
    "subtitle1", "subtitle2",
    "body1", "body2",
    "caption",
}

# Max characters before an expansion panel header wraps and clips
MAX_PANEL_TITLE = 62


# ---------------------------------------------------------------------------
# GenAI Part Wire Wrapping & Decoding
# ---------------------------------------------------------------------------

def wrap_message(message: dict[str, Any]) -> types.Part:
    """Wrap a single A2UI message as a GenAI Part intercepted natively by Gemini Enterprise."""
    payload = json.dumps({"kind": "data", "metadata": {"mimeType": MIME}, "data": message})
    blob_bytes = (SENTINEL_OPEN + payload + SENTINEL_CLOSE).encode("utf-8")
    return types.Part(
        inline_data=types.Blob(mime_type="text/plain", data=blob_bytes),
        part_metadata={"mimeType": MIME},
    )


def is_a2ui_part(part: Any) -> bool:
    """Return True if part is an A2UI part emitted for the frontend."""
    meta = getattr(part, "part_metadata", None)
    if isinstance(meta, dict) and meta.get("mimeType") == MIME:
        return True
    blob = getattr(part, "inline_data", None)
    data = getattr(blob, "data", None)
    return isinstance(data, (bytes, bytearray)) and data.lstrip().startswith(
        SENTINEL_OPEN.encode("utf-8")
    )


def decode_a2ui_payload(part: Any) -> Optional[dict[str, Any]]:
    """Decode the JSON envelope of an A2UI part, or None if invalid/absent."""
    blob = getattr(part, "inline_data", None)
    data = getattr(blob, "data", None)
    if not isinstance(data, (bytes, bytearray)):
        return None
    try:
        text = bytes(data).decode("utf-8", errors="replace").strip()
    except Exception:
        return None
    if not text.startswith(SENTINEL_OPEN):
        return None
    payload = text[len(SENTINEL_OPEN):]
    if SENTINEL_CLOSE in payload:
        payload = payload.split(SENTINEL_CLOSE, 1)[0]
    try:
        envelope = json.loads(payload)
    except (ValueError, TypeError):
        return None
    return envelope if isinstance(envelope, dict) else None


def parse_a2ui_action(part: Any) -> Optional[dict[str, Any]]:
    """Decode the A2UI action payload sent by Gemini Enterprise on user interaction.

    Returns the action dictionary containing 'name', 'context', 'sourceComponentId', 'surfaceId',
    or None if the part does not represent an action.
    """
    envelope = decode_a2ui_payload(part)
    if envelope is None:
        return None
    data = envelope.get("data", {})
    if isinstance(data, dict):
        action = data.get("action")
        if isinstance(action, dict):
            return action
    return None


def find_a2ui_action(parts: Any) -> Optional[dict[str, Any]]:
    """Return the first decodable inbound A2UI action across parts, or None."""
    for part in parts or []:
        action = parse_a2ui_action(part)
        if action:
            return action
    return None


def as_surface_patch(parts: Any) -> list[types.Part]:
    """Filter A2UI parts to keep only update messages, dropping createSurface.

    Used when repainting an already open surface to prevent duplicate tab creation.
    """
    patch: list[types.Part] = []
    for part in parts or []:
        envelope = decode_a2ui_payload(part)
        if envelope is None:
            continue
        message = envelope.get("data")
        if not isinstance(message, dict) or "createSurface" in message:
            continue
        patch.append(part)
    return patch


# ---------------------------------------------------------------------------
# History Sanitization & Model Imitation Prevention
# ---------------------------------------------------------------------------

def _component_lines(components: Any) -> list[str]:
    """Extract reader-visible text from a component list in reading order."""
    out: list[str] = []
    for c in components if isinstance(components, list) else []:
        if not isinstance(c, dict):
            continue
        for key in ("cardTitle", "title", "text", "cardDescription"):
            val = c.get(key)
            if isinstance(val, str) and val.strip():
                out.append(val.strip())
        label = c.get("label")
        if isinstance(label, str) and label.strip():
            out.append(f"[button: {label.strip()}]")
        table = c.get("tableData")
        if isinstance(table, dict):
            rows = table.get("data")
            out.append(f"[table: {len(rows)} rows]" if isinstance(rows, list) else "[table]")
        if c.get("component") == "VegaChart":
            out.append("[interactive chart]")
    return out


def readable_text(part: Any) -> str:
    """Return plain-text representation of what a user sees in an A2UI part."""
    envelope = decode_a2ui_payload(part)
    if envelope is None:
        return ""
    message = envelope.get("data")
    if not isinstance(message, dict):
        return ""
    components = (message.get("updateComponents") or {}).get("components")
    return "\n\n".join(_component_lines(components))


def history_callback(callback_context: Any, llm_request: Any) -> None:
    """Clean A2UI parts in prior turns so the LLM does not imitate raw JSON wire format.

    Replaces A2UI parts with plain text summaries while preserving conversational grounding.
    """
    for content in getattr(llm_request, "contents", []) or []:
        parts = getattr(content, "parts", None)
        if not parts:
            continue
        had_a2ui = False
        rebuilt = []
        for part in parts:
            if not is_a2ui_part(part):
                rebuilt.append(part)
                continue
            had_a2ui = True
            prose = readable_text(part)
            if prose:
                rebuilt.append(types.Part(text=prose))
        if had_a2ui and not rebuilt:
            rebuilt = [types.Part(text="(interactive UI action)")]
        content.parts = rebuilt
    return None


# ---------------------------------------------------------------------------
# Data Coercion & Looker Studio Table Formatting
# ---------------------------------------------------------------------------

def coerce_cell_value(val: Any) -> Any:
    """Coerce cell values into JSON-safe types that Looker RichTable can sort and chart.

    Numbers remain numeric (rounded to 4 decimal places); null/NaN/inf become None.
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val != val or val in (float("inf"), float("-inf")):
            return None
        return round(val, 4)
    return str(val)


def infer_rich_data_type(values: list[Any]) -> str:
    """Infer Looker FieldDataType ('DOUBLE' or 'STRING') from sample values."""
    saw_number = False
    for v in values:
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return "STRING"
        saw_number = True
    return "DOUBLE" if saw_number else "STRING"


# ---------------------------------------------------------------------------
# Component Builders
# ---------------------------------------------------------------------------

def heading_components(prefix: str, title: str, subtitle: str = "") -> list[dict[str, Any]]:
    """Build a clean title and optional subtitle as separate MaterialText components.

    Ensures no markdown heading syntax conflicts with typography hints.
    """
    out: list[dict[str, Any]] = []
    t = (title or "").strip()
    s = (subtitle or "").strip()
    if t:
        out.append({
            "id": f"{prefix}_title",
            "component": "MaterialText",
            "text": t,
            "usageHint": "subtitle1",
            "style": {"marginTop": "8px", "marginBottom": "4px" if s else "16px"},
        })
    if s:
        out.append({
            "id": f"{prefix}_sub",
            "component": "MaterialText",
            "text": s,
            "usageHint": "caption",
            "style": {"marginTop": "0px", "marginBottom": "16px"},
        })
    return out


def material_text(
    component_id: str,
    text: str,
    usage_hint: str = "body1",
    style: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a validated MaterialText component."""
    hint = usage_hint.strip()
    if hint not in ALLOWED_USAGE_HINTS:
        logger.warning("usageHint '%s' is not in allowed enum; falling back to 'body1'", hint)
        hint = "body1"
    comp = {
        "id": component_id,
        "component": "MaterialText",
        "text": text,
        "usageHint": hint,
    }
    if style:
        comp["style"] = style
    return comp


def material_button(
    component_id: str,
    label: str,
    action_name: str,
    action_context: Optional[dict[str, Any]] = None,
    variant: str = "raised",
    color: str = "primary",
    leading_icon: Optional[str] = None,
    disabled: bool = False,
    style: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a clickable MaterialButton component with action event and context."""
    comp: dict[str, Any] = {
        "id": component_id,
        "component": "MaterialButton",
        "label": label,
        "variant": variant,
        "color": color,
        "disabled": disabled,
        "action": {
            "event": {
                "name": action_name,
                "context": action_context or {},
            }
        },
    }
    if leading_icon:
        comp["leadingIcon"] = leading_icon
    if style:
        comp["style"] = style
    return comp


def material_row(
    component_id: str,
    children: list[str],
    justify: str = "start",
    align: str = "center",
    style: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a MaterialRow flex container."""
    comp: dict[str, Any] = {
        "id": component_id,
        "component": "MaterialRow",
        "justify": justify,
        "align": align,
        "children": children,
    }
    if style:
        comp["style"] = style
    return comp


def material_column(
    component_id: str,
    children: list[str],
    justify: str = "start",
    align: str = "stretch",
    style: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a MaterialColumn flex container."""
    comp: dict[str, Any] = {
        "id": component_id,
        "component": "MaterialColumn",
        "justify": justify,
        "align": align,
        "children": children,
    }
    if style:
        comp["style"] = style
    return comp


def material_card(
    component_id: str,
    children: list[str],
    appearance: str = "outlined",
    style: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a MaterialCard container."""
    comp: dict[str, Any] = {
        "id": component_id,
        "component": "MaterialCard",
        "appearance": appearance,
        "children": children,
    }
    if style:
        comp["style"] = style
    return comp


def material_expansion_panel(
    component_id: str,
    title: str,
    children: list[str],
    expanded: bool = False,
    style: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a MaterialExpansionPanel with header length safety."""
    panel_title = title.strip()
    if len(panel_title) > MAX_PANEL_TITLE:
        panel_title = panel_title[:MAX_PANEL_TITLE - 1].rstrip() + "…"
    comp: dict[str, Any] = {
        "id": component_id,
        "component": "MaterialExpansionPanel",
        "title": panel_title,
        "expanded": expanded,
        "children": children,
    }
    if style:
        comp["style"] = style
    return comp


def rich_table_component(
    component_id: str,
    schema: list[dict[str, str]],
    data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Construct a Looker Studio RichTable component.

    Critical: spec MUST be an empty dict {} to engage withAutoChartConfig() without crashing.
    """
    return {
        "id": component_id,
        "component": "RichTable",
        "tableData": {
            "schema": schema,
            "data": data,
            "spec": {},
        },
    }


# ---------------------------------------------------------------------------
# High-Level Surface Builders
# ---------------------------------------------------------------------------

def build_canvas_surface(
    surface_id: Optional[str],
    card_title: str,
    card_description: str,
    card_icon: str,
    components: list[dict[str, Any]],
    root_children: list[str],
    auto_open: bool = False,
) -> list[types.Part]:
    """Construct a complete Canvas side panel surface with anti-flex-stretch protection.

    Packs all content into a single MaterialColumn under Canvas root to prevent 200px+ blank bands.
    """
    sid = surface_id or f"canvas_{uuid.uuid4().hex[:8]}"

    # Single wrapper column to fix GE equal-share flex item height bug
    main_col_id = f"{sid}_main_col"
    main_col = material_column(
        component_id=main_col_id,
        children=root_children,
        justify="start",
        style={"padding": "16px 20px", "gap": "16px"},
    )

    root_component = {
        "id": "root",
        "component": "Canvas",
        "children": [main_col_id],
        "cardTitle": card_title[:20],  # Avoid tab strip ellipsis truncation
        "cardDescription": card_description,
        "cardIcon": card_icon,
        "autoOpen": auto_open,
    }

    all_components = [root_component, main_col] + components

    return [
        wrap_message({"version": VERSION, "createSurface": {"surfaceId": sid, "catalogId": CATALOG_ID}}),
        wrap_message({"version": VERSION, "updateComponents": {"surfaceId": sid, "components": all_components}}),
    ]


def build_inline_card_surface(
    surface_id: Optional[str],
    components: list[dict[str, Any]],
    root_children: list[str],
    appearance: str = "outlined",
) -> list[types.Part]:
    """Construct an inline chat stream surface (MaterialCard root)."""
    sid = surface_id or f"inline_{uuid.uuid4().hex[:8]}"
    root_component = {
        "id": "root",
        "component": "MaterialCard",
        "appearance": appearance,
        "children": root_children,
    }
    all_components = [root_component] + components
    return [
        wrap_message({"version": VERSION, "createSurface": {"surfaceId": sid, "catalogId": CATALOG_ID}}),
        wrap_message({"version": VERSION, "updateComponents": {"surfaceId": sid, "components": all_components}}),
    ]


def build_vega_chart_surface(
    surface_id: Optional[str],
    spec: dict[str, Any],
    title: str = "",
    subtitle: str = "",
    in_canvas: bool = False,
    card_title: str = "Chart",
    card_description: str = "Interactive visualization",
    height: int = 420,
) -> list[types.Part]:
    """Construct an interactive VegaChart surface with title extraction and data model binding."""
    sid = surface_id or f"chart_{uuid.uuid4().hex[:8]}"
    heading = heading_components("chart_head", title, subtitle)
    chart_comp = {
        "id": "vega_chart",
        "component": "VegaChart",
        "spec": {"path": "/spec"},
        "height": height,
    }

    body_ids = [c["id"] for c in heading] + ["vega_chart"]
    components = heading + [chart_comp]

    if in_canvas:
        return build_canvas_surface(
            surface_id=sid,
            card_title=card_title,
            card_description=card_description,
            card_icon="bar_chart",
            components=components,
            root_children=body_ids,
            auto_open=True,
        ) + [
            wrap_message({"version": VERSION, "updateDataModel": {"surfaceId": sid, "path": "/spec", "value": spec}})
        ]

    # Inline card
    inline_parts = build_inline_card_surface(
        surface_id=sid,
        components=components,
        root_children=body_ids,
        appearance="outlined",
    )
    data_model_part = wrap_message(
        {"version": VERSION, "updateDataModel": {"surfaceId": sid, "path": "/spec", "value": spec}}
    )
    return inline_parts + [data_model_part]
