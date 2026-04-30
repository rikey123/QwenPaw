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
    progress_callback: Any = None,
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
    progress_callback:
        Optional callable invoked after each iteration with
        ``(iteration: int, max_iterations: int)``.
        Used by the runner to emit real-time progress messages.

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

            # Fire progress callback for real-time UI updates.
            if progress_callback is not None:
                progress_callback(state.iteration, state.max_iterations)

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


class RalphRunner:
    """Synchronous wrapper for the ralph-loop runner.

    Provides a class-based API used by integration tests and the
    console command handler.  Delegates to the async :func:`run_loop`
    for real agents and runs a synchronous loop for mock agents that
    expose a ``step()`` method.
    """

    def __init__(
        self,
        state: LoopState,
        agent: Any,
        on_progress: Any = None,
    ) -> None:
        self._state = state
        self._agent = agent
        self._on_progress = on_progress
        self._running = False

    def run(self) -> None:
        """Execute the loop to completion, cancellation, or max iterations."""
        self._running = True
        try:
            if hasattr(self._agent, "step"):
                self._run_sync_loop()
            else:
                import asyncio

                # Bridge dict-based on_progress to two-arg progress_callback.
                callback = None
                if self._on_progress is not None:
                    def _cb(iteration: int, max_iterations: int) -> None:
                        self._on_progress({
                            "iteration": iteration,
                            "max_iterations": max_iterations,
                        })
                    callback = _cb

                asyncio.run(
                    run_loop(self._agent, self._state, progress_callback=callback)
                )
        finally:
            self._running = False
            self._state.active = False

    def _run_sync_loop(self) -> None:
        """Synchronous loop for agents that expose a ``step(state)`` method."""
        import time as _time

        while self._state.is_active() and not self._state.is_done():
            if self._state.cancelled:
                break

            result = self._agent.step(self._state)

            # Check for cancellation signalled by another thread.
            if self._state.cancelled:
                break

            if self._on_progress is not None:
                self._on_progress(
                    {
                        "iteration": self._state.iteration,
                        "max_iterations": self._state.max_iterations,
                        "done": result.get("done", False),
                    },
                )

            if result.get("done"):
                break

            # Yield the GIL so background cancellation threads can
            # acquire it and set the cancelled flag.
            _time.sleep(0.01)

    def start(self) -> str | None:
        """Mark the loop as started.

        Returns:
            ``None`` on success, or an error message string if the
            loop is already running.
        """
        if self._running:
            return "Ralph loop is already active"
        self._running = True
        return None

    def stop(self) -> None:
        """Mark the loop as stopped."""
        self._running = False

    @staticmethod
    def handle_command(command: str) -> dict[str, Any]:
        """Parse a ``/ralph-loop`` command string.

        Returns:
            ``{"routed": True, "command": "ralph-loop", "task": ...}``
            when the command is recognised, otherwise ``{"routed": False}``.
        """
        from qwenpaw.agents.ralph_loop.handler import parse_ralph_command

        parsed = parse_ralph_command(command)
        if parsed:
            return {
                "routed": True,
                "command": "ralph-loop",
                "task": parsed["task"],
            }
        return {"routed": False}
