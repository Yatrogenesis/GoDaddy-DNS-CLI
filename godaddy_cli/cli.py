#!/usr/bin/env python3
"""
GoDaddy DNS CLI - Main Entry Point
Enterprise-grade DNS management tool inspired by Cloudflare Wrangler
"""

import click
import sys
import os
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from godaddy_cli.__version__ import __version__
from godaddy_cli.core.config import ConfigManager
from godaddy_cli.core.auth import AuthManager
# Commands will be imported individually below

console = Console()

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(version=__version__, prog_name='GoDaddy DNS CLI')
@click.option('--profile', '-p', default='default', help='Configuration profile to use')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.option('--config-file', type=click.Path(), help='Custom config file path')
@click.pass_context
def cli(ctx, profile, debug, output_json, config_file):
    """
    GoDaddy DNS CLI - Enterprise DNS Management Tool

    A powerful command-line interface for managing GoDaddy DNS records,
    inspired by Cloudflare's Wrangler. Streamline your DNS operations
    with enterprise-grade features.

    Quick Start:
        $ godaddy init              # Initialize configuration
        $ godaddy dns list          # List all DNS records
        $ godaddy dns add A example.com 192.168.1.1
        $ godaddy deploy            # Deploy from template

    For more information: https://github.com/Yatrogenesis/GoDaddy-DNS-CLI
    """

    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj['profile'] = profile
    ctx.obj['debug'] = debug
    ctx.obj['output_json'] = output_json
    ctx.obj['console'] = console

    # Initialize configuration manager
    config_path = Path(config_file) if config_file else None
    ctx.obj['config'] = ConfigManager(profile=profile, config_path=config_path)

    # Initialize auth manager
    ctx.obj['auth'] = AuthManager(ctx.obj['config'])

    # Show banner if no command specified
    if ctx.invoked_subcommand is None:
        show_banner()
        ctx.invoke(status)

def show_banner():
    """Display the CLI banner"""
    banner = Panel.fit(
        f"""[bold cyan]GoDaddy DNS CLI[/bold cyan] v{__version__}
[dim]Enterprise DNS Management Tool[/dim]

[yellow]Type 'godaddy --help' for commands[/yellow]""",
        border_style="cyan"
    )
    console.print(banner)

@cli.command()
@click.pass_context
def status(ctx):
    """Show current configuration and connection status"""
    config = ctx.obj['config']
    auth = ctx.obj['auth']

    table = Table(title="Configuration Status", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Profile", ctx.obj['profile'])
    table.add_row("Config File", str(config.config_file))
    table.add_row("API Configured", "✓" if auth.is_configured() else "✗")

    if auth.is_configured():
        try:
            # Test API connection
            auth.test_connection()
            table.add_row("API Connection", "✓ Connected")
        except Exception as e:
            table.add_row("API Connection", f"✗ {str(e)}")

    console.print(table)

@cli.command()
@click.option('--web', is_flag=True, help='Launch web interface')
@click.option('--port', default=8080, help='Port for web interface')
@click.option('--host', default='127.0.0.1', help='Host for web interface')
@click.pass_context
def ui(ctx, web, port, host):
    """Launch the interactive UI (Terminal or Web)"""
    if web:
        from godaddy_cli.web.server import start_server
        console.print(f"[green]Starting web UI at http://{host}:{port}[/green]")
        start_server(host=host, port=port, config=ctx.obj['config'])
    else:
        from godaddy_cli.ui.terminal import TerminalUI
        ui = TerminalUI(ctx.obj['config'], ctx.obj['auth'])
        ui.run()

@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive shell mode"""
    from godaddy_cli.core.shell import InteractiveShell
    shell = InteractiveShell(ctx.obj['config'], ctx.obj['auth'])
    shell.run()

# Register command groups
try:
    from godaddy_cli.commands.dns import dns_group
    cli.add_command(dns_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.domain import domains_group
    cli.add_command(domains_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.config import config_group
    cli.add_command(config_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.auth import auth_group
    cli.add_command(auth_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.template import template_group
    cli.add_command(template_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.export import export_group
    cli.add_command(export_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.import_cmd import import_group
    cli.add_command(import_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.monitor import monitor_group
    cli.add_command(monitor_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.bulk import bulk_group
    cli.add_command(bulk_group)
except ImportError:
    pass

try:
    from godaddy_cli.commands.init import init_project
    cli.add_command(init_project)
except ImportError:
    pass

try:
    from godaddy_cli.commands.deploy import deploy_group
    cli.add_command(deploy_group)
except ImportError:
    pass

def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        if '--debug' in sys.argv or '-d' in sys.argv:
            console.print_exception()
        else:
            console.print(f"[red]Error: {str(e)}[/red]")
            console.print("[dim]Use --debug for full traceback[/dim]")
        sys.exit(1)

if __name__ == '__main__':
    main()