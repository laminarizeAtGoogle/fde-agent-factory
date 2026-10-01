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

"""Golden Pattern: Inline Action Card with Button Grid for Gemini Enterprise.

Features:
- MaterialCard root rendered directly in the chat stream (not a side panel).
- 2-column button grid with MaterialButton (basic/raised variant).
- Action context payloads containing structured selection metadata.
- Manual row chunking (prevents horizontal overflow since MaterialRow has no CSS wrap).
"""

from __future__ import annotations

from typing import Any, Dict, List
import uuid

from google.genai import types

from ..scripts.a2ui_builder import (
    build_inline_card_surface,
    material_button,
    material_row,
    material_text,
)

BUTTONS_PER_ROW = 2


def create_option_picker_card(
    title: str,
    options: List[Dict[str, str]],
    event_name: str = "select_option",
) -> List[types.Part]:
    """Construct an inline interactive selection card.

    Args:
        title: Explanatory header text.
        options: List of options with 'id', 'label', and optional 'category'.
        event_name: Action event name to dispatch back to the agent.
    """
    surface_id = f"picker_{uuid.uuid4().hex[:8]}"

    components: List[Dict[str, Any]] = []
    card_children: List[str] = []

    # Title component
    title_comp = material_text(
        component_id="picker_title",
        text=title,
        usage_hint="subtitle2",
        style={"marginBottom": "8px"},
    )
    components.append(title_comp)
    card_children.append("picker_title")

    # Build buttons
    btn_ids: List[str] = []
    for idx, opt in enumerate(options):
        btn_id = f"btn_{idx}"
        btn = material_button(
            component_id=btn_id,
            label=opt["label"],
            action_name=event_name,
            action_context={"option_id": opt["id"], "label": opt["label"], **opt},
            variant="basic",  # Renders like a clickable link/chip
            leading_icon="touch_app",
        )
        components.append(btn)
        btn_ids.append(btn_id)

    # Chunk buttons into rows of 2 to prevent horizontal overflow in narrow chat stream
    for r_idx in range(0, len(btn_ids), BUTTONS_PER_ROW):
        row_id = f"row_{r_idx}"
        chunk = btn_ids[r_idx : r_idx + BUTTONS_PER_ROW]
        row_comp = material_row(
            component_id=row_id,
            children=chunk,
            align="center",
            style={"marginBottom": "4px"},
        )
        components.append(row_comp)
        card_children.append(row_id)

    return build_inline_card_surface(
        surface_id=surface_id,
        components=components,
        root_children=card_children,
        appearance="outlined",
    )
