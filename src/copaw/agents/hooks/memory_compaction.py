# -*- coding: utf-8 -*-
"""Memory compaction hook for managing context window.

This hook monitors token usage and automatically compacts older messages
when the context window approaches its limit, preserving recent messages
and the system prompt.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from agentscope.agent import ReActAgent
from agentscope.message import Msg, TextBlock
from pydantic import ValidationError
from copaw.constant import MEMORY_COMPACT_KEEP_RECENT

from ...config.config import load_agent_config
from ..utils import (
    check_valid_messages,
    get_copaw_token_counter,
)

if TYPE_CHECKING:
    from ..memory import BaseMemoryManager

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class MemoryCompactionHook:
    """Hook for automatic memory compaction when context is full.

    This hook monitors the token count of messages and triggers compaction
    when it exceeds the threshold. It preserves the system prompt and recent
    messages while summarizing older conversation history.
    """

    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE_SECONDS = 1.0
    STATUS_STARTED = "\U0001F4E7 Context compaction started..."
    STATUS_COMPLETED = "\u2705 Context compaction completed"
    STATUS_SKIPPED = "\u2705 Context compaction skipped"
    STATUS_FAILED_PREFIX = "\u26A0\uFE0F Context compaction failed: "

    def __init__(self, memory_manager: "BaseMemoryManager"):
        """Initialize memory compaction hook.

        Args:
            memory_manager: Memory manager instance for compaction
        """
        self.memory_manager = memory_manager

    @staticmethod
    async def _print_status_message(
        agent: ReActAgent,
        text: str,
    ) -> None:
        """Print a status message to the agent's output.

        Args:
            agent: The agent instance to print the message for.
            text: The text content of the status message.
        """
        msg = Msg(
            name=agent.name,
            role="assistant",
            content=[TextBlock(type="text", text=text)],
        )
        await agent.print(msg)

    @classmethod
    def _compute_retry_backoff(cls, attempt: int) -> float:
        """Return exponential backoff delay for the next retry."""
        return cls.RETRY_BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1))

    @staticmethod
    def _is_valid_compact_content(compact_content: str) -> bool:
        """Return True when compaction produced usable summary content."""
        return bool(
            compact_content and not compact_content.lstrip().startswith("["),
        )

    @staticmethod
    def _is_threshold_exhausted(left_compact_threshold: int) -> bool:
        """Return True when no compaction budget remains.

        This is measured after fixed context is accounted for.
        """
        return left_compact_threshold <= 0

    async def _get_token_context(
        self,
        agent: ReActAgent,
        agent_config: Any,
    ) -> tuple[Any, Any, int]:
        """Return memory, token counter, and remaining compaction budget."""
        memory = agent.memory
        token_counter = get_copaw_token_counter(agent_config)
        combined_text = (agent.sys_prompt or "") + (
            memory.get_compressed_summary() or ""
        )
        str_token_count = await token_counter.count(
            messages=[],
            text=combined_text,
        )
        left_compact_threshold = (
            agent_config.running.memory_compact_threshold - str_token_count
        )
        return memory, token_counter, left_compact_threshold

    async def _compact_tool_results_if_enabled(
        self,
        messages: list[Msg],
        running_config: Any,
    ) -> None:
        """Compact stored tool results when the feature is enabled."""
        tool_result_config = running_config.tool_result_compact
        if not tool_result_config.enabled:
            return

        await self.memory_manager.compact_tool_result(
            messages=messages,
            recent_n=tool_result_config.recent_n,
            old_max_bytes=tool_result_config.old_max_bytes,
            recent_max_bytes=tool_result_config.recent_max_bytes,
            retention_days=tool_result_config.retention_days,
        )

    @staticmethod
    def _handle_invalid_messages(messages: list[Msg]) -> list[Msg]:
        """Return the compactable portion for invalid message history."""
        logger.warning(
            "Please include the output of the /history command when "
            "reporting the bug to the community. Invalid "
            "messages=%s",
            messages,
        )
        keep_length: int = MEMORY_COMPACT_KEEP_RECENT
        messages_length = len(messages)
        while keep_length > 0 and not check_valid_messages(
            messages[max(messages_length - keep_length, 0) :],
        ):
            keep_length -= 1

        if keep_length > 0:
            return messages[: max(messages_length - keep_length, 0)]

        return messages

    async def _get_messages_to_compact(
        self,
        messages: list[Msg],
        left_compact_threshold: int,
        memory_compact_reserve: int,
        token_counter: Any,
    ) -> list[Msg]:
        """Return the validated set of messages to compact."""
        (
            messages_to_compact,
            _,
            is_valid,
        ) = await self.memory_manager.check_context(
            messages=messages,
            memory_compact_threshold=left_compact_threshold,
            memory_compact_reserve=memory_compact_reserve,
            as_token_counter=token_counter,
        )

        if not messages_to_compact:
            return []

        if not is_valid:
            return self._handle_invalid_messages(messages)

        return messages_to_compact

    async def _execute_compact_with_retry(
        self,
        memory: Any,
        messages_to_compact: list[Msg],
    ) -> tuple[str, str]:
        """Run memory compaction with retry and exponential backoff."""
        compact_content = ""
        last_error = ""

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                compact_content = await self.memory_manager.compact_memory(
                    messages=messages_to_compact,
                    previous_summary=memory.get_compressed_summary(),
                )
                break
            except (
                asyncio.TimeoutError,
                OSError,
                RuntimeError,
            ) as exc:
                last_error = str(exc)
                if attempt < self.MAX_RETRIES:
                    backoff = self._compute_retry_backoff(attempt)
                    logger.warning(
                        "compact_memory attempt %d/%d failed: %s, "
                        "retrying in %.1fs...",
                        attempt,
                        self.MAX_RETRIES,
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "compact_memory failed after %d attempts: %s",
                        self.MAX_RETRIES,
                        exc,
                    )

        return compact_content, last_error

    async def _run_context_compaction(
        self,
        agent: ReActAgent,
        running_config: Any,
        memory: Any,
        messages_to_compact: list[Msg],
    ) -> str:
        """Run context compaction and emit status messages."""
        await self._print_status_message(agent, self.STATUS_STARTED)

        if not running_config.context_compact.context_compact_enabled:
            await self._print_status_message(agent, self.STATUS_SKIPPED)
            return ""

        compact_content, last_error = await self._execute_compact_with_retry(
            memory=memory,
            messages_to_compact=messages_to_compact,
        )

        if not self._is_valid_compact_content(compact_content):
            error_msg = last_error or "empty result"
            await self._print_status_message(
                agent,
                f"{self.STATUS_FAILED_PREFIX}{error_msg}",
            )
            return ""

        await self._print_status_message(agent, self.STATUS_COMPLETED)
        return compact_content

    @staticmethod
    async def _persist_compacted_summary(
        memory: Any,
        messages_to_compact: list[Msg],
        compact_content: str,
    ) -> None:
        """Mark compacted messages and store the new compressed summary."""
        updated_count = await memory.mark_messages_compressed(
            messages_to_compact,
        )
        logger.info("Marked %d messages as compacted", updated_count)
        await memory.update_compressed_summary(compact_content)

    async def __call__(
        self,
        agent: ReActAgent,
        kwargs: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Pre-reasoning hook to check and compact memory if needed.

        This hook extracts system prompt messages and recent messages,
        builds an estimated full context prompt, and triggers compaction
        when the total estimated token count exceeds the threshold.

        Memory structure:
            [System Prompt (preserved)] + [Compactable (counted)] +
            [Recent (preserved)]

        Args:
            agent: The agent instance
            kwargs: Input arguments to the _reasoning method

        Returns:
            None (hook doesn't modify kwargs)
        """
        del kwargs

        try:
            agent_config = load_agent_config(self.memory_manager.agent_id)
            running_config = agent_config.running
            (
                memory,
                token_counter,
                left_compact_threshold,
            ) = await self._get_token_context(
                agent=agent,
                agent_config=agent_config,
            )

            if self._is_threshold_exhausted(left_compact_threshold):
                logger.warning(
                    "The memory_compact_threshold is set too low; "
                    "the combined token length of system_prompt and "
                    "compressed_summary exceeds the configured threshold. "
                    "Alternatively, you could use /clear to reset the context "
                    "and compressed_summary, ensuring the total remains "
                    "below the threshold.",
                )
                return None

            messages = await memory.get_memory(prepend_summary=False)
            await self._compact_tool_results_if_enabled(
                messages=messages,
                running_config=running_config,
            )
            # pylint: disable=no-member
            messages_to_compact = await self._get_messages_to_compact(
                messages=messages,
                left_compact_threshold=left_compact_threshold,
                memory_compact_reserve=running_config.memory_compact_reserve,
                token_counter=token_counter,
            )
            if not messages_to_compact:
                return None

            if running_config.memory_summary.memory_summary_enabled:
                self.memory_manager.add_async_summary_task(
                    messages=messages_to_compact,
                )
            # pylint: enable=no-member

            compact_content = await self._run_context_compaction(
                agent=agent,
                running_config=running_config,
                memory=memory,
                messages_to_compact=messages_to_compact,
            )
            if compact_content:
                await self._persist_compacted_summary(
                    memory=memory,
                    messages_to_compact=messages_to_compact,
                    compact_content=compact_content,
                )

        except (
            asyncio.TimeoutError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            logger.exception(
                "Failed to compact memory in pre_reasoning hook: %s",
                exc,
                exc_info=True,
            )

        return None
