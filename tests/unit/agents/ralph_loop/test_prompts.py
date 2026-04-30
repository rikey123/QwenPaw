# -*- coding: utf-8 -*-
"""Tests for Ralph Loop prompt templates."""

from qwenpaw.agents.ralph_loop.prompts import (
    build_initial_prompt,
    build_continuation_prompt,
)


class TestBuildInitialPrompt:
    """Tests for build_initial_prompt."""

    def test_initial_prompt_contains_task(self):
        """The prompt should contain the task description."""
        prompt = build_initial_prompt("Implement feature X", 20)
        assert "Implement feature X" in prompt

    def test_initial_prompt_contains_completion_instruction(self):
        """The prompt should mention completion.json."""
        prompt = build_initial_prompt("Do something", 10)
        assert "completion.json" in prompt

    def test_initial_prompt_contains_max_iterations(self):
        """The prompt should contain the max_iterations number."""
        prompt = build_initial_prompt("Do something", 42)
        assert "42" in prompt

    def test_prompt_rejects_empty_task(self):
        """An empty task string should result in a non-empty or helpful prompt."""
        prompt = build_initial_prompt("", 20)
        # The prompt itself is still returned; it should not blow up
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_completion_indicator_format(self):
        """The prompt should mention completion.json."""
        prompt = build_initial_prompt("Test task", 5)
        assert "completion.json" in prompt


class TestBuildContinuationPrompt:
    """Tests for build_continuation_prompt."""

    def test_continuation_prompt_different_from_initial(self):
        """Continuation prompt should differ from the initial prompt (different text)."""
        initial = build_initial_prompt("Do thing", 10)
        continuation = build_continuation_prompt("Do thing", 1, 10)
        assert continuation != initial

    def test_continuation_prompt_reminds_task(self):
        """Continuation prompt should contain the task."""
        prompt = build_continuation_prompt("Fix bug #42", 3, 10)
        assert "Fix bug #42" in prompt

    def test_continuation_prompt_mentions_iteration(self):
        """Continuation prompt should mention iteration N / max."""
        prompt = build_continuation_prompt("Do thing", 3, 10)
        assert "3/10" in prompt

    def test_continuation_prompt_mentions_completion(self):
        """Continuation prompt should also mention completion.json."""
        prompt = build_continuation_prompt("Do thing", 2, 10)
        assert "completion.json" in prompt
