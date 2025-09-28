"""
Authentication and Authorization Management
Handles API key management, secure storage, and authentication flows
"""

import os
import time
import hashlib
import secrets
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import requests
from cryptography.fernet import Fernet
from rich.console import Console
from rich.prompt import Prompt, Confirm

from godaddy_cli.core.config import ConfigManager, ProfileConfig

console = Console()

@dataclass
class APICredentials:
    """API credentials container"""
    api_key: str
    api_secret: str
    environment: str = 'production'  # production or ote (sandbox)

    @property
    def base_url(self) -> str:
        """Get base URL for the environment"""
        if self.environment == 'ote':
            return 'https://api.ote-godaddy.com'
        return 'https://api.godaddy.com'

    @property
    def auth_header(self) -> str:
        """Get authorization header value"""
        return f"sso-key {self.api_key}:{self.api_secret}"

class AuthManager:
    """Manages authentication and API credentials"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self._credentials_cache: Dict[str, APICredentials] = {}

    def is_configured(self, profile: Optional[str] = None) -> bool:
        """Check if authentication is configured for profile"""
        profile_config = self.config.get_profile(profile)
        return bool(profile_config.api_key and profile_config.api_secret)

    def get_credentials(self, profile: Optional[str] = None) -> Optional[APICredentials]:
        """Get API credentials for profile"""
        profile_name = profile or self.config.profile

        if profile_name in self._credentials_cache:
            return self._credentials_cache[profile_name]

        profile_config = self.config.get_profile(profile_name)
        if not profile_config.api_key or not profile_config.api_secret:
            return None

        environment = 'ote' if profile_config.sandbox_mode else 'production'
        credentials = APICredentials(
            api_key=profile_config.api_key,
            api_secret=profile_config.api_secret,
            environment=environment
        )

        self._credentials_cache[profile_name] = credentials
        return credentials

    def set_credentials(self, api_key: str, api_secret: str,
                       profile: Optional[str] = None, sandbox: bool = False):
        """Set API credentials for profile"""
        profile_name = profile or self.config.profile
        profile_config = self.config.get_profile(profile_name)

        profile_config.api_key = api_key
        profile_config.api_secret = api_secret
        profile_config.sandbox_mode = sandbox

        self.config.set_profile(profile_name, profile_config)

        # Update cache
        environment = 'ote' if sandbox else 'production'
        self._credentials_cache[profile_name] = APICredentials(
            api_key=api_key,
            api_secret=api_secret,
            environment=environment
        )

        console.print(f"[green]✓ API credentials configured for profile '{profile_name}'[/green]")

    def remove_credentials(self, profile: Optional[str] = None):
        """Remove API credentials for profile"""
        profile_name = profile or self.config.profile
        profile_config = self.config.get_profile(profile_name)

        profile_config.api_key = None
        profile_config.api_secret = None

        self.config.set_profile(profile_name, profile_config)

        # Remove from cache
        self._credentials_cache.pop(profile_name, None)

        console.print(f"[yellow]Credentials removed for profile '{profile_name}'[/yellow]")

    def test_connection(self, profile: Optional[str] = None) -> bool:
        """Test API connection and credentials"""
        credentials = self.get_credentials(profile)
        if not credentials:
            raise ValueError("No API credentials configured")

        try:
            # Test with a simple API call
            response = requests.get(
                f"{credentials.base_url}/v1/domains/available?domain=test-domain-12345.com",
                headers={
                    'Authorization': credentials.auth_header,
                    'Accept': 'application/json'
                },
                timeout=10
            )

            if response.status_code == 401:
                raise ValueError("Invalid API credentials")
            elif response.status_code == 403:
                raise ValueError("API access forbidden - check permissions")
            elif response.status_code >= 400:
                raise ValueError(f"API error: {response.status_code}")

            return True

        except requests.RequestException as e:
            raise ValueError(f"Connection failed: {str(e)}")

    def interactive_setup(self, profile: Optional[str] = None):
        """Interactive setup of API credentials"""
        profile_name = profile or self.config.profile

        console.print(f"\n[bold cyan]Setting up API credentials for profile '{profile_name}'[/bold cyan]")
        console.print("\nYou need to obtain API credentials from your GoDaddy Developer account:")
        console.print("1. Go to https://developer.godaddy.com/keys")
        console.print("2. Create a new API key or use existing one")
        console.print("3. Copy your API Key and Secret\n")

        # Get API key
        api_key = Prompt.ask(
            "[bold]Enter your GoDaddy API Key[/bold]",
            password=True
        ).strip()

        if not api_key:
            console.print("[red]API Key is required[/red]")
            return False

        # Get API secret
        api_secret = Prompt.ask(
            "[bold]Enter your GoDaddy API Secret[/bold]",
            password=True
        ).strip()

        if not api_secret:
            console.print("[red]API Secret is required[/red]")
            return False

        # Ask about sandbox mode
        sandbox = Confirm.ask(
            "Do you want to use sandbox mode (for testing)?",
            default=False
        )

        # Set credentials
        self.set_credentials(api_key, api_secret, profile_name, sandbox)

        # Test connection
        console.print("\n[yellow]Testing API connection...[/yellow]")
        try:
            if self.test_connection(profile_name):
                console.print("[green]✓ API connection successful![/green]")
                return True
        except Exception as e:
            console.print(f"[red]✗ API connection failed: {e}[/red]")

            if Confirm.ask("Do you want to keep these credentials anyway?", default=False):
                return True
            else:
                self.remove_credentials(profile_name)
                return False

        return False

    def get_rate_limit_info(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """Get current rate limit information"""
        credentials = self.get_credentials(profile)
        if not credentials:
            raise ValueError("No API credentials configured")

        try:
            response = requests.get(
                f"{credentials.base_url}/v1/domains",
                headers={
                    'Authorization': credentials.auth_header,
                    'Accept': 'application/json'
                },
                params={'limit': 1},
                timeout=10
            )

            rate_limit_info = {
                'remaining': response.headers.get('X-RateLimit-Remaining'),
                'limit': response.headers.get('X-RateLimit-Limit'),
                'reset': response.headers.get('X-RateLimit-Reset'),
                'retry_after': response.headers.get('Retry-After')
            }

            # Convert string values to integers where possible
            for key in ['remaining', 'limit', 'reset', 'retry_after']:
                if rate_limit_info[key]:
                    try:
                        rate_limit_info[key] = int(rate_limit_info[key])
                    except ValueError:
                        pass

            return rate_limit_info

        except requests.RequestException as e:
            raise ValueError(f"Failed to get rate limit info: {str(e)}")

    def rotate_credentials(self, profile: Optional[str] = None):
        """Interactive credential rotation"""
        profile_name = profile or self.config.profile

        if not self.is_configured(profile_name):
            console.print(f"[red]No credentials configured for profile '{profile_name}'[/red]")
            return False

        console.print(f"\n[bold yellow]Rotating credentials for profile '{profile_name}'[/bold yellow]")

        if not Confirm.ask("This will replace your current credentials. Continue?"):
            return False

        # Backup current credentials
        current_credentials = self.get_credentials(profile_name)

        # Setup new credentials
        success = self.interactive_setup(profile_name)

        if not success:
            console.print("[yellow]Credential rotation cancelled[/yellow]")
            # Restore previous credentials if setup failed
            if current_credentials:
                self.set_credentials(
                    current_credentials.api_key,
                    current_credentials.api_secret,
                    profile_name,
                    current_credentials.environment == 'ote'
                )
            return False

        console.print("[green]✓ Credentials rotated successfully[/green]")
        return True

    def validate_api_key_format(self, api_key: str) -> bool:
        """Validate API key format"""
        # GoDaddy API keys are typically 32 characters long
        return len(api_key.strip()) >= 20 and api_key.replace('_', '').replace('-', '').isalnum()

    def validate_api_secret_format(self, api_secret: str) -> bool:
        """Validate API secret format"""
        # GoDaddy API secrets are typically longer than keys
        return len(api_secret.strip()) >= 20 and api_secret.replace('_', '').replace('-', '').isalnum()

    def export_credentials(self, output_path: Path, profile: Optional[str] = None):
        """Export credentials to file (use with extreme caution)"""
        if not Confirm.ask(
            "[red]WARNING: This will export credentials in plain text. "
            "Only use for secure backup purposes. Continue?[/red]"
        ):
            return False

        profile_name = profile or self.config.profile
        credentials = self.get_credentials(profile_name)

        if not credentials:
            console.print(f"[red]No credentials found for profile '{profile_name}'[/red]")
            return False

        export_data = {
            'profile': profile_name,
            'api_key': credentials.api_key,
            'api_secret': credentials.api_secret,
            'environment': credentials.environment,
            'exported_at': time.time()
        }

        try:
            with open(output_path, 'w') as f:
                import json
                json.dump(export_data, f, indent=2)

            console.print(f"[yellow]Credentials exported to {output_path}[/yellow]")
            console.print("[red]WARNING: Keep this file secure and delete after use![/red]")
            return True

        except Exception as e:
            console.print(f"[red]Export failed: {e}[/red]")
            return False

    def import_credentials(self, input_path: Path, profile: Optional[str] = None):
        """Import credentials from file"""
        profile_name = profile or self.config.profile

        try:
            with open(input_path, 'r') as f:
                import json
                data = json.load(f)

            if not all(key in data for key in ['api_key', 'api_secret']):
                console.print("[red]Invalid credentials file format[/red]")
                return False

            sandbox = data.get('environment') == 'ote'
            self.set_credentials(
                data['api_key'],
                data['api_secret'],
                profile_name,
                sandbox
            )

            console.print(f"[green]✓ Credentials imported for profile '{profile_name}'[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Import failed: {e}[/red]")
            return False