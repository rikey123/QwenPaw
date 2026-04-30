# -*- coding: utf-8 -*-
"""Contract tests for ralph-loop module interface compliance.

These tests verify that the ralph-loop modules conform to expected
interfaces. When any interface changes, these tests catch regressions
across all consumers.

All tests are currently RED (failing) because the implementation modules
do not yet exist or are incomplete. They will turn GREEN as the
ralph-loop feature is implemented.

Run:
    pytest tests/contract/agents/ralph_loop/ -v
"""

from __future__ import annotations

import inspect

import pytest


class TestRalphLoopContracts:
    """Verify ralph-loop modules conform to expected interfaces."""

    # =========================================================================
    # Contract: LoopState interface
    # =========================================================================

    def test_loop_state_interface(self):
        """LoopState must have: task, iteration, max_iterations, active,
        completed, cancelled, is_active(), is_max_reached(), is_done(),
        increment(), mark_complete(), cancel().

        This contract ensures the state object provides all attributes
        and methods that the runner and dispatch modules depend on.
        """
        try:
            from qwenpaw.agents.ralph_loop.state import LoopState
        except ImportError:
            pytest.fail(
                "LoopState cannot be imported from "
                "qwenpaw.agents.ralph_loop.state"
            )

        # Verify required attributes
        required_attrs = [
            "task",
            "iteration",
            "max_iterations",
            "active",
            "completed",
            "cancelled",
        ]
        for attr in required_attrs:
            if not hasattr(LoopState, attr) and attr not in (
                LoopState.__dataclass_fields__
                if hasattr(LoopState, "__dataclass_fields__")
                else {}
            ):
                pytest.fail(
                    f"LoopState missing required attribute: {attr}"
                )

        # Verify required methods
        required_methods = [
            "is_active",
            "is_max_reached",
            "is_done",
            "increment",
            "mark_complete",
            "cancel",
        ]
        for method in required_methods:
            if not hasattr(LoopState, method):
                pytest.fail(
                    f"LoopState missing required method: {method}"
                )
            if not callable(getattr(LoopState, method, None)):
                pytest.fail(
                    f"LoopState.{method} must be callable"
                )

    # =========================================================================
    # Contract: prompts module interface
    # =========================================================================

    def test_prompt_interface(self):
        """prompts module must expose:
        build_initial_prompt(task, max_iterations) -> str
        build_continuation_prompt(task, iteration, max_iterations) -> str

        The runner depends on these two functions to generate the initial
        and continuation prompts for each iteration.
        """
        try:
            from qwenpaw.agents.ralph_loop import prompts
        except ImportError:
            pytest.fail(
                "prompts module cannot be imported from "
                "qwenpaw.agents.ralph_loop"
            )

        # Verify build_initial_prompt exists and is callable
        if not hasattr(prompts, "build_initial_prompt"):
            pytest.fail(
                "prompts module missing build_initial_prompt function"
            )
        if not callable(prompts.build_initial_prompt):
            pytest.fail("build_initial_prompt must be callable")

        # Verify build_initial_prompt signature
        sig = inspect.signature(prompts.build_initial_prompt)
        param_names = list(sig.parameters.keys())
        if "task" not in param_names:
            pytest.fail(
                "build_initial_prompt must accept 'task' parameter"
            )
        if "max_iterations" not in param_names:
            pytest.fail(
                "build_initial_prompt must accept 'max_iterations' "
                "parameter"
            )

        # Verify build_continuation_prompt exists and is callable
        if not hasattr(prompts, "build_continuation_prompt"):
            pytest.fail(
                "prompts module missing build_continuation_prompt function"
            )
        if not callable(prompts.build_continuation_prompt):
            pytest.fail("build_continuation_prompt must be callable")

        # Verify build_continuation_prompt signature
        sig = inspect.signature(prompts.build_continuation_prompt)
        param_names = list(sig.parameters.keys())
        for required_param in ("task", "iteration", "max_iterations"):
            if required_param not in param_names:
                pytest.fail(
                    f"build_continuation_prompt must accept "
                    f"'{required_param}' parameter"
                )

    # =========================================================================
    # Contract: handler return type
    # =========================================================================

    def test_handler_returns_dict_or_none(self):
        """parse_ralph_command must return dict (valid) or None (invalid).

        This contract ensures the handler's return type is consistent:
        - Valid /ralph-loop command → dict with 'task' and
          'max_iterations' keys
        - Invalid command → None
        """
        try:
            from qwenpaw.agents.ralph_loop.handler import (
                parse_ralph_command,
            )
        except ImportError:
            pytest.fail(
                "parse_ralph_command cannot be imported from "
                "qwenpaw.agents.ralph_loop.handler"
            )

        # Test with valid input
        result = parse_ralph_command("/ralph-loop Implement hello world")
        if result is not None and not isinstance(result, dict):
            pytest.fail(
                f"parse_ralph_command must return dict or None, "
                f"got {type(result).__name__}"
            )
        if isinstance(result, dict):
            if "task" not in result:
                pytest.fail(
                    "parse_ralph_command result dict must contain "
                    "'task' key"
                )

        # Test with invalid input
        result_invalid = parse_ralph_command("/help")
        if result_invalid is not None:
            pytest.fail(
                f"parse_ralph_command must return None for non-ralph "
                f"commands, got {type(result_invalid).__name__}"
            )

    # =========================================================================
    # Contract: handler accepts valid tasks
    # =========================================================================

    def test_handler_accepts_valid_task(self):
        """Handler must accept valid tasks (>=5 chars, not meta-questions).

        Valid tasks should be parsed successfully and return a dict with
        at minimum a 'task' key containing the task description.
        """
        try:
            from qwenpaw.agents.ralph_loop.handler import (
                parse_ralph_command,
            )
        except ImportError:
            pytest.fail(
                "parse_ralph_command cannot be imported from "
                "qwenpaw.agents.ralph_loop.handler"
            )

        # Valid task with sufficient length
        result = parse_ralph_command(
            "/ralph-loop Implement a hello world program"
        )
        if result is None:
            pytest.fail(
                "parse_ralph_command must return dict for valid tasks "
                "with >=5 chars"
            )
        if not isinstance(result, dict):
            pytest.fail(
                f"parse_ralph_command must return dict for valid input, "
                f"got {type(result).__name__}"
            )
        if "task" not in result:
            pytest.fail(
                "parse_ralph_command result must contain 'task' key"
            )

    # =========================================================================
    # Contract: handler rejects invalid input
    # =========================================================================

    def test_handler_rejects_invalid(self):
        """Handler must reject empty/short tasks and meta-questions.

        - Empty task (no text after /ralph-loop) → should return None
          or dict with help info
        - Short task (<5 chars) → should return None or indicate error
        - Meta-questions about ralph-loop itself → should be rejected
        """
        try:
            from qwenpaw.agents.ralph_loop.handler import (
                parse_ralph_command,
            )
        except ImportError:
            pytest.fail(
                "parse_ralph_command cannot be imported from "
                "qwenpaw.agents.ralph_loop.handler"
            )

        # Short task (<5 chars) should be rejected
        short_result = parse_ralph_command("/ralph-loop abc")
        if short_result is not None and isinstance(short_result, dict):
            if "task" in short_result:
                task_val = short_result["task"]
                if isinstance(task_val, str) and len(task_val) < 5:
                    pytest.fail(
                        "parse_ralph_command must reject tasks shorter "
                        "than 5 characters"
                    )

        # Meta-question about ralph loop should be rejected
        meta_result = parse_ralph_command(
            "/ralph-loop what is ralph loop?"
        )
        if meta_result is not None and isinstance(meta_result, dict):
            if "task" in meta_result:
                pytest.fail(
                    "parse_ralph_command must reject meta-questions "
                    "about ralph loop itself"
                )

    # =========================================================================
    # Contract: dispatch function signature
    # =========================================================================

    def test_dispatch_function_signature(self):
        """maybe_handle_ralph_command(query, agent_manager) -> dict | None.

        The dispatch function is the entry point for ralph-loop command
        routing. It must accept a query string and agent manager, and
        return either a dict (when /ralph-loop is detected) or None
        (when the query is not a ralph-loop command).
        """
        try:
            from qwenpaw.app.runner.ralph_dispatch import (
                maybe_handle_ralph_command,
            )
        except ImportError:
            pytest.fail(
                "maybe_handle_ralph_command cannot be imported from "
                "qwenpaw.app.runner.ralph_dispatch"
            )

        # Verify function exists and is callable
        if not callable(maybe_handle_ralph_command):
            pytest.fail("maybe_handle_ralph_command must be callable")

        # Verify signature accepts query and agent_manager
        sig = inspect.signature(maybe_handle_ralph_command)
        param_names = list(sig.parameters.keys())
        if "query" not in param_names:
            pytest.fail(
                "maybe_handle_ralph_command must accept 'query' parameter"
            )

    # =========================================================================
    # Contract: cancel handler is a control command
    # =========================================================================

    def test_cancel_handler_is_control_command(self):
        """CancelLoopHandler must have:
        command_name = '/cancel-loop' and async handle(context).

        The cancel handler must conform to the BaseControlCommandHandler
        interface: it must define command_name and implement an async
        handle() method that accepts a ControlContext and returns a str.
        """
        try:
            from qwenpaw.app.runner.control_commands.cancel_loop import (
                CancelLoopHandler,
            )
        except ImportError:
            pytest.fail(
                "CancelLoopHandler cannot be imported from "
                "qwenpaw.app.runner.control_commands.cancel_loop"
            )

        # Verify command_name attribute
        if not hasattr(CancelLoopHandler, "command_name"):
            pytest.fail(
                "CancelLoopHandler must have 'command_name' class "
                "attribute"
            )

        # Verify command_name value
        command_name = CancelLoopHandler.command_name
        if command_name != "/cancel-loop":
            pytest.fail(
                f"CancelLoopHandler.command_name must be "
                f"'/cancel-loop', got {command_name!r}"
            )

        # Verify handle method exists and is async
        if not hasattr(CancelLoopHandler, "handle"):
            pytest.fail("CancelLoopHandler must implement 'handle' method")

        if not callable(getattr(CancelLoopHandler, "handle")):
            pytest.fail("CancelLoopHandler.handle must be callable")

        # Verify handle is a coroutine function
        if not inspect.iscoroutinefunction(CancelLoopHandler.handle):
            pytest.fail(
                "CancelLoopHandler.handle must be an async method "
                "(coroutine function)"
            )
