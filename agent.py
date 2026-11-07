"""Backward-compatible export for the application agent.

Prefer importing ``app.agent.CodeAssistantAgent`` in new code.
"""

from app.agent import CodeAssistantAgent

__all__ = ["CodeAssistantAgent"]
