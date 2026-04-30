# -*- coding: utf-8 -*-
"""Handler for the /cancel-loop control command.

The /cancel-loop command cancels an active Ralph Loop (self-referential
development loop) in the current session.  It checks the shared registry
of active loops held by the ``ralph_loop`` module.
"""

from __future__ import annotations

import logging

from qwenpaw.agents.ralph_loop import _active_loop_states
from .base import BaseControlCommandHandler, ControlContext

logger = logging.getLogger(__name__)


class CancelLoopHandler(BaseControlCommandHandler):
    """Handler for /cancel-loop command.

    Cancels an active Ralph Loop for the current session.  The loop state
    is looked up from the shared ``_active_loop_states`` registry that the
    ralph-loop initiator populates when a loop is started.

    Usage:
        /cancel-loop              # Cancel loop for current session
    """

    command_name = "/cancel-loop"

    async def handle(self, context: ControlContext) -> str:
        """Check for active ralph-loop and cancel it.

        Args:
            context: Control context with access to workspace, session, etc.

        Returns:
            Confirmation message (str).
        """
        session_id = context.session_id
        if not session_id:
            return "No active session."

        # Look up the loop state for this session in the shared registry
        loop_state = _active_loop_states.get(session_id)
        if loop_state is None or not loop_state.is_active():
            logger.debug(
                "No active Ralph Loop for session %s",
                session_id[:20],
            )
            return "No active Ralph Loop to cancel."

        loop_state.cancel()
        # Remove from registry to keep the dict clean
        _active_loop_states.pop(session_id, None)

        logger.info(
            "Ralph Loop cancelled for session %s "
            "(had run %d iterations)",
            session_id[:20],
            loop_state.iteration,
        )
        return "Ralph Loop cancelled."
