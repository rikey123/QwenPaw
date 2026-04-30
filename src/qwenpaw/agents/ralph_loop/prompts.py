# -*- coding: utf-8 -*-
"""Prompt templates for the Ralph Loop — a self-referential development loop."""

from __future__ import annotations


def build_initial_prompt(task: str, max_iterations: int) -> str:
    """Build the initial system prompt for starting a ralph loop.

    Instructs the agent to work on the task and signal completion by writing
    a completion.json file with '{"done": true}' using write_file tool.
    """
    return f"""You are starting a Ralph Loop — a self-referential development loop that runs until the task is 100% complete.

Your task: {task}

IMPORTANT RULES:
1. Work continuously on the task above. Use all tools available to you.
2. When you have FULLY COMPLETED the task, write a file named 'completion.json' with content: {{"done": true, "summary": "<brief summary of what was accomplished>"}}
3. Do NOT write completion.json until the task is truly done.
4. Maximum iterations allowed: {max_iterations}
5. After each work iteration, the system will check if completion.json exists. If it doesn't, you will be asked to continue.
"""


def build_continuation_prompt(task: str, iteration: int, max_iterations: int) -> str:
    """Build the prompt injected between iterations when task is not done yet."""
    return f"""Continue working on the task. It is not yet complete.

Your task reminder: {task}
Current iteration: {iteration}/{max_iterations}

Remember: When you have FULLY COMPLETED the task, write a file named 'completion.json' with content: {{"done": true, "summary": "<brief summary>"}}
Do NOT mark it complete until it is truly done.
"""
