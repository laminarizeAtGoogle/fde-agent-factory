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

"""Golden Pattern: Interactive VegaChart for Gemini Enterprise.

Features:
- Vega-Lite JSON specification bound via `updateDataModel` (path: `/spec`).
- Replaces heavy rasterized PNG charts (~250KB) with lightweight, interactive specs (~3KB).
- Enables native browser hover tooltips, zoom, and interactive legend selection.
- Automatic extraction of title and subtitle into MaterialText components (GE drops native Vega titles).
- Support for inline chat stream cards or resizable Canvas side panels.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from google.genai import types

from ..scripts.a2ui_builder import (
    build_vega_chart_surface,
)


def create_sample_bar_chart(
    categories: List[str],
    values: List[float],
    title: str = "Quarterly Distribution",
    subtitle: str = "Interactive breakdown with hover inspection",
    in_canvas: bool = False,
) -> List[types.Part]:
    """Construct an interactive Vega-Lite bar chart surface."""
    surface_id = f"chart_{uuid.uuid4().hex[:8]}"

    # Standard Vega-Lite v5 specification
    vega_spec: Dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": title,
        "width": "container",
        "height": 320,
        "data": {
            "values": [
                {"category": cat, "value": val}
                for cat, val in zip(categories, values)
            ]
        },
        "mark": {"type": "bar", "cornerRadiusEnd": 4, "tooltip": True},
        "encoding": {
            "x": {
                "field": "category",
                "type": "nominal",
                "axis": {"labelAngle": 0, "title": None},
            },
            "y": {
                "field": "value",
                "type": "quantitative",
                "axis": {"title": "Metric Value"},
            },
            "color": {
                "field": "category",
                "type": "nominal",
                "legend": None,
                "scale": {"scheme": "tableau10"},
            },
            "tooltip": [
                {"field": "category", "type": "nominal", "title": "Category"},
                {"field": "value", "type": "quantitative", "title": "Value", "format": ",.2f"},
            ],
        },
    }

    return build_vega_chart_surface(
        surface_id=surface_id,
        spec=vega_spec,
        title=title,
        subtitle=subtitle,
        in_canvas=in_canvas,
        card_title="Bar Chart",
        card_description=f"{len(categories)} categories",
        height=380,
    )
