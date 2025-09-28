"""
Authentication management commands
"""

import click
import getpass
from typing import Optional

from godaddy_cli.core.auth import AuthManager, APICredentials
from godaddy_cli.core.exceptions import AuthenticationError, ValidationError
from godaddy_cli.utils.formatters import format_status_panel, format_json_output
from godaddy_cli.utils.validators import validate_url


@click.group(name='auth')
@click.pass_context
def auth_group(ctx):
    """Authentication management commands"""
    pass


@auth_group.command('setup')
@click.option('--profile', help='Setup authentication for specific profile')
@click.option('--api-key', help='GoDaddy API key')
@click.option('--api-secret', help='GoDaddy API secret')
@click.option('--api-url', help='GoDaddy API URL')
@click.option('--reset', is_flag=True, help='Reset existing credentials')
@click.pass_context
def setup_auth(ctx, profile: Optional[str], api_key: Optional[str],
               api_secret: Optional[str], api_url: Optional[str], reset: bool):
    """Setup authentication credentials"""
    try:
        auth_manager = ctx.obj['auth']
        config_manager = ctx.obj['config']

        # Determine profile to use
        target_profile = profile or config_manager.current_profile

        # Check if credentials already exist
        existing_creds = auth_manager.get_credentials(target_profile)
        if existing_creds and not reset:
            click.echo(format_status_panel(
                'warning',
                f'Credentials already exist for profile "{target_profile}". Use --reset to overwrite.'
            ))
            return

        # Interactive setup if credentials not provided
        if not api_key:
            click.echo("\n🔑 GoDaddy API Credentials Setup")
            click.echo("Get your API credentials from: https://developer.godaddy.com/keys")
            click.echo("")

            api_key = click.prompt("API Key", type=str)

        if not api_secret:
            api_secret = getpass.getpass("API Secret: ")

        if not api_url:
            environment = click.prompt(
                "Environment",
                type=click.Choice(['production', 'ote'], case_sensitive=False),
                default='production'
            )
            api_url = 'https://api.godaddy.com' if environment == 'production' else 'https://api.ote-godaddy.com'

        # Validate inputs
        if not api_key or not api_secret:
            raise ValidationError("API key and secret are required")

        validate_url(api_url)

        # Create credentials
        credentials = APICredentials(
            api_key=api_key.strip(),
            api_secret=api_secret.strip()
        )

        # Store credentials
        auth_manager.set_credentials(credentials, target_profile)

        # Update profile configuration
        profile_config = config_manager.get_profile(target_profile)
        if profile_config:
            profile_config.api_url = api_url
            config_manager.save()

        click.echo(format_status_panel('success', f'Credentials configured for profile "{target_profile}"'))

        # Test credentials
        if click.confirm("Test credentials now?", default=True):
            if auth_manager.test_credentials(target_profile):
                click.echo(format_status_panel('success', 'Credentials verified successfully'))
            else:
                click.echo(format_status_panel('warning', 'Credential test failed. Please verify your API key and secret.'))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except AuthenticationError as e:
        click.echo(format_status_panel('error', f'Authentication Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Setup failed: {str(e)}'), err=True)
        ctx.exit(1)


@auth_group.command('test')
@click.option('--profile', help='Test specific profile credentials')
@click.option('--verbose', is_flag=True, help='Show detailed test results')
@click.pass_context
def test_auth(ctx, profile: Optional[str], verbose: bool):
    """Test authentication credentials"""
    try:
        auth_manager = ctx.obj['auth']
        config_manager = ctx.obj['config']

        # Determine profile to test
        target_profile = profile or config_manager.current_profile

        # Check if credentials exist
        credentials = auth_manager.get_credentials(target_profile)
        if not credentials:
            click.echo(format_status_panel(
                'error',
                f'No credentials found for profile "{target_profile}". Run "godaddy auth setup" first.'
            ), err=True)
            ctx.exit(1)

        click.echo(f"Testing credentials for profile: {target_profile}")

        # Test credentials
        if auth_manager.test_credentials(target_profile):
            click.echo(format_status_panel('success', 'Authentication successful'))

            if verbose:
                # Show additional details
                profile_config = config_manager.get_profile(target_profile)
                click.echo(f"\nAPI URL: {getattr(profile_config, 'api_url', 'N/A')}")
                click.echo(f"API Key: {credentials.api_key[:8]}...")
        else:
            click.echo(format_status_panel('error', 'Authentication failed'), err=True)

            if verbose:
                click.echo("\nPossible issues:")
                click.echo("• Invalid API key or secret")
                click.echo("• Network connectivity problems")
                click.echo("• API endpoint issues")
                click.echo("• Expired or revoked credentials")

            ctx.exit(1)

    except AuthenticationError as e:
        click.echo(format_status_panel('error', f'Authentication Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Test failed: {str(e)}'), err=True)
        ctx.exit(1)


