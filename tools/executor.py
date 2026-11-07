"""Tool execution and confirmation policy."""

from typing import Any

from langchain_core.messages import ToolMessage
from rich.console import Console
from rich.prompt import Confirm

from .repository_sandbox import has_active_sandbox


console = Console()


class ToolExecutor:
    """Execute model-requested tools and request confirmation for remote mutations."""

    _SENSITIVE_TOOLS = {"push_folder", "quick_push_file", "create_github_repo", "publish_sandbox_changes"}
    _SENSITIVE_KEYWORDS = {"delete", "remove", "drop", "truncate"}
    _HOST_FILE_TOOLS = {
        "read_file", "list_files", "write_file", "run_pytest", "search_files",
        "get_file_info", "scan_project", "read_multiple_files",
    }

    def __init__(self, tools: list[Any]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    async def execute_all(self, tool_calls: list[dict[str, Any]]) -> list[ToolMessage]:
        console.print("[dim]Executing tools...[/dim]")
        results = []
        for tool_call in tool_calls:
            console.print(f"[cyan]Working: {tool_call['name']}[/cyan]")
            results.append(self._execute(tool_call))
            console.print(f"[green]Completed: {tool_call['name']}[/green]")
        return results

    def _execute(self, tool_call: dict[str, Any]) -> ToolMessage:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if has_active_sandbox() and tool_name in self._HOST_FILE_TOOLS:
            return ToolMessage(
                content=(
                    "A repository sandbox is active. Use read_sandbox_file, "
                    "write_sandbox_file, list_sandbox_files, scan_sandbox_repository, or "
                    "run_sandbox_checks instead."
                ),
                tool_call_id=tool_call["id"],
                name=tool_name,
            )

        if self._requires_confirmation(tool_name, tool_args):
            console.print(f"[bold red]Sensitive operation: {tool_name}[/bold red]")
            if not Confirm.ask(f"Execute {tool_name}?"):
                return ToolMessage(
                    content="Operation cancelled by user",
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                )

        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolMessage(
                content=f"Tool {tool_name} not found", tool_call_id=tool_call["id"], name=tool_name
            )

        try:
            return ToolMessage(
                content=str(tool.invoke(tool_args)), tool_call_id=tool_call["id"], name=tool_name
            )
        except Exception as error:
            return ToolMessage(
                content=f"Tool error: {error}", tool_call_id=tool_call["id"], name=tool_name
            )

    @classmethod
    def _requires_confirmation(cls, tool_name: str, tool_args: dict[str, Any]) -> bool:
        if tool_name in cls._SENSITIVE_TOOLS:
            return True
        return any(keyword in str(tool_args).lower() for keyword in cls._SENSITIVE_KEYWORDS)
