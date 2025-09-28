"""
DNS export commands
"""

import click
import json
import csv
from typing import Optional
from datetime import datetime

from godaddy_cli.core.api_client import SyncGoDaddyAPIClient
from godaddy_cli.core.exceptions import APIError, ValidationError
from godaddy_cli.utils.formatters import format_status_panel, format_json_output, format_yaml_output, format_csv_output
from godaddy_cli.utils.validators import validate_domain, validate_file_path


@click.group(name='export')
@click.pass_context
def export_group(ctx):
    """DNS export commands"""
    pass


@export_group.command('dns')
@click.argument('domain')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml', 'csv']),
              default='json', help='Export format')
@click.option('--type', 'record_type', help='Filter by record type')
@click.option('--name', 'record_name', help='Filter by record name')
@click.pass_context
def export_dns(ctx, domain: str, output: Optional[str], output_format: str,
               record_type: Optional[str], record_name: Optional[str]):
    """Export DNS records for a domain"""
    try:
        validate_domain(domain)

        client = SyncGoDaddyAPIClient(ctx.obj['auth'])
        records = client.list_dns_records(domain, record_type, record_name)

        if not records:
            click.echo(format_status_panel('info', f'No DNS records found for {domain}'))
            return

        # Create export data
        export_data = {
            'domain': domain,
            'export_date': datetime.now().isoformat(),
            'total_records': len(records),
            'filters': {
                'type': record_type,
                'name': record_name
            },
            'records': [
                {
                    'name': r.name,
                    'type': r.type,
                    'data': r.data,
                    'ttl': r.ttl,
                    'priority': r.priority,
                    'weight': r.weight,
                    'port': r.port
                }
                for r in records
            ]
        }

        # Format output
        if output_format == 'json':
            content = format_json_output(export_data)
        elif output_format == 'yaml':
            content = format_yaml_output(export_data)
        elif output_format == 'csv':
            content = format_csv_output(records)

        # Write to file or stdout
        if output:
            validate_file_path(output)
            with open(output, 'w') as f:
                f.write(content)
            click.echo(format_status_panel('success', f'Exported {len(records)} records to {output}'))
        else:
            click.echo(content)

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Export failed: {str(e)}'), err=True)
        ctx.exit(1)


@export_group.command('all')
@click.option('--output-dir', '-d', default='.', help='Output directory')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml', 'csv']),
              default='json', help='Export format')
@click.pass_context
def export_all(ctx, output_dir: str, output_format: str):
    """Export DNS records for all domains"""
    try:
        import os

        validate_file_path(output_dir)

        client = SyncGoDaddyAPIClient(ctx.obj['auth'])
        domains = client.list_domains()

        if not domains:
            click.echo(format_status_panel('info', 'No domains found'))
            return

        exported_count = 0

        for domain in domains:
            try:
                records = client.list_dns_records(domain.domain)

                if records:
                    # Create filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"dns_export_{domain.domain}_{timestamp}.{output_format}"
                    filepath = os.path.join(output_dir, filename)

                    # Create export data
                    export_data = {
                        'domain': domain.domain,
                        'export_date': datetime.now().isoformat(),
                        'total_records': len(records),
                        'records': [
                            {
                                'name': r.name,
                                'type': r.type,
                                'data': r.data,
                                'ttl': r.ttl,
                                'priority': r.priority,
                                'weight': r.weight,
                                'port': r.port
                            }
                            for r in records
                        ]
                    }

                    # Format and write
                    if output_format == 'json':
                        content = format_json_output(export_data)
                    elif output_format == 'yaml':
                        content = format_yaml_output(export_data)
                    elif output_format == 'csv':
                        content = format_csv_output(records)

                    with open(filepath, 'w') as f:
                        f.write(content)

                    exported_count += 1
                    click.echo(f"Exported {len(records)} records for {domain.domain}")

            except Exception as e:
                click.echo(f"Failed to export {domain.domain}: {str(e)}", err=True)

        click.echo(format_status_panel('success', f'Exported DNS records for {exported_count} domains'))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Export failed: {str(e)}'), err=True)
        ctx.exit(1)


def register_commands(cli):
    """Register export commands with the main CLI"""
    cli.add_command(export_group)