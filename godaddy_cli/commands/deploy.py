"""
DNS deployment commands for CI/CD integration
"""

import click
import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from godaddy_cli.core.api_client import SyncGoDaddyAPIClient, DNSRecord
from godaddy_cli.core.exceptions import APIError, ValidationError
from godaddy_cli.utils.formatters import format_status_panel, format_bulk_operation_summary
from godaddy_cli.utils.validators import validate_domain, validate_file_path


@click.group(name='deploy')
@click.pass_context
def deploy_group(ctx):
    """DNS deployment commands for CI/CD"""
    pass


@deploy_group.command('plan')
@click.argument('domain')
@click.argument('config_file')
@click.option('--output', '-o', help='Save deployment plan to file')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml', 'text']),
              default='text', help='Plan output format')
@click.pass_context
def deployment_plan(ctx, domain: str, config_file: str, output: Optional[str], output_format: str):
    """Generate deployment plan for DNS changes"""
    try:
        validate_domain(domain)
        validate_file_path(config_file)

        if not os.path.exists(config_file):
            raise ValidationError(f"Configuration file not found: {config_file}")

        client = SyncGoDaddyAPIClient(ctx.obj['auth'])

        # Load desired configuration
        with open(config_file, 'r') as f:
            if config_file.endswith('.json'):
                desired_config = json.load(f)
            else:
                import yaml
                desired_config = yaml.safe_load(f)

        # Get current DNS records
        current_records = client.list_dns_records(domain)
        current_state = {
            f"{r.name}.{r.type}": r
            for r in current_records
        }

        # Parse desired records
        desired_records = []
        for record_data in desired_config.get('records', []):
            record = DNSRecord.from_api_dict(record_data)
            desired_records.append(record)

        desired_state = {
            f"{r.name}.{r.type}": r
            for r in desired_records
        }

        # Generate deployment plan
        plan = _generate_deployment_plan(current_state, desired_state)

        # Format and output plan
        if output_format == 'json':
            plan_content = json.dumps(plan, indent=2, default=str)
        elif output_format == 'yaml':
            import yaml
            plan_content = yaml.dump(plan, default_flow_style=False)
        else:
            plan_content = _format_text_plan(plan)

        if output:
            validate_file_path(output)
            with open(output, 'w') as f:
                f.write(plan_content)
            click.echo(format_status_panel('success', f'Deployment plan saved to {output}'))
        else:
            click.echo(plan_content)

        # Summary
        total_changes = len(plan['create']) + len(plan['update']) + len(plan['delete'])
        if total_changes == 0:
            click.echo(format_status_panel('info', 'No changes required'))
        else:
            click.echo(format_status_panel('warning', f'{total_changes} changes planned'))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Plan generation failed: {str(e)}'), err=True)
        ctx.exit(1)


