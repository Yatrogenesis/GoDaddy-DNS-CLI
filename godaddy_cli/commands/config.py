"""
Configuration management commands
"""

import click
import os
from typing import Optional, Dict, Any

from godaddy_cli.core.config import ConfigManager
from godaddy_cli.core.exceptions import ValidationError
from godaddy_cli.utils.formatters import (
    format_status_panel, format_json_output, format_yaml_output, format_config_info
)
from godaddy_cli.utils.validators import validate_file_path


@click.group(name='config')
@click.pass_context
def config_group(ctx):
    """Configuration management commands"""
    pass


@config_group.command('show')
@click.option('--profile', help='Show specific profile configuration')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.pass_context
def show_config(ctx, profile: Optional[str], output_format: str):
    """Show current configuration"""
    try:
        config_manager = ctx.obj['config']

        if profile:
            # Show specific profile
            profile_config = config_manager.get_profile(profile)
            if not profile_config:
                click.echo(format_status_panel('error', f'Profile "{profile}" not found'), err=True)
                ctx.exit(1)

            config_data = profile_config.__dict__
        else:
            # Show all configuration
            config_data = {
                'current_profile': config_manager.current_profile,
                'profiles': {
                    name: profile.__dict__
                    for name, profile in config_manager.profiles.items()
                },
                'global_settings': config_manager.global_config
            }

        # Format output
        if output_format == 'table':
            click.echo(format_config_info(config_data))
        elif output_format == 'json':
            click.echo(format_json_output(config_data))
        elif output_format == 'yaml':
            click.echo(format_yaml_output(config_data))

    except Exception as e:
        click.echo(format_status_panel('error', f'Error reading configuration: {str(e)}'), err=True)
        ctx.exit(1)


@config_group.command('set')
@click.argument('key')
@click.argument('value')
@click.option('--profile', help='Set value for specific profile')
@click.option('--type', 'value_type', type=click.Choice(['string', 'int', 'float', 'bool']),
              default='string', help='Value type')
@click.pass_context
def set_config(ctx, key: str, value: str, profile: Optional[str], value_type: str):
    """Set configuration value"""
    try:
        config_manager = ctx.obj['config']

        # Convert value to appropriate type
        converted_value = _convert_value(value, value_type)

        if profile:
            # Set profile-specific setting
            config_manager.set_profile_setting(profile, key, converted_value)
            click.echo(format_status_panel('success', f'Set {key}={converted_value} for profile "{profile}"'))
        else:
            # Set global setting
            config_manager.set_global_setting(key, converted_value)
            click.echo(format_status_panel('success', f'Set {key}={converted_value} globally'))

        # Save configuration
        config_manager.save()

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Error setting configuration: {str(e)}'), err=True)
        ctx.exit(1)


@config_group.command('get')
@click.argument('key')
@click.option('--profile', help='Get value from specific profile')
@click.pass_context
def get_config(ctx, key: str, profile: Optional[str]):
    """Get configuration value"""
    try:
        config_manager = ctx.obj['config']

        if profile:
            # Get profile-specific setting
            profile_config = config_manager.get_profile(profile)
            if not profile_config:
                click.echo(format_status_panel('error', f'Profile "{profile}" not found'), err=True)
                ctx.exit(1)

            value = getattr(profile_config, key, None)
            if value is None:
                click.echo(format_status_panel('error', f'Setting "{key}" not found in profile "{profile}"'), err=True)
                ctx.exit(1)
        else:
            # Get global setting
            value = config_manager.get_global_setting(key)
            if value is None:
                click.echo(format_status_panel('error', f'Setting "{key}" not found'), err=True)
                ctx.exit(1)

        click.echo(str(value))

    except Exception as e:
        click.echo(format_status_panel('error', f'Error getting configuration: {str(e)}'), err=True)
        ctx.exit(1)


