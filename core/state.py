"""State management for the agent workflow"""
from typing import Annotated, Sequence
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(BaseModel):
    """State management for the agent workflow"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_file: str = ""
    error_context: str = ""
    tool_calls_count: int = 0
    working_directory: str = ""
    memory_summary: str = ""
    memory_message_count: int = 0