@deploy_group.command('apply')
@click.argument('domain')
@click.argument('config_file')
@click.option('--plan-file', help='Use existing deployment plan file')
@click.option('--auto-approve', is_flag=True, help='Apply changes without confirmation')
@click.option('--backup', is_flag=True, help='Create backup before applying changes')
@click.option('--batch-size', type=int, default=10, help='Batch size for bulk operations')
@click.pass_context
def apply_deployment(ctx, domain: str, config_file: str, plan_file: Optional[str],
                     auto_approve: bool, backup: bool, batch_size: int):
    """Apply DNS deployment plan"""
    try:
        validate_domain(domain)

        client = SyncGoDaddyAPIClient(ctx.obj['auth'])

        # Create backup if requested
        if backup:
            backup_file = f"dns_backup_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            current_records = client.list_dns_records(domain)

            backup_data = {
                'domain': domain,
                'backup_date': datetime.now().isoformat(),
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
                    for r in current_records
                ]
            }

            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)

            click.echo(format_status_panel('success', f'Backup created: {backup_file}'))

        # Load or generate deployment plan
        if plan_file:
            validate_file_path(plan_file)
            if not os.path.exists(plan_file):
                raise ValidationError(f"Plan file not found: {plan_file}")

            with open(plan_file, 'r') as f:
                if plan_file.endswith('.json'):
                    plan = json.load(f)
                else:
                    import yaml
                    plan = yaml.safe_load(f)
        else:
            # Generate plan from config file
            validate_file_path(config_file)
            if not os.path.exists(config_file):
                raise ValidationError(f"Configuration file not found: {config_file}")

            with open(config_file, 'r') as f:
                if config_file.endswith('.json'):
                    desired_config = json.load(f)
                else:
                    import yaml
                    desired_config = yaml.safe_load(f)

            # Get current state and generate plan
            current_records = client.list_dns_records(domain)
            current_state = {f"{r.name}.{r.type}": r for r in current_records}

            desired_records = []
            for record_data in desired_config.get('records', []):
                record = DNSRecord.from_api_dict(record_data)
                desired_records.append(record)
            desired_state = {f"{r.name}.{r.type}": r for r in desired_records}

            plan = _generate_deployment_plan(current_state, desired_state)

        # Display plan summary
        total_changes = len(plan['create']) + len(plan['update']) + len(plan['delete'])

        if total_changes == 0:
            click.echo(format_status_panel('info', 'No changes to apply'))
            return

        click.echo(f"\nDeployment Plan Summary:")
        click.echo(f"• {len(plan['create'])} records to create")
        click.echo(f"• {len(plan['update'])} records to update")
        click.echo(f"• {len(plan['delete'])} records to delete")
        click.echo(f"• Total: {total_changes} changes")

        # Confirm deployment
        if not auto_approve:
            if not click.confirm(f'\nApply {total_changes} changes to {domain}?'):
                click.echo(format_status_panel('info', 'Deployment cancelled'))
                return

        # Apply changes
        click.echo(f"\nApplying deployment to {domain}...")

        all_changes = []

        # Process deletions first
        for change in plan['delete']:
            try:
                success = client.delete_dns_record(domain, change['type'], change['name'])
                if success:
                    click.echo(f"✓ Deleted {change['name']} {change['type']}")
                else:
                    click.echo(f"✗ Failed to delete {change['name']} {change['type']}")
            except Exception as e:
                click.echo(f"✗ Error deleting {change['name']} {change['type']}: {str(e)}")

        # Process creates and updates in batches
        update_records = []

        for change in plan['create']:
            record = DNSRecord.from_api_dict(change['record'])
            update_records.append(record)

        for change in plan['update']:
            record = DNSRecord.from_api_dict(change['new_record'])
            update_records.append(record)

        if update_records:
            with click.progressbar(length=len(update_records), label='Applying changes') as bar:
                results = client.bulk_update_records(domain, update_records, batch_size)
                bar.update(len(update_records))

            click.echo(format_bulk_operation_summary(results))

        click.echo(format_status_panel('success', f'Deployment completed for {domain}'))

        # Post-deployment verification
        if click.confirm('Verify deployment?', default=True):
            click.echo("Verifying deployment...")
            time.sleep(5)  # Wait for propagation

            try:
                new_records = client.list_dns_records(domain)
                click.echo(f"✓ Verified {len(new_records)} DNS records")
            except Exception as e:
                click.echo(f"✗ Verification failed: {str(e)}")

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Deployment failed: {str(e)}'), err=True)
        ctx.exit(1)


@deploy_group.command('rollback')
@click.argument('domain')
@click.argument('backup_file')
@click.option('--auto-approve', is_flag=True, help='Rollback without confirmation')
@click.pass_context
def rollback_deployment(ctx, domain: str, backup_file: str, auto_approve: bool):
    """Rollback DNS changes using backup file"""
    try:
        validate_domain(domain)
        validate_file_path(backup_file)

        if not os.path.exists(backup_file):
            raise ValidationError(f"Backup file not found: {backup_file}")

        # Load backup
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)

        if backup_data.get('domain') != domain:
            if not click.confirm(f"Backup is for domain '{backup_data.get('domain')}' but rolling back to '{domain}'. Continue?"):
                click.echo(format_status_panel('info', 'Rollback cancelled'))
                return

        records_to_restore = []
        for record_data in backup_data.get('records', []):
            record = DNSRecord.from_api_dict(record_data)
            records_to_restore.append(record)

        click.echo(f"Rollback Plan:")
        click.echo(f"• Backup date: {backup_data.get('backup_date', 'Unknown')}")
        click.echo(f"• Records to restore: {len(records_to_restore)}")

        if not auto_approve:
            if not click.confirm(f'Rollback {domain} to backup state?'):
                click.echo(format_status_panel('info', 'Rollback cancelled'))
                return

        # Perform rollback
        client = SyncGoDaddyAPIClient(ctx.obj['auth'])

        # Clear existing records (dangerous!)
        click.echo("Clearing existing DNS records...")
        current_records = client.list_dns_records(domain)

        for record in current_records:
            try:
                client.delete_dns_record(domain, record.type, record.name)
            except Exception as e:
                click.echo(f"Warning: Failed to delete {record.name} {record.type}: {str(e)}")

        # Restore from backup
        click.echo("Restoring records from backup...")

        with click.progressbar(length=len(records_to_restore), label='Restoring records') as bar:
            results = client.bulk_update_records(domain, records_to_restore, batch_size=10)
            bar.update(len(records_to_restore))

        click.echo(format_bulk_operation_summary(results))

        if results['failed'] == 0:
            click.echo(format_status_panel('success', f'Rollback completed for {domain}'))
        else:
            click.echo(format_status_panel('warning', f'Rollback completed with {results["failed"]} failures'))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except APIError as e:
        click.echo(format_status_panel('error', f'API Error: {e.message}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Rollback failed: {str(e)}'), err=True)
        ctx.exit(1)