@config_group.command('unset')
@click.argument('key')
@click.option('--profile', help='Unset value from specific profile')
@click.pass_context
def unset_config(ctx, key: str, profile: Optional[str]):
    """Remove configuration value"""
    try:
        config_manager = ctx.obj['config']

        if profile:
            # Unset profile-specific setting
            profile_config = config_manager.get_profile(profile)
            if not profile_config:
                click.echo(format_status_panel('error', f'Profile "{profile}" not found'), err=True)
                ctx.exit(1)

            if hasattr(profile_config, key):
                delattr(profile_config, key)
                click.echo(format_status_panel('success', f'Unset {key} from profile "{profile}"'))
            else:
                click.echo(format_status_panel('error', f'Setting "{key}" not found in profile "{profile}"'), err=True)
                ctx.exit(1)
        else:
            # Unset global setting
            if key in config_manager.global_config:
                del config_manager.global_config[key]
                click.echo(format_status_panel('success', f'Unset {key} globally'))
            else:
                click.echo(format_status_panel('error', f'Setting "{key}" not found'), err=True)
                ctx.exit(1)

        # Save configuration
        config_manager.save()

    except Exception as e:
        click.echo(format_status_panel('error', f'Error unsetting configuration: {str(e)}'), err=True)
        ctx.exit(1)


@config_group.group('profile')
@click.pass_context
def profile_group(ctx):
    """Profile management commands"""
    pass


@profile_group.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.pass_context
def list_profiles(ctx, output_format: str):
    """List all configuration profiles"""
    try:
        config_manager = ctx.obj['config']
        profiles = config_manager.list_profiles()
        current_profile = config_manager.current_profile

        if output_format == 'table':
            from rich.console import Console
            from rich.table import Table
            from rich import box

            table = Table(title="Configuration Profiles", box=box.ROUNDED)
            table.add_column("Profile", style="cyan")
            table.add_column("Current", style="green")
            table.add_column("API URL", style="yellow")
            table.add_column("Default TTL", style="blue")

            for profile_name in profiles:
                profile_config = config_manager.get_profile(profile_name)
                current_marker = "✓" if profile_name == current_profile else ""

                table.add_row(
                    profile_name,
                    current_marker,
                    getattr(profile_config, 'api_url', 'N/A'),
                    str(getattr(profile_config, 'default_ttl', 'N/A'))
                )

            console = Console()
            console.print(table)

        elif output_format == 'json':
            profile_data = {
                'current_profile': current_profile,
                'profiles': profiles
            }
            click.echo(format_json_output(profile_data))

        elif output_format == 'yaml':
            profile_data = {
                'current_profile': current_profile,
                'profiles': profiles
            }
            click.echo(format_yaml_output(profile_data))

    except Exception as e:
        click.echo(format_status_panel('error', f'Error listing profiles: {str(e)}'), err=True)
        ctx.exit(1)


@profile_group.command('create')
@click.argument('profile_name')
@click.option('--api-url', default='https://api.godaddy.com', help='API URL')
@click.option('--default-ttl', type=int, default=3600, help='Default TTL')
@click.option('--rate-limit', type=int, default=1000, help='Rate limit')
@click.option('--timeout', type=int, default=30, help='Request timeout')
@click.pass_context
def create_profile(ctx, profile_name: str, api_url: str, default_ttl: int, rate_limit: int, timeout: int):
    """Create a new configuration profile"""
    try:
        config_manager = ctx.obj['config']

        # Check if profile already exists
        if config_manager.get_profile(profile_name):
            click.echo(format_status_panel('error', f'Profile "{profile_name}" already exists'), err=True)
            ctx.exit(1)

        # Create new profile
        config_manager.create_profile(
            profile_name,
            api_url=api_url,
            default_ttl=default_ttl,
            rate_limit=rate_limit,
            timeout=timeout
        )

        # Save configuration
        config_manager.save()

        click.echo(format_status_panel('success', f'Created profile "{profile_name}"'))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Error creating profile: {str(e)}'), err=True)
        ctx.exit(1)


@profile_group.command('delete')
@click.argument('profile_name')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete_profile(ctx, profile_name: str, force: bool):
    """Delete a configuration profile"""
    try:
        config_manager = ctx.obj['config']

        # Check if profile exists
        if not config_manager.get_profile(profile_name):
            click.echo(format_status_panel('error', f'Profile "{profile_name}" not found'), err=True)
            ctx.exit(1)

        # Check if it's the current profile
        if profile_name == config_manager.current_profile:
            click.echo(format_status_panel('error', 'Cannot delete the current profile'), err=True)
            ctx.exit(1)

        # Confirm deletion
        if not force:
            if not click.confirm(f'Delete profile "{profile_name}"?'):
                click.echo(format_status_panel('info', 'Deletion cancelled'))
                return

        # Delete profile
        config_manager.delete_profile(profile_name)

        # Save configuration
        config_manager.save()

        click.echo(format_status_panel('success', f'Deleted profile "{profile_name}"'))

    except Exception as e:
        click.echo(format_status_panel('error', f'Error deleting profile: {str(e)}'), err=True)
        ctx.exit(1)


