# -*- coding: utf-8 -*-
"""Ralph Loop — a self-referential development loop.

The Ralph Loop continuously works on a task until it signals completion.
This module provides the LoopState for tracking iteration state, prompt
templates for guiding the agent, and a shared registry of active loops
that other components (e.g. the /cancel-loop handler) can access.
"""

from __future__ import annotations

from typing import Dict

from .state import LoopState

# Active loop states keyed by session_id.
# Populated when a ralph-loop is started and cleared on completion or
# cancellation.  Other components (e.g. CancelLoopHandler) read this
# registry to inspect or cancel running loops.
_active_loop_states: Dict[str, LoopState] = {}

__all__ = [
    "_active_loop_states",
    "LoopState",
]
