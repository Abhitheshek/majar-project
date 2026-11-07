"""Resilient LLM invocation policy."""

import re
import time
from typing import Any

from rich.console import Console

from core.config import config
from core.llm import LLMManager


class ModelInvoker:
    """Invoke the configured LLM and retry short-lived provider rate limits."""

    def __init__(self, llm_manager: LLMManager, console: Console) -> None:
        self._llm_manager = llm_manager
        self._console = console

    def invoke_with_tools(self, messages: list[Any]) -> Any:
        for attempt in range(config.llm_rate_limit_retries + 1):
            try:
                return self._llm_manager.invoke_with_tools(messages)
            except Exception as error:
                if not self._should_retry(error, attempt):
                    raise
                wait_seconds = self._retry_delay(error)
                self._console.print(
                    f"[yellow]LLM rate limit reached. Retrying in {wait_seconds:.1f} seconds "
                    f"({attempt + 1}/{config.llm_rate_limit_retries})...[/yellow]"
                )
                time.sleep(wait_seconds)
        raise RuntimeError("Model invocation did not return a response")

    @staticmethod
    def _should_retry(error: Exception, attempt: int) -> bool:
        message = str(error).lower()
        return attempt < config.llm_rate_limit_retries and ("429" in message or "rate_limit" in message)

    @staticmethod
    def _retry_delay(error: Exception) -> float:
        match = re.search(r"try again in\s+(\d+)ms", str(error), re.IGNORECASE)
        return max(1.0, int(match.group(1)) / 1000 + 0.5) if match else 2.0