@profile_group.command('use')
@click.argument('profile_name')
@click.pass_context
def use_profile(ctx, profile_name: str):
    """Switch to a different profile"""
    try:
        config_manager = ctx.obj['config']

        # Check if profile exists
        if not config_manager.get_profile(profile_name):
            click.echo(format_status_panel('error', f'Profile "{profile_name}" not found'), err=True)
            ctx.exit(1)

        # Switch profile
        config_manager.set_current_profile(profile_name)

        # Save configuration
        config_manager.save()

        click.echo(format_status_panel('success', f'Switched to profile "{profile_name}"'))

    except Exception as e:
        click.echo(format_status_panel('error', f'Error switching profile: {str(e)}'), err=True)
        ctx.exit(1)


@config_group.command('export')
@click.option('--output', '-o', help='Output file path')
@click.option('--profile', help='Export specific profile only')
@click.option('--no-secrets', is_flag=True, help='Exclude sensitive data')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml']),
              default='yaml', help='Output format')
@click.pass_context
def export_config(ctx, output: Optional[str], profile: Optional[str], no_secrets: bool, output_format: str):
    """Export configuration to file"""
    try:
        config_manager = ctx.obj['config']

        if profile:
            # Export specific profile
            profile_config = config_manager.get_profile(profile)
            if not profile_config:
                click.echo(format_status_panel('error', f'Profile "{profile}" not found'), err=True)
                ctx.exit(1)

            config_data = profile_config.__dict__
        else:
            # Export all configuration
            config_data = {
                'current_profile': config_manager.current_profile,
                'profiles': {
                    name: profile.__dict__
                    for name, profile in config_manager.profiles.items()
                },
                'global_settings': config_manager.global_config
            }

        # Remove secrets if requested
        if no_secrets:
            config_data = _remove_secrets(config_data)

        # Format output
        if output_format == 'json':
            content = format_json_output(config_data)
        else:
            content = format_yaml_output(config_data)

        # Write to file or stdout
        if output:
            validate_file_path(output)
            with open(output, 'w') as f:
                f.write(content)
            click.echo(format_status_panel('success', f'Configuration exported to {output}'))
        else:
            click.echo(content)

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Error exporting configuration: {str(e)}'), err=True)
        ctx.exit(1)


@config_group.command('import')
@click.argument('file_path')
@click.option('--profile', help='Import as specific profile')
@click.option('--merge', is_flag=True, help='Merge with existing configuration')
@click.pass_context
def import_config(ctx, file_path: str, profile: Optional[str], merge: bool):
    """Import configuration from file"""
    try:
        validate_file_path(file_path)

        if not os.path.exists(file_path):
            click.echo(format_status_panel('error', f'File not found: {file_path}'), err=True)
            ctx.exit(1)

        config_manager = ctx.obj['config']

        # Read configuration file
        with open(file_path, 'r') as f:
            content = f.read()

        # Parse based on file extension
        if file_path.endswith('.json'):
            import json
            config_data = json.loads(content)
        elif file_path.endswith(('.yaml', '.yml')):
            import yaml
            config_data = yaml.safe_load(content)
        else:
            click.echo(format_status_panel('error', 'Unsupported file format. Use .json or .yaml'), err=True)
            ctx.exit(1)

        # Import configuration
        if profile:
            # Import as specific profile
            config_manager.import_profile(profile, config_data)
            click.echo(format_status_panel('success', f'Imported configuration as profile "{profile}"'))
        else:
            # Import full configuration
            config_manager.import_config(config_data, merge=merge)
            click.echo(format_status_panel('success', 'Configuration imported successfully'))

        # Save configuration
        config_manager.save()

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Error importing configuration: {str(e)}'), err=True)
        ctx.exit(1)


