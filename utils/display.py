"""Rich console rendering for the interactive assistant."""

import re
from pathlib import Path

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree


console = Console()


class DisplayManager:
    """Render assistant messages and retain numbered response options."""

    def __init__(self) -> None:
        self.last_options: dict[str, str] = {}

    def display_welcome(self) -> None:
        console.print(
            Panel(
                "[bold cyan]Code Assistant[/bold cyan]\n"
                "[bold]Project-aware coding help for your terminal[/bold]\n\n"
                "[bold green]Type help to begin[/bold green]",
                border_style="cyan",
                title="[bold cyan]Welcome[/bold cyan]",
                subtitle="[dim]AI coding companion[/dim]",
                box=box.HEAVY_EDGE,
                padding=(1, 2),
            )
        )

    def display_quick_start(self) -> None:
        self.last_options = {
            "1": "List all files in the current directory",
            "2": "Show available tools",
            "3": "Scan the entire project",
            "4": "Read the README.md file",
        }
        console.print(
            Panel(
                "[bold]Quick actions[/bold]\n"
                "[cyan]1.[/cyan] List all files in the current directory\n"
                "[cyan]2.[/cyan] Show available tools\n"
                "[cyan]3.[/cyan] Scan the entire project\n"
                "[cyan]4.[/cyan] Read the README.md file\n\n"
                "[bold]Commands:[/bold] [green]help[/green]  [green]tools[/green]  [green]clear[/green]  [green]exit[/green]",
                border_style="cyan",
                title="[bold cyan]Quick Start[/bold cyan]",
                subtitle="[dim]Choose a task or type your request[/dim]",
                box=box.HEAVY_EDGE,
                padding=(1, 2),
            )
        )

    def format_with_numbers(self, content: object) -> str:
        """Number Markdown bullets and map their text to user selections."""
        text = self._content_to_text(content)
        self.last_options = {}
        formatted_lines: list[str] = []

        for line in text.splitlines():
            match = re.match(r"^(\s*)[-*]\s+(.+)$", line)
            if not match:
                formatted_lines.append(line)
                continue

            indent, option = match.groups()
            option_number = str(len(self.last_options) + 1)
            self.last_options[option_number] = option
            formatted_lines.append(f"{indent}**{option_number}.** {option}")

        if self.last_options:
            formatted_lines.append(
                f"\n*Type a number from 1 to {len(self.last_options)} to select an option.*"
            )
        return "\n".join(formatted_lines)

    @staticmethod
    def _content_to_text(content: object) -> str:
        if not isinstance(content, list):
            return str(content)

        parts: list[str] = []
        for block in content:
            if hasattr(block, "text"):
                parts.append(block.text)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)

    def display_tools(self, tools: list) -> None:
        """Show loaded tools grouped by responsibility in a readable tabular view."""
        table = Table(
            title="[bold cyan]Available Tools[/bold cyan]",
            header_style="bold cyan",
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            expand=True,
        )
        table.add_column("Category", style="bold yellow", width=18)
        table.add_column("Tool", style="bold green", width=28)
        table.add_column("Description", style="white")

        categories = {
            "local": "Local",
            "web": "Web",
            "github": "GitHub",
            "repository sandbox": "Sandbox",
            "screenshots": "Screenshots",
        }

        for tool in tools:
            name = tool.name.lower()
            if "github" in name or "repo" in name or "push" in name:
                category = "GitHub"
            elif any(word in name for word in ("search", "web", "docs", "library")):
                category = "Web"
            elif "sandbox" in name:
                category = "Sandbox"
            elif "screenshot" in name:
                category = "Screenshots"
            else:
                category = "Local"
            table.add_row(category, tool.name, tool.description or "No description")

        console.print(Panel(table, border_style="cyan", box=box.HEAVY_EDGE, padding=(1, 1)))

    def display_project_table(self, working_dir: str) -> None:
        """Display a recursive summary of visible project files."""
        root = Path(working_dir)
        table = Table(title=f"Project files: {root}")
        table.add_column("File", style="cyan")
        table.add_column("Size", style="green")
        table.add_column("Type", style="yellow")

        for path in sorted(root.rglob("*")):
            if not path.is_file() or any(part.startswith(".") for part in path.parts):
                continue
            table.add_row(str(path.relative_to(root)), f"{path.stat().st_size} B", path.suffix)
        console.print(table)
