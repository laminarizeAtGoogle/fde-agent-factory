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

"""Golden Pattern: ADK Turn Lifecycle & Callback Integration for Gemini Enterprise.

Features:
1. `before_model_call`: Strips raw A2UI JSON wire format from history to prevent LLM format imitation.
2. Inbound UI event dispatcher: Intercepts synthetic "User action triggered." turns and decodes
   action payloads (name, context) deterministically without wasting model tokens.
3. `after_model_callback`: Safely attaches A2UI parts with blast-radius protection (exceptions degrade
   gracefully to text-only instead of failing the HTTP stream with a 500).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from google.genai import types

from ..scripts.a2ui_builder import (
    find_a2ui_action,
    history_callback,
    is_a2ui_part,
)
from .interactive_canvas import create_analysis_canvas

logger = logging.getLogger(__name__)

# Synthetic trigger strings emitted by Gemini Enterprise when an A2UI component is clicked
SYNTHETIC_UI_TEXTS = {
    "user action triggered",
    "user action triggered.",
    "action triggered",
    "user action",
}


def is_synthetic_ui_turn(text: str) -> bool:
    """Return True if this turn represents a GE frontend button click rather than typed text."""
    cleaned = text.strip().lower().rstrip(".!").strip()
    return cleaned in SYNTHETIC_UI_TEXTS


# ---------------------------------------------------------------------------
# 1. ADK Before Model Callback
# ---------------------------------------------------------------------------

async def before_model_call(callback_context: Any, llm_request: Any) -> None:
    """ADK Hook: Executed before prompt contents are transmitted to the LLM.

    Sanitizes conversation history: replaces past A2UI parts with reader-visible text
    so the model does not attempt to write raw JSON wire sentinels in subsequent turns.
    """
    history_callback(callback_context, llm_request)


# ---------------------------------------------------------------------------
# 2. Deterministic Action Dispatcher
# ---------------------------------------------------------------------------

def handle_inbound_turn(
    user_text: str,
    turn_parts: List[Any],
    session_state: Dict[str, Any],
) -> Optional[List[types.Part]]:
    """Determine whether the turn is an interactive UI click or regular chat.

    If an A2UI action is detected, routes the event directly without invoking the LLM.
    """
    action = find_a2ui_action(turn_parts)

    # Check for synthetic turn or explicit action payload
    if action or is_synthetic_ui_turn(user_text):
        action_name = action.get("name") if action else None
        context = action.get("context", {}) if action else {}

        logger.info("Intercepted UI action: %s with context: %s", action_name, context)

        if action_name == "submit_execution":
            task_count = context.get("task_count", 0)
            session_state["executed"] = True
            # Return immediate deterministic confirmation
            return [
                types.Part(
                    text=f"🚀 Successfully triggered execution for {task_count} tasks! Processing in background..."
                )
            ]

        if action_name == "select_option":
            opt = context.get("option_id")
            session_state["selected_option"] = opt
            return [
                types.Part(text=f"Selected option: **{context.get('label', opt)}**. Proceeding with next step...")
            ]

    # Return None to let standard LLM orchestrator handle normal chat
    return None


# ---------------------------------------------------------------------------
# 3. ADK After Model Callback
# ---------------------------------------------------------------------------

def after_model_callback(callback_context: Any, llm_response: Any) -> None:
    """ADK Hook: Executed after the LLM produces a response.

    Attaches A2UI components (Canvas or Inline Card) to the model's text response.
    CRITICAL: Wrapped in try/except so that UI generation errors NEVER terminate the
    turn with an HTTP 500 stream failure.
    """
    # Guard: check response structure
    if not getattr(llm_response, "content", None) or not getattr(llm_response.content, "parts", None):
        return
    if getattr(llm_response, "partial", False):
        return
    # Skip if LLM made a tool call (function call turn)
    if any(getattr(p, "function_call", None) for p in llm_response.content.parts):
        return

    # Check session state for items to display in UI
    tasks = callback_context.state.get("tasks", [])
    already_has_ui = any(is_a2ui_part(p) for p in llm_response.content.parts)

    if tasks and not already_has_ui:
        try:
            # Build sample table data
            sample_schema = [{"name": "task_id", "dataType": "STRING"}, {"name": "priority", "dataType": "STRING"}]
            sample_data = [{"task_id": t.get("name"), "priority": "high"} for t in tasks[:5]]

            canvas_parts = create_analysis_canvas(
                title="Pending Tasks",
                items=tasks,
                table_schema=sample_schema,
                table_data=sample_data,
            )

            # Append A2UI parts alongside the LLM's text parts
            llm_response.content.parts.extend(canvas_parts)
            logger.info("Successfully attached %d A2UI parts to turn", len(canvas_parts))

        except Exception as e:
            # Blast-radius protection: log error and allow text response to deliver safely
            logger.exception("A2UI Canvas generation failed; delivering text-only response: %s", e)