@config_group.command('validate')
@click.option('--file', 'config_file', help='Validate specific configuration file')
@click.option('--verbose', is_flag=True, help='Show detailed validation results')
@click.pass_context
def validate_config(ctx, config_file: Optional[str], verbose: bool):
    """Validate configuration"""
    try:
        if config_file:
            # Validate specific file
            validate_file_path(config_file)
            if not os.path.exists(config_file):
                click.echo(format_status_panel('error', f'File not found: {config_file}'), err=True)
                ctx.exit(1)

            # Read and parse file
            with open(config_file, 'r') as f:
                content = f.read()

            if config_file.endswith('.json'):
                import json
                config_data = json.loads(content)
            elif config_file.endswith(('.yaml', '.yml')):
                import yaml
                config_data = yaml.safe_load(content)
            else:
                click.echo(format_status_panel('error', 'Unsupported file format'), err=True)
                ctx.exit(1)

            # Validate configuration data
            validation_result = _validate_config_data(config_data)
        else:
            # Validate current configuration
            config_manager = ctx.obj['config']
            validation_result = config_manager.validate()

        if validation_result['valid']:
            click.echo(format_status_panel('success', 'Configuration is valid'))
        else:
            click.echo(format_status_panel('error', 'Configuration validation failed'), err=True)

            if verbose or validation_result.get('errors'):
                for error in validation_result.get('errors', []):
                    click.echo(f"  • {error}", err=True)

            ctx.exit(1)

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Error validating configuration: {str(e)}'), err=True)
        ctx.exit(1)


@config_group.command('reset')
@click.option('--profile', help='Reset specific profile to defaults')
@click.option('--force', is_flag=True, help='Force reset without confirmation')
@click.pass_context
def reset_config(ctx, profile: Optional[str], force: bool):
    """Reset configuration to defaults"""
    try:
        config_manager = ctx.obj['config']

        if profile:
            # Reset specific profile
            if not config_manager.get_profile(profile):
                click.echo(format_status_panel('error', f'Profile "{profile}" not found'), err=True)
                ctx.exit(1)

            if not force:
                if not click.confirm(f'Reset profile "{profile}" to defaults?'):
                    click.echo(format_status_panel('info', 'Reset cancelled'))
                    return

            config_manager.reset_profile(profile)
            click.echo(format_status_panel('success', f'Reset profile "{profile}" to defaults'))
        else:
            # Reset all configuration
            if not force:
                if not click.confirm('Reset all configuration to defaults?'):
                    click.echo(format_status_panel('info', 'Reset cancelled'))
                    return

            config_manager.reset_to_defaults()
            click.echo(format_status_panel('success', 'Reset all configuration to defaults'))

        # Save configuration
        config_manager.save()

    except Exception as e:
        click.echo(format_status_panel('error', f'Error resetting configuration: {str(e)}'), err=True)
        ctx.exit(1)


def _convert_value(value: str, value_type: str) -> Any:
    """Convert string value to appropriate type"""
    if value_type == 'int':
        return int(value)
    elif value_type == 'float':
        return float(value)
    elif value_type == 'bool':
        return value.lower() in ('true', '1', 'yes', 'on')
    else:
        return value


def _remove_secrets(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive data from configuration"""
    import copy
    cleaned_data = copy.deepcopy(data)

    secret_keys = ['api_key', 'api_secret', 'password', 'token']

    def clean_dict(d):
        if isinstance(d, dict):
            for key, value in d.items():
                if any(secret in key.lower() for secret in secret_keys):
                    d[key] = '***'
                elif isinstance(value, dict):
                    clean_dict(value)

    clean_dict(cleaned_data)
    return cleaned_data


def _validate_config_data(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration data structure"""
    errors = []

    # Basic structure validation
    if not isinstance(config_data, dict):
        errors.append("Configuration must be a dictionary")
        return {'valid': False, 'errors': errors}

    # Validate profiles
    if 'profiles' in config_data:
        if not isinstance(config_data['profiles'], dict):
            errors.append("Profiles must be a dictionary")
        else:
            for profile_name, profile_config in config_data['profiles'].items():
                if not isinstance(profile_config, dict):
                    errors.append(f"Profile '{profile_name}' must be a dictionary")

    return {'valid': len(errors) == 0, 'errors': errors}


# Register commands
def register_commands(cli):
    """Register configuration commands with the main CLI"""
    cli.add_command(config_group)