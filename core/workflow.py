"""LangGraph workflow definition for Code Assistant.

This module contains only graph wiring. Node behavior remains in ``agent.py`` so
the workflow is easy to inspect independently from the assistant's business logic.
"""

from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from .state import AgentState


Route = Literal["tool_use", END]
END_ROUTE = END


def build_agent_workflow(
    model_node: Callable[[AgentState], dict],
    tool_node: Callable[[AgentState], Any],
    route_after_model: Callable[[AgentState], Route],
    checkpointer: Any,
) -> Any:
    """Build and compile the assistant's two-node LangGraph workflow.

    Graph structure:

    ``START -> model_response -> END``
    ``                         -> tool_use -> model_response``

    The route function decides whether the model's response contains tool calls.
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("model_response", model_node)
    workflow.add_node("tool_use", tool_node)
    workflow.set_entry_point("model_response")
    workflow.add_edge("tool_use", "model_response")
    workflow.add_conditional_edges(
        "model_response",
        route_after_model,
        {"tool_use": "tool_use", END: END},
    )
    return workflow.compile(checkpointer=checkpointer)
