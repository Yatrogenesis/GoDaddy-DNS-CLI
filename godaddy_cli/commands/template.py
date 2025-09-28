"""
Template Management Commands
DNS configuration templates for automation and standardization
"""

import click
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from jinja2 import Template, Environment, FileSystemLoader
from jsonschema import validate, ValidationError

from godaddy_cli.core.api_client import SyncGoDaddyAPIClient, DNSRecord
from godaddy_cli.core.config import ConfigManager
from godaddy_cli.utils.validators import validate_domain

console = Console()

TEMPLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"},
        "variables": {
            "type": "object",
            "properties": {
                "required": {"type": "array", "items": {"type": "string"}},
                "optional": {"type": "array", "items": {"type": "string"}},
                "defaults": {"type": "object"}
            }
        },
        "records": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "data": {"type": "string"},
                    "ttl": {"type": "integer"},
                    "priority": {"type": "integer"}
                },
                "required": ["name", "type", "data"]
            }
        }
    },
    "required": ["name", "records"]
}

@click.group()
@click.pass_context
def template(ctx):
    """DNS template management commands"""
    pass

@template.command()
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.pass_context
def list(ctx, output_format):
    """List available DNS templates"""

    config = ctx.obj['config']
    templates_dir = config.config_dir / 'templates'

    if not templates_dir.exists():
        console.print("[yellow]No templates directory found[/yellow]")
        return

    templates = []
    for template_file in templates_dir.glob('*.yaml'):
        try:
            with open(template_file, 'r') as f:
                template_data = yaml.safe_load(f)
                templates.append({
                    'file': template_file.name,
                    'name': template_data.get('name', 'Unknown'),
                    'description': template_data.get('description', ''),
                    'version': template_data.get('version', '1.0.0')
                })
        except Exception:
            continue

    if not templates:
        console.print("[yellow]No templates found[/yellow]")
        return

    if output_format == 'json':
        console.print(json.dumps(templates, indent=2))
    elif output_format == 'yaml':
        console.print(yaml.dump(templates, default_flow_style=False))
    else:
        table = Table(title="DNS Templates", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Version", style="green")
        table.add_column("File", style="dim")

        for template in templates:
            table.add_row(
                template['name'],
                template['description'][:50] + '...' if len(template['description']) > 50 else template['description'],
                template['version'],
                template['file']
            )

        console.print(table)

@template.command()
@click.argument('name')
@click.option('--vars', '-v', multiple=True, help='Template variables in key=value format')
@click.option('--vars-file', type=click.Path(exists=True), help='Variables file (JSON or YAML)')
@click.option('--dry-run', is_flag=True, help='Show what would be created without applying')
@click.pass_context
def show(ctx, name, vars, vars_file, dry_run):
    """Show template details and preview generated records"""

    config = ctx.obj['config']
    template_path = _find_template(config, name)

    if not template_path:
        console.print(f"[red]Template '{name}' not found[/red]")
        return

    try:
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)

        # Validate template
        validate(template_data, TEMPLATE_SCHEMA)

        # Parse variables
        variables = _parse_variables(vars, vars_file)

        # Show template info
        info_table = Table(title="Template Information", show_header=True)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Name", template_data.get('name', 'Unknown'))
        info_table.add_row("Description", template_data.get('description', ''))
        info_table.add_row("Version", template_data.get('version', '1.0.0'))

        console.print(info_table)

        # Show variables
        if 'variables' in template_data:
            var_info = template_data['variables']

            if 'required' in var_info or 'optional' in var_info:
                var_table = Table(title="Template Variables", show_header=True)
                var_table.add_column("Variable", style="cyan")
                var_table.add_column("Required", style="yellow")
                var_table.add_column("Value", style="green")

                for var in var_info.get('required', []):
                    value = variables.get(var, '[MISSING]')
                    var_table.add_row(var, "Yes", str(value))

                for var in var_info.get('optional', []):
                    value = variables.get(var, var_info.get('defaults', {}).get(var, ''))
                    var_table.add_row(var, "No", str(value))

                console.print(var_table)

        # Generate and show records
        records = _generate_records(template_data, variables)

        if records:
            records_table = Table(title="Generated DNS Records", show_header=True)
            records_table.add_column("Name", style="cyan")
            records_table.add_column("Type", style="yellow")
            records_table.add_column("Data", style="white")
            records_table.add_column("TTL", style="green")
            records_table.add_column("Priority", style="magenta")

            for record in records:
                records_table.add_row(
                    record.name,
                    record.type,
                    record.data,
                    str(record.ttl),
                    str(record.priority) if record.priority else ''
                )

            console.print(records_table)

    except ValidationError as e:
        console.print(f"[red]Invalid template format: {e.message}[/red]")
    except Exception as e:
        console.print(f"[red]Error loading template: {e}[/red]")

