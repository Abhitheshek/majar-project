"""Application orchestrator for Code Assistant."""

import os
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from app.invocation import ModelInvoker
from app.session import InteractiveSession
from core.config import config
from core.llm import LLMManager
from core.memory import ConversationMemory
from core.prompts import ASSISTANT_SYSTEM_PROMPT
from core.state import AgentState
from core.workflow import END_ROUTE, build_agent_workflow
from tools.executor import ToolExecutor
from tools.registry import load_tools
from utils.display import DisplayManager


console = Console()


class CodeAssistantAgent:
    """Coordinate models, tools, memory, graph execution, and the terminal UI."""

    def __init__(
        self,
        working_directory: str | None = None,
        *,
        working_dir: str | None = None,
    ) -> None:
        """Create an agent for a project directory.

        ``working_dir`` remains supported for compatibility with earlier releases.
        """
        if working_directory and working_dir:
            raise ValueError("Use either working_directory or working_dir, not both")
        selected_directory = working_directory or working_dir or os.getcwd()
        self.working_directory = Path(selected_directory).resolve()
        os.chdir(self.working_directory)

        self.llm_manager = LLMManager()
        self.model_invoker = ModelInvoker(self.llm_manager, console)
        self.memory = ConversationMemory()
        self.display = DisplayManager()
        self.thread_id = f"session_{os.urandom(8).hex()}"
        self._checkpointer_context: Any = None
        self.graph: Any = None
        self.tools: list[Any] = []
        self.tool_executor: ToolExecutor | None = None

        self.display.display_welcome()
        console.print(f"[cyan]Working directory: {self.working_directory}[/cyan]")

    async def initialize(self) -> None:
        """Initialize providers, tools, persistence, and the LangGraph workflow."""
        self.llm_manager.initialize_llm()
        console.print("[bold green]✔ LLM initialized[/bold green]")
        if self.llm_manager.has_gemini_fallback:
            console.print("[bold yellow]↺ Gemini fallback enabled for Groq rate limits[/bold yellow]")

        self._load_tools()
        self.llm_manager.bind_tools(self.tools)
        console.print("[bold green]✔ Tools bound to the model[/bold green]")

        checkpointer = await self._open_checkpointer()
        self.graph = build_agent_workflow(
            model_node=self._model_response,
            tool_node=self._tool_use,
            route_after_model=self._check_tool_use,
            checkpointer=checkpointer,
        )
        console.print("[bold green]✔ Agent initialized successfully[/bold green]\n")
        self.display.display_quick_start()

    def _load_tools(self) -> None:
        console.print("[cyan]Loading tools...[/cyan]")
        tool_groups = load_tools()
        self.tools = [tool for group in tool_groups.values() for tool in group]
        self.tool_executor = ToolExecutor(self.tools)
        for group_name, group_tools in tool_groups.items():
            console.print(f"[green]✓ Loaded {len(group_tools)} {group_name} tools[/green]")

    async def _open_checkpointer(self) -> Any:
        database_path = self.working_directory / "checkpoints.db"
        console.print(f"[cyan]Initializing checkpoint database: {database_path}[/cyan]")
        self._checkpointer_context = AsyncSqliteSaver.from_conn_string(str(database_path))
        return await self._checkpointer_context.__aenter__()

    def _model_response(self, state: AgentState) -> dict[str, Any]:
        memory_summary, memory_count = self.memory.update(state, list(state.messages), self.llm_manager)
        context = self._build_model_context(list(state.messages), memory_summary, memory_count)

        with console.status("[bold cyan]Thinking...", spinner="dots"):
            response = self.model_invoker.invoke_with_tools(context)
        console.print(f"[dim]{self.llm_manager.last_invocation_provider}[/dim]")

        self._display_response(response)
        return {
            "messages": [response],
            "memory_summary": memory_summary,
            "memory_message_count": memory_count,
        }

    @staticmethod
    def _build_model_context(messages: list[Any], memory_summary: str, memory_count: int) -> list[Any]:
        context: list[Any] = [SystemMessage(content=ASSISTANT_SYSTEM_PROMPT)]
        if memory_summary:
            context.append(SystemMessage(content=f"Conversation memory (compressed):\n{memory_summary}"))

        retained_messages = messages[memory_count:]
        if retained_messages and getattr(retained_messages[0], "tool_calls", None):
            context.append(HumanMessage(content="Continue the existing tool workflow using the retained context."))
        return context + retained_messages

    def _display_response(self, response: Any) -> None:
        if getattr(response, "content", None):
            formatted = self.display.format_with_numbers(response.content)
            console.print(
                Panel(
                    Markdown(formatted),
                    title="[bold cyan]Assistant[/bold cyan]",
                    subtitle="[dim]Response[/dim]",
                    border_style="cyan",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
        elif getattr(response, "tool_calls", None):
            console.print(
                Panel(
                    "[bold yellow]Processing your request...[/bold yellow]",
                    border_style="yellow",
                    box=box.ROUNDED,
                    padding=(0, 2),
                )
            )

    async def _tool_use(self, state: AgentState) -> dict[str, Any]:
        if self.tool_executor is None:
            raise RuntimeError("Tools have not been initialized")
        tool_messages = await self.tool_executor.execute_all(state.messages[-1].tool_calls)
        return {"messages": tool_messages, "tool_calls_count": state.tool_calls_count + 1}

    @staticmethod
    def _check_tool_use(state: AgentState) -> str:
        last_message = state.messages[-1]
        if getattr(last_message, "tool_calls", None) and state.tool_calls_count < config.max_tool_rounds:
            return "tool_use"
        return END_ROUTE

    async def run(self) -> None:
        """Start the interactive terminal session."""
        if self.graph is None:
            raise RuntimeError("Agent must be initialized before it can run")
        await InteractiveSession(self, console).run()

    async def cleanup(self) -> None:
        """Close checkpoint storage resources."""
        if self._checkpointer_context:
            await self._checkpointer_context.__aexit__(None, None, None)