def _generate_deployment_plan(current_state: Dict[str, DNSRecord],
                             desired_state: Dict[str, DNSRecord]) -> Dict[str, List[Dict[str, Any]]]:
    """Generate deployment plan by comparing current and desired states"""
    plan = {
        'create': [],
        'update': [],
        'delete': []
    }

    # Find records to create or update
    for key, desired_record in desired_state.items():
        if key in current_state:
            current_record = current_state[key]
            if _records_differ(current_record, desired_record):
                plan['update'].append({
                    'name': desired_record.name,
                    'type': desired_record.type,
                    'old_record': {
                        'name': current_record.name,
                        'type': current_record.type,
                        'data': current_record.data,
                        'ttl': current_record.ttl,
                        'priority': current_record.priority
                    },
                    'new_record': {
                        'name': desired_record.name,
                        'type': desired_record.type,
                        'data': desired_record.data,
                        'ttl': desired_record.ttl,
                        'priority': desired_record.priority
                    }
                })
        else:
            plan['create'].append({
                'name': desired_record.name,
                'type': desired_record.type,
                'record': {
                    'name': desired_record.name,
                    'type': desired_record.type,
                    'data': desired_record.data,
                    'ttl': desired_record.ttl,
                    'priority': desired_record.priority
                }
            })

    # Find records to delete
    for key, current_record in current_state.items():
        if key not in desired_state:
            plan['delete'].append({
                'name': current_record.name,
                'type': current_record.type
            })

    return plan


def _records_differ(record1: DNSRecord, record2: DNSRecord) -> bool:
    """Check if two DNS records differ in meaningful ways"""
    return (
        record1.data != record2.data or
        record1.ttl != record2.ttl or
        record1.priority != record2.priority or
        record1.weight != record2.weight or
        record1.port != record2.port
    )


def _format_text_plan(plan: Dict[str, List[Dict[str, Any]]]) -> str:
    """Format deployment plan as human-readable text"""
    lines = []
    lines.append("DNS Deployment Plan")
    lines.append("=" * 50)

    if plan['create']:
        lines.append(f"\n{len(plan['create'])} Records to CREATE:")
        for change in plan['create']:
            record = change['record']
            lines.append(f"  + {change['name']} {change['type']} {record['data']} (TTL: {record['ttl']})")

    if plan['update']:
        lines.append(f"\n{len(plan['update'])} Records to UPDATE:")
        for change in plan['update']:
            old = change['old_record']
            new = change['new_record']
            lines.append(f"  ~ {change['name']} {change['type']}")
            if old['data'] != new['data']:
                lines.append(f"    data: {old['data']} → {new['data']}")
            if old['ttl'] != new['ttl']:
                lines.append(f"    ttl: {old['ttl']} → {new['ttl']}")

    if plan['delete']:
        lines.append(f"\n{len(plan['delete'])} Records to DELETE:")
        for change in plan['delete']:
            lines.append(f"  - {change['name']} {change['type']}")

    total_changes = len(plan['create']) + len(plan['update']) + len(plan['delete'])
    lines.append(f"\nTotal Changes: {total_changes}")

    return '\n'.join(lines)


def register_commands(cli):
    """Register deployment commands with the main CLI"""
    cli.add_command(deploy_group)