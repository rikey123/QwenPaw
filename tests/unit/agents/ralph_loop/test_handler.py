# -*- coding: utf-8 -*-
"""Tests for the ralph-loop command handler (RED phase).

These tests will fail because ``ralph_loop.handler`` does not exist yet.
They define the expected contract for the handler module to be implemented
in Task 9.
"""

from __future__ import annotations

import pytest

from qwenpaw.agents.ralph_loop.handler import (
    is_ralph_command,
    parse_ralph_command,
    validate_ralph_task,
)


class TestIsRalphCommand:
    """Tests for ``is_ralph_command``."""

    def test_is_ralph_command_true(self) -> None:
        """Return True when query starts with /ralph-loop and has args."""
        assert is_ralph_command("/ralph-loop Implement hello world") is True

    def test_is_ralph_command_with_prefix_only(self) -> None:
        """Return True even when /ralph-loop has no additional arguments."""
        assert is_ralph_command("/ralph-loop") is True

    def test_is_ralph_command_false(self) -> None:
        """Return False for unrelated commands like /help."""
        assert is_ralph_command("/help") is False

    def test_is_ralph_command_false_for_similar(self) -> None:
        """Return False for similar-looking but different commands."""
        assert is_ralph_command("/ralph-something") is False


class TestParseRalphCommand:
    """Tests for ``parse_ralph_command``."""

    def test_parse_ralph_command_with_task(self) -> None:
        """Parse a full command and return the task with default iterations."""
        result = parse_ralph_command("/ralph-loop Implement hello world")
        assert result == {
            "task": "Implement hello world",
            "max_iterations": 20,
        }

    def test_parse_ralph_command_no_task(self) -> None:
        """Return None when no task is provided."""
        result = parse_ralph_command("/ralph-loop")
        assert result is None

    def test_parse_ralph_command_with_max_iterations_flag(self) -> None:
        """Parse --max-iterations=N flag and the remaining task text."""
        result = parse_ralph_command(
            "/ralph-loop --max-iterations=10 test task",
        )
        assert result == {
            "task": "test task",
            "max_iterations": 10,
        }


class TestValidateRalphTask:
    """Tests for ``validate_ralph_task``."""

    def test_validate_ralph_task_short(self) -> None:
        """Return an error string when the task is too short."""
        error = validate_ralph_task("hi")
        assert isinstance(error, str)
        assert len(error) > 0

    def test_validate_ralph_task_valid(self) -> None:
        """Return None when the task passes validation."""
        result = validate_ralph_task("Implement a hello world program")
        assert result is None
