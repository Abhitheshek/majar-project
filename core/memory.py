"""Rolling conversation memory for the LangGraph agent."""

from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from rich.console import Console

from .config import config
from .state import AgentState


console = Console()


class ConversationMemory:
    """Keep recent messages verbatim and compress older messages into a summary."""

    def update(self, state: AgentState, messages: list[BaseMessage], llm: Any) -> tuple[str, int]:
        """Return the updated summary and count of messages it represents."""
        target_count = max(0, len(messages) - config.recent_message_limit)
        target_count = self._safe_message_boundary(messages, target_count)
        already_compressed = min(state.memory_message_count, target_count)

        if target_count == already_compressed:
            return state.memory_summary, already_compressed

        messages_to_compress = messages[already_compressed:target_count]
        summary = self._compress(state.memory_summary, messages_to_compress, llm)
        return summary, target_count

    @staticmethod
    def _safe_message_boundary(messages: list[BaseMessage], boundary: int) -> int:
        """Avoid starting the LLM context with a dangling tool result.

        A ToolMessage is only valid after the AI message that requested its tool
        call. The rolling memory window may therefore grow beyond five raw
        messages when keeping that pair intact.
        """
        while boundary > 0 and isinstance(messages[boundary], ToolMessage):
            boundary -= 1
        return boundary

    def _compress(self, existing_summary: str, messages: list[BaseMessage], llm: Any) -> str:
        transcript = self._messages_to_transcript(messages)
        transcript = self._limit_compression_input(transcript)
        prompt = (
            "Maintain concise memory for a coding assistant. Preserve user goals, project facts, "
            "decisions, changed files, errors, and unfinished work. Do not invent details. "
            "Return only the updated memory summary.\n\n"
            f"Existing memory:\n{existing_summary or '(none)'}\n\n"
            f"New conversation to compress:\n{transcript}"
        )
        try:
            response = llm.invoke([
                SystemMessage(content="You create compact, factual conversation memory."),
                HumanMessage(content=prompt),
            ])
            summary = self.message_content(response).strip()
        except Exception as error:
            # Context remains available when the optional summarization request fails.
            summary = f"{existing_summary}\n{transcript}".strip()
            console.print(f"[yellow]Memory compression fallback: {error}[/yellow]")

        return summary[-config.memory_summary_max_chars:]

    @staticmethod
    def _limit_compression_input(transcript: str) -> str:
        """Keep a recovery summary request safely below the provider token limit."""
        max_chars = config.memory_compression_input_max_chars
        if len(transcript) <= max_chars:
            return transcript
        return "[Earlier messages omitted; newest prior context follows]\n" + transcript[-max_chars:]

    @classmethod
    def _messages_to_transcript(cls, messages: list[BaseMessage]) -> str:
        entries = []
        for message in messages:
            role = message.__class__.__name__.replace("Message", "")
            entries.append(f"{role}: {cls.message_content(message)[:1200]}")
        return "\n".join(entries)

    @staticmethod
    def message_content(message: BaseMessage) -> str:
        """Normalize string and multimodal LangChain message content."""
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                block.get("text", str(block)) if isinstance(block, dict) else str(block)
                for block in content
            )
        return str(content)
