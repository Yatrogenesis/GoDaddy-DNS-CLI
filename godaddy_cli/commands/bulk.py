"""
Bulk Operations Commands
High-performance batch operations for DNS management
"""

import click
import json
import csv
import yaml
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table
from rich.panel import Panel

from godaddy_cli.core.api_client import GoDaddyAPIClient, DNSRecord
from godaddy_cli.core.auth import AuthManager
from godaddy_cli.utils.validators import validate_domain

console = Console()

@click.group()
@click.pass_context
def bulk(ctx):
    """Bulk DNS operations for multiple domains/records"""
    pass

@bulk.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--format', '-f', 'input_format',
              type=click.Choice(['csv', 'json', 'yaml']),
              help='Input file format (auto-detected if not specified)')
@click.option('--dry-run', is_flag=True, help='Show what would be created without making changes')
@click.option('--batch-size', default=50, help='Number of records per batch')
@click.option('--max-workers', default=5, help='Maximum concurrent workers')
@click.option('--continue-on-error', is_flag=True, help='Continue processing if errors occur')
@click.pass_context
def import_records(ctx, input_file, input_format, dry_run, batch_size, max_workers, continue_on_error):
    """Import DNS records from file

    File formats:
    CSV: domain,name,type,data,ttl,priority
    JSON: [{"domain": "example.com", "name": "www", "type": "A", "data": "1.1.1.1", "ttl": 3600}]
    YAML: Similar to JSON but in YAML format

    Examples:
        godaddy bulk import-records records.csv
        godaddy bulk import-records records.json --dry-run
        godaddy bulk import-records records.yaml --batch-size 100
    """

    input_path = Path(input_file)

    # Auto-detect format if not specified
    if not input_format:
        if input_path.suffix.lower() == '.csv':
            input_format = 'csv'
        elif input_path.suffix.lower() == '.json':
            input_format = 'json'
        elif input_path.suffix.lower() in ['.yaml', '.yml']:
            input_format = 'yaml'
        else:
            console.print(f"[red]Cannot determine format for {input_file}. Use --format[/red]")
            return

    try:
        # Load records from file
        records_data = _load_records_file(input_path, input_format)

        if not records_data:
            console.print("[yellow]No records found in file[/yellow]")
            return

        # Group records by domain
        domain_records = {}
        for record_data in records_data:
            domain = record_data.get('domain')
            if not domain:
                console.print("[red]Record missing domain field[/red]")
                continue

            if not validate_domain(domain):
                console.print(f"[red]Invalid domain: {domain}[/red]")
                if not continue_on_error:
                    return
                continue

            if domain not in domain_records:
                domain_records[domain] = []

            try:
                record = DNSRecord(
                    name=record_data.get('name', '@'),
                    type=record_data.get('type'),
                    data=record_data.get('data'),
                    ttl=record_data.get('ttl', 3600),
                    priority=record_data.get('priority')
                )
                domain_records[domain].append(record)
            except Exception as e:
                console.print(f"[red]Invalid record data: {e}[/red]")
                if not continue_on_error:
                    return

        # Show summary
        total_records = sum(len(records) for records in domain_records.values())
        summary_table = Table(title="Import Summary", show_header=True)
        summary_table.add_column("Domain", style="cyan")
        summary_table.add_column("Records", style="green")

        for domain, records in domain_records.items():
            summary_table.add_row(domain, str(len(records)))

        console.print(summary_table)
        console.print(f"\n[bold]Total: {len(domain_records)} domains, {total_records} records[/bold]")

        if dry_run:
            console.print("[yellow]Dry run - no changes made[/yellow]")
            return

        # Process domains
        results = asyncio.run(_process_bulk_import(
            ctx.obj['auth'],
            ctx.obj['profile'],
            domain_records,
            batch_size,
            max_workers,
            continue_on_error
        ))

        # Show results
        _show_bulk_results(results)

    except Exception as e:
        console.print(f"[red]Error importing records: {e}[/red]")

