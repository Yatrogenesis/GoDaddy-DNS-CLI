"""
DNS import commands
"""

import click
import json
import csv
import os
from typing import Optional, List, Dict, Any
from io import StringIO

from godaddy_cli.core.api_client import SyncGoDaddyAPIClient, DNSRecord
from godaddy_cli.core.exceptions import APIError, ValidationError
from godaddy_cli.utils.formatters import format_status_panel, format_bulk_operation_summary
from godaddy_cli.utils.validators import validate_domain, validate_file_path, validate_batch_size


@click.group(name='import')
@click.pass_context
def import_group(ctx):
    """DNS import commands"""
    pass


@import_group.command('dns')
@click.argument('domain')
@click.argument('file_path')
@click.option('--format', 'input_format', type=click.Choice(['json', 'yaml', 'csv']),
              help='Input format (auto-detected if not specified)')
@click.option('--dry-run', is_flag=True, help='Validate without applying changes')
@click.option('--batch-size', type=int, default=10, help='Batch size for bulk operations')
@click.option('--force', is_flag=True, help='Force import without confirmation')
@click.pass_context
def import_dns(ctx, domain: str, file_path: str, input_format: Optional[str],
               dry_run: bool, batch_size: int, force: bool):
    """Import DNS records from file"""
    try:
        validate_domain(domain)
        validate_file_path(file_path)
        validate_batch_size(batch_size)

        if not os.path.exists(file_path):
            raise ValidationError(f"File not found: {file_path}")

        # Auto-detect format if not specified
        if not input_format:
            if file_path.endswith('.json'):
                input_format = 'json'
            elif file_path.endswith(('.yaml', '.yml')):
                input_format = 'yaml'
            elif file_path.endswith('.csv'):
                input_format = 'csv'
            else:
                raise ValidationError("Cannot auto-detect format. Please specify --format")

        # Read and parse file
        with open(file_path, 'r') as f:
            content = f.read()

        records = _parse_records(content, input_format)

        if not records:
            click.echo(format_status_panel('info', 'No records found in file'))
            return

        click.echo(f"Found {len(records)} records to import")

        # Validate records
        validation_errors = []
        for i, record in enumerate(records):
            try:
                record.validate()
            except Exception as e:
                validation_errors.append(f"Record {i+1}: {str(e)}")

        if validation_errors:
            click.echo(format_status_panel('error', 'Validation failed:'), err=True)
            for error in validation_errors[:10]:  # Show first 10 errors
                click.echo(f"  • {error}", err=True)
            if len(validation_errors) > 10:
                click.echo(f"  ... and {len(validation_errors) - 10} more errors", err=True)
            ctx.exit(1)

        if dry_run:
            click.echo(format_status_panel('success', f'Validation passed for {len(records)} records'))
            return

        # Confirm import
        if not force:
            if not click.confirm(f'Import {len(records)} records to {domain}?'):
                click.echo(format_status_panel('info', 'Import cancelled'))
                return

        # Perform import
        client = SyncGoDaddyAPIClient(ctx.obj['auth'])

        with click.progressbar(length=len(records), label='Importing records') as bar:
            results = client.bulk_update_records(domain, records, batch_size)
            bar.update(len(records))

        # Display results
        click.echo(format_bulk_operation_summary(results))

        if results['failed'] > 0:
            ctx.exit(1)

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Import failed: {str(e)}'), err=True)
        ctx.exit(1)


@import_group.command('template')
@click.argument('domain')
@click.argument('template_file')
@click.option('--vars', multiple=True, help='Template variables (key=value)')
@click.option('--vars-file', help='Variables file (JSON/YAML)')
@click.option('--dry-run', is_flag=True, help='Validate without applying changes')
@click.option('--force', is_flag=True, help='Force import without confirmation')
@click.pass_context
def import_template(ctx, domain: str, template_file: str, vars: tuple,
                    vars_file: Optional[str], dry_run: bool, force: bool):
    """Import DNS records from template"""
    try:
        validate_domain(domain)
        validate_file_path(template_file)

        if not os.path.exists(template_file):
            raise ValidationError(f"Template file not found: {template_file}")

        # Load template
        with open(template_file, 'r') as f:
            if template_file.endswith('.json'):
                template_data = json.load(f)
            else:
                import yaml
                template_data = yaml.safe_load(f)

        # Load variables
        template_vars = {'domain': domain}

        # Add variables from command line
        for var in vars:
            if '=' not in var:
                raise ValidationError(f"Invalid variable format: {var}. Use key=value")
            key, value = var.split('=', 1)
            template_vars[key] = value

        # Add variables from file
        if vars_file:
            validate_file_path(vars_file)
            if not os.path.exists(vars_file):
                raise ValidationError(f"Variables file not found: {vars_file}")

            with open(vars_file, 'r') as f:
                if vars_file.endswith('.json'):
                    file_vars = json.load(f)
                else:
                    import yaml
                    file_vars = yaml.safe_load(f)

                template_vars.update(file_vars)

        # Process template
        from godaddy_cli.core.template import TemplateProcessor
        processor = TemplateProcessor()
        processed_template = processor.process_template(template_data, template_vars)

        records = []
        for record_data in processed_template.get('records', []):
            record = DNSRecord.from_api_dict(record_data)
            records.append(record)

        if not records:
            click.echo(format_status_panel('info', 'No records generated from template'))
            return

        click.echo(f"Generated {len(records)} records from template")

        if dry_run:
            click.echo(format_status_panel('success', f'Template validation passed'))
            # Show generated records
            for record in records[:5]:  # Show first 5 records
                click.echo(f"  {record.name} {record.type} {record.data}")
            if len(records) > 5:
                click.echo(f"  ... and {len(records) - 5} more records")
            return

        # Confirm import
        if not force:
            if not click.confirm(f'Import {len(records)} template records to {domain}?'):
                click.echo(format_status_panel('info', 'Import cancelled'))
                return

        # Perform import
        client = SyncGoDaddyAPIClient(ctx.obj['auth'])

        with click.progressbar(length=len(records), label='Importing template') as bar:
            results = client.bulk_update_records(domain, records, batch_size=10)
            bar.update(len(records))

        # Display results
        click.echo(format_bulk_operation_summary(results))

        if results['failed'] > 0:
            ctx.exit(1)

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Template import failed: {str(e)}'), err=True)
        ctx.exit(1)


def _parse_records(content: str, input_format: str) -> List[DNSRecord]:
    """Parse records from various formats"""
    records = []

    if input_format == 'json':
        data = json.loads(content)

        # Handle different JSON structures
        if isinstance(data, list):
            record_list = data
        elif isinstance(data, dict):
            record_list = data.get('records', [])
        else:
            raise ValidationError("Invalid JSON structure")

        for record_data in record_list:
            record = DNSRecord.from_api_dict(record_data)
            records.append(record)

    elif input_format == 'yaml':
        import yaml
        data = yaml.safe_load(content)

        # Handle different YAML structures
        if isinstance(data, list):
            record_list = data
        elif isinstance(data, dict):
            record_list = data.get('records', [])
        else:
            raise ValidationError("Invalid YAML structure")

        for record_data in record_list:
            record = DNSRecord.from_api_dict(record_data)
            records.append(record)

    elif input_format == 'csv':
        csv_file = StringIO(content)
        reader = csv.DictReader(csv_file)

        for row in reader:
            # Convert CSV row to record
            record_data = {
                'name': row.get('name', ''),
                'type': row.get('type', ''),
                'data': row.get('data', ''),
                'ttl': int(row.get('ttl', 3600)) if row.get('ttl') else 3600
            }

            # Add optional fields
            if row.get('priority'):
                record_data['priority'] = int(row['priority'])
            if row.get('weight'):
                record_data['weight'] = int(row['weight'])
            if row.get('port'):
                record_data['port'] = int(row['port'])

            record = DNSRecord.from_api_dict(record_data)
            records.append(record)

    return records


def register_commands(cli):
    """Register import commands with the main CLI"""
    cli.add_command(import_group)