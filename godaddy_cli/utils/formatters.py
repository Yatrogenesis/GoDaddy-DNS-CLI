"""
Output formatting utilities for CLI responses
"""

import json
import csv
import yaml
from typing import List, Dict, Any, Optional
from io import StringIO
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from godaddy_cli.core.api_client import DNSRecord, Domain


console = Console()


def format_dns_table(records: List[DNSRecord], title: str = "DNS Records") -> str:
    """
    Format DNS records as a table

    Args:
        records: List of DNS records
        title: Table title

    Returns:
        Formatted table string
    """
    table = Table(title=title, box=box.ROUNDED)

    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Data", style="green")
    table.add_column("TTL", style="yellow", justify="right")
    table.add_column("Priority", style="blue", justify="right")

    for record in records:
        priority = str(record.priority) if record.priority else "-"
        table.add_row(
            record.name,
            record.type,
            record.data,
            str(record.ttl),
            priority
        )

    with StringIO() as output:
        console.print(table, file=output)
        return output.getvalue()


def format_domain_table(domains: List[Domain], title: str = "Domains") -> str:
    """
    Format domains as a table

    Args:
        domains: List of domains
        title: Table title

    Returns:
        Formatted table string
    """
    table = Table(title=title, box=box.ROUNDED)

    table.add_column("Domain", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Expires", style="yellow")
    table.add_column("Privacy", style="green")
    table.add_column("Locked", style="red")

    for domain in domains:
        # Format expiration date
        expires = domain.expires[:10] if domain.expires else "N/A"

        # Format boolean values
        privacy = "✓" if domain.privacy else "✗"
        locked = "✓" if domain.locked else "✗"

        table.add_row(
            domain.domain,
            domain.status,
            expires,
            privacy,
            locked
        )

    with StringIO() as output:
        console.print(table, file=output)
        return output.getvalue()


def format_json_output(data: Any, pretty: bool = True) -> str:
    """
    Format data as JSON

    Args:
        data: Data to format
        pretty: Whether to pretty-print

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(data, indent=2, default=str)
    return json.dumps(data, default=str)


def format_yaml_output(data: Any) -> str:
    """
    Format data as YAML

    Args:
        data: Data to format

    Returns:
        YAML string
    """
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def format_csv_output(records: List[DNSRecord]) -> str:
    """
    Format DNS records as CSV

    Args:
        records: List of DNS records

    Returns:
        CSV string
    """
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['name', 'type', 'data', 'ttl', 'priority', 'weight', 'port'])

    # Write records
    for record in records:
        writer.writerow([
            record.name,
            record.type,
            record.data,
            record.ttl,
            record.priority or '',
            record.weight or '',
            record.port or ''
        ])

    return output.getvalue()


def format_status_panel(status: str, message: str) -> str:
    """
    Format status message as a panel

    Args:
        status: Status type (success, error, warning, info)
        message: Status message

    Returns:
        Formatted panel string
    """
    colors = {
        'success': 'green',
        'error': 'red',
        'warning': 'yellow',
        'info': 'blue'
    }

    icons = {
        'success': '✓',
        'error': '✗',
        'warning': '⚠',
        'info': 'ℹ'
    }

    color = colors.get(status, 'white')
    icon = icons.get(status, '•')

    panel = Panel(
        f"{icon} {message}",
        title=status.upper(),
        border_style=color
    )

    with StringIO() as output:
        console.print(panel, file=output)
        return output.getvalue()


def format_progress_bar(current: int, total: int, description: str = "") -> str:
    """
    Format a simple progress indicator

    Args:
        current: Current progress
        total: Total items
        description: Progress description

    Returns:
        Progress string
    """
    percentage = (current / total) * 100 if total > 0 else 0
    bar_length = 40
    filled_length = int(bar_length * current / total) if total > 0 else 0

    bar = '█' * filled_length + '░' * (bar_length - filled_length)

    return f"{description} [{bar}] {current}/{total} ({percentage:.1f}%)"


def format_error_details(error: Exception, show_traceback: bool = False) -> str:
    """
    Format error details

    Args:
        error: Exception to format
        show_traceback: Whether to include traceback

    Returns:
        Formatted error string
    """
    import traceback

    error_text = Text()
    error_text.append("Error: ", style="red bold")
    error_text.append(str(error), style="red")

    if show_traceback:
        error_text.append("\n\nTraceback:\n", style="red bold")
        error_text.append(traceback.format_exc(), style="red dim")

    with StringIO() as output:
        console.print(error_text, file=output)
        return output.getvalue()


def format_validation_results(results: Dict[str, Any]) -> str:
    """
    Format DNS validation results

    Args:
        results: Validation results

    Returns:
        Formatted results string
    """
    table = Table(title="Validation Results", box=box.ROUNDED)

    table.add_column("Record", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Message", style="white")

    for record_name, result in results.items():
        status_color = "green" if result.get('valid', False) else "red"
        status_icon = "✓" if result.get('valid', False) else "✗"

        table.add_row(
            record_name,
            f"[{status_color}]{status_icon}[/{status_color}]",
            result.get('message', '')
        )

    with StringIO() as output:
        console.print(table, file=output)
        return output.getvalue()


def format_bulk_operation_summary(results: Dict[str, Any]) -> str:
    """
    Format bulk operation summary

    Args:
        results: Operation results

    Returns:
        Formatted summary string
    """
    success_count = results.get('success', 0)
    failed_count = results.get('failed', 0)
    total_count = success_count + failed_count

    summary_text = Text()
    summary_text.append("Bulk Operation Summary\n", style="bold")
    summary_text.append(f"Total: {total_count}\n", style="white")
    summary_text.append(f"Success: {success_count}\n", style="green")
    summary_text.append(f"Failed: {failed_count}\n", style="red")

    if results.get('errors'):
        summary_text.append("\nErrors:\n", style="red bold")
        for error in results['errors']:
            summary_text.append(f"• {error}\n", style="red")

    with StringIO() as output:
        console.print(summary_text, file=output)
        return output.getvalue()


def format_monitoring_status(status: Dict[str, Any]) -> str:
    """
    Format monitoring status

    Args:
        status: Monitoring status data

    Returns:
        Formatted status string
    """
    table = Table(title="Monitoring Status", box=box.ROUNDED)

    table.add_column("Domain", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Last Check", style="yellow")
    table.add_column("Interval", style="blue")

    for domain, info in status.items():
        status_color = "green" if info.get('healthy', False) else "red"
        status_text = info.get('status', 'Unknown')
        last_check = info.get('last_check', 'Never')
        interval = f"{info.get('interval', 0)}s"

        table.add_row(
            domain,
            f"[{status_color}]{status_text}[/{status_color}]",
            last_check,
            interval
        )

    with StringIO() as output:
        console.print(table, file=output)
        return output.getvalue()


def format_template_info(template: Dict[str, Any]) -> str:
    """
    Format template information

    Args:
        template: Template data

    Returns:
        Formatted template info
    """
    info_text = Text()
    info_text.append(f"Template: {template.get('name', 'Unknown')}\n", style="cyan bold")
    info_text.append(f"Description: {template.get('description', 'No description')}\n", style="white")
    info_text.append(f"Version: {template.get('version', '1.0.0')}\n", style="yellow")
    info_text.append(f"Author: {template.get('author', 'Unknown')}\n", style="blue")

    variables = template.get('variables', [])
    if variables:
        info_text.append("\nVariables:\n", style="green bold")
        for var in variables:
            required = "(required)" if var.get('required', False) else "(optional)"
            info_text.append(f"• {var.get('name', 'unknown')}: {var.get('description', 'No description')} {required}\n", style="white")

    records = template.get('records', [])
    if records:
        info_text.append(f"\nRecords: {len(records)} DNS records defined\n", style="magenta")

    with StringIO() as output:
        console.print(info_text, file=output)
        return output.getvalue()


def format_config_info(config: Dict[str, Any]) -> str:
    """
    Format configuration information

    Args:
        config: Configuration data

    Returns:
        Formatted config info
    """
    table = Table(title="Configuration", box=box.ROUNDED)

    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    def add_config_section(section_name: str, section_data: Dict[str, Any], prefix: str = ""):
        for key, value in section_data.items():
            if isinstance(value, dict):
                add_config_section(key, value, f"{prefix}{key}.")
            else:
                display_key = f"{prefix}{key}" if prefix else key
                display_value = str(value) if not isinstance(value, str) or not value.startswith('secret:') else "***"
                table.add_row(display_key, display_value)

    add_config_section("", config)

    with StringIO() as output:
        console.print(table, file=output)
        return output.getvalue()


def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """
    Format timestamp for display

    Args:
        timestamp: Timestamp to format, defaults to now

    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now()

    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text with ellipsis

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."