@bulk.command()
@click.argument('domains', nargs=-1, required=True)
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['csv', 'json', 'yaml']),
              default='json', help='Output format')
@click.option('--filter-type', help='Filter by record type')
@click.option('--max-workers', default=10, help='Maximum concurrent workers')
@click.pass_context
def export_records(ctx, domains, output, output_format, filter_type, max_workers):
    """Export DNS records from multiple domains

    Examples:
        godaddy bulk export-records example.com test.com
        godaddy bulk export-records example.com --format csv --output records.csv
        godaddy bulk export-records *.mydomain.com --filter-type A
    """

    # Validate domains
    valid_domains = []
    for domain in domains:
        if validate_domain(domain):
            valid_domains.append(domain)
        else:
            console.print(f"[red]Invalid domain: {domain}[/red]")

    if not valid_domains:
        console.print("[red]No valid domains provided[/red]")
        return

    try:
        # Export records
        all_records = asyncio.run(_export_bulk_records(
            ctx.obj['auth'],
            ctx.obj['profile'],
            valid_domains,
            filter_type,
            max_workers
        ))

        if not all_records:
            console.print("[yellow]No records found[/yellow]")
            return

        # Format output
        if output_format == 'csv':
            output_data = _format_csv_output(all_records)
        elif output_format == 'yaml':
            output_data = yaml.dump(all_records, default_flow_style=False)
        else:
            output_data = json.dumps(all_records, indent=2)

        # Save or print
        if output:
            with open(output, 'w') as f:
                f.write(output_data)
            console.print(f"[green]Exported {len(all_records)} records to {output}[/green]")
        else:
            console.print(output_data)

    except Exception as e:
        console.print(f"[red]Error exporting records: {e}[/red]")

@bulk.command()
@click.argument('domains', nargs=-1, required=True)
@click.option('--record-type', required=True, help='Record type to update')
@click.option('--old-data', required=True, help='Old data to replace')
@click.option('--new-data', required=True, help='New data')
@click.option('--new-ttl', type=int, help='New TTL')
@click.option('--dry-run', is_flag=True, help='Show what would be updated')
@click.option('--max-workers', default=5, help='Maximum concurrent workers')
@click.pass_context
def update_records(ctx, domains, record_type, old_data, new_data, new_ttl, dry_run, max_workers):
    """Bulk update DNS records across multiple domains

    Examples:
        godaddy bulk update-records example.com test.com --record-type A --old-data 1.1.1.1 --new-data 2.2.2.2
        godaddy bulk update-records *.mydomain.com --record-type CNAME --old-data old.example.com --new-data new.example.com
    """

    # Validate domains
    valid_domains = []
    for domain in domains:
        if validate_domain(domain):
            valid_domains.append(domain)
        else:
            console.print(f"[red]Invalid domain: {domain}[/red]")

    if not valid_domains:
        console.print("[red]No valid domains provided[/red]")
        return

    try:
        # Process updates
        results = asyncio.run(_process_bulk_updates(
            ctx.obj['auth'],
            ctx.obj['profile'],
            valid_domains,
            record_type,
            old_data,
            new_data,
            new_ttl,
            dry_run,
            max_workers
        ))

        # Show results
        _show_bulk_results(results)

    except Exception as e:
        console.print(f"[red]Error updating records: {e}[/red]")

@bulk.command()
@click.argument('domains', nargs=-1, required=True)
@click.option('--record-type', help='Filter by record type')
@click.option('--name-pattern', help='Filter by name pattern (supports wildcards)')
@click.option('--backup-dir', type=click.Path(), help='Backup directory')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted')
@click.option('--max-workers', default=5, help='Maximum concurrent workers')
@click.pass_context
def delete_records(ctx, domains, record_type, name_pattern, backup_dir, dry_run, max_workers):
    """Bulk delete DNS records across multiple domains

    Examples:
        godaddy bulk delete-records example.com --record-type TXT --name-pattern "_*"
        godaddy bulk delete-records *.mydomain.com --backup-dir ./backups
    """

    # Validate domains
    valid_domains = []
    for domain in domains:
        if validate_domain(domain):
            valid_domains.append(domain)
        else:
            console.print(f"[red]Invalid domain: {domain}[/red]")

    if not valid_domains:
        console.print("[red]No valid domains provided[/red]")
        return

    console.print("[bold red]WARNING: This will permanently delete DNS records![/bold red]")
    if not dry_run and not click.confirm("Are you sure you want to continue?"):
        return

    try:
        # Process deletions
        results = asyncio.run(_process_bulk_deletions(
            ctx.obj['auth'],
            ctx.obj['profile'],
            valid_domains,
            record_type,
            name_pattern,
            backup_dir,
            dry_run,
            max_workers
        ))

        # Show results
        _show_bulk_results(results)

    except Exception as e:
        console.print(f"[red]Error deleting records: {e}[/red]")

@bulk.command()
@click.argument('domains', nargs=-1, required=True)
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--max-workers', default=10, help='Maximum concurrent workers')
@click.pass_context
def validate_domains(ctx, domains, output, max_workers):
    """Validate DNS configuration for multiple domains

    Examples:
        godaddy bulk validate-domains example.com test.com
        godaddy bulk validate-domains *.mydomain.com --output validation-report.json
    """

    # Validate domain names
    valid_domains = []
    for domain in domains:
        if validate_domain(domain):
            valid_domains.append(domain)
        else:
            console.print(f"[red]Invalid domain: {domain}[/red]")

    if not valid_domains:
        console.print("[red]No valid domains provided[/red]")
        return

    try:
        # Process validation
        results = asyncio.run(_process_bulk_validation(
            ctx.obj['auth'],
            ctx.obj['profile'],
            valid_domains,
            max_workers
        ))

        # Show summary
        total_issues = sum(len(r.get('issues', [])) for r in results if r['success'])
        total_warnings = sum(len(r.get('warnings', [])) for r in results if r['success'])

        console.print(f"\n[bold]Validation Summary:[/bold]")
        console.print(f"Domains checked: {len(valid_domains)}")
        console.print(f"Total issues: {total_issues}")
        console.print(f"Total warnings: {total_warnings}")

        # Save or display results
        if output:
            with open(output, 'w') as f:
                json.dump(results, f, indent=2)
            console.print(f"[green]Validation report saved to {output}[/green]")
        else:
            for result in results:
                if result['success']:
                    domain = result['domain']
                    issues = result.get('issues', [])
                    warnings = result.get('warnings', [])

                    if issues or warnings:
                        console.print(f"\n[cyan]{domain}:[/cyan]")
                        for issue in issues:
                            console.print(f"  [red]• {issue}[/red]")
                        for warning in warnings:
                            console.print(f"  [yellow]• {warning}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error validating domains: {e}[/red]")

# Helper functions

def _load_records_file(file_path: Path, format_type: str) -> List[Dict[str, Any]]:
    """Load records from file"""
    with open(file_path, 'r') as f:
        if format_type == 'csv':
            reader = csv.DictReader(f)
            return list(reader)
        elif format_type == 'json':
            return json.load(f)
        elif format_type == 'yaml':
            return yaml.safe_load(f) or []

def _format_csv_output(records: List[Dict[str, Any]]) -> str:
    """Format records as CSV"""
    import io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['domain', 'name', 'type', 'data', 'ttl', 'priority'])
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()

async def _process_bulk_import(auth_manager: AuthManager, profile: str,
                              domain_records: Dict[str, List[DNSRecord]],
                              batch_size: int, max_workers: int,
                              continue_on_error: bool) -> List[Dict[str, Any]]:
    """Process bulk import with progress tracking"""
    results = []

    with Progress() as progress:
        task = progress.add_task("Importing records...", total=len(domain_records))

        semaphore = asyncio.Semaphore(max_workers)

        async def process_domain(domain: str, records: List[DNSRecord]):
            async with semaphore:
                try:
                    async with GoDaddyAPIClient(auth_manager, profile) as client:
                        result = await client.bulk_update_records(domain, records, batch_size)
                        result['domain'] = domain
                        results.append(result)
                        progress.update(task, advance=1)
                except Exception as e:
                    results.append({
                        'domain': domain,
                        'success': 0,
                        'failed': len(records),
                        'errors': [str(e)]
                    })
                    progress.update(task, advance=1)
                    if not continue_on_error:
                        raise

        tasks = [process_domain(domain, records) for domain, records in domain_records.items()]
        await asyncio.gather(*tasks, return_exceptions=continue_on_error)

    return results

async def _export_bulk_records(auth_manager: AuthManager, profile: str,
                              domains: List[str], filter_type: Optional[str],
                              max_workers: int) -> List[Dict[str, Any]]:
    """Export records from multiple domains"""
    all_records = []

    with Progress() as progress:
        task = progress.add_task("Exporting records...", total=len(domains))

        semaphore = asyncio.Semaphore(max_workers)

        async def export_domain(domain: str):
            async with semaphore:
                try:
                    async with GoDaddyAPIClient(auth_manager, profile) as client:
                        records = await client.list_dns_records(domain, filter_type)
                        for record in records:
                            all_records.append({
                                'domain': domain,
                                'name': record.name,
                                'type': record.type,
                                'data': record.data,
                                'ttl': record.ttl,
                                'priority': record.priority
                            })
                        progress.update(task, advance=1)
                except Exception as e:
                    console.print(f"[red]Error exporting {domain}: {e}[/red]")
                    progress.update(task, advance=1)

        tasks = [export_domain(domain) for domain in domains]
        await asyncio.gather(*tasks, return_exceptions=True)

    return all_records

async def _process_bulk_updates(auth_manager: AuthManager, profile: str,
                               domains: List[str], record_type: str,
                               old_data: str, new_data: str,
                               new_ttl: Optional[int], dry_run: bool,
                               max_workers: int) -> List[Dict[str, Any]]:
    """Process bulk updates"""
    results = []

    with Progress() as progress:
        task = progress.add_task("Updating records...", total=len(domains))

        semaphore = asyncio.Semaphore(max_workers)

        async def update_domain(domain: str):
            async with semaphore:
                try:
                    async with GoDaddyAPIClient(auth_manager, profile) as client:
                        records = await client.list_dns_records(domain, record_type)
                        updates = []

                        for record in records:
                            if record.data == old_data:
                                updated_record = DNSRecord(
                                    name=record.name,
                                    type=record.type,
                                    data=new_data,
                                    ttl=new_ttl or record.ttl,
                                    priority=record.priority
                                )
                                updates.append(updated_record)

                        if updates and not dry_run:
                            for record in updates:
                                await client.update_dns_record(domain, record)

                        results.append({
                            'domain': domain,
                            'updates': len(updates),
                            'success': True
                        })
                        progress.update(task, advance=1)

                except Exception as e:
                    results.append({
                        'domain': domain,
                        'updates': 0,
                        'success': False,
                        'error': str(e)
                    })
                    progress.update(task, advance=1)

        tasks = [update_domain(domain) for domain in domains]
        await asyncio.gather(*tasks, return_exceptions=True)

    return results

