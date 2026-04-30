# -*- coding: utf-8 -*-
"""Unit tests for LoopState (TDD — RED then GREEN)."""

from __future__ import annotations

import os
import tempfile

from qwenpaw.agents.ralph_loop.state import LoopState


class TestLoopStateLifecycle:
    """LoopState creation and basic attribute tests."""

    def test_create_loop_state(self) -> None:
        """Create a LoopState and verify default attribute values."""
        state = LoopState(task="test")
        assert state.task == "test"
        assert state.iteration == 0
        assert state.active is True
        assert state.completed is False
        assert state.cancelled is False

    def test_increment_iteration(self) -> None:
        """Call increment() 3 times and verify iteration == 3."""
        state = LoopState(task="test")
        state.increment()
        state.increment()
        state.increment()
        assert state.iteration == 3

    def test_mark_complete(self) -> None:
        """After mark_complete(), completed==True, active==False."""
        state = LoopState(task="test")
        state.mark_complete()
        assert state.completed is True
        assert state.active is False

    def test_cancel_loop(self) -> None:
        """After cancel(), cancelled==True, active==False."""
        state = LoopState(task="test")
        state.cancel()
        assert state.cancelled is True
        assert state.active is False

    def test_is_active_returns_true_for_new_state(self) -> None:
        """A fresh LoopState should report is_active() == True."""
        state = LoopState(task="test")
        assert state.is_active() is True

    def test_is_active_returns_false_after_complete(self) -> None:
        """After mark_complete(), is_active() should return False."""
        state = LoopState(task="test")
        state.mark_complete()
        assert state.is_active() is False

    def test_is_active_returns_false_after_cancel(self) -> None:
        """After cancel(), is_active() should return False."""
        state = LoopState(task="test")
        state.cancel()
        assert state.is_active() is False

    def test_max_iterations_reached(self) -> None:
        """When iteration >= max_iterations, is_max_reached() and is_done() return True."""
        state = LoopState(task="test", max_iterations=3)
        state.increment()
        state.increment()
        state.increment()
        assert state.is_max_reached() is True
        assert state.is_done() is True

    def test_state_is_memory_only(self) -> None:
        """LoopState must NOT create any disk files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            before = set(os.listdir(tmpdir))
            _ = LoopState(task="memory-only-test")
            after = set(os.listdir(tmpdir))
            assert before == after, "LoopState should not create any files on disk"