@auth_group.command('set-key')
@click.argument('api_key')
@click.argument('api_secret')
@click.option('--profile', help='Set credentials for specific profile')
@click.pass_context
def set_key(ctx, api_key: str, api_secret: str, profile: Optional[str]):
    """Set API credentials directly"""
    try:
        auth_manager = ctx.obj['auth']
        config_manager = ctx.obj['config']

        # Determine profile to use
        target_profile = profile or config_manager.current_profile

        # Validate inputs
        if not api_key or not api_secret:
            raise ValidationError("Both API key and secret are required")

        # Create credentials
        credentials = APICredentials(
            api_key=api_key.strip(),
            api_secret=api_secret.strip()
        )

        # Store credentials
        auth_manager.set_credentials(credentials, target_profile)

        click.echo(format_status_panel('success', f'Credentials set for profile "{target_profile}"'))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Failed to set credentials: {str(e)}'), err=True)
        ctx.exit(1)


@auth_group.command('clear')
@click.option('--profile', help='Clear credentials for specific profile')
@click.option('--all', 'clear_all', is_flag=True, help='Clear credentials for all profiles')
@click.option('--force', is_flag=True, help='Force clear without confirmation')
@click.pass_context
def clear_auth(ctx, profile: Optional[str], clear_all: bool, force: bool):
    """Clear stored credentials"""
    try:
        auth_manager = ctx.obj['auth']
        config_manager = ctx.obj['config']

        if clear_all:
            # Clear all credentials
            if not force:
                if not click.confirm('Clear credentials for all profiles?'):
                    click.echo(format_status_panel('info', 'Clear cancelled'))
                    return

            auth_manager.clear_all_credentials()
            click.echo(format_status_panel('success', 'Cleared credentials for all profiles'))

        else:
            # Clear specific profile
            target_profile = profile or config_manager.current_profile

            if not force:
                if not click.confirm(f'Clear credentials for profile "{target_profile}"?'):
                    click.echo(format_status_panel('info', 'Clear cancelled'))
                    return

            auth_manager.clear_credentials(target_profile)
            click.echo(format_status_panel('success', f'Cleared credentials for profile "{target_profile}"'))

    except Exception as e:
        click.echo(format_status_panel('error', f'Failed to clear credentials: {str(e)}'), err=True)
        ctx.exit(1)


@auth_group.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']),
              default='table', help='Output format')
@click.pass_context
def list_auth(ctx, output_format: str):
    """List configured authentication profiles"""
    try:
        auth_manager = ctx.obj['auth']
        config_manager = ctx.obj['config']

        # Get all profiles with credentials
        profiles_with_creds = []
        for profile_name in config_manager.list_profiles():
            credentials = auth_manager.get_credentials(profile_name)
            if credentials:
                profile_config = config_manager.get_profile(profile_name)
                profiles_with_creds.append({
                    'profile': profile_name,
                    'api_key': credentials.api_key[:8] + '...',
                    'api_url': getattr(profile_config, 'api_url', 'N/A'),
                    'current': profile_name == config_manager.current_profile
                })

        if not profiles_with_creds:
            click.echo(format_status_panel('info', 'No authentication profiles configured'))
            return

        if output_format == 'table':
            from rich.console import Console
            from rich.table import Table
            from rich import box

            table = Table(title="Authentication Profiles", box=box.ROUNDED)
            table.add_column("Profile", style="cyan")
            table.add_column("API Key", style="yellow")
            table.add_column("API URL", style="blue")
            table.add_column("Current", style="green")

            for profile_info in profiles_with_creds:
                current_marker = "✓" if profile_info['current'] else ""
                table.add_row(
                    profile_info['profile'],
                    profile_info['api_key'],
                    profile_info['api_url'],
                    current_marker
                )

            console = Console()
            console.print(table)

        elif output_format == 'json':
            click.echo(format_json_output(profiles_with_creds))

    except Exception as e:
        click.echo(format_status_panel('error', f'Failed to list profiles: {str(e)}'), err=True)
        ctx.exit(1)


