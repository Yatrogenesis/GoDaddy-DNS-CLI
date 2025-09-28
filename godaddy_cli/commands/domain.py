"""
Domain management commands
"""

import click
from typing import Optional

from godaddy_cli.core.api_client import SyncGoDaddyAPIClient
from godaddy_cli.core.exceptions import APIError, ValidationError
from godaddy_cli.utils.formatters import format_domain_table, format_json_output, format_status_panel
from godaddy_cli.utils.validators import validate_domain


@click.group(name='domains')
@click.pass_context
def domains_group(ctx):
    """Domain management commands"""
    pass


@domains_group.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.option('--status', help='Filter by domain status')
@click.option('--limit', type=int, help='Limit number of results')
@click.pass_context
def list_domains(ctx, output_format: str, status: Optional[str], limit: Optional[int]):
    """List all domains in your account"""
    try:
        client = SyncGoDaddyAPIClient(ctx.obj['auth'])
        domains = client.list_domains()

        # Apply filters
        if status:
            domains = [d for d in domains if d.status.upper() == status.upper()]

        if limit:
            domains = domains[:limit]

        if not domains:
            click.echo(format_status_panel('info', 'No domains found'))
            return

        # Format output
        if output_format == 'table':
            click.echo(format_domain_table(domains))
        elif output_format == 'json':
            domain_data = [
                {
                    'domain': d.domain,
                    'status': d.status,
                    'expires': d.expires,
                    'created': d.created,
                    'nameservers': d.nameservers,
                    'privacy': d.privacy,
                    'locked': d.locked
                }
                for d in domains
            ]
            click.echo(format_json_output(domain_data))
        elif output_format == 'yaml':
            from godaddy_cli.utils.formatters import format_yaml_output
            domain_data = [
                {
                    'domain': d.domain,
                    'status': d.status,
                    'expires': d.expires,
                    'created': d.created,
                    'nameservers': d.nameservers,
                    'privacy': d.privacy,
                    'locked': d.locked
                }
                for d in domains
            ]
            click.echo(format_yaml_output(domain_data))

    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Unexpected error: {str(e)}'), err=True)
        ctx.exit(1)


@domains_group.command('info')
@click.argument('domain')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.pass_context
def domain_info(ctx, domain: str, output_format: str):
    """Get detailed information about a specific domain"""
    try:
        validate_domain(domain)

        client = SyncGoDaddyAPIClient(ctx.obj['auth'])
        domain_info = client.get_domain(domain)

        if output_format == 'table':
            from rich.console import Console
            from rich.panel import Panel
            from rich.text import Text

            console = Console()

            info_text = Text()
            info_text.append(f"Domain: {domain_info.domain}\n", style="cyan bold")
            info_text.append(f"Status: {domain_info.status}\n", style="magenta")
            info_text.append(f"Created: {domain_info.created}\n", style="yellow")
            info_text.append(f"Expires: {domain_info.expires}\n", style="yellow")
            info_text.append(f"Privacy Protection: {'Enabled' if domain_info.privacy else 'Disabled'}\n", style="green" if domain_info.privacy else "red")
            info_text.append(f"Domain Lock: {'Enabled' if domain_info.locked else 'Disabled'}\n", style="green" if domain_info.locked else "red")

            if domain_info.nameservers:
                info_text.append("\nNameservers:\n", style="blue bold")
                for ns in domain_info.nameservers:
                    info_text.append(f"• {ns}\n", style="white")

            panel = Panel(info_text, title="Domain Information", border_style="blue")
            console.print(panel)

        elif output_format == 'json':
            domain_data = {
                'domain': domain_info.domain,
                'status': domain_info.status,
                'expires': domain_info.expires,
                'created': domain_info.created,
                'nameservers': domain_info.nameservers,
                'privacy': domain_info.privacy,
                'locked': domain_info.locked
            }
            click.echo(format_json_output(domain_data))

        elif output_format == 'yaml':
            from godaddy_cli.utils.formatters import format_yaml_output
            domain_data = {
                'domain': domain_info.domain,
                'status': domain_info.status,
                'expires': domain_info.expires,
                'created': domain_info.created,
                'nameservers': domain_info.nameservers,
                'privacy': domain_info.privacy,
                'locked': domain_info.locked
            }
            click.echo(format_yaml_output(domain_data))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Unexpected error: {str(e)}'), err=True)
        ctx.exit(1)


@domains_group.command('status')
@click.argument('domain')
@click.pass_context
def domain_status(ctx, domain: str):
    """Check domain status and health"""
    try:
        validate_domain(domain)

        client = SyncGoDaddyAPIClient(ctx.obj['auth'])
        domain_info = client.get_domain(domain)

        # Basic status check
        status_color = "green" if domain_info.status == "ACTIVE" else "yellow"
        click.echo(format_status_panel(
            'success' if domain_info.status == "ACTIVE" else 'warning',
            f'Domain {domain} is {domain_info.status}'
        ))

        # Check expiration
        if domain_info.expires:
            from datetime import datetime, timezone
            try:
                expires_date = datetime.fromisoformat(domain_info.expires.replace('Z', '+00:00'))
                days_until_expiry = (expires_date - datetime.now(timezone.utc)).days

                if days_until_expiry < 30:
                    click.echo(format_status_panel(
                        'warning',
                        f'Domain expires in {days_until_expiry} days ({domain_info.expires})'
                    ))
                else:
                    click.echo(format_status_panel(
                        'info',
                        f'Domain expires in {days_until_expiry} days'
                    ))
            except Exception:
                click.echo(format_status_panel('info', f'Expires: {domain_info.expires}'))

        # Check security settings
        if not domain_info.privacy:
            click.echo(format_status_panel('warning', 'Privacy protection is disabled'))

        if not domain_info.locked:
            click.echo(format_status_panel('warning', 'Domain lock is disabled'))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Unexpected error: {str(e)}'), err=True)
        ctx.exit(1)


@domains_group.command('nameservers')
@click.argument('domain')
@click.option('--set', 'new_nameservers', multiple=True, help='Set new nameservers')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.pass_context
def manage_nameservers(ctx, domain: str, new_nameservers: tuple, output_format: str):
    """Manage domain nameservers"""
    try:
        validate_domain(domain)

        client = SyncGoDaddyAPIClient(ctx.obj['auth'])

        if new_nameservers:
            # Set new nameservers
            nameserver_list = list(new_nameservers)

            # Validate nameservers
            for ns in nameserver_list:
                validate_domain(ns)

            # Note: This would require implementing the nameserver update functionality
            # in the API client, which isn't available in GoDaddy API v1
            click.echo(format_status_panel(
                'warning',
                'Nameserver management requires direct access to GoDaddy control panel'
            ))
            return

        # Get current nameservers
        domain_info = client.get_domain(domain)

        if output_format == 'table':
            from rich.console import Console
            from rich.table import Table
            from rich import box

            table = Table(title=f"Nameservers for {domain}", box=box.ROUNDED)
            table.add_column("Nameserver", style="cyan")

            for ns in domain_info.nameservers or []:
                table.add_row(ns)

            console = Console()
            console.print(table)

        elif output_format == 'json':
            nameserver_data = {
                'domain': domain,
                'nameservers': domain_info.nameservers or []
            }
            click.echo(format_json_output(nameserver_data))

        elif output_format == 'yaml':
            from godaddy_cli.utils.formatters import format_yaml_output
            nameserver_data = {
                'domain': domain,
                'nameservers': domain_info.nameservers or []
            }
            click.echo(format_yaml_output(nameserver_data))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Unexpected error: {str(e)}'), err=True)
        ctx.exit(1)


# Add the command group to the main CLI
def register_commands(cli):
    """Register domain commands with the main CLI"""
    cli.add_command(domains_group)