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

"""Golden Pattern: Interactive Canvas Side Panel for Gemini Enterprise.

Features:
- Canvas root with compact launcher chip (cardTitle, cardDescription, cardIcon).
- Anti-flex-stretch layout wrapper (single MaterialColumn root).
- Top action bar with MaterialText title and primary MaterialButton.
- Collapsible MaterialExpansionPanels for complex items.
- Looker Studio RichTable preview embedded inside the panel.
"""

from __future__ import annotations

from typing import Any, Dict, List
import uuid

from google.genai import types

from ..scripts.a2ui_builder import (
    build_canvas_surface,
    heading_components,
    material_button,
    material_card,
    material_column,
    material_expansion_panel,
    material_row,
    material_text,
    rich_table_component,
)


def create_analysis_canvas(
    title: str,
    items: List[Dict[str, Any]],
    table_schema: List[Dict[str, str]],
    table_data: List[Dict[str, Any]],
    action_name: str = "submit_execution",
) -> List[types.Part]:
    """Construct an interactive analysis Canvas side panel."""
    surface_id = f"analysis_{uuid.uuid4().hex[:8]}"
    count = len(items)

    components: List[Dict[str, Any]] = []
    col_children: List[str] = []

    # 1. Top Action Bar: Title + Action Button
    submit_btn = material_button(
        component_id="action_btn",
        label=f"Execute {count} Selected Tasks",
        action_name=action_name,
        action_context={"task_count": count, "surface_id": surface_id},
        variant="raised",
        color="primary",
        leading_icon="send",
    )
    title_text = material_text(
        component_id="header_title",
        text=f"{title} ({count})",
        usage_hint="subtitle1",
    )
    action_bar = material_row(
        component_id="action_bar",
        children=["header_title", "action_btn"],
        justify="spaceBetween",
        align="center",
    )
    components.extend([title_text, submit_btn, action_bar])
    col_children.append("action_bar")

    # 2. Expansion Panels for items
    panel_ids: List[str] = []
    for idx, item in enumerate(items, 1):
        p_id = f"panel_{idx}"
        p_title = item.get("name", f"Task {idx}")
        p_desc = item.get("description", "")
        p_details = item.get("details", "")

        desc_id = f"p_{idx}_desc"
        det_id = f"p_{idx}_det"

        components.append(material_text(desc_id, p_desc, usage_hint="body2"))
        components.append(material_text(det_id, f"**Details**: {p_details}", usage_hint="caption"))

        panel = material_expansion_panel(
            component_id=p_id,
            title=f"#{idx}: {p_title}",
            children=[desc_id, det_id],
            expanded=(idx == 1),  # Expand first panel by default
            style={"marginBottom": "8px"},
        )
        components.append(panel)
        panel_ids.append(p_id)

    # Wrap expansion panels inside an outlined card
    panels_card = material_card(
        component_id="panels_card",
        children=panel_ids,
        appearance="outlined",
        style={"padding": "8px"},
    )
    components.append(panels_card)
    col_children.append("panels_card")

    # 3. Looker Studio RichTable Section
    if table_data:
        table_headings = heading_components(
            prefix="table_sec",
            title="Sample Data Preview",
            subtitle=f"{len(table_data)} sample rows. Sort, filter, and chart in-place.",
        )
        components.extend(table_headings)
        col_children.extend([c["id"] for c in table_headings])

        table_comp = rich_table_component(
            component_id="data_table",
            schema=table_schema,
            data=table_data,
        )
        components.append(table_comp)
        col_children.append("data_table")

    # Build the full Canvas surface with single top-level column protection
    return build_canvas_surface(
        surface_id=surface_id,
        card_title=title[:20],
        card_description=f"{count} tasks ready for execution",
        card_icon="science",
        components=components,
        root_children=col_children,
        auto_open=False,  # Don't yank user away from conversational chat stream
    )
