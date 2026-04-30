# -*- coding: utf-8 -*-
"""Test fixtures for ralph-loop unit tests.

Provides shared fixtures for all ralph-loop test modules:
    - LoopState instances (fresh, completed, cancelled)
    - MockAgent with controllable completion, error, and empty-response behavior
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from qwenpaw.agents.ralph_loop.state import LoopState


# =============================================================================
# Helper Types
# =============================================================================


@dataclass
class MockMsg:
    """Simulate an LLM response message for testing."""

    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class MockAgent:
    """Mock agent that simulates controllable ralph-loop behavior.

    Args:
        completion_iteration: If set, agent signals completion at this iteration.
            None means the agent never completes.
        raises_error: If True, agent raises RuntimeError on 2nd call.
        empty_response: If True, agent returns empty/None responses.
    """

    def __init__(
        self,
        completion_iteration: int | None = None,
        raises_error: bool = False,
        empty_response: bool = False,
    ) -> None:
        self.call_count = 0
        self.completion_iteration = completion_iteration
        self.raises_error = raises_error
        self.empty_response = empty_response
        self.auto_continue_on_text_only = True

    async def __call__(self, messages: list[dict], **kwargs: Any) -> MockMsg:
        """Simulate an agent invocation.

        Increments call count on each invocation. Optionally raises an error
        or signals completion based on constructor parameters.
        """
        self.call_count += 1
        if self.raises_error and self.call_count == 2:
            raise RuntimeError("Simulated agent error")

        result = MockMsg(
            content=(
                ""
                if self.empty_response
                else f"Iteration {self.call_count} response"
            ),
        )

        if (
            self.completion_iteration is not None
            and self.call_count >= self.completion_iteration
        ):
            result.metadata["completed"] = True

        return result


# =============================================================================
# LoopState Fixtures
# =============================================================================


@pytest.fixture
def mock_loop_state() -> LoopState:
    """Create a fresh LoopState with default values for a simple task."""
    return LoopState(task="Implement hello world", max_iterations=10)


@pytest.fixture
def completed_loop_state() -> LoopState:
    """Create a completed LoopState."""
    state = LoopState(task="Implement hello world", max_iterations=5)
    state.mark_complete()
    return state


@pytest.fixture
def cancelled_loop_state() -> LoopState:
    """Create a cancelled LoopState."""
    state = LoopState(task="Implement hello world", max_iterations=5)
    state.cancel()
    return state


# =============================================================================
# Mock Agent Fixtures
# =============================================================================


@pytest.fixture
def mock_agent_for_ralph() -> MockAgent:
    """Mock agent that completes at iteration 3."""
    return MockAgent(completion_iteration=3)


@pytest.fixture
def mock_agent_never_finishes() -> MockAgent:
    """Mock agent that never completes (for max iterations test)."""
    return MockAgent(completion_iteration=None)


@pytest.fixture
def mock_agent_throws_error() -> MockAgent:
    """Mock agent that throws error on 2nd call (for error handling test)."""
    return MockAgent(completion_iteration=None, raises_error=True)