@template.command()
@click.argument('domain')
@click.argument('template_name')
@click.option('--vars', '-v', multiple=True, help='Template variables in key=value format')
@click.option('--vars-file', type=click.Path(exists=True), help='Variables file (JSON or YAML)')
@click.option('--dry-run', is_flag=True, help='Show what would be applied without making changes')
@click.option('--backup', '-b', type=click.Path(), help='Backup existing records before applying')
@click.option('--merge', is_flag=True, help='Merge with existing records instead of replacing')
@click.pass_context
def apply(ctx, domain, template_name, vars, vars_file, dry_run, backup, merge):
    """Apply DNS template to a domain"""

    if not validate_domain(domain):
        console.print(f"[red]Invalid domain: {domain}[/red]")
        return

    config = ctx.obj['config']
    template_path = _find_template(config, template_name)

    if not template_path:
        console.print(f"[red]Template '{template_name}' not found[/red]")
        return

    try:
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)

        # Validate template
        validate(template_data, TEMPLATE_SCHEMA)

        # Parse variables
        variables = _parse_variables(vars, vars_file)
        variables['domain'] = domain  # Add domain as implicit variable

        # Generate records
        records = _generate_records(template_data, variables)

        if not records:
            console.print("[yellow]No records generated from template[/yellow]")
            return

        # Show what will be applied
        records_table = Table(title=f"Records to Apply to {domain}", show_header=True)
        records_table.add_column("Name", style="cyan")
        records_table.add_column("Type", style="yellow")
        records_table.add_column("Data", style="white")
        records_table.add_column("TTL", style="green")

        for record in records:
            records_table.add_row(record.name, record.type, record.data, str(record.ttl))

        console.print(records_table)

        if dry_run:
            console.print("[yellow]Dry run - no changes made[/yellow]")
            return

        # Get existing records if needed
        client = SyncGoDaddyAPIClient(ctx.obj['auth'], ctx.obj['profile'])
        existing_records = []

        if backup or merge:
            existing_records = client.list_dns_records(domain)

        # Create backup
        if backup and existing_records:
            backup_data = {
                'domain': domain,
                'template': template_name,
                'timestamp': time.time(),
                'records': [r.__dict__ for r in existing_records]
            }
            with open(backup, 'w') as f:
                json.dump(backup_data, f, indent=2)
            console.print(f"[green]Backup created at {backup}[/green]")

        # Apply records
        if merge:
            # Merge with existing records
            all_records = existing_records + records
            # Remove duplicates (keep template records)
            unique_records = {}
            for record in all_records:
                key = f"{record.name}:{record.type}"
                unique_records[key] = record
            final_records = list(unique_records.values())
        else:
            final_records = records

        # Apply to domain
        success = client._run_async(
            client._execute_with_client(
                lambda c: c.replace_all_records(domain, final_records)
            )
        )

        if success:
            console.print(f"[green]Template applied successfully to {domain}[/green]")
            console.print(f"[cyan]Applied {len(records)} records from template[/cyan]")
        else:
            console.print("[red]Failed to apply template[/red]")

    except ValidationError as e:
        console.print(f"[red]Invalid template format: {e.message}[/red]")
    except Exception as e:
        console.print(f"[red]Error applying template: {e}[/red]")

@template.command()
@click.argument('name')
@click.option('--description', '-d', help='Template description')
@click.option('--from-domain', help='Create template from existing domain')
@click.option('--interactive', '-i', is_flag=True, help='Interactive template creation')
@click.pass_context
def create(ctx, name, description, from_domain, interactive):
    """Create a new DNS template"""

    config = ctx.obj['config']
    templates_dir = config.config_dir / 'templates'
    templates_dir.mkdir(exist_ok=True)

    template_file = templates_dir / f"{name}.yaml"

    if template_file.exists():
        console.print(f"[red]Template '{name}' already exists[/red]")
        return

    template_data = {
        'name': name,
        'description': description or f'DNS template {name}',
        'version': '1.0.0',
        'variables': {
            'required': ['domain'],
            'optional': [],
            'defaults': {}
        },
        'records': []
    }

    if from_domain:
        # Create template from existing domain
        if not validate_domain(from_domain):
            console.print(f"[red]Invalid domain: {from_domain}[/red]")
            return

        try:
            client = SyncGoDaddyAPIClient(ctx.obj['auth'], ctx.obj['profile'])
            records = client.list_dns_records(from_domain)

            template_records = []
            for record in records:
                # Convert absolute names to template variables
                record_name = record.name
                if record_name == '@':
                    record_name = '@'
                elif record_name.endswith(f'.{from_domain}'):
                    record_name = record_name[:-len(f'.{from_domain}')]

                template_record = {
                    'name': record_name,
                    'type': record.type,
                    'data': record.data,
                    'ttl': record.ttl
                }

                if record.priority:
                    template_record['priority'] = record.priority

                template_records.append(template_record)

            template_data['records'] = template_records
            console.print(f"[green]Created template from {len(records)} records in {from_domain}[/green]")

        except Exception as e:
            console.print(f"[red]Error reading domain records: {e}[/red]")
            return

    elif interactive:
        # Interactive template creation
        console.print("[cyan]Interactive template creation[/cyan]")

        # Add variables
        while True:
            var_name = click.prompt("Variable name (or 'done' to finish)", default='done')
            if var_name.lower() == 'done':
                break

            required = click.confirm(f"Is '{var_name}' required?", default=True)
            if required:
                template_data['variables']['required'].append(var_name)
            else:
                template_data['variables']['optional'].append(var_name)
                default_value = click.prompt(f"Default value for '{var_name}'", default='')
                if default_value:
                    template_data['variables']['defaults'][var_name] = default_value

        # Add records
        while True:
            if not click.confirm("Add a DNS record?", default=True):
                break

            record_name = click.prompt("Record name")
            record_type = click.prompt("Record type", type=click.Choice(['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV']))
            record_data = click.prompt("Record data")
            record_ttl = click.prompt("TTL", default=3600, type=int)

            record = {
                'name': record_name,
                'type': record_type,
                'data': record_data,
                'ttl': record_ttl
            }

            if record_type == 'MX':
                priority = click.prompt("Priority", type=int)
                record['priority'] = priority

            template_data['records'].append(record)

    # Save template
    try:
        with open(template_file, 'w') as f:
            yaml.dump(template_data, f, default_flow_style=False, indent=2)

        console.print(f"[green]Template '{name}' created at {template_file}[/green]")

    except Exception as e:
        console.print(f"[red]Error saving template: {e}[/red]")

@template.command()
@click.argument('name')
@click.pass_context
def delete(ctx, name):
    """Delete a DNS template"""

    config = ctx.obj['config']
    template_path = _find_template(config, name)

    if not template_path:
        console.print(f"[red]Template '{name}' not found[/red]")
        return

    if click.confirm(f"Delete template '{name}'?"):
        try:
            template_path.unlink()
            console.print(f"[green]Template '{name}' deleted[/green]")
        except Exception as e:
            console.print(f"[red]Error deleting template: {e}[/red]")

def _find_template(config: ConfigManager, name: str) -> Optional[Path]:
    """Find template file by name"""
    templates_dir = config.config_dir / 'templates'

    # Try exact filename
    template_path = templates_dir / f"{name}.yaml"
    if template_path.exists():
        return template_path

    # Try without extension
    template_path = templates_dir / f"{name}"
    if template_path.exists():
        return template_path

    return None

def _parse_variables(vars_list: tuple, vars_file: Optional[str]) -> Dict[str, Any]:
    """Parse variables from command line and file"""
    variables = {}

    # Load from file first
    if vars_file:
        with open(vars_file, 'r') as f:
            if vars_file.endswith('.json'):
                variables.update(json.load(f))
            else:
                variables.update(yaml.safe_load(f) or {})

    # Override with command line variables
    for var in vars_list:
        if '=' in var:
            key, value = var.split('=', 1)
            variables[key] = value

    return variables

def _generate_records(template_data: Dict[str, Any], variables: Dict[str, Any]) -> List[DNSRecord]:
    """Generate DNS records from template and variables"""
    env = Environment()
    records = []

    # Add defaults for missing optional variables
    if 'variables' in template_data:
        defaults = template_data['variables'].get('defaults', {})
        for key, value in defaults.items():
            if key not in variables:
                variables[key] = value

    for record_data in template_data.get('records', []):
        try:
            # Render template fields
            name = env.from_string(record_data['name']).render(**variables)
            data = env.from_string(record_data['data']).render(**variables)

            record = DNSRecord(
                name=name,
                type=record_data['type'],
                data=data,
                ttl=record_data.get('ttl', 3600),
                priority=record_data.get('priority')
            )

            records.append(record)

        except Exception as e:
            console.print(f"[red]Error generating record: {e}[/red]")

    return records