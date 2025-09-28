"""
DNS Management Commands
Core DNS record operations with enterprise features
"""

import click
import asyncio
import json
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
from tabulate import tabulate

from godaddy_cli.core.api_client import GoDaddyAPIClient, SyncGoDaddyAPIClient, DNSRecord, RecordType
from godaddy_cli.core.simple_api_client import APIClient
from godaddy_cli.core.auth import AuthManager
from godaddy_cli.utils.validators import validate_domain, validate_ip, validate_ttl
from godaddy_cli.utils.formatters import format_dns_table, format_json_output
from godaddy_cli.utils.error_handlers import UserFriendlyErrorHandler
from godaddy_cli.core.exceptions import GoDaddyDNSError

console = Console()

@click.group()
@click.pass_context
def dns(ctx):
    """DNS record management commands"""
    pass

@dns.command()
@click.argument('domain')
@click.option('--type', '-t', 'record_type', help='Filter by record type (A, AAAA, CNAME, etc.)')
@click.option('--name', '-n', help='Filter by record name')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json', 'yaml', 'csv']),
              default='table', help='Output format')
@click.option('--export', '-e', type=click.Path(), help='Export to file')
@click.pass_context
def list(ctx, domain, record_type, name, output_format, export):
    """List DNS records for a domain

    Examples:
        godaddy dns list example.com
        godaddy dns list example.com --type A
        godaddy dns list example.com --name www
        godaddy dns list example.com --format json
    """

    if not validate_domain(domain):
        console.print(f"[red]Invalid domain: {domain}[/red]")
        return

    try:
        # Get API credentials
        auth_manager = ctx.obj['auth']
        if not auth_manager.is_configured():
            console.print("[red]API credentials not configured. Run 'godaddy auth setup' first.[/red]")
            return

        api_key, api_secret = auth_manager.get_credentials()

        # Use enhanced API client
        with APIClient(api_key, api_secret) as client:
            records = client.get_records(domain, record_type, name)

            if not records:
                if name and record_type:
                    console.print(f"[yellow]No {record_type} record named '{name}' found for {domain}[/yellow]")
                    console.print(f"[dim]Try: godaddy dns list {domain} --type {record_type}[/dim]")
                elif name:
                    console.print(f"[yellow]No record named '{name}' found for {domain}[/yellow]")
                    console.print(f"[dim]Try: godaddy dns list {domain}[/dim]")
                elif record_type:
                    console.print(f"[yellow]No {record_type} records found for {domain}[/yellow]")
                    console.print(f"[dim]Try: godaddy dns add {domain} --type {record_type}[/dim]")
                else:
                    console.print(f"[yellow]No DNS records found for {domain}[/yellow]")
                    console.print(f"[dim]Try: godaddy dns add {domain}[/dim]")
                return

        # Format output
        if ctx.obj['output_json'] or output_format == 'json':
            output = format_json_output(records)
        elif output_format == 'yaml':
            import yaml
            output = yaml.dump([r.__dict__ for r in records], default_flow_style=False)
        elif output_format == 'csv':
            import csv
            import io
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(['Name', 'Type', 'Data', 'TTL', 'Priority'])
            for record in records:
                writer.writerow([record.name, record.type, record.data,
                               record.ttl, record.priority or ''])
            output = buffer.getvalue()
        else:
            # Table format
            table = format_dns_table(records)
            console.print(table)

            # Show summary
            type_counts = {}
            for record in records:
                type_counts[record.type] = type_counts.get(record.type, 0) + 1

            summary = Panel(
                f"[bold]Total Records:[/bold] {len(records)}\n" +
                "\n".join([f"[cyan]{t}:[/cyan] {c}" for t, c in sorted(type_counts.items())]),
                title="Summary",
                border_style="green"
            )
            console.print(summary)
            return

        # Export or print
        if export:
            with open(export, 'w') as f:
                f.write(output)
            console.print(f"[green]Records exported to {export}[/green]")
        else:
            console.print(output)

    except GoDaddyDNSError as e:
        UserFriendlyErrorHandler.display_error_with_suggestions(e, ctx.obj.get('debug', False))
        if ctx.obj.get('debug'):
            UserFriendlyErrorHandler.suggest_alternative_commands("list", domain)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()

