"""
Terminal UI components for GoDaddy DNS CLI
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import List, Dict, Any, Optional

console = Console()


class TerminalUI:
    """Terminal user interface for GoDaddy DNS CLI"""

    def __init__(self):
        self.console = console

    def print_banner(self):
        """Print CLI banner"""
        banner_text = Text()
        banner_text.append("GoDaddy DNS CLI", style="bold cyan")
        banner_text.append(" v2.0.0", style="dim")

        panel = Panel(
            banner_text,
            title="Enterprise DNS Management",
            border_style="blue"
        )
        self.console.print(panel)

    def print_success(self, message: str):
        """Print success message"""
        self.console.print(f"✅ {message}", style="green")

    def print_error(self, message: str):
        """Print error message"""
        self.console.print(f"❌ {message}", style="red")

    def print_warning(self, message: str):
        """Print warning message"""
        self.console.print(f"⚠️  {message}", style="yellow")

    def print_info(self, message: str):
        """Print info message"""
        self.console.print(f"ℹ️  {message}", style="blue")

    def prompt_text(self, message: str, default: str = None) -> str:
        """Prompt for text input"""
        return Prompt.ask(message, default=default, console=self.console)

    def prompt_choice(self, message: str, choices: List[str], default: str = None) -> str:
        """Prompt for choice from list"""
        return Prompt.ask(message, choices=choices, default=default, console=self.console)

    def confirm(self, message: str, default: bool = False) -> bool:
        """Prompt for confirmation"""
        return Confirm.ask(message, default=default, console=self.console)

    def print_table(self, title: str, headers: List[str], rows: List[List[str]]):
        """Print formatted table"""
        table = Table(title=title)

        for header in headers:
            table.add_column(header, style="cyan")

        for row in rows:
            table.add_row(*row)

        self.console.print(table)

    def print_status_panel(self, title: str, content: str, style: str = "blue"):
        """Print status panel"""
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)

    def progress_spinner(self, description: str):
        """Create progress spinner context manager"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        )

    def clear_screen(self):
        """Clear terminal screen"""
        self.console.clear()

    def print_json(self, data: Dict[str, Any]):
        """Print JSON data with syntax highlighting"""
        import json
        from rich.syntax import Syntax

        json_str = json.dumps(data, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        self.console.print(syntax)