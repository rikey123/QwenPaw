# -*- coding: utf-8 -*-
"""Ralph Loop dispatch — runner integration bridge.

Integration layer between ``runner.py`` and the Ralph Loop execution engine:

- Detects ``/ralph-loop`` in the user query.
- Delegates command parsing to :mod:`~qwenpaw.agents.ralph_loop.handler`.
- Detects an active ralph-loop awaiting continuation.
"""
from __future__ import annotations

import logging
from typing import Any

from ...agents.ralph_loop import _active_loop_states
from ...agents.ralph_loop.handler import is_ralph_command, parse_ralph_command

logger = logging.getLogger(__name__)


# ── Public API ───────────────────────────────────────────────────────────


def maybe_handle_ralph_command(
    query: str | None,
    multi_agent_manager: Any = None,
) -> dict[str, Any] | None:
    """Handle ``/ralph-loop`` if the query matches.

    Args:
        query: The user's message text.
        multi_agent_manager: Multi-agent manager instance (reserved for
            future use when the runner integrates ralph-loop execution).

    Returns:
        ``dict`` with ``{"ralph_phase": 1, "task": ..., "max_iterations": ...}``
            if the caller should enter Ralph Loop execution.
        ``None`` if the query is not a ralph-loop command.
    """
    if not query or not is_ralph_command(query):
        return None

    parsed = parse_ralph_command(query)
    if parsed is None:
        return None

    return {
        "ralph_phase": 1,
        "task": parsed["task"],
        "max_iterations": parsed["max_iterations"],
    }


def detect_active_ralph_phase(
    session: Any = None,
) -> str | None:
    """Check if the session has an active ralph-loop.

    Args:
        session: Session object with a ``session_id`` attribute.

    Returns:
        ``"ralph-loop"`` if an active loop is found for this session.
        ``None`` otherwise.
    """
    if session is None:
        return None

    session_id = getattr(session, "session_id", None)
    if session_id is None:
        return None

    loop_state = _active_loop_states.get(session_id)
    if loop_state is not None and loop_state.is_active():
        return "ralph-loop"

    return None