async def _process_bulk_deletions(auth_manager: AuthManager, profile: str,
                                 domains: List[str], record_type: Optional[str],
                                 name_pattern: Optional[str], backup_dir: Optional[str],
                                 dry_run: bool, max_workers: int) -> List[Dict[str, Any]]:
    """Process bulk deletions"""
    results = []

    if backup_dir:
        Path(backup_dir).mkdir(parents=True, exist_ok=True)

    with Progress() as progress:
        task = progress.add_task("Deleting records...", total=len(domains))

        semaphore = asyncio.Semaphore(max_workers)

        async def delete_domain(domain: str):
            async with semaphore:
                try:
                    async with GoDaddyAPIClient(auth_manager, profile) as client:
                        records = await client.list_dns_records(domain, record_type)

                        # Filter by name pattern if specified
                        if name_pattern:
                            import fnmatch
                            records = [r for r in records if fnmatch.fnmatch(r.name, name_pattern)]

                        # Create backup
                        if backup_dir and records:
                            backup_file = Path(backup_dir) / f"{domain}_backup.json"
                            with open(backup_file, 'w') as f:
                                json.dump([r.__dict__ for r in records], f, indent=2)

                        # Delete records
                        deletions = 0
                        if not dry_run:
                            for record in records:
                                success = await client.delete_dns_record(domain, record.type, record.name)
                                if success:
                                    deletions += 1

                        results.append({
                            'domain': domain,
                            'deletions': deletions if not dry_run else len(records),
                            'success': True
                        })
                        progress.update(task, advance=1)

                except Exception as e:
                    results.append({
                        'domain': domain,
                        'deletions': 0,
                        'success': False,
                        'error': str(e)
                    })
                    progress.update(task, advance=1)

        tasks = [delete_domain(domain) for domain in domains]
        await asyncio.gather(*tasks, return_exceptions=True)

    return results

async def _process_bulk_validation(auth_manager: AuthManager, profile: str,
                                  domains: List[str], max_workers: int) -> List[Dict[str, Any]]:
    """Process bulk validation"""
    results = []

    with Progress() as progress:
        task = progress.add_task("Validating domains...", total=len(domains))

        semaphore = asyncio.Semaphore(max_workers)

        async def validate_domain(domain: str):
            async with semaphore:
                try:
                    async with GoDaddyAPIClient(auth_manager, profile) as client:
                        records = await client.list_dns_records(domain)

                        # Basic validation logic (same as in dns.py validate command)
                        issues = []
                        warnings = []

                        a_records = [r for r in records if r.type == 'A']
                        cname_records = [r for r in records if r.type == 'CNAME']

                        if not any(r.name == '@' for r in a_records):
                            issues.append("No A record for root domain (@)")

                        for cname in cname_records:
                            conflicting = [r for r in records
                                         if r.name == cname.name and r.type != 'CNAME']
                            if conflicting:
                                issues.append(f"CNAME record '{cname.name}' conflicts with other records")

                        low_ttl_records = [r for r in records if r.ttl < 300]
                        if low_ttl_records:
                            warnings.append(f"{len(low_ttl_records)} record(s) have very low TTL (<300s)")

                        results.append({
                            'domain': domain,
                            'success': True,
                            'issues': issues,
                            'warnings': warnings
                        })
                        progress.update(task, advance=1)

                except Exception as e:
                    results.append({
                        'domain': domain,
                        'success': False,
                        'error': str(e)
                    })
                    progress.update(task, advance=1)

        tasks = [validate_domain(domain) for domain in domains]
        await asyncio.gather(*tasks, return_exceptions=True)

    return results

def _show_bulk_results(results: List[Dict[str, Any]]):
    """Display bulk operation results"""
    success_count = sum(1 for r in results if r.get('success', True))
    failed_count = len(results) - success_count

    console.print(f"\n[bold]Operation Results:[/bold]")
    console.print(f"[green]Successful: {success_count}[/green]")
    console.print(f"[red]Failed: {failed_count}[/red]")

    # Show details for failed operations
    for result in results:
        if not result.get('success', True):
            domain = result.get('domain', 'Unknown')
            error = result.get('error', 'Unknown error')
            console.print(f"[red]{domain}: {error}[/red]")