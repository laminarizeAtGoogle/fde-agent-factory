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

"""A2UI v0.9 components for Gemini Enterprise in the Population Questionnaire Agent.

Emits structured A2UI parts in the `<a2a_datapart_json>` format intercepted natively by
the Gemini Enterprise frontend.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from typing import Any
import uuid

from google.genai import types

logger = logging.getLogger(__name__)


def _coerce_cell_value(val: Any) -> Any:
    """Coerce a BigQuery cell into a JSON-safe value a `RichTable` can sort and chart.

    `RichTable` is a Looker Studio viz: it sorts, filters and auto-charts the values ITSELF, so it
    needs `1234.5` and not `"1,234.50"`. Pre-formatted strings are exactly what made the previous
    `MaterialTable` preview look static — every column arrived as `STRING`, so nothing was orderable.

    Floats are ROUNDED here rather than formatted: `withAutoChartConfig()` applies no number
    formatting of its own, so a raw float64 renders as `87.16788000000001` and gets clipped mid-number
    by the column width (the same failure documented in `pop_insights_agent`'s `rich_table_component`).
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val != val or val in (float("inf"), float("-inf")):  # NaN / inf are not valid JSON
            return None
        return round(val, 4)
    # Dates, timestamps, Decimals, BQ STRUCT/ARRAY values: Looker takes them as their text form.
    return str(val)


def _infer_rich_data_type(values: list[Any]) -> str:
    """Pick a Looker `FieldDataType` for a column from its sampled values.

    The enum values are the literal strings (`STRING = 'STRING'`). Everything numeric is a `DOUBLE` —
    the distinction between an integer count and a ratio is a FORMATTING concern, not a typing one.
    A column that is entirely NULL in the sample is `STRING`, the type that accepts anything.
    """
    saw_number = False
    for v in values:
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return "STRING"
        saw_number = True
    return "DOUBLE" if saw_number else "STRING"


def _normalize_table_id(table_name: str, project_id: str | None = None) -> str:
    """Resolve shorthand or partial table names into fully qualified project.dataset.table strings."""
    if not table_name:
        return ""
    clean = table_name.strip("`'\" ").strip()
    proj = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "hcls-agentspace")
    parts = clean.split(".")
    if len(parts) == 1:
        tbl = parts[0]
        if any(k in tbl.lower() for k in ("member", "user", "claim", "patient")):
            return f"{proj}.phai_member.{tbl}"
        return f"{proj}.phai_sources.{tbl}"
    elif len(parts) == 2:
        return f"{proj}.{parts[0]}.{parts[1]}"
    return clean


def fetch_table_preview_rows(
    table_name: str,
    requested_columns: list[str] | None = None,
    limit: int = 15,
    strict: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Fetch live BigQuery sample rows for grounded tables and columns.

    Args:
        strict: select ONLY the requested columns, plus at most one identity column for
            context. The default (False) is the older behaviour used by the whole-table
            previews: up to three context columns are prepended and the result is padded out
            to at least four columns with whatever comes first in the table.

            Padding is wrong for a column click. Asking for `feature_127` on a 330-column PDI
            table returned `zip_code, feature_127` plus four arbitrary neighbours, so the answer
            to "show me this column" read like a table dump and buried the column the user
            actually asked about.

    Returns:
        tuple of (schema, data) in `RichTable.tableData` shape: `schema` is a list of
        `{"name", "dataType"}` Looker fields and `data` is a list of TYPED row dicts keyed by the
        raw BigQuery column name. Column names are left raw rather than humanized because the
        schema `name` and the row keys are the same identifier to Looker — prettifying one without
        the other silently drops the column from the viz.
    """
    if os.getenv("DISABLE_A2UI_PREVIEW") == "1":
        return [], []
    if not table_name:
        return [], []
    full_table = _normalize_table_id(table_name)
    if not full_table:
        return [], []

    try:
        from google.cloud import bigquery
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "hcls-agentspace")
        client = bigquery.Client(project=project_id)
        query = f"SELECT * FROM `{full_table}` LIMIT {limit}"
        result_rows = list(client.query(query).result())
        if not result_rows:
            return [], []

        row_dicts = [dict(r.items()) for r in result_rows]
        all_cols = list(row_dicts[0].keys())

        # Key contextual entity columns, most identifying first.
        context_candidates = ["user_id", "state_name", "state", "zip_code", "zipcode", "age"]

        def _resolve(col: Any) -> str:
            """The real column name for a grounded name, or "" if the table has no such column.

            Grounding and BigQuery disagree on the zip column's spelling depending on the table,
            and the model writes whichever it saw, so the two are treated as aliases.
            """
            c = str(col).strip()
            if not c:
                return ""
            if c in all_cols:
                return c
            for a, b in (("zipcode", "zip_code"), ("zip_code", "zipcode")):
                if c == a and b in all_cols:
                    return b
            return ""

        selected_cols: list[str] = []

        if strict:
            # Exactly one identity column, purely so the rows are readable — a bare column of
            # floats says nothing about which postal code or member each row belongs to.
            for c in context_candidates:
                if c in all_cols:
                    selected_cols.append(c)
                    break
            for col in requested_columns or []:
                c = _resolve(col)
                if c and c not in selected_cols:
                    selected_cols.append(c)
                if len(selected_cols) >= 8:
                    break
            # Deliberately no padding here. If nothing resolved we would be left with just the
            # identity column, which is not an answer, so fall through to the old selection
            # rather than show a one-column table.
            if len(selected_cols) <= 1:
                selected_cols = []

        if not selected_cols:
            for c in context_candidates:
                if c in all_cols and c not in selected_cols:
                    selected_cols.append(c)
                    if len(selected_cols) >= 3:
                        break

            # Grounded requested columns
            if requested_columns:
                for col in requested_columns:
                    c = _resolve(col)
                    if c and c not in selected_cols:
                        selected_cols.append(c)
                    if len(selected_cols) >= 8:
                        break

            # Fallback to general columns if too few
            if len(selected_cols) < 4:
                for c in all_cols:
                    if c not in selected_cols:
                        selected_cols.append(c)
                    if len(selected_cols) >= 6:
                        break

        data: list[dict[str, Any]] = [
            {c: _coerce_cell_value(r.get(c)) for c in selected_cols} for r in row_dicts
        ]

        schema = [
            {"name": c, "dataType": _infer_rich_data_type([row.get(c) for row in data])}
            for c in selected_cols
        ]
        return schema, data
    except Exception as e:
        logger.warning("fetch_table_preview_rows failed for %s: %s", full_table, e)
        return [], []


VERSION = "v0.9"
CATALOG_ID = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
)
MIME = "application/json+a2ui"

SENTINEL_OPEN = "<a2a_datapart_json>"
SENTINEL_CLOSE = "</a2a_datapart_json>"


def _wrap(message: dict) -> types.Part:
    """Wrap a single A2UI message as a GenAI Part intercepted by Gemini Enterprise frontend."""
    payload = json.dumps(
        {"kind": "data", "metadata": {"mimeType": MIME}, "data": message}
    )
    blob_bytes = (SENTINEL_OPEN + payload + SENTINEL_CLOSE).encode("utf-8")
    return types.Part(
        inline_data=types.Blob(mime_type="text/plain", data=blob_bytes),
        part_metadata={"mimeType": MIME},
    )


def is_a2ui_part(part: Any) -> bool:
    """True if part is an A2UI part emitted for the frontend."""
    meta = getattr(part, "part_metadata", None)
    if isinstance(meta, dict) and meta.get("mimeType") == MIME:
        return True
    blob = getattr(part, "inline_data", None)
    data = getattr(blob, "data", None)
    return isinstance(data, bytes) and data.lstrip().startswith(
        SENTINEL_OPEN.encode("utf-8")
    )


def _decode_a2ui_payload(part: Any) -> dict[str, Any] | None:
    """The decoded JSON envelope of an A2UI part, or None if this part is not one.

    Shared by the inbound reader (`parse_a2ui_action`) and the outbound rewriter
    (`as_surface_patch`) because both directions use the identical `<a2a_datapart_json>`
    envelope — GE echoes our own wire format straight back on a click.
    """
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
    # The close sentinel is not guaranteed — truncate on it only when present.
    payload = text[len(SENTINEL_OPEN):]
    if SENTINEL_CLOSE in payload:
        payload = payload.split(SENTINEL_CLOSE, 1)[0]
    try:
        envelope = json.loads(payload)
    except (ValueError, TypeError):
        return None
    return envelope if isinstance(envelope, dict) else None


def parse_a2ui_action(part: Any) -> dict[str, Any] | None:
    """Decode the A2UI `action` payload GE sends back when a user clicks a component.

    A click produces TWO parts on the synthetic user turn: a generic text bubble reading
    "User action triggered." and an `inline_data` part using the SAME `<a2a_datapart_json>`
    envelope we emit outbound. Captured verbatim from Agent Runtime, 2026-09-14::

        {"data": {"action": {"context": {},
                             "name": "submit_job",
                             "sourceComponentId": "submit_btn",
                             "surfaceId": "hyp_86ee5ba9",
                             "timestamp": "2026-09-14T04:00:58.324Z"},
                  "version": "v0.9"}}

    Four things matter here:

    * `name` is the `action.event.name` we put on the button, so dispatches can be told apart
      by intent instead of by GE's generic label. Matching the label works only while exactly
      one clickable component exists.
    * `context` round-trips. It is empty above only because our Submit button sends none — this
      is the channel for "which column did they click".
    * `sourceComponentId` identifies the exact component, which is a usable fallback key when
      an action deliberately carries no context.
    * `surfaceId` names the LIVE surface the click came from, which is what makes it possible to
      patch that existing tab on a later turn instead of opening a new one — see
      `as_surface_patch`.

    Returns the inner `action` dict, or None if this part is not an inbound action.
    """
    envelope = _decode_a2ui_payload(part)
    if envelope is None:
        return None
    action = envelope.get("data", {})
    action = action.get("action") if isinstance(action, dict) else None
    return action if isinstance(action, dict) else None


def as_surface_patch(parts: Any) -> list[types.Part]:
    """Keep only the messages that UPDATE an existing surface, dropping every `createSurface`.

    Used to re-render a Canvas tab the user is already looking at — specifically, to grey out
    the Submit button on the turn after they click it. The click payload hands us the live
    `surfaceId` (see `parse_a2ui_action`), so rebuilding the same component tree against that id
    and sending only the `updateComponents` message should repaint the open tab in place.

    Two deliberate constraints, both about not knowing GE's semantics rather than about style:

    * `createSurface` is stripped because re-announcing an id that already exists is undefined
      here — the plausible failure is a duplicate tab in the strip, and the strip already
      accumulates tabs (known GE surface accumulation issue). Dropping it is the conservative half:
      if the surface is gone the patch is simply ignored, which costs nothing.
    * The CALLER must pass the FULL component list for the surface, not just the components that
      changed. Whether `updateComponents` merges by id or replaces the whole map is unverified,
      and a full list is correct under both readings — whereas a three-component patch would
      blank the entire tab under replace semantics. This codebase has already lost a whole tab
      once to a surface-level validation failure (`usageHint: h6`), so the blast radius here is
      not hypothetical.

    UNPROVEN IN GE as of 2026-09-14: no cross-turn patch has been observed working. The visual
    disable is therefore best-effort and the real duplicate-submit protection is the
    `job_submitted` check in `agent.enrichment_orchestrator`.
    """
    patch: list[types.Part] = []
    for part in parts or []:
        envelope = _decode_a2ui_payload(part)
        if envelope is None:
            continue
        # `createSurface` sits one level down, under `data` — `_wrap` builds
        # `{"kind", "metadata", "data": {"version", "createSurface"|"updateComponents"}}`, the
        # same nesting `parse_a2ui_action` reaches through for `data.action`. Testing the top
        # level instead matches nothing and quietly passes every message through, which is
        # exactly what the first version of this did.
        message = envelope.get("data")
        if not isinstance(message, dict) or "createSurface" in message:
            continue
        patch.append(part)
    return patch


def find_a2ui_action(parts: Any) -> dict[str, Any] | None:
    """The first decodable inbound A2UI action across `parts`, or None."""
    for part in parts or []:
        action = parse_a2ui_action(part)
        if action:
            return action
    return None


def _component_lines(components: Any) -> list[str]:
    """The reader-visible text of a component list, in the order it was emitted.

    The tree is flat and built in reading order, so walking the list IS the reading order.

    The property names here are PQA's, not the insights agent's, and the difference matters: a
    straight port of that agent's version reads only `text`/`tableData` and would silently return
    almost nothing for a PQA Canvas, whose content lives in `cardTitle`/`cardDescription`
    (Canvas, MaterialCard) and `title` (MaterialExpansionPanel — the hypothesis panel headings).

    A `RichTable` contributes its shape rather than its rows. The rows are a live BigQuery preview
    the model never wrote and does not need to re-read; replaying a few hundred cells of sample
    data would cost more context than it returns.
    """
    out: list[str] = []

    def add(value: str) -> None:
        """Append `value`, unless it is a CLIPPED restatement of something already added.

        The hypothesis heading reaches this function twice — once in full from the card, and once
        from the expansion-panel title, which is clipped to 62 chars with an ellipsis so the tab
        strip stays readable. Emitting both replays every heading one and a half times for no
        added meaning.

        The suppression is deliberately narrow: it applies ONLY to values that are themselves
        ellipsis-clipped. A first attempt de-duplicated every repeat, which looked right on one
        hypothesis and quietly destroyed the structure of the rest — "**Core Concept**" and
        "**Variables & Mode**" are *supposed* to recur once per hypothesis, and suppressing them
        left every panel after the first as unlabelled prose.
        """
        value = value.strip()
        if not value:
            return
        if value.endswith("…"):
            stem = value[:-1].strip()
            if stem and any(seen.startswith(stem) for seen in out):
                return
        out.append(value)

    for c in components if isinstance(components, list) else []:
        if not isinstance(c, dict):
            continue
        for key in ("cardTitle", "title", "text", "cardDescription"):
            value = c.get(key)
            if isinstance(value, str):
                add(value)
        label = c.get("label")
        if isinstance(label, str) and label.strip():
            # Buttons are state, not prose: "Submitted 6 Hypotheses" vs "Submit 6 Hypotheses" is
            # how the model can tell from history alone that the job already went in.
            out.append(f"[button: {label.strip()}]")
        table = c.get("tableData")
        if isinstance(table, dict):
            rows = table.get("data")
            out.append(f"[table: {len(rows)} rows]" if isinstance(rows, list) else "[table]")
    return out


def readable_text(part: Any) -> str:
    """What a reader saw in an A2UI part, as plain text — or `""` when there is nothing to say.

    Only `updateComponents` yields anything. PQA emits a bare `createSurface` (surfaceId +
    catalogId, no components) immediately followed by the `updateComponents` that fills it, so the
    prose is never lost by ignoring the former.
    """
    envelope = _decode_a2ui_payload(part)
    if envelope is None:
        return ""
    message = envelope.get("data")
    if not isinstance(message, dict):
        return ""
    components = (message.get("updateComponents") or {}).get("components")
    return "\n\n".join(_component_lines(components))


def history_callback(callback_context: Any, llm_request: Any) -> None:
    """Replace replayed A2UI parts with the text a reader saw, so the model does not imitate A2UI JSON.

    Keep the content, drop the instruction.

    This used to delete A2UI parts outright, which stopped the model imitating the wire format but
    also erased its only record of what it had just shown. That bites PQA harder than it bites the
    insights agent, because PQA's Canvas carries SERVER-BUILT content the model never wrote —
    hypothesis panels, grounded column lists, table previews. With the parts gone, "change the
    second one" or "why did you pick that column" are questions about a panel the model cannot
    see, and it has no way to know it is guessing.

    A part with no readable prose is still dropped; and a turn whose parts were ALL A2UI collapses
    to a placeholder rather than an empty `parts` list, because a Content with no parts is not
    something every backend accepts.
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


def create_submit_button_parts(
    surface_id: str | None = None,
    count: int | None = None,
) -> list[types.Part]:
    """Constructs native A2UI v0.9 parts for the Submit Hypotheses button in Gemini Enterprise."""
    sid = surface_id or f"submit_{uuid.uuid4().hex[:8]}"

    create_surface_msg = {
        "version": VERSION,
        "createSurface": {
            "surfaceId": sid,
            "catalogId": CATALOG_ID,
        },
    }

    label_text = (
        f"Submit {count} Hypotheses for Execution"
        if count and count > 0
        else "Submit Hypotheses for Execution"
    )

    components = [
        {
            "id": "root",
            "component": "MaterialColumn",
            "children": ["submit_card"],
        },
        {
            "id": "submit_card",
            "component": "MaterialCard",
            "appearance": "outlined",
            "children": ["submit_row"],
        },
        {
            "id": "submit_row",
            "component": "MaterialRow",
            "justify": "spaceBetween",
            "align": "center",
            "children": ["submit_text", "submit_btn"],
        },
        {
            "id": "submit_text",
            "component": "MaterialText",
            "text": (
                "Ready to execute these hypotheses against population data in parallel?"
            ),
            "usageHint": "body2",
        },
        {
            "id": "submit_btn",
            "component": "MaterialButton",
            "label": label_text,
            "variant": "raised",
            "color": "primary",
            "leadingIcon": "send",
            "action": {
                "event": {
                    "name": "submit_job",
                },
            },
        },
    ]

    update_components_msg = {
        "version": VERSION,
        "updateComponents": {
            "surfaceId": sid,
            "components": components,
        },
    }

    return [_wrap(create_surface_msg), _wrap(update_components_msg)]


def rich_table_component(
    component_id: str,
    schema: list[dict[str, str]],
    data: list[dict[str, Any]],
) -> dict[str, Any]:
    """A `RichTable` — the Looker Studio viz, and the only interactive table in the GE catalog.

    `MaterialTable` provably cannot sort: its template is a bare `mat-table` with no `matSort`
    directive and no `mat-sort-header`, so sorting is ABSENT rather than switched off. That is why
    the previous preview looked static. A Looker table sorts, filters and paginates inside its own
    iframe, gives a sticky header, and exposes a Chart/Data switcher — all at no cost to us.

    `tableData` is a LITERAL object (`{schema, data, spec}`), not a data-model binding.

    `spec` is deliberately `{}` and NOT omitted. From Looker's
    `interactive_chart/lit_interactive_chart.ts`:

        if (spec && this.hasChartSpec(spec)) builder.withSpecChartConfig(spec);
        else                                 builder.withAutoChartConfig();

    `hasChartSpec` is true when the object names a viz (`table`, `barChart`, ...), so a
    half-populated `{"table": {}}` takes the EXPLICIT branch with no dimensions or metrics bound and
    the Looker bundle dies on it (`ERROR lg_SU`, permanent spinner). An empty `{}` is truthy but
    fails `hasChartSpec`, so the host infers the layout from the schema instead. See the same
    reasoning, measured against live GE, in `pop_insights_agent/app/a2ui.py::rich_table_component`.

    ## The "Add filter" bar and Chart/Data switcher cannot be removed, and that is accepted

    They are the viz host's own chrome on the `withAutoChartConfig()` branch, not something
    `tableData` controls — `RichTable` takes `tableData` and nothing else. Suppressing them would
    mean the `withSpecChartConfig` branch with a FULLY populated spec (every required proto
    field), which is the branch that already failed as a permanent spinner when it was only
    partly populated. There is no middle setting.

    Asked and answered 2026-09-14: keep the toolbar. Dropping to `MaterialTable` would remove it
    but also removes sorting, the sticky header and the Looker styling — which is the "it looks
    static" complaint that put us on `RichTable` in the first place. Do not trade back without
    revisiting that.
    """
    return {
        "id": component_id,
        "component": "RichTable",
        "tableData": {"schema": schema, "data": data, "spec": {}},
    }


# Longest "Hypothesis N: <title>" that stays on ONE line in the expansion panel header at the
# Canvas's width. Past this the header wraps and overflows its fixed height.
_MAX_PANEL_TITLE = 62

# Whether the target / exploratory BigQuery preview tabs are built at all.
#
# OFF since 2026-09-14. Two reasons, and the second is the real one:
#
#   1. Three chips per turn was too much furniture for what they gave back.
#   2. They were STRUCTURALLY WRONG. Only the first target table and the first exploratory table
#      ever got a tab (`if ... and not target_table`), while columns were accumulated across ALL
#      hypotheses into one list and queried against that single table. Columns belonging to any
#      other table were silently dropped by the `c in all_cols` filter in
#      `fetch_table_preview_rows` — no error, they just were not there. A preview that quietly
#      shows the wrong grounding is worse than no preview.
#
# The builder below is intact and still covered by tests; flip this to re-enable it. The intended
# replacement is a preview opened per-column on demand — see `docs` in the commit that set this.
ENABLE_PREVIEW_TABS = os.getenv("ENABLE_A2UI_PREVIEW_TABS", "0") == "1"


def heading_components(prefix: str, title: str, subtitle: str = "") -> list[dict[str, Any]]:
    """A tab heading as a TITLE component plus an optional CAPTION component.

    Two rules here, both learned from how this rendered wrong (2026-09-14):

    1. NO markdown heading syntax in `text`. A `MaterialText` carrying "### Live BigQuery Data
       Preview" with `usageHint: "body2"` puts the markdown renderer and the typography token in
       direct conflict — GE applies the `body2` token to text the markdown has already marked as a
       heading, and what lands is small bold body copy. It reads as a styling bug, because it is
       one. `usageHint` is the ONLY typography control; the text must be plain.
    2. Title and subtitle are SEPARATE components. Crammed into one `text` with a `\\n` between
       them, both get the same token and the heading stops being a heading.

    `subtitle1` + `caption` mirrors `pop_insights_agent/app/a2ui.py` (`_table_heading`, and the
    per-table headings in `_combined_parts`), which is the look this agent is being matched to.
    """
    out: list[dict[str, Any]] = []
    title = (title or "").strip()
    subtitle = (subtitle or "").strip()
    if title:
        out.append({
            "id": f"{prefix}_title",
            "component": "MaterialText",
            "text": title,
            "usageHint": "subtitle1",
            "style": {
                "marginTop": "8px",
                "marginBottom": "4px" if subtitle else "16px",
            },
        })
    if subtitle:
        out.append({
            "id": f"{prefix}_sub",
            "component": "MaterialText",
            "text": subtitle,
            "usageHint": "caption",
            "style": {
                "marginTop": "0px",
                "marginBottom": "16px",
            },
        })
    return out


def _humanize_key(key: str) -> str:
    """`min_pass_ratio` -> `Min pass ratio`. Keeps acronyms that are already upper-case."""
    words = str(key).replace("-", "_").split("_")
    out = []
    for i, w in enumerate(words):
        if not w:
            continue
        out.append(w if w.isupper() else (w.capitalize() if i == 0 else w.lower()))
    return " ".join(out) or str(key)


def _scalar_str(value: Any) -> str:
    """A compact, human-readable rendering of a leaf value."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        # Thresholds like 0.08 and 0.001 must not become 0.08000000000000001.
        return f"{value:g}"
    return str(value).strip()


def format_spec_value(value: Any, _depth: int = 0) -> str:
    """Render a Blueprint sub-spec as readable markdown, NOT as a Python repr.

    The hypothesis blocks (`metric_transformation`, `g_validation`, `r_cohort`, `temporal_split`)
    are nested dicts in session state. Passing them through `str()` dumped raw Python into the
    Canvas — a live panel read:

        {'target_association_min_spearman_rho': 0.08, 'minimum_target_lift_decile_10_vs_1_pct': 10,
         'mann_whitney_u_max_pvalue': 0.05, 'target_association_max_pvalue': 0.05, ...}

    ...quotes, braces, underscores and all. This turns the same data into labelled bullets.

    `None` and empty values are DROPPED rather than printed: `'secondary_variable': None` and
    `'cohort_filter_sql': None` are "not configured", and printing them as "None" invites the
    reader to think something is broken.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            rendered = format_spec_value(v, _depth + 1)
            if rendered == "":
                continue
            lines.append(f"{'  ' * _depth}• **{_humanize_key(k)}**: {rendered}")
        return "\n".join(lines) if _depth == 0 else ", ".join(
            f"{_humanize_key(k)}={format_spec_value(v, _depth + 1)}"
            for k, v in value.items() if format_spec_value(v, _depth + 1) != ""
        )
    if isinstance(value, (list, tuple)):
        rendered = [format_spec_value(v, _depth + 1) for v in value]
        rendered = [r for r in rendered if r]
        if not rendered:
            return ""
        if _depth == 0:
            return "\n".join(f"• {r}" for r in rendered)
        return ", ".join(rendered)
    return _scalar_str(value)


def variables_and_mode_text(h: dict[str, Any]) -> str:
    """Render one hypothesis's mode, target and exploratory tables as the "Variables & Mode" body.

    Extracted from `create_schema_canvas_part_groups` on 2026-09-15 so the post-execution
    results Canvas can show the same summary the user approved before submitting. It is shared
    rather than copied because the null-handling below is the accumulated result of several
    live failures, and a second copy would drift away from it silently.

    The defensive bits are all load-bearing:
      * `target_variables` entries can be null, or bare strings instead of objects;
      * `feature_cols` can contain nulls, and `", ".join` raises TypeError on one, while
        `fc[0]`/`fc[-1]` would print "None .. None";
      * either block can arrive as a list instead of a dict.
    """
    mode = str(h.get("mode") or h.get("Mode") or "F_latent")

    t_tgt = h.get("t_target") or h.get("T_target") or {}
    if isinstance(t_tgt, dict):
        tbl = t_tgt.get("table", "")
        tv = []
        for v in t_tgt.get("target_variables") or []:
            if isinstance(v, dict):
                v_name = v.get("name") or "?"
                tv.append(f"`{v_name}` ({v.get('role', 'primary')}, {v.get('aggregation', 'mean')})")
            elif isinstance(v, str) and v.strip():
                tv.append(f"`{v.strip()}`")
        target_desc = f"{tbl} ({', '.join(tv)})" if tv else tbl
    elif isinstance(t_tgt, list):
        target_desc = ", ".join(str(x) for x in t_tgt)
    else:
        target_desc = str(t_tgt)

    t_exp = h.get("t_expl") or h.get("T_expl") or {}
    if isinstance(t_exp, dict):
        tbl = t_exp.get("table", "")
        fc = [str(c).strip() for c in (t_exp.get("feature_cols") or []) if c is not None and str(c).strip()]
        if len(fc) > 10:
            col_str = f"{fc[0]} .. {fc[-1]} ({len(fc)} features)"
        elif fc:
            col_str = ", ".join(fc)
        else:
            col_str = "All features"
        expl_desc = f"{tbl} ({col_str})" if tbl else col_str
    elif isinstance(t_exp, list):
        if len(t_exp) > 10:
            expl_desc = f"{t_exp[0]} .. {t_exp[-1]} ({len(t_exp)} features)"
        else:
            expl_desc = ", ".join(str(x) for x in t_exp)
    else:
        expl_desc = str(t_exp)

    return f"• **Mode**: `{mode}`\n• **Target**: {target_desc}\n• **Exploratory**: {expl_desc}"


def create_schema_canvas_part_groups(
    surface_id: str | None = None,
    hypotheses: list[dict[str, Any]] | None = None,
    data_grounding: dict[str, Any] | None = None,
    fetch_preview: bool = True,
    preview_fetcher: Any = None,
    submit_disabled: bool = False,
) -> dict[str, list[types.Part]]:
    """The Canvas parts, KEYED BY TAB (`target`, `exploratory`, `hypotheses`).

    Grouped rather than flat because the caller places each group at a different point in the
    response. GE renders one chat-stream chip per surface, positioned wherever that surface's
    parts sit among the response parts — so returning a flat list pins all three chips to the
    bottom of the turn, far from the prose each one belongs to. See
    `agent._interleave_canvas_parts`.

    Constructs native A2UI v0.9 parts for the Canvas side panel in Gemini Enterprise.

    When candidate hypotheses exist, opens a Canvas tab containing:
    1. A Submit Hypotheses button card at the top.
    2. Each candidate hypothesis as a collapsible MaterialExpansionPanel.
    3. Live BigQuery Sample Data Preview tables for target and exploratory datasets.

    When only data grounding exists, displays the live BigQuery sample data preview tables.
    """
    target_table = ""
    target_columns: list[str] = []
    expl_table = ""
    expl_columns: list[str] = []

    # Extract target and exploratory columns from active hypotheses.
    #
    # EVERY value below is model-authored and reaches us straight out of session state, so nothing
    # here may assume a shape. This ran with a bare `var.get("name")` until a turn produced
    # `target_variables: [null]` — one null element in an otherwise well-formed list — and the
    # `AttributeError` propagated out of `_after_model_callback` and took the WHOLE TURN down with
    # a 500, losing an answer the model had already finished generating. The Canvas is a side
    # panel; it must never be able to do that. `_coerce_name` and the isinstance guards are the
    # belt, and the try/except in the callers is the braces.
    def _coerce_name(value: Any) -> str:
        """A column name from either `{"name": "x"}` or a bare `"x"`, or "" for anything else."""
        if isinstance(value, dict):
            name = value.get("name", "")
            return name.strip() if isinstance(name, str) else ""
        if isinstance(value, str):
            return value.strip()
        return ""

    for h in hypotheses or []:
        if not isinstance(h, dict):
            logger.warning("Skipping non-dict hypothesis in canvas build: %r", type(h))
            continue

        t_target = h.get("t_target") or h.get("T_target") or {}
        if isinstance(t_target, dict):
            tbl = t_target.get("table", "")
            if isinstance(tbl, str) and tbl and not target_table:
                target_table = tbl
            for var in t_target.get("target_variables") or []:
                name = _coerce_name(var)
                if name and name not in target_columns:
                    target_columns.append(name)
        elif isinstance(t_target, list):
            for t_item in t_target:
                if isinstance(t_item, dict):
                    tbl = t_item.get("table", "")
                    if isinstance(tbl, str) and tbl and not target_table:
                        target_table = tbl
                name = _coerce_name(t_item)
                if name and name not in target_columns:
                    target_columns.append(name)

        t_expl = h.get("t_expl") or h.get("T_expl") or {}
        if isinstance(t_expl, dict):
            tbl_expl = t_expl.get("table", "")
            if isinstance(tbl_expl, str) and tbl_expl and not expl_table:
                expl_table = tbl_expl
            for fc in t_expl.get("feature_cols") or []:
                name = _coerce_name(fc)
                if name and name not in expl_columns:
                    expl_columns.append(name)
        elif isinstance(t_expl, list):
            for e_item in t_expl:
                name = _coerce_name(e_item)
                if name and name not in expl_columns:
                    expl_columns.append(name)

    # Fallback to data_grounding state if no hypotheses yet
    if not target_table and isinstance(data_grounding, dict):
        for ds, tbls in (data_grounding.get("target_columns") or {}).items():
            if not isinstance(tbls, dict):
                continue
            for tbl, cols in tbls.items():
                if not target_table:
                    target_table = f"{ds}.{tbl}"
                for c in cols or []:
                    name = _coerce_name(c)
                    if name and name not in target_columns:
                        target_columns.append(name)
    if not expl_table and isinstance(data_grounding, dict):
        for ds, tbls in (data_grounding.get("exploratory_columns") or {}).items():
            if not isinstance(tbls, dict):
                continue
            for tbl, cols in tbls.items():
                if not expl_table:
                    expl_table = f"{ds}.{tbl}"
                for c in cols or []:
                    name = _coerce_name(c)
                    if name and name not in expl_columns:
                        expl_columns.append(name)

    # Fetch live BigQuery preview rows if enabled
    target_schema: list[dict[str, str]] = []
    target_preview_rows: list[dict[str, Any]] = []
    expl_schema: list[dict[str, str]] = []
    expl_preview_rows: list[dict[str, Any]] = []

    if fetch_preview and ENABLE_PREVIEW_TABS and (target_table or expl_table):
        fetch_fn = preview_fetcher or fetch_table_preview_rows
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_tgt = executor.submit(fetch_fn, target_table, target_columns, 15) if target_table else None
            fut_exp = executor.submit(fetch_fn, expl_table, expl_columns, 15) if expl_table else None

            if fut_tgt:
                try:
                    target_schema, target_preview_rows = fut_tgt.result(timeout=4.0)
                except Exception as exc:
                    logger.warning("Error fetching target preview for %s: %s", target_table, exc)
            if fut_exp:
                try:
                    expl_schema, expl_preview_rows = fut_exp.result(timeout=4.0)
                except Exception as exc:
                    logger.warning("Error fetching exploratory preview for %s: %s", expl_table, exc)

    # The picker is built from `data_grounding` directly, not from the hypotheses, so it survives
    # a turn that grounds columns without yet proposing anything.
    pickers_by_table = create_column_picker_parts_by_table(data_grounding)
    column_picker = [p for _t, parts in pickers_by_table for p in parts]

    if not hypotheses and not target_preview_rows and not expl_preview_rows and not column_picker:
        return {}

    groups: dict[str, Any] = {}
    if column_picker:
        # Both forms. `columns` is the flat fallback every generic consumer understands
        # (`CANVAS_GROUP_ORDER`, the append-everything error path); `columns_by_table` carries the
        # table name the interleaver needs to position each card individually. Keeping the flat
        # form means a placement failure still renders the buttons, just grouped together.
        groups["columns"] = column_picker
        groups["columns_by_table"] = pickers_by_table

    # Tab 1: Target Data Preview (Dedicated Canvas tab)
    if target_preview_rows:
        t_sid = f"target_{uuid.uuid4().hex[:8]}"
        t_short = target_table.split(".")[-1] if target_table else "Target"
        t_heading = heading_components(
            "target_heading",
            f"Target data · {t_short}",
            f"{len(target_preview_rows)} sample rows from {target_table}. "
            "Sort, filter and chart them in place.",
        )
        t_components = [
            {
                "id": "root",
                "component": "Canvas",
                "children": [c["id"] for c in t_heading] + ["target_table"],
                # SHORT title, detail in `cardDescription` -- the split `pop_insights_agent`
                # uses ("Data table" / "24 rows"). The Canvas TAB renders `cardTitle` only, in
                # a fixed-width strip that ellipsises at roughly fifteen characters, so
                # whatever identifies the tab has to come first and has to be brief. Titles
                # that began with a shared prefix all collapsed to the same "Data preview: …"
                # and the strip became unreadable (observed 2026-09-14 with four tabs open).
                #
                # This reverses an earlier decision to omit `cardDescription` so the chat-stream
                # chip would stay one line tall. That was worth it when three preview chips
                # stacked in a single turn, but the preview tabs are off by default now
                # (`ENABLE_PREVIEW_TABS`), so the cost is one extra line on one chip -- and it
                # buys back the table name that no longer fits in the title.
                "cardTitle": "Target data",
                "cardDescription": f"{len(target_preview_rows)} rows · {t_short}",
                "cardIcon": "table_chart",
                "autoOpen": True if not hypotheses else False,
            },
            *t_heading,
            rich_table_component("target_table", target_schema, target_preview_rows),
        ]
        groups["target"] = [
            _wrap({"version": VERSION, "createSurface": {"surfaceId": t_sid, "catalogId": CATALOG_ID}}),
            _wrap({"version": VERSION, "updateComponents": {"surfaceId": t_sid, "components": t_components}}),
        ]

    # Tab 2: Exploratory Data Preview (Dedicated Canvas tab)
    if expl_preview_rows:
        e_sid = f"expl_{uuid.uuid4().hex[:8]}"
        e_short = expl_table.split(".")[-1] if expl_table else "Exploratory"
        e_heading = heading_components(
            "expl_heading",
            f"Exploratory data · {e_short}",
            f"{len(expl_preview_rows)} sample rows from {expl_table}. "
            "Sort, filter and chart them in place.",
        )
        e_components = [
            {
                "id": "root",
                "component": "Canvas",
                "children": [c["id"] for c in e_heading] + ["expl_table"],
                "cardTitle": "Exploratory data",
                "cardDescription": f"{len(expl_preview_rows)} rows · {e_short}",
                "cardIcon": "table_chart",
                "autoOpen": True if not hypotheses else False,
            },
            *e_heading,
            rich_table_component("expl_table", expl_schema, expl_preview_rows),
        ]
        groups["exploratory"] = [
            _wrap({"version": VERSION, "createSurface": {"surfaceId": e_sid, "catalogId": CATALOG_ID}}),
            _wrap({"version": VERSION, "updateComponents": {"surfaceId": e_sid, "components": e_components}}),
        ]

    # Tab 3: Hypotheses Tab (Dedicated Canvas tab, auto-opened & focused by default)
    if hypotheses:
        h_sid = surface_id or f"hyp_{uuid.uuid4().hex[:8]}"
        count = len(hypotheses)
        label_text = (f"Submitted {count} Hypotheses" if submit_disabled
                      else f"Submit {count} Hypotheses for Execution")

        h_components: list[dict[str, Any]] = []
        h_children: list[str] = []
        panel_ids: list[str] = []

        # Top Right Button Bar: Title on left, Submit button on top right
        h_components.extend([
            {
                "id": "submit_bar",
                "component": "MaterialRow",
                "justify": "spaceBetween",
                "align": "center",
                "children": ["submit_title", "submit_btn"],
            },
            {
                "id": "submit_title",
                "component": "MaterialText",
                "text": f"Candidate Hypotheses ({count})",
                # Plain text, NOT "### Candidate Hypotheses". Markdown heading syntax fights the
                # typography token and renders as small bold body copy — see `heading_components`.
                #
                # `usageHint` is a CLOSED enum in the GE catalog — `h1`-`h5`, `caption`, `body`,
                # `subtitle1`, `subtitle2`, `body1`, `body2`. There is no `h6`, and a bad hint
                # rejects the WHOLE surface before rendering any of it: one of them replaced this
                # entire tab with "This content could not be displayed. Validation failed for
                # component 'MaterialText' (submit_title): usageHint: Expected undefined,
                # received h6".
                #
                # That rule is narrower than it first looked, and the distinction matters when
                # reaching for a component that may not be in the catalog. Measured in live GE
                # on 2026-09-15 with five isolated surfaces:
                #
                #   bad property VALUE on a known component -> whole surface rejected (this case)
                #   structurally invalid component, e.g. no
                #     "component" key at all                -> whole surface rejected, no chip
                #   unknown component NAME                  -> silently SKIPPED; the rest of the
                #                                              surface renders, with no error
                #
                # `CodeViewer` (a real widget-internal component, absent from the v0.9 catalog)
                # was indistinguishable from a made-up name: chip fine, siblings fine, component
                # simply gone. So an unrecognised component cannot take a tab down — but it also
                # fails INVISIBLY, which is worse to debug. If you ever emit a non-catalog
                # component, put a known-good sibling next to it, or its absence looks exactly
                # like the surface never arrived.
                "usageHint": "subtitle1",
            },
            {
                "id": "submit_btn",
                "component": "MaterialButton",
                "label": label_text,
                "variant": "raised",
                "color": "primary",
                "leadingIcon": "check" if submit_disabled else "send",
                # `disabled` is a real `MaterialButton` property in the GE catalog, but whether
                # GE honours it on a CROSS-TURN surface patch is unverified — see
                # `as_surface_patch`. So the `action` is deliberately LEFT ATTACHED even when
                # disabled. If GE greys the button out, the action is unreachable and costs
                # nothing; if GE ignores `disabled`, the click still lands on the orchestrator's
                # `job_submitted` guard and the user gets an honest "already submitted" reply.
                # Stripping the action would instead give them a live-looking button that
                # silently does nothing, which is the worse of the two failure modes.
                "disabled": submit_disabled,
                "action": {
                    "event": {
                        "name": "submit_job",
                    },
                },
            },
        ])
        h_children.append("submit_bar")

        # Each Hypothesis as a Collapsible MaterialExpansionPanel
        for idx, h in enumerate(hypotheses, 1):
            if not isinstance(h, dict):
                continue
            panel_id = f"hyp_panel_{idx}"
            title = str(h.get("title") or h.get("Title") or f"Hypothesis {idx}").strip()
            # The header is a FIXED-HEIGHT strip. A generated hypothesis title runs to ~90
            # characters, which wrapped to three lines and overflowed it — the first line was
            # clipped by the panel above, so every collapsed header read "…othesis 4: Multimorbid"
            # (live GE, 2026-09-14). Truncated here and repeated in full inside the body.
            full_title = f"Hypothesis {idx}: {title}"
            panel_title = (full_title if len(full_title) <= _MAX_PANEL_TITLE
                           else full_title[:_MAX_PANEL_TITLE - 1].rstrip() + "…")
            is_expanded = (idx == 1)
            panel_kids: list[str] = []

            if panel_title != full_title:
                ft_id = f"hyp_{idx}_fulltitle"
                h_components.append({"id": ft_id, "component": "MaterialText",
                                     "text": full_title, "usageHint": "subtitle2"})
                panel_kids.append(ft_id)

            # Core Concept
            concept = str(h.get("core_concept") or h.get("Core Concept") or "").strip()
            if concept:
                c_lbl = f"hyp_{idx}_concept_lbl"
                c_val = f"hyp_{idx}_concept_val"
                h_components.extend([
                    {"id": c_lbl, "component": "MaterialText", "text": "**Core Concept**", "usageHint": "subtitle2"},
                    {"id": c_val, "component": "MaterialText", "text": concept, "usageHint": "body2"},
                ])
                panel_kids.extend([c_lbl, c_val])

            # Variables & Mode
            #
            # Shared with the post-execution results Canvas via `variables_and_mode_text`, so the
            # summary the user approves before submitting is character-for-character the summary
            # they see afterwards.
            v_lbl = f"hyp_{idx}_vars_lbl"
            v_val = f"hyp_{idx}_vars_val"
            v_div = f"hyp_{idx}_div_1"
            vars_text = variables_and_mode_text(h)
            h_components.extend([
                {"id": v_div, "component": "MaterialDivider"},
                {"id": v_lbl, "component": "MaterialText", "text": "**Variables & Mode**", "usageHint": "subtitle2"},
                {"id": v_val, "component": "MaterialText", "text": vars_text, "usageHint": "body2"},
            ])
            panel_kids.extend([v_div, v_lbl, v_val])

            # Metric & Direction
            #
            # These four blocks are nested dicts in state, not strings. They used to go through
            # `str()`, which put raw Python reprs on screen — `{'feature_slug': 'built_env_rx',
            # 'secondary_variable': None, ...}`, braces and all. `format_spec_value` renders them
            # as labelled bullets and drops the nulls.
            metric = format_spec_value(
                h.get("metric_transformation") or h.get("Metric Transformation")).strip()
            if metric:
                m_div = f"hyp_{idx}_div_2"
                m_lbl = f"hyp_{idx}_metric_lbl"
                m_val = f"hyp_{idx}_metric_val"
                h_components.extend([
                    {"id": m_div, "component": "MaterialDivider"},
                    {"id": m_lbl, "component": "MaterialText", "text": "**Metric & Direction**", "usageHint": "subtitle2"},
                    {"id": m_val, "component": "MaterialText", "text": metric, "usageHint": "body2"},
                ])
                panel_kids.extend([m_div, m_lbl, m_val])

            # Validation Criteria
            val_crit = format_spec_value(
                h.get("g_validation") or h.get("G_validation")
                or h.get("evaluation_criteria")).strip()
            if val_crit:
                val_div = f"hyp_{idx}_div_3"
                val_lbl = f"hyp_{idx}_val_lbl"
                val_val = f"hyp_{idx}_val_val"
                h_components.extend([
                    {"id": val_div, "component": "MaterialDivider"},
                    {"id": val_lbl, "component": "MaterialText", "text": "**Validation Criteria**", "usageHint": "subtitle2"},
                    {"id": val_val, "component": "MaterialText", "text": val_crit, "usageHint": "body2"},
                ])
                panel_kids.extend([val_div, val_lbl, val_val])

            # Cohort & Assumptions
            cohort = format_spec_value(h.get("r_cohort") or h.get("R_cohort")).strip()
            temporal = format_spec_value(h.get("temporal_split") or h.get("Temporal Split")).strip()
            assump = h.get("assumptions") or h.get("Assumptions") or []
            assump_str = "; ".join(str(a).strip() for a in assump if a) if isinstance(assump, list) else _scalar_str(assump)
            cohort_lines = []
            # The nested blocks already render as their own bullet lists, so they go on the line
            # BELOW their label rather than being inlined after it.
            if cohort:
                cohort_lines.append(f"**Cohort**\n{cohort}")
            if temporal:
                cohort_lines.append(f"**Temporal Window**\n{temporal}")
            if assump_str:
                cohort_lines.append(f"**Assumptions**\n{assump_str}")
            if cohort_lines:
                c_div = f"hyp_{idx}_div_4"
                c_lbl = f"hyp_{idx}_cohort_lbl"
                c_val = f"hyp_{idx}_cohort_val"
                h_components.extend([
                    {"id": c_div, "component": "MaterialDivider"},
                    {"id": c_lbl, "component": "MaterialText", "text": "**Cohort & Assumptions**", "usageHint": "subtitle2"},
                    {"id": c_val, "component": "MaterialText", "text": "\n\n".join(cohort_lines), "usageHint": "body2"},
                ])
                panel_kids.extend([c_div, c_lbl, c_val])

            # NO `description` here, deliberately.
            #
            # It was added on 2026-09-14 so a collapsed panel would say something, and it made
            # things worse: GE lays the header out as two columns, so a description takes width
            # away from the title, which then wrapped from one line to three and overflowed the
            # fixed-height header. Mode and target are already the first thing inside the body
            # under "Variables & Mode", so nothing is lost by leaving the header to the title.
            h_components.append({
                "id": panel_id,
                "component": "MaterialExpansionPanel",
                "title": panel_title,
                "expanded": is_expanded,
                "style": {"marginBottom": "12px"},
                "children": panel_kids,
            })
            panel_ids.append(panel_id)

        # The panels live inside an outlined `MaterialCard`, not directly under the Canvas root.
        # This mirrors `pop_insights_agent`'s `insight_card_components`, whose collapsed panels DO
        # render as single lines in GE, and it measurably improved the per-panel blank space.
        if panel_ids:
            h_components.append({
                "id": "hyp_card",
                "component": "MaterialCard",
                "appearance": "outlined",
                "style": {"padding": "8px", "marginBottom": "16px"},
                "children": panel_ids,
            })
            h_children.append("hyp_card")

        # Everything goes into ONE top-justified column, and the Canvas root gets exactly one
        # child. This is the fix for the large blank bands reported on 2026-09-14: GE lays a
        # Canvas's children out as flex items that GROW to share the panel's full height, so with
        # two children the ~825px panel was split into two ~412px halves. `submit_bar` is a
        # `MaterialRow` with `align: center`, so its single line of content floated to the middle
        # of its half — putting ~230px of nothing above the title and another ~215px below it
        # before the first panel. (Measured against the screenshot: title centred at y≈243 in a
        # 20-432 box, card starting at y≈470. Both land where equal-share flex predicts.)
        #
        # `pop_insights_agent` never hit this because its canvases carry many children, one of
        # which is a tall table that soaks up the free space.
        #
        # `justify: start` is the default for MaterialColumn but is set explicitly here, because
        # the whole point of this wrapper is that the content must pack to the top.
        h_components.append({
            "id": "hyp_col",
            "component": "MaterialColumn",
            "justify": "start",
            "style": {"padding": "16px 20px", "gap": "16px"},
            "children": h_children,
        })

        h_root = {
            "id": "root",
            "component": "Canvas",
            "children": ["hyp_col"],
            # "Proposed Hypotheses (6)" clipped to "Proposed Hypot…" in the tab strip, which is
            # every character except the count that made it worth reading. The noun alone fits.
            "cardTitle": f"Hypotheses ({count})",
            "cardDescription": "Review, then submit for testing",
            "cardIcon": "science",
            # Deliberately NOT auto-opened. GE pops the Canvas over the conversation, so every
            # turn that carries hypotheses would yank the user out of the chat they are reading.
            # The chip in the chat stream is the entry point; they open it when they want it.
            "autoOpen": False,
        }
        h_components.insert(0, h_root)

        groups["hypotheses"] = [
            _wrap({"version": VERSION, "createSurface": {"surfaceId": h_sid, "catalogId": CATALOG_ID}}),
            _wrap({"version": VERSION, "updateComponents": {"surfaceId": h_sid, "components": h_components}}),
        ]

    return groups


# ---------------------------------------------------------------------------
# Clickable grounded columns -> live table preview
# ---------------------------------------------------------------------------

# `action.event.name` for "show me this column's table".
COLUMN_PREVIEW_EVENT = "preview_column"

# Buttons per row in the picker. `MaterialRow` has no wrap property in the catalog, so a row that
# overflows the (narrow) chat column just clips — the chunking is manual for that reason. Two
# fits the widest real column names, e.g. `hcc_medicare_risk_score`.
_PICKER_COLS_PER_ROW = 2

# Ceiling on buttons per table. Exploratory grounding can name whole PDI blocks (`pdi_all_330`
# expands to 330 feature columns in `update_workspace_state.expand_pdi_columns`), and 330 buttons
# is not a UI. The tail is summarised in the caption instead.
_PICKER_MAX_PER_TABLE = 12


def grounded_columns_by_table(data_grounding: Any) -> list[tuple[str, str, list[str]]]:
    """`[(role, "dataset.table", [column, ...])]` from a `ColumnMapping` dump.

    `ColumnMapping` nests `role -> dataset -> table -> columns`, and the columns are a `set` in
    the model, so a round-trip through JSON makes their order arbitrary — they are sorted here so
    the picker does not reshuffle itself between turns.

    Every level is model-authored and arrives straight out of session state, so every level is
    isinstance-guarded. The Canvas must never be able to take a turn down; see the note on
    `create_schema_canvas_part_groups`.
    """
    out: list[tuple[str, str, list[str]]] = []
    if not isinstance(data_grounding, dict):
        return out
    for role in ("target_columns", "exploratory_columns"):
        datasets = data_grounding.get(role)
        if not isinstance(datasets, dict):
            continue
        for dataset, tables in datasets.items():
            if not isinstance(tables, dict):
                continue
            for table, columns in tables.items():
                if not isinstance(columns, (list, set, tuple)):
                    continue
                names = sorted({str(c).strip() for c in columns if str(c).strip()})
                if names:
                    out.append((role.replace("_columns", ""), f"{dataset}.{table}", names))
    return out


def _column_picker_card(table: str, columns: list[str]) -> list[types.Part]:
    """One small INLINE card of clickable column names, for ONE table.

    Why a component and not markdown: the column names in the model's prose are ordinary
    backticked text, and GE has no hook to make rendered markdown clickable. Only a real A2UI
    component can carry an `action`, so to make a column clickable it has to be re-rendered as
    one. The catalog admits `action` on exactly: MaterialButton, MaterialIconButton,
    MaterialChips, MaterialMenu, Button, SplitButton and the four list/form widgets.

    `MaterialButton` per column, NOT one `MaterialChips` for all of them. Chips carry a single
    shared `action` and would have to route the selected chip's identity through a two-way
    `value` binding into `action.context` — plausible, but unproven, and GE validates a surface
    before rendering ANY of it, so one unsupported property blanks the whole card. A button with
    a literal `context` is the shape already proven in production by the Submit button.
    `variant: "basic"` renders as a text button, so it reads as a link rather than a heavy chip.

    The root is a `MaterialCard`, NOT a `Canvas`: a non-Canvas root renders inline in the chat
    stream instead of collapsing to an opener chip, which is the point — the buttons should sit
    with the prose, not behind another click.

    ONE SURFACE PER TABLE, and no heading inside it. GE positions a surface wherever its parts
    fall among the response parts, so a card per table is what lets each one be dropped next to
    the bullet that names its table (`canvas_placement.place_column_pickers`). The card carries
    no title because the bullet immediately above it already says which table these are and what
    the columns are for; repeating it was the duplication this change exists to remove.
    """
    if not columns:
        return []

    sid = f"cols_{uuid.uuid4().hex[:8]}"
    components: list[dict[str, Any]] = []
    children: list[str] = []

    # A block too large to list is collapsed to ONE table-level button rather than an arbitrary
    # first-N. `pdi_all_330` expands to 330 `feature_*` columns that all live in the same table,
    # so twelve of them are twelve buttons that open the identical preview — noise, and the twelve
    # are whichever ones sort first (`feature_0, feature_1, feature_10, feature_100…`), which is
    # not even a meaningful subset. The count goes in the label so the collapse is visible rather
    # than silent, now that there is no caption line to carry it.
    collapsed = len(columns) > _PICKER_MAX_PER_TABLE
    if collapsed:
        shown = [(f"Preview table · {len(columns)} columns", "")]
    else:
        # An empty `column` means "no particular column" — the preview then falls back to the
        # table's own default column selection.
        shown = [(c, c) for c in columns]

    btn_ids: list[str] = []
    for c_idx, (btn_label, column) in enumerate(shown):
        btn_id = f"c{c_idx}"
        components.append({
            "id": btn_id,
            "component": "MaterialButton",
            "label": btn_label,
            "variant": "basic",
            "leadingIcon": "table_chart",
            # Literal context. Production proved `action.context` round-trips intact — it came
            # back as `{}` only because the Submit button sends none. Both the table AND the
            # column travel, so the handler never has to guess which table a column came from;
            # that guess is exactly what the old preview tabs got wrong (first-table-wins).
            "action": {"event": {"name": COLUMN_PREVIEW_EVENT,
                                 "context": {"table": table, "column": column}}},
        })
        btn_ids.append(btn_id)

    for r_idx in range(0, len(btn_ids), _PICKER_COLS_PER_ROW):
        row_id = f"r{r_idx}"
        components.append({"id": row_id, "component": "MaterialRow", "align": "center",
                           "children": btn_ids[r_idx:r_idx + _PICKER_COLS_PER_ROW]})
        children.append(row_id)

    components.insert(0, {"id": "root", "component": "MaterialCard",
                          "appearance": "outlined", "children": children})
    return [
        _wrap({"version": VERSION, "createSurface": {"surfaceId": sid, "catalogId": CATALOG_ID}}),
        _wrap({"version": VERSION, "updateComponents": {"surfaceId": sid, "components": components}}),
    ]


def create_column_picker_parts_by_table(
    data_grounding: Any,
) -> list[tuple[str, list[types.Part]]]:
    """`[("dataset.table", parts), ...]` — one pickable card per grounded table.

    Kept separate from the flattened form because the caller needs the table name to decide
    WHERE each card goes: beside the prose bullet that introduces that table.
    """
    out: list[tuple[str, list[types.Part]]] = []
    for _role, table, columns in grounded_columns_by_table(data_grounding):
        parts = _column_picker_card(table, columns)
        if parts:
            out.append((table, parts))
    return out


def create_column_picker_parts(data_grounding: Any) -> list[types.Part]:
    """Every table's picker card, concatenated.

    The fallback shape, for the paths that cannot place cards individually (see
    `canvas_placement.place_canvas_groups`, which appends groups wholesale when interleaving
    fails). Placement is cosmetic; losing the buttons entirely is not.
    """
    out: list[types.Part] = []
    for _table, parts in create_column_picker_parts_by_table(data_grounding):
        out.extend(parts)
    return out



def create_column_preview_parts(
    table: str,
    column: str = "",
    data_grounding: Any = None,
    preview_fetcher: Any = None,
) -> list[types.Part]:
    """A Canvas tab holding a live `RichTable` sample of one grounded table.

    Built in response to a column click, so this one DOES `autoOpen` — the user asked for the
    panel by clicking, and opening it is the whole answer.

    The fetch is scoped to the ONE table the click named. That is the difference from the removed
    preview tabs, which merged every hypothesis's columns into a single list and queried them
    against whichever table happened to come first; foreign columns were then dropped silently by
    the `c in all_cols` filter, so the tab looked fine and showed the wrong thing.

    What the table CONTAINS is the clicked column, then the other grounded columns from that same
    table, then one identity column — and nothing else. Showing only the grounded columns keeps
    the preview about the analysis rather than about the table: the surrounding columns are not
    part of any hypothesis, and on the wide PDI tables they crowd out the one column the user
    asked for. Siblings are included rather than the clicked column alone because the grounded
    columns of a table are what the hypotheses actually compare, so seeing them side by side is
    the useful view.
    """
    fetcher = preview_fetcher or fetch_table_preview_rows
    table = str(table or "").strip()
    if not table:
        return []

    # Clicked column first so it survives the column cap inside the fetcher, then its grounded
    # siblings. A click on a collapsed block sends no column, in which case this is simply every
    # grounded column for the table, capped the same way.
    requested: list[str] = [column] if column else []
    for _role, t, cols in grounded_columns_by_table(data_grounding):
        if t != table:
            continue
        for c in cols:
            if c not in requested:
                requested.append(c)

    schema, data = fetcher(table, requested or None, strict=True)
    if not schema or not data:
        return []

    sid = f"colprev_{uuid.uuid4().hex[:8]}"
    heading = heading_components(
        "colprev",
        column or table,
        f"{len(data)} sample rows from {table}",
    )
    components = list(heading)
    components.append(rich_table_component("colprev_table", schema, data))
    children = [c["id"] for c in components]

    # Single child under the root, for the same reason the hypotheses Canvas has one: GE grows
    # Canvas children to share the panel height, so N children means N evenly-spaced bands.
    components.append({
        "id": "colprev_col",
        "component": "MaterialColumn",
        "justify": "start",
        "style": {"padding": "16px 20px", "gap": "16px"},
        "children": children,
    })
    short_table = table.split(".")[-1]
    components.insert(0, {
        "id": "root",
        "component": "Canvas",
        "children": ["colprev_col"],
        # The column name and NOTHING else. Every one of these tabs used to be titled
        # "Data preview: {column}", and because the tab strip ellipsises at roughly fifteen
        # characters, four open previews all read "Data preview: …" — the prefix consumed the
        # entire width and the only distinguishing part was the part that got cut. The icon
        # already says "table", so the words never earned their space.
        "cardTitle": column or short_table,
        "cardDescription": f"{len(data)} rows · {short_table}",
        "cardIcon": "table_chart",
        "autoOpen": True,
    })
    return [
        _wrap({"version": VERSION, "createSurface": {"surfaceId": sid, "catalogId": CATALOG_ID}}),
        _wrap({"version": VERSION, "updateComponents": {"surfaceId": sid, "components": components}}),
    ]


# The order groups are concatenated in when they are NOT being interleaved. The column picker
# first because it belongs with the grounding prose, then the previews, so the hypotheses tab is
# the last surface created — the one GE puts in front if the user does open the Canvas.
CANVAS_GROUP_ORDER = ("columns", "target", "exploratory", "hypotheses")



def create_schema_canvas_parts(*args: Any, **kwargs: Any) -> list[types.Part]:
    """`create_schema_canvas_part_groups` flattened into a single ordered list.

    Retained for callers that place the whole Canvas in one spot.
    """
    groups = create_schema_canvas_part_groups(*args, **kwargs)
    out: list[types.Part] = []
    for key in CANVAS_GROUP_ORDER:
        out.extend(groups.get(key) or [])
    return out

