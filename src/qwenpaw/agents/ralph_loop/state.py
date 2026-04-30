# -*- coding: utf-8 -*-
"""LoopState — in-memory state for a Ralph Loop iteration.

All state is kept in-memory — no disk files are created.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class LoopState:
    """Tracks iteration count, completion, and cancellation status."""

    task: str
    iteration: int = 0
    max_iterations: int = 20
    active: bool = True
    completed: bool = False
    cancelled: bool = False
    start_time: float = field(default_factory=time.time)

    def is_active(self) -> bool:
        """Return True if the loop is still running."""
        return self.active and not self.completed and not self.cancelled

    def is_max_reached(self) -> bool:
        """Return True when iteration count meets or exceeds the limit."""
        return self.iteration >= self.max_iterations

    def is_done(self) -> bool:
        """Return True if the loop should stop for any reason."""
        return self.completed or self.cancelled or self.is_max_reached()

    def increment(self) -> None:
        """Advance the iteration counter by one."""
        self.iteration += 1

    def mark_complete(self) -> None:
        """Mark the loop as successfully completed."""
        self.completed = True
        self.active = False

    def cancel(self) -> None:
        """Mark the loop as cancelled by the user."""
        self.cancelled = True
        self.active = False
