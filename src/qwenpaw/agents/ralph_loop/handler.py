# -*- coding: utf-8 -*-
"""Command handler for the /ralph-loop magic command."""
from __future__ import annotations

import re

# Regex to detect /ralph-loop prefix
RALPH_PREFIX_RE = re.compile(r"^/ralph-loop\b\s*", re.IGNORECASE)
# Regex for --max-iterations=N flag
MAX_ITER_RE = re.compile(r"--max-iterations=(\d+)\s*")
# Meta-question patterns to reject
META_PATTERNS = [
    r"what\s+is\s+ralph",
    r"how\s+(does|do)\s+ralph",
    r"explain\s+ralph",
]
MIN_TASK_LENGTH = 5


def is_ralph_command(query: str) -> bool:
    """Check if the query starts with /ralph-loop prefix."""
    return bool(RALPH_PREFIX_RE.match(query.strip()))


def parse_ralph_command(query: str) -> dict | None:
    """Parse /ralph-loop command and extract task and max_iterations.

    Returns:
        dict with "task" (str) and "max_iterations" (int) if valid,
        None if no task provided.
    """
    query = query.strip()

    # Remove the /ralph-loop prefix
    match = RALPH_PREFIX_RE.match(query)
    if not match:
        return None

    remainder = query[match.end() :].strip()

    # Check for --max-iterations flag
    max_iter = 20  # default
    iter_match = MAX_ITER_RE.match(remainder)
    if iter_match:
        max_iter = int(iter_match.group(1))
        remainder = remainder[iter_match.end() :].strip()

    if not remainder:
        return None

    # Validate the task content (length, meta-questions).
    if validate_ralph_task(remainder) is not None:
        return None

    return {
        "task": remainder,
        "max_iterations": max_iter,
    }


def validate_ralph_task(task: str) -> str | None:
    """Validate the task text.

    Returns:
        Error message if invalid, None if valid.
    """
    if len(task.strip()) < MIN_TASK_LENGTH:
        return f"Task too short (minimum {MIN_TASK_LENGTH} characters)"

    for pattern in META_PATTERNS:
        if re.search(pattern, task, re.IGNORECASE):
            return "Meta-question detected. Please provide a concrete task."

    return None
