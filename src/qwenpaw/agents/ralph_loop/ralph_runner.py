# -*- coding: utf-8 -*-
"""Ralph Loop runner engine — the core self-referential loop."""

from __future__ import annotations

import logging
from typing import Any

from qwenpaw.agents.ralph_loop.prompts import build_continuation_prompt, build_initial_prompt
from qwenpaw.agents.ralph_loop.state import LoopState

logger = logging.getLogger(__name__)


class LoopResult:
    """Result of a completed/cancelled ralph-loop execution."""

    def __init__(self, state: LoopState, iterations: int) -> None:
        self.state = state
        self.iterations = iterations


async def run_loop(
    agent: Any,
    state: LoopState,
) -> LoopResult:
    """Execute a Ralph Loop — self-referential loop until completion.

    Runs *agent* in a loop, injecting initial and continuation prompts.
    Stops when the agent signals completion (via metadata), the state is
    cancelled, or ``max_iterations`` is reached.

    Parameters
    ----------
    agent:
        Callable that accepts a list of messages and returns an object
        with ``content`` (str) and ``metadata`` (dict) attributes.
    state:
        The :class:`LoopState` tracking iteration count and status.

    Returns
    -------
    LoopResult
        Wrapper containing the final *state* and the total iteration count.
    """
    # Disable auto-continue on the agent during the loop.
    original_auto_continue = getattr(agent, "auto_continue_on_text_only", True)
    agent.auto_continue_on_text_only = False

    try:
        # Build the initial prompt.
        initial_prompt = build_initial_prompt(state.task, state.max_iterations)
        current_messages: list[Any] = [{"role": "system", "content": initial_prompt}]

        while state.is_active() and not state.is_done():
            # Check for pre-existing cancellation.
            if state.cancelled:
                break

            state.increment()

            # Run the agent.
            try:
                result = await agent(list(current_messages))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Agent error during iteration %d: %s",
                    state.iteration,
                    exc,
                )
                # Continue to next iteration unless cancelled.
                if state.cancelled:
                    break
                continue

            # Check for completion signal in metadata.
            metadata = getattr(result, "metadata", {}) or {}
            if metadata.get("completed"):
                state.mark_complete()
                break

            # Inject continuation prompt for the next iteration.
            continuation = build_continuation_prompt(
                state.task, state.iteration, state.max_iterations
            )
            current_messages.append({"role": "system", "content": continuation})

        return LoopResult(state=state, iterations=state.iteration)

    finally:
        # Restore original auto-continue setting.
        agent.auto_continue_on_text_only = original_auto_continue
