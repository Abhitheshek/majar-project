"""Interactive terminal session handling."""

import os
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from core.config import config

if TYPE_CHECKING:
    from .agent import CodeAssistantAgent


class InteractiveSession:
    """Handle prompts, built-in commands, and LangGraph requests."""

    def __init__(self, agent: "CodeAssistantAgent", console: Console) -> None:
        self._agent = agent
        self._console = console
        self._graph_config: dict[str, Any] = {
            "configurable": {"thread_id": agent.thread_id},
            "recursion_limit": config.recursion_limit,
        }

    async def run(self) -> None:
        while True:
            try:
                request = Prompt.ask(
                    "[bold green]✦ Request[/bold green] [dim](type 'help' for commands)[/dim]",
                    default="",
                ).strip()
                if not request:
                    continue
                if request.lower() in {"exit", "quit", "q"}:
                    self._console.print("\n[bold cyan]Goodbye![/bold cyan]\n")
                    return
                if await self._handle_command(request):
                    continue
                await self._invoke(request)
            except KeyboardInterrupt:
                self._console.print("\n[bold cyan]Goodbye![/bold cyan]\n")
                return
            except Exception as error:
                self._console.print(f"[bold red]Error: {error}[/bold red]")
                self._console.print("[yellow]Continuing... Type 'exit' to quit[/yellow]")

    async def _handle_command(self, request: str) -> bool:
        command = request.lower()
        if command == "help":
            self._show_help()
            return True
        if command == "tools":
            self._agent.display.display_tools(self._agent.tools)
            return True
        if command == "clear":
            self._graph_config["configurable"]["thread_id"] = f"session_{os.urandom(8).hex()}"
            self._console.print("[green]Conversation history cleared[/green]")
            return True
        if request.isdigit() and request in self._agent.display.last_options:
            await self._invoke(self._agent.display.last_options[request])
            return True
        return False

    async def _invoke(self, request: str) -> None:
        await self._agent.graph.ainvoke(
            {"messages": [HumanMessage(content=request)], "tool_calls_count": 0},
            self._graph_config,
        )

    def _show_help(self) -> None:
        text = """
# Code Assistant Help

- **help**: Show this help panel
- **tools**: List the currently loaded tools
- **clear**: Start a fresh conversation thread
- **exit/quit/q**: Leave the assistant

Examples:
- "Read main.py and explain it"
- "Run the project tests"
- "Search Python docs for asyncio"
        """
        self._console.print(
            Panel(
                Markdown(text),
                title="[bold cyan]Help[/bold cyan]",
                subtitle="[dim]Commands[/dim]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
