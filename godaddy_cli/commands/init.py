"""
Project initialization commands
"""

import click
import os
import getpass
from typing import Optional

from godaddy_cli.core.config import ConfigManager
from godaddy_cli.core.auth import AuthManager, APICredentials
from godaddy_cli.core.exceptions import ValidationError
from godaddy_cli.utils.formatters import format_status_panel
from godaddy_cli.utils.validators import validate_url


@click.command('init')
@click.option('--profile', default='default', help='Profile name to initialize')
@click.option('--api-key', help='GoDaddy API key')
@click.option('--api-secret', help='GoDaddy API secret')
@click.option('--environment', type=click.Choice(['production', 'ote'], case_sensitive=False),
              default='production', help='API environment')
@click.option('--force', is_flag=True, help='Force initialization, overwriting existing config')
@click.pass_context
def init_project(ctx, profile: str, api_key: Optional[str], api_secret: Optional[str],
                 environment: str, force: bool):
    """Initialize GoDaddy DNS CLI configuration"""
    try:
        # Welcome message
        click.echo("🚀 GoDaddy DNS CLI Setup")
        click.echo("=" * 50)

        # Check if already initialized
        config_manager = ConfigManager()
        existing_profile = config_manager.get_profile(profile)

        if existing_profile and not force:
            click.echo(format_status_panel(
                'warning',
                f'Profile "{profile}" already exists. Use --force to overwrite.'
            ))
            return

        # Interactive setup if credentials not provided
        click.echo("\n1. API Credentials Setup")
        click.echo("Get your API credentials from: https://developer.godaddy.com/keys")

        if not api_key:
            api_key = click.prompt("API Key", type=str)

        if not api_secret:
            api_secret = getpass.getpass("API Secret: ")

        # Validate inputs
        if not api_key or not api_secret:
            raise ValidationError("API key and secret are required")

        # Determine API URL
        api_url = 'https://api.godaddy.com' if environment == 'production' else 'https://api.ote-godaddy.com'

        click.echo(f"\n2. Environment Configuration")
        click.echo(f"Environment: {environment}")
        click.echo(f"API URL: {api_url}")

        # Create profile
        if existing_profile:
            click.echo(f"\n3. Updating Profile: {profile}")
        else:
            click.echo(f"\n3. Creating Profile: {profile}")

        config_manager.create_profile(
            profile,
            api_url=api_url,
            default_ttl=3600,
            rate_limit=1000 if environment == 'production' else 100,
            timeout=30
        )

        # Set as current profile
        config_manager.set_current_profile(profile)
        config_manager.save()

        # Store credentials
        auth_manager = AuthManager()
        credentials = APICredentials(
            api_key=api_key.strip(),
            api_secret=api_secret.strip()
        )
        auth_manager.set_credentials(credentials, profile)

        click.echo(format_status_panel('success', f'Profile "{profile}" configured successfully'))

        # Test credentials
        click.echo("\n4. Testing Connection")
        if click.confirm("Test API connection now?", default=True):
            if auth_manager.test_credentials(profile):
                click.echo(format_status_panel('success', 'API connection successful!'))
            else:
                click.echo(format_status_panel('warning', 'API connection test failed. Please verify your credentials.'))

        # Quick start guide
        click.echo("\n5. Quick Start Guide")
        click.echo("=" * 20)
        click.echo("Your GoDaddy DNS CLI is now ready! Try these commands:")
        click.echo("")
        click.echo("• List domains:        godaddy domains list")
        click.echo("• List DNS records:    godaddy dns list example.com")
        click.echo("• Add A record:        godaddy dns add example.com A www 192.168.1.1")
        click.echo("• Start web UI:        godaddy web")
        click.echo("• Show help:           godaddy --help")
        click.echo("")

        # Configuration summary
        click.echo("6. Configuration Summary")
        click.echo("=" * 25)
        click.echo(f"Profile: {profile}")
        click.echo(f"Environment: {environment}")
        click.echo(f"Config location: {config_manager.config_file}")
        click.echo("")

        # Security recommendations
        click.echo("7. Security Recommendations")
        click.echo("=" * 28)
        click.echo("• Keep your API credentials secure")
        click.echo("• Use OTE environment for testing")
        click.echo("• Regularly rotate your API keys")
        click.echo("• Enable audit logging for production use")
        click.echo("")

        click.echo("🎉 Setup complete! Happy DNS managing!")

    except ValidationError as e:
        click.echo(format_status_panel('error', f'Validation Error: {str(e)}'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(format_status_panel('error', f'Initialization failed: {str(e)}'), err=True)
        ctx.exit(1)


def register_commands(cli):
    """Register init command with the main CLI"""
    cli.add_command(init_project)