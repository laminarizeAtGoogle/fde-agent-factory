#!/usr/bin/env python3
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

"""A2UI v0.9 Validator for Gemini Enterprise.

Checks A2UI component trees against known Gemini Enterprise runtime failure modes:
1. usageHint closed enum validation (flags 'h6', 'header', etc.).
2. Markdown heading syntax (#, ##, ###) conflicting with usageHint tokens.
3. Canvas root having > 1 child (which causes the 200px+ flex stretching bug).
4. Children list containing objects instead of string IDs.
5. Dangling child references or duplicate component IDs.
6. RichTable spec configuration (must be {}).
7. Non-JSON compliant numbers (NaN, inf).
8. Expansion panel title overflow (>62 chars).

Usage:
    python validate_a2ui.py components.json
    python validate_a2ui.py --inline '[{"id": "root", "component": "Canvas", ...}]'
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any, List, Set, Tuple

ALLOWED_USAGE_HINTS = {
    "h1", "h2", "h3", "h4", "h5",
    "subtitle1", "subtitle2",
    "body1", "body2",
    "caption",
}

MAX_PANEL_TITLE = 62


class ValidationError:
    def __init__(self, component_id: str, message: str, is_fatal: bool = True):
        self.component_id = component_id
        self.message = message
        self.is_fatal = is_fatal

    def __str__(self) -> str:
        prefix = "❌ [FATAL]" if self.is_fatal else "⚠️  [WARNING]"
        return f"{prefix} Component '{self.component_id}': {self.message}"


def validate_component_tree(components: List[dict[str, Any]]) -> Tuple[List[ValidationError], List[ValidationError]]:
    """Validate a list of A2UI components against GE catalog rules and runtime traps."""
    fatals: List[ValidationError] = []
    warnings: List[ValidationError] = []

    if not isinstance(components, list):
        return [ValidationError("global", "Components must be a list of component dictionaries")], []

    seen_ids: Set[str] = set()
    all_ids: Set[str] = set()
    referenced_children: Set[str] = set()
    has_root = False

    # First pass: collect IDs and verify uniqueness
    for idx, comp in enumerate(components):
        if not isinstance(comp, dict):
            fatals.append(ValidationError(f"index_{idx}", "Component is not a dictionary"))
            continue

        cid = comp.get("id")
        if not cid or not isinstance(cid, str):
            fatals.append(ValidationError(f"index_{idx}", "Missing or non-string 'id' property"))
            continue

        if cid in seen_ids:
            fatals.append(ValidationError(cid, f"Duplicate component id '{cid}'"))
        seen_ids.add(cid)
        all_ids.add(cid)

        if cid == "root":
            has_root = True

    if not has_root:
        fatals.append(ValidationError("root", "No component with 'id': 'root' found in surface"))

    # Second pass: validate properties and relationships
    for comp in components:
        if not isinstance(comp, dict):
            continue
        cid = comp.get("id", "unknown")
        ctype = comp.get("component")

        if not ctype or not isinstance(ctype, str):
            fatals.append(ValidationError(cid, "Missing or non-string 'component' type"))
            continue

        # Check children format
        children = comp.get("children")
        if children is not None:
            if not isinstance(children, list):
                fatals.append(ValidationError(cid, f"'children' must be a list of string IDs, got {type(children).__name__}"))
            else:
                for c_child in children:
                    if not isinstance(c_child, str):
                        fatals.append(ValidationError(cid, f"Child must be a string ID, found nested object: {c_child}"))
                    else:
                        referenced_children.add(c_child)

        # 1. Canvas root check
        if ctype == "Canvas":
            if cid != "root":
                warnings.append(ValidationError(cid, "Canvas is typically used exclusively as the surface 'root'", is_fatal=False))
            card_title = comp.get("cardTitle", "")
            if len(card_title) > 20:
                warnings.append(ValidationError(
                    cid,
                    f"cardTitle '{card_title}' exceeds 20 characters; GE tab strip will likely truncate it with ellipsis",
                    is_fatal=False,
                ))
            if children and len(children) > 1:
                warnings.append(ValidationError(
                    cid,
                    f"Canvas has {len(children)} direct children. GE flex-layout will stretch them vertically to fill 825px, causing 200px+ blank bands! Wrap all content into a single MaterialColumn with justify: 'start'.",
                    is_fatal=False,
                ))

        # 2. MaterialText typography and markdown conflict check
        if ctype == "MaterialText":
            hint = comp.get("usageHint")
            text = str(comp.get("text", ""))

            if hint is not None:
                if hint not in ALLOWED_USAGE_HINTS:
                    fatals.append(ValidationError(
                        cid,
                        f"Invalid usageHint '{hint}'. Closed enum: {sorted(ALLOWED_USAGE_HINTS)}. (Specifying 'h6' will blank the entire tab!)",
                    ))
                # Check for markdown heading fight
                if any(text.strip().startswith(prefix) for prefix in ("# ", "## ", "### ", "#### ")):
                    warnings.append(ValidationError(
                        cid,
                        f"Text contains markdown heading syntax ('#') while usageHint='{hint}' is set. This fights the renderer and causes small bold body text. Use plain text when usageHint is specified.",
                        is_fatal=False,
                    ))

        # 3. MaterialExpansionPanel header length
        if ctype == "MaterialExpansionPanel":
            title = str(comp.get("title", ""))
            if len(title) > MAX_PANEL_TITLE:
                warnings.append(ValidationError(
                    cid,
                    f"Expansion panel title has {len(title)} characters (> {MAX_PANEL_TITLE}). GE header strip has fixed height; title may wrap and clip.",
                    is_fatal=False,
                ))

        # 4. RichTable spec check & data inspection
        if ctype == "RichTable":
            tdata = comp.get("tableData")
            if not isinstance(tdata, dict):
                fatals.append(ValidationError(cid, "RichTable missing 'tableData' dictionary"))
            else:
                spec = tdata.get("spec")
                if spec is None:
                    warnings.append(ValidationError(
                        cid,
                        "RichTable tableData.spec is missing. Must be an empty dict {} to trigger Looker's withAutoChartConfig() without errors.",
                        is_fatal=False,
                    ))
                elif spec != {}:
                    warnings.append(ValidationError(
                        cid,
                        f"RichTable tableData.spec is {spec}. Unpopulated or partial specs cause Looker runtime error 'ERROR lg_SU' and permanent spinner. Use empty dict {{}}.",
                        is_fatal=False,
                    ))

                # Check rows for non-JSON floats
                rows = tdata.get("data", [])
                if isinstance(rows, list):
                    for r_idx, row in enumerate(rows[:50]):  # Sample first 50 rows
                        if isinstance(row, dict):
                            for col_name, val in row.items():
                                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                                    fatals.append(ValidationError(
                                        cid,
                                        f"Row {r_idx} column '{col_name}' has non-JSON float {val}. Coerce to None/null before rendering.",
                                    ))

        # 5. Button action check
        if ctype == "MaterialButton":
            action = comp.get("action")
            if action is not None:
                if not isinstance(action, dict) or "event" not in action:
                    fatals.append(ValidationError(cid, "MaterialButton action must contain an 'event' object"))
                else:
                    event = action.get("event", {})
                    if not isinstance(event, dict) or "name" not in event:
                        fatals.append(ValidationError(cid, "MaterialButton action.event must have a 'name' string"))

    # Third pass: check for dangling children
    for child_id in referenced_children:
        if child_id not in all_ids:
            fatals.append(ValidationError("children", f"Referenced child id '{child_id}' does not exist in component list"))

    return fatals, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate A2UI v0.9 Component Trees for Gemini Enterprise")
    parser.add_argument("file", nargs="?", help="Path to JSON file containing component tree")
    parser.add_argument("--inline", help="Inline JSON string of components")
    args = parser.parse_args()

    if args.inline:
        try:
            data = json.loads(args.inline)
        except Exception as e:
            print(f"❌ Failed to parse inline JSON: {e}", file=sys.stderr)
            return 1
    elif args.file:
        try:
            with open(args.file, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Failed to read {args.file}: {e}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1

    # Extract component list if wrapped in updateComponents message
    components = data
    if isinstance(data, dict):
        if "updateComponents" in data:
            components = data["updateComponents"].get("components", [])
        elif "components" in data:
            components = data["components"]

    fatals, warnings = validate_component_tree(components)

    print(f"\n🔍 Validating {len(components) if isinstance(components, list) else 0} A2UI components...")
    print("=" * 60)

    for w in warnings:
        print(w)

    for f in fatals:
        print(f)

    print("=" * 60)
    if fatals:
        print(f"❌ Validation FAILED with {len(fatals)} fatal error(s) and {len(warnings)} warning(s).")
        return 1
    elif warnings:
        print(f"⚠️  Validation PASSED with {len(warnings)} warning(s). Fix warnings for optimal UX.")
        return 0
    else:
        print("✅ Validation PASSED with 0 errors and 0 warnings! Ready for Gemini Enterprise.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