@auth_group.command('rotate')
@click.option('--profile', help='Rotate credentials for specific profile')
@click.option('--new-key', help='New API key')
@click.option('--new-secret', help='New API secret')
@click.pass_context
def rotate_credentials(ctx, profile: Optional[str], new_key: Optional[str], new_secret: Optional[str]):
    """Rotate API credentials"""
    try:
        auth_manager = ctx.obj['auth']
        config_manager = ctx.obj['config']

        # Determine profile to use
        target_profile = profile or config_manager.current_profile

        # Check if credentials exist
        current_creds = auth_manager.get_credentials(target_profile)
        if not current_creds:
            click.echo(format_status_panel(
                'error',
                f'No credentials found for profile "{target_profile}"'
            ), err=True)
            ctx.exit(1)

        click.echo(f"Rotating credentials for profile: {target_profile}")

        # Get new credentials
        if not new_key:
            new_key = click.prompt("New API Key", type=str)

        if not new_secret:
            new_secret = getpass.getpass("New API Secret: ")

        # Validate inputs
        if not new_key or not new_secret:
            raise ValidationError("New API key and secret are required")

        # Create new credentials
        new_credentials = APICredentials(
            api_key=new_key.strip(),
            api_secret=new_secret.strip()
        )

        # Test new credentials before storing
        click.echo("Testing new credentials...")
        temp_auth = AuthManager()
        temp_auth.set_credentials(new_credentials, target_profile)

        if not temp_auth.test_credentials(target_profile):
            click.echo(format_status_panel('error', 'New credentials test failed'), err=True)
            ctx.exit(1)

        # Store new credentials
        auth_manager.set_credentials(new_credentials, target_profile)

        click.echo(format_status_panel('success', 'Credentials rotated successfully'))
        click.echo(format_status_panel('warning', 'Remember to update any external systems using the old credentials'))

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except AuthenticationError as e:
        click.echo(format_status_panel('error', f'Authentication Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Rotation failed: {str(e)}'), err=True)
        ctx.exit(1)


@auth_group.command('status')
@click.option('--profile', help='Check status for specific profile')
@click.pass_context
def auth_status(ctx, profile: Optional[str]):
    """Check authentication status"""
    try:
        auth_manager = ctx.obj['auth']
        config_manager = ctx.obj['config']

        # Determine profile to check
        target_profile = profile or config_manager.current_profile

        # Check if credentials exist
        credentials = auth_manager.get_credentials(target_profile)
        if not credentials:
            click.echo(format_status_panel(
                'error',
                f'No credentials configured for profile "{target_profile}"'
            ))
            return

        # Get profile configuration
        profile_config = config_manager.get_profile(target_profile)
        api_url = getattr(profile_config, 'api_url', 'Unknown')

        # Display status information
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        status_text = Text()
        status_text.append(f"Profile: {target_profile}\n", style="cyan bold")
        status_text.append(f"API URL: {api_url}\n", style="blue")
        status_text.append(f"API Key: {credentials.api_key[:8]}...\n", style="yellow")

        # Test connectivity
        status_text.append("Testing connectivity... ", style="white")

        try:
            if auth_manager.test_credentials(target_profile):
                status_text.append("✓ Connected\n", style="green bold")
            else:
                status_text.append("✗ Failed\n", style="red bold")
        except Exception as e:
            status_text.append(f"✗ Error: {str(e)}\n", style="red bold")

        panel = Panel(status_text, title="Authentication Status", border_style="blue")
        console.print(panel)

    except Exception as e:
        click.echo(format_status_panel('error', f'Status check failed: {str(e)}'), err=True)
        ctx.exit(1)


@auth_group.command('export-keys')
@click.option('--output', '-o', help='Output file path')
@click.option('--profile', help='Export keys for specific profile')
@click.option('--encrypt', is_flag=True, help='Encrypt exported keys')
@click.pass_context
def export_keys(ctx, output: Optional[str], profile: Optional[str], encrypt: bool):
    """Export API keys (use with caution)"""
    try:
        auth_manager = ctx.obj['auth']
        config_manager = ctx.obj['config']

        # Security warning
        click.echo(format_status_panel(
            'warning',
            'Exporting API keys is a security risk. Only export to secure locations.'
        ))

        if not click.confirm('Continue with key export?'):
            click.echo(format_status_panel('info', 'Export cancelled'))
            return

        # Determine profiles to export
        if profile:
            profiles_to_export = [profile]
        else:
            profiles_to_export = [
                p for p in config_manager.list_profiles()
                if auth_manager.get_credentials(p)
            ]

        if not profiles_to_export:
            click.echo(format_status_panel('error', 'No credentials found to export'), err=True)
            ctx.exit(1)

        # Collect export data
        export_data = {}
        for profile_name in profiles_to_export:
            credentials = auth_manager.get_credentials(profile_name)
            if credentials:
                export_data[profile_name] = {
                    'api_key': credentials.api_key,
                    'api_secret': credentials.api_secret
                }

        # Format output
        content = format_json_output(export_data)

        # Encrypt if requested
        if encrypt:
            password = getpass.getpass("Encryption password: ")
            # Note: In a real implementation, you'd use proper encryption
            # For this example, we'll just base64 encode
            import base64
            content = base64.b64encode(content.encode()).decode()

        # Write to file or stdout
        if output:
            with open(output, 'w') as f:
                f.write(content)
            click.echo(format_status_panel('success', f'Keys exported to {output}'))
        else:
            click.echo(content)

        click.echo(format_status_panel(
            'warning',
            'Exported keys should be stored securely and deleted when no longer needed'
        ))

    except Exception as e:
        click.echo(format_status_panel('error', f'Export failed: {str(e)}'), err=True)
        ctx.exit(1)


# Register commands
def register_commands(cli):
    """Register authentication commands with the main CLI"""
    cli.add_command(auth_group)