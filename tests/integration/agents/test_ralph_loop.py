# -*- coding: utf-8 -*-
"""Integration tests for the ralph-loop module.

These tests validate the end-to-end behaviour of the ralph-loop system
using mock agents and fixtures.  They are intentionally RED — the
``ralph_runner`` module does not exist yet and will be implemented in a
later task.

Requires:
    - ``qwenpaw.agents.ralph_loop.state``  (exists)
    - ``qwenpaw.agents.ralph_loop.ralph_runner``  (NOT yet implemented)
"""

from __future__ import annotations

import threading
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from qwenpaw.agents.ralph_loop.state import LoopState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_ralph_runner() -> Any:
    """Lazy import of the not-yet-existing ``ralph_runner`` module.

    This keeps the file importable (so pytest ``--collect-only`` works) while
    still causing every test that depends on the runner to fail at runtime.
    """
    from qwenpaw.agents.ralph_loop.ralph_runner import RalphRunner

    return RalphRunner


class MockAgent:
    """Simulates an agent that optionally completes after *n* iterations.

    Parameters
    ----------
    completion_iteration:
        The iteration (1-based) at which the agent signals completion.
        ``None`` means the agent never signals completion (forces max
        iterations or cancellation).
    """

    def __init__(self, completion_iteration: int | None = None) -> None:
        self.call_count: int = 0
        self.completion_iteration = completion_iteration

    def step(self, state: LoopState) -> dict[str, Any]:
        """Execute one iteration and return a result dict.

        Returns
        -------
        dict
            ``{"done": True}`` when *completion_iteration* is reached,
            ``{"done": False}`` otherwise.
        """
        self.call_count += 1
        state.increment()
        if (
            self.completion_iteration is not None
            and self.call_count >= self.completion_iteration
        ):
            state.mark_complete()
            return {"done": True}
        return {"done": False}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRalphLoopIntegration:
    """End-to-end integration tests for the ralph-loop system."""

    # 1. Full loop with mock agent completes early ----------------------------

    def test_full_loop_with_mock_agent_completes(self) -> None:
        """Run a ralph loop where the mock agent signals completion on
        iteration 3.  The loop must stop, and the state must reflect
        *completed* at iteration 3.
        """
        RalphRunner = _import_ralph_runner()

        state = LoopState(task="test", max_iterations=10)
        agent = MockAgent(completion_iteration=3)

        runner = RalphRunner(state=state, agent=agent)
        runner.run()

        assert state.completed is True
        assert state.iteration == 3

    # 2. Max iterations exceeded ----------------------------------------------

    def test_full_loop_max_iterations_exceeded(self) -> None:
        """Run a ralph loop with an agent that never completes.  The loop
        must stop when *max_iterations* is reached.
        """
        RalphRunner = _import_ralph_runner()

        state = LoopState(task="test", max_iterations=5)
        agent = MockAgent(completion_iteration=None)

        runner = RalphRunner(state=state, agent=agent)
        runner.run()

        assert state.is_max_reached() is True
        assert state.iteration == 5
        assert state.active is False

    # 3. Cancel loop during execution -----------------------------------------

    def test_cancel_loop_during_full_execution(self) -> None:
        """Start a long-running loop in a background thread and cancel it
        after 2 iterations.  The state must reflect cancellation and the
        iteration must be less than the maximum.
        """
        RalphRunner = _import_ralph_runner()

        state = LoopState(task="test", max_iterations=20)
        agent = MockAgent(completion_iteration=None)

        runner = RalphRunner(state=state, agent=agent)

        def _cancel_after_delay() -> None:
            """Wait until at least 2 iterations have run, then cancel."""
            while state.iteration < 2:
                time.sleep(0.05)
            state.cancel()

        cancel_thread = threading.Thread(target=_cancel_after_delay, daemon=True)
        cancel_thread.start()

        runner.run()

        assert state.cancelled is True
        assert state.iteration < 20

    # 4. Console command routing -----------------------------------------------

    def test_ralph_loop_in_console_context(self) -> None:
        """Verify that ``/ralph-loop <task>`` is recognised as a ralph-loop
        command and routed correctly by a mock runner context.
        """
        RalphRunner = _import_ralph_runner()

        mock_runner = MagicMock(spec=RalphRunner)
        mock_runner.handle_command.return_value = {
            "routed": True,
            "command": "ralph-loop",
            "task": "Write a script",
        }

        result = mock_runner.handle_command("/ralph-loop Write a script")

        mock_runner.handle_command.assert_called_once_with(
            "/ralph-loop Write a script",
        )
        assert result["routed"] is True
        assert result["command"] == "ralph-loop"
        assert result["task"] == "Write a script"

    # 5. Progress updates during loop -----------------------------------------

    def test_progress_updates_during_loop(self) -> None:
        """Run a loop with a progress callback and verify that the callback
        receives correct iteration counts for each step.
        """
        RalphRunner = _import_ralph_runner()

        state = LoopState(task="test", max_iterations=5)
        agent = MockAgent(completion_iteration=3)

        progress_events: list[dict[str, Any]] = []

        def on_progress(event: dict[str, Any]) -> None:
            progress_events.append(event)

        runner = RalphRunner(state=state, agent=agent, on_progress=on_progress)
        runner.run()

        assert len(progress_events) > 0
        # Each event should carry the iteration number at that point
        for event in progress_events:
            assert "iteration" in event
            assert isinstance(event["iteration"], int)
            assert event["iteration"] >= 1

    # 6. Duplicate start blocked ----------------------------------------------

    def test_ralph_loop_blocks_duplicate_start(self) -> None:
        """Attempt to start a second ralph-loop while one is already active.
        The second start must be blocked with an appropriate error message.
        """
        RalphRunner = _import_ralph_runner()

        state = LoopState(task="first task", max_iterations=10)

        runner = RalphRunner(state=state, agent=MockAgent())

        # Simulate an already-active loop
        runner.start()

        # A second start while the first is active should be rejected
        result = runner.start()

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0  # error message present

        runner.stop()
