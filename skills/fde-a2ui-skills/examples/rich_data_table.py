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

"""Golden Pattern: Looker Studio RichTable for Gemini Enterprise.

Features:
- Looker Studio interactive visualization inside an iframe.
- Client-side column sorting, filtering, and auto-charting (zero backend model turns).
- Automated type inference ('DOUBLE' vs 'STRING').
- Number rounding & NaN/infinity sanitization.
- Mandatory empty `spec: {}` ensuring Looker enters `withAutoChartConfig()`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from google.genai import types

from ..scripts.a2ui_builder import (
    build_canvas_surface,
    build_inline_card_surface,
    coerce_cell_value,
    heading_components,
    infer_rich_data_type,
    rich_table_component,
)


def create_looker_table_surface(
    raw_rows: List[Dict[str, Any]],
    table_title: str,
    subtitle: str = "",
    in_canvas: bool = True,
    surface_id: Optional[str] = None,
    columns_to_include: Optional[List[str]] = None,
) -> List[types.Part]:
    """Build an interactive Looker Studio RichTable surface from raw dictionaries."""
    if not raw_rows:
        return []

    sid = surface_id or f"table_{uuid.uuid4().hex[:8]}"

    # Determine column set
    cols = columns_to_include or list(raw_rows[0].keys())

    # 1. Coerce values for sorting and charting
    clean_data: List[Dict[str, Any]] = []
    for r in raw_rows:
        row = {c: coerce_cell_value(r.get(c)) for c in cols}
        clean_data.append(row)

    # 2. Infer Looker FieldDataType
    schema: List[Dict[str, str]] = []
    for c in cols:
        col_values = [row.get(c) for row in clean_data]
        schema.append({
            "name": c,
            "dataType": infer_rich_data_type(col_values),
        })

    # 3. Headings & RichTable Component
    headings = heading_components(
        prefix="tbl_head",
        title=table_title,
        subtitle=subtitle or f"{len(clean_data)} rows. Sort, filter, or chart using the Looker controls.",
    )
    table_comp = rich_table_component(
        component_id="looker_table",
        schema=schema,
        data=clean_data,
    )

    all_components = headings + [table_comp]
    child_ids = [c["id"] for c in all_components]

    if in_canvas:
        return build_canvas_surface(
            surface_id=sid,
            card_title=table_title[:20],
            card_description=f"{len(clean_data)} rows · Data table",
            card_icon="table_chart",
            components=all_components,
            root_children=child_ids,
            auto_open=True,
        )

    return build_inline_card_surface(
        surface_id=sid,
        components=all_components,
        root_children=child_ids,
        appearance="outlined",
    )