@dns.command()
@click.argument('domain')
@click.argument('record_type', type=click.Choice([t.value for t in RecordType]))
@click.argument('name')
@click.argument('data')
@click.option('--ttl', default=3600, type=int, help='TTL in seconds (default: 3600)')
@click.option('--priority', type=int, help='Priority for MX/SRV records')
@click.option('--port', type=int, help='Port for SRV records')
@click.option('--weight', type=int, help='Weight for SRV records')
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation')
@click.pass_context
def add(ctx, domain, record_type, name, data, ttl, priority, port, weight, confirm):
    """Add a new DNS record

    Examples:
        godaddy dns add example.com A www 192.168.1.1
        godaddy dns add example.com CNAME blog www.example.com
        godaddy dns add example.com MX @ mail.example.com --priority 10
        godaddy dns add example.com TXT @ "v=spf1 include:_spf.google.com ~all"
    """

    if not validate_domain(domain):
        console.print(f"[red]Invalid domain: {domain}[/red]")
        return

    if not validate_ttl(ttl):
        console.print(f"[red]Invalid TTL: {ttl} (must be between 300 and 86400)[/red]")
        return

    # Validate record-specific data
    if record_type == 'A' and not validate_ip(data, version=4):
        console.print(f"[red]Invalid IPv4 address: {data}[/red]")
        return
    elif record_type == 'AAAA' and not validate_ip(data, version=6):
        console.print(f"[red]Invalid IPv6 address: {data}[/red]")
        return
    elif record_type == 'MX' and priority is None:
        console.print(f"[red]MX records require --priority[/red]")
        return

    # Create record
    record = DNSRecord(
        name=name,
        type=record_type,
        data=data,
        ttl=ttl,
        priority=priority,
        port=port,
        weight=weight
    )

    # Show what will be created
    table = Table(title="DNS Record to Add", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Domain", domain)
    table.add_row("Name", record.name)
    table.add_row("Type", record.type)
    table.add_row("Data", record.data)
    table.add_row("TTL", str(record.ttl))
    if record.priority:
        table.add_row("Priority", str(record.priority))
    if record.port:
        table.add_row("Port", str(record.port))
    if record.weight:
        table.add_row("Weight", str(record.weight))

    console.print(table)

    if not confirm and not Confirm.ask("Create this DNS record?"):
        console.print("[yellow]Operation cancelled[/yellow]")
        return

    try:
        client = SyncGoDaddyAPIClient(ctx.obj['auth'], ctx.obj['profile'])
        success = client.create_dns_record(domain, record)

        if success:
            console.print(f"[green]✓ DNS record created successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to create DNS record[/red]")

    except GoDaddyDNSError as e:
        UserFriendlyErrorHandler.display_error_with_suggestions(e, ctx.obj.get('debug', False))
        if ctx.obj.get('debug'):
            UserFriendlyErrorHandler.suggest_alternative_commands("add", domain)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()

@dns.command()
@click.argument('domain')
@click.argument('record_type', type=click.Choice([t.value for t in RecordType]))
@click.argument('name')
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation')
@click.pass_context
def delete(ctx, domain, record_type, name, confirm):
    """Delete DNS record(s)

    Examples:
        godaddy dns delete example.com A www
        godaddy dns delete example.com CNAME blog
    """

    if not validate_domain(domain):
        console.print(f"[red]Invalid domain: {domain}[/red]")
        return

    try:
        # First, show what will be deleted
        client = SyncGoDaddyAPIClient(ctx.obj['auth'], ctx.obj['profile'])
        existing_records = client.list_dns_records(domain, record_type)
        records_to_delete = [r for r in existing_records if r.name == name]

        if not records_to_delete:
            console.print(f"[yellow]No {record_type} records found for {name}.{domain}[/yellow]")
            return

        # Show records to be deleted
        table = format_dns_table(records_to_delete)
        console.print(Panel(table, title="Records to Delete", border_style="red"))

        if not confirm and not Confirm.ask(f"Delete {len(records_to_delete)} record(s)?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return

        # Delete the record
        success = await_result(
            client._execute_with_client(
                lambda c: c.delete_dns_record(domain, record_type, name)
            )
        )

        if success:
            console.print(f"[green]✓ DNS record(s) deleted successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to delete DNS record(s)[/red]")

    except GoDaddyDNSError as e:
        UserFriendlyErrorHandler.display_error_with_suggestions(e, ctx.obj.get('debug', False))
        if ctx.obj.get('debug'):
            UserFriendlyErrorHandler.suggest_alternative_commands("delete", domain)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()

@dns.command()
@click.argument('domain')
@click.argument('record_type', type=click.Choice([t.value for t in RecordType]))
@click.argument('name')
@click.argument('new_data')
@click.option('--ttl', type=int, help='New TTL')
@click.option('--priority', type=int, help='New priority for MX/SRV records')
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation')
@click.pass_context
def update(ctx, domain, record_type, name, new_data, ttl, priority, confirm):
    """Update existing DNS record

    Examples:
        godaddy dns update example.com A www 192.168.1.2
        godaddy dns update example.com A www 192.168.1.2 --ttl 7200
    """

    if not validate_domain(domain):
        console.print(f"[red]Invalid domain: {domain}[/red]")
        return

    try:
        # Get existing record
        client = SyncGoDaddyAPIClient(ctx.obj['auth'], ctx.obj['profile'])
        existing_records = client.list_dns_records(domain, record_type)
        target_records = [r for r in existing_records if r.name == name]

        if not target_records:
            console.print(f"[yellow]No {record_type} record found for {name}.{domain}[/yellow]")
            return

        if len(target_records) > 1:
            console.print(f"[yellow]Multiple records found. This will update all {len(target_records)} records.[/yellow]")

        # Show before/after
        old_record = target_records[0]
        new_record = DNSRecord(
            name=name,
            type=record_type,
            data=new_data,
            ttl=ttl or old_record.ttl,
            priority=priority or old_record.priority
        )

        comparison_table = Table(title="DNS Record Update", show_header=True)
        comparison_table.add_column("Field", style="cyan")
        comparison_table.add_column("Current", style="red")
        comparison_table.add_column("New", style="green")

        comparison_table.add_row("Data", old_record.data, new_record.data)
        comparison_table.add_row("TTL", str(old_record.ttl), str(new_record.ttl))
        if old_record.priority or new_record.priority:
            comparison_table.add_row("Priority",
                                   str(old_record.priority or 'None'),
                                   str(new_record.priority or 'None'))

        console.print(comparison_table)

        if not confirm and not Confirm.ask("Update this DNS record?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return

        success = await_result(
            client._execute_with_client(
                lambda c: c.update_dns_record(domain, new_record)
            )
        )

        if success:
            console.print(f"[green]✓ DNS record updated successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to update DNS record[/red]")

    except GoDaddyDNSError as e:
        UserFriendlyErrorHandler.display_error_with_suggestions(e, ctx.obj.get('debug', False))
        if ctx.obj.get('debug'):
            UserFriendlyErrorHandler.suggest_alternative_commands("update", domain)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()

@dns.command()
@click.argument('domain')
@click.option('--backup', '-b', type=click.Path(), help='Backup current records before clearing')
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation')
@click.pass_context
def clear(ctx, domain, backup, confirm):
    """Clear all DNS records for a domain (DANGEROUS!)

    Examples:
        godaddy dns clear example.com --backup backup.json
    """

    if not validate_domain(domain):
        console.print(f"[red]Invalid domain: {domain}[/red]")
        return

    try:
        client = SyncGoDaddyAPIClient(ctx.obj['auth'], ctx.obj['profile'])
        records = client.list_dns_records(domain)

        if not records:
            console.print(f"[yellow]No DNS records found for {domain}[/yellow]")
            return

        # Show what will be deleted
        table = format_dns_table(records)
        console.print(Panel(table, title=f"All Records for {domain}", border_style="red"))

        console.print(f"\n[bold red]WARNING: This will delete ALL {len(records)} DNS records for {domain}![/bold red]")
        console.print("[red]This action cannot be undone![/red]")

        if backup:
            console.print(f"[yellow]Records will be backed up to {backup}[/yellow]")

        if not confirm and not Confirm.ask("Are you absolutely sure?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return

        # Create backup if requested
        if backup:
            backup_data = {
                'domain': domain,
                'timestamp': time.time(),
                'records': [r.__dict__ for r in records]
            }
            with open(backup, 'w') as f:
                json.dump(backup_data, f, indent=2)
            console.print(f"[green]✓ Backup created at {backup}[/green]")

        # Clear all records by replacing with empty list
        success = await_result(
            client._execute_with_client(
                lambda c: c.replace_all_records(domain, [])
            )
        )

        if success:
            console.print(f"[green]✓ All DNS records cleared for {domain}[/green]")
        else:
            console.print(f"[red]✗ Failed to clear DNS records[/red]")

    except Exception as e:
        console.print(f"[red]Error clearing DNS records: {e}[/red]")

@dns.command()
@click.argument('domain')
@click.option('--dry-run', is_flag=True, help='Show what would be validated without making changes')
@click.pass_context
def validate(ctx, domain, dry_run):
    """Validate DNS configuration for common issues

    Examples:
        godaddy dns validate example.com
        godaddy dns validate example.com --dry-run
    """

    if not validate_domain(domain):
        console.print(f"[red]Invalid domain: {domain}[/red]")
        return

    try:
        client = SyncGoDaddyAPIClient(ctx.obj['auth'], ctx.obj['profile'])
        records = client.list_dns_records(domain)

        issues = []
        warnings = []
        suggestions = []

        # Check for common issues
        a_records = [r for r in records if r.type == 'A']
        aaaa_records = [r for r in records if r.type == 'AAAA']
        mx_records = [r for r in records if r.type == 'MX']
        cname_records = [r for r in records if r.type == 'CNAME']

        # No A record for root domain
        if not any(r.name == '@' for r in a_records):
            issues.append("No A record for root domain (@)")

        # CNAME conflicts
        for cname in cname_records:
            conflicting = [r for r in records
                         if r.name == cname.name and r.type != 'CNAME']
            if conflicting:
                issues.append(f"CNAME record '{cname.name}' conflicts with {len(conflicting)} other record(s)")

        # TTL recommendations
        low_ttl_records = [r for r in records if r.ttl < 300]
        if low_ttl_records:
            warnings.append(f"{len(low_ttl_records)} record(s) have very low TTL (<300s)")

        high_ttl_records = [r for r in records if r.ttl > 86400]
        if high_ttl_records:
            suggestions.append(f"{len(high_ttl_records)} record(s) have very high TTL (>24h)")

        # MX record validation
        if mx_records:
            priorities = [r.priority for r in mx_records if r.priority]
            if len(set(priorities)) != len(priorities):
                warnings.append("Duplicate MX priorities found")

        # Missing common records
        if not any(r.name == 'www' for r in records):
            suggestions.append("Consider adding a 'www' record")

        # Display results
        if issues:
            console.print(Panel(
                "\n".join([f"• {issue}" for issue in issues]),
                title="❌ Issues Found",
                border_style="red"
            ))

        if warnings:
            console.print(Panel(
                "\n".join([f"• {warning}" for warning in warnings]),
                title="⚠️  Warnings",
                border_style="yellow"
            ))

        if suggestions:
            console.print(Panel(
                "\n".join([f"• {suggestion}" for suggestion in suggestions]),
                title="💡 Suggestions",
                border_style="blue"
            ))

        if not issues and not warnings:
            console.print(Panel(
                "DNS configuration looks good! ✅",
                title="Validation Complete",
                border_style="green"
            ))

    except Exception as e:
        console.print(f"[red]Error validating DNS records: {e}[/red]")

def await_result(coro):
    """Helper to run async coroutine in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)