# -*- coding: utf-8 -*-
"""Tests for the ralph-loop runner engine (RED phase).

These tests will fail because ``ralph_loop.ralph_runner`` does not exist yet.
They define the expected contract for the runner module to be implemented
in Task 10 (Wave 2).

RED-phase strategy: we import ``run_loop`` and ``LoopResult`` inside each
test function via a helper so that the file can be *collected* by pytest
even though the module does not exist yet.  Every test will raise
``ImportError`` at runtime, which counts as a RED failure.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from qwenpaw.agents.ralph_loop.state import LoopState


def _import_runner():
    """Deferred import — will raise ImportError until ralph_runner is created."""
    from qwenpaw.agents.ralph_loop.ralph_runner import LoopResult, run_loop

    return run_loop, LoopResult


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


@dataclass
class MockMsg:
    """Lightweight message stub returned by MockAgent."""

    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class MockAgent:
    """Mock agent that simulates ralph-loop behavior for testing.

    Parameters
    ----------
    completion_iteration:
        The iteration number at which the agent yields a completion signal.
        *None* means the agent never signals completion.
    raises_error:
        If True, the agent raises ``RuntimeError`` on its second call.
    empty_response:
        If True, the agent returns an empty-string response.
    """

    def __init__(
        self,
        completion_iteration: int | None = None,
        raises_error: bool = False,
        empty_response: bool = False,
    ) -> None:
        self.call_count: int = 0
        self.completion_iteration = completion_iteration
        self.raises_error = raises_error
        self.empty_response = empty_response
        self.auto_continue_on_text_only: bool = True

    async def __call__(self, messages: list[Any], **kwargs: Any) -> MockMsg:
        self.call_count += 1

        if self.raises_error and self.call_count == 2:
            raise RuntimeError("Simulated agent error")

        text = "" if self.empty_response else f"Iteration {self.call_count} response for task"
        result = MockMsg(content=text)

        if self.completion_iteration and self.call_count >= self.completion_iteration:
            result.metadata = {"completed": True}

        return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunLoopCompletesOnDoneSignal:
    """Agent signals completion — loop should stop and mark state completed."""

    @pytest.mark.asyncio
    async def test_run_loop_completes_on_done_signal(self) -> None:
        """Create MockAgent(completion_iteration=3), run loop.

        Expected: state.completed == True, agent.call_count == 3.
        """
        run_loop, _ = _import_runner()

        agent = MockAgent(completion_iteration=3)
        state = LoopState(task="implement feature X", max_iterations=10)

        result = await run_loop(agent=agent, state=state)

        assert state.completed is True
        assert agent.call_count == 3


class TestRunLoopStopsAtMaxIterations:
    """Agent never completes — loop stops at max_iterations."""

    @pytest.mark.asyncio
    async def test_run_loop_stops_at_max_iterations(self) -> None:
        """Create MockAgent(completion_iteration=None), max_iterations=5.

        Expected: state.is_max_reached() == True, agent.call_count == 5.
        """
        run_loop, _ = _import_runner()

        agent = MockAgent(completion_iteration=None)
        state = LoopState(task="never-ending task", max_iterations=5)

        result = await run_loop(agent=agent, state=state)

        assert state.is_max_reached() is True
        assert agent.call_count == 5


class TestRunLoopInjectsContinuationPrompt:
    """After the first iteration the prompt injected into the next call must
    differ from the initial task prompt, proving the loop builds a
    continuation message."""

    @pytest.mark.asyncio
    async def test_run_loop_injects_continuation_prompt(self) -> None:
        """Verify the second agent call receives a different prompt than the first."""
        run_loop, _ = _import_runner()

        captured_messages: list[list[Any]] = []

        class CapturingAgent(MockAgent):
            async def __call__(self, messages: list[Any], **kwargs: Any) -> MockMsg:  # type: ignore[override]
                captured_messages.append(messages)
                return await super().__call__(messages, **kwargs)

        agent = CapturingAgent(completion_iteration=3)
        state = LoopState(task="write tests", max_iterations=10)

        await run_loop(agent=agent, state=state)

        # Must have at least 2 calls to compare prompts
        assert len(captured_messages) >= 2
        first_prompt = captured_messages[0]
        second_prompt = captured_messages[1]
        assert first_prompt != second_prompt, (
            "Continuation prompt should differ from initial prompt"
        )


class TestRunLoopTracksIterationCount:
    """Loop must accurately track the number of iterations in state."""

    @pytest.mark.asyncio
    async def test_run_loop_tracks_iteration_count(self) -> None:
        """Run 4 iterations, verify state.iteration == 4."""
        run_loop, _ = _import_runner()

        agent = MockAgent(completion_iteration=4)
        state = LoopState(task="count iterations", max_iterations=10)

        await run_loop(agent=agent, state=state)

        assert state.iteration == 4


class TestRunLoopHandlesAgentError:
    """Loop should not crash when the agent raises an error; it should
    continue to the next iteration."""

    @pytest.mark.asyncio
    async def test_run_loop_handles_agent_error(self) -> None:
        """Create MockAgent(raises_error=True), run loop.

        Expected: loop doesn't crash, continues to next iteration.
        """
        run_loop, _ = _import_runner()

        agent = MockAgent(raises_error=True, completion_iteration=5)
        state = LoopState(task="resilient task", max_iterations=10)

        # Should not raise — error is swallowed / handled
        result = await run_loop(agent=agent, state=state)

        # Agent was called more than 2 times, meaning the loop recovered
        assert agent.call_count >= 3


class TestRunLoopCancelDuringExecution:
    """Cancelling the state mid-loop should cause the loop to terminate."""

    @pytest.mark.asyncio
    async def test_run_loop_cancel_during_execution(self) -> None:
        """Start loop with agent that never completes, then cancel via state.cancel().

        Expected: loop terminates, state.cancelled == True.
        """
        run_loop, _ = _import_runner()

        class CancelAgent(MockAgent):
            """Agent that cancels the loop on its 3rd call."""

            def __init__(self) -> None:
                super().__init__(completion_iteration=None)
                self._state: LoopState | None = None

            async def __call__(self, messages: list[Any], **kwargs: Any) -> MockMsg:  # type: ignore[override]
                result = await super().__call__(messages, **kwargs)
                if self.call_count == 3 and self._state is not None:
                    self._state.cancel()
                return result

        agent = CancelAgent()
        state = LoopState(task="cancellable task", max_iterations=20)
        agent._state = state

        result = await run_loop(agent=agent, state=state)

        assert state.cancelled is True
        assert agent.call_count == 3


class TestRunLoopAutoContinueDisabled:
    """The runner must disable auto_continue_on_text_only on the agent
    before executing the loop."""

    @pytest.mark.asyncio
    async def test_run_loop_auto_continue_disabled(self) -> None:
        """Verify agent.auto_continue_on_text_only is set to False during loop execution."""
        run_loop, _ = _import_runner()

        # Record value during execution
        captured_values: list[bool] = []

        class InspectAgent(MockAgent):
            async def __call__(self, messages: list[Any], **kwargs: Any) -> MockMsg:  # type: ignore[override]
                captured_values.append(self.auto_continue_on_text_only)
                return await super().__call__(messages, **kwargs)

        inspect_agent = InspectAgent(completion_iteration=2)
        state = LoopState(task="disable auto-continue", max_iterations=10)

        await run_loop(agent=inspect_agent, state=state)

        # During execution auto_continue_on_text_only should be False
        assert all(v is False for v in captured_values), (
            f"auto_continue_on_text_only should be False during loop, got {captured_values}"
        )


class TestRunLoopEmptyResponseCountsAsIteration:
    """An empty response from the agent still counts as one iteration."""

    @pytest.mark.asyncio
    async def test_run_loop_empty_response_counts_as_iteration(self) -> None:
        """MockAgent returns empty response, verify iteration increments."""
        run_loop, _ = _import_runner()

        agent = MockAgent(empty_response=True, completion_iteration=3)
        state = LoopState(task="empty response task", max_iterations=10)

        await run_loop(agent=agent, state=state)

        assert state.iteration == 3
        assert agent.call_count == 3


class TestRunLoopReturnsLoopResult:
    """The return value of run_loop must have the expected structure."""

    @pytest.mark.asyncio
    async def test_run_loop_returns_loop_result(self) -> None:
        """Verify return value has expected structure (LoopResult)."""
        run_loop, LoopResult = _import_runner()

        agent = MockAgent(completion_iteration=2)
        state = LoopState(task="verify result", max_iterations=10)

        result = await run_loop(agent=agent, state=state)

        assert isinstance(result, LoopResult)
        assert hasattr(result, "state")
        assert result.state is state
        assert hasattr(result, "iterations")
        assert result.iterations == 2
