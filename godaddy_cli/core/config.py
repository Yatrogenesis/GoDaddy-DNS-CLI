"""
Configuration Management System
Handles configuration files, profiles, and settings persistence
"""

import os
import json
import yaml
import toml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import keyring
from rich.console import Console

console = Console()

@dataclass
class ProfileConfig:
    """Configuration for a single profile"""
    name: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    default_domain: Optional[str] = None
    default_ttl: int = 3600
    timeout: int = 30
    retries: int = 3
    sandbox_mode: bool = False
    output_format: str = 'table'  # table, json, yaml
    auto_confirm: bool = False
    backup_enabled: bool = True
    webhook_url: Optional[str] = None
    monitoring_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding sensitive data"""
        data = asdict(self)
        # Remove sensitive data from config file
        data.pop('api_key', None)
        data.pop('api_secret', None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProfileConfig':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

class ConfigManager:
    """Manages configuration files and profiles"""

    DEFAULT_CONFIG_DIR = Path.home() / '.godaddy-cli'
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / 'config.yaml'

    def __init__(self, profile: str = 'default', config_path: Optional[Path] = None):
        self.profile = profile
        self.config_file = config_path or self.DEFAULT_CONFIG_FILE
        self.config_dir = self.config_file.parent
        self._config: Dict[str, Any] = {}
        self._profiles: Dict[str, ProfileConfig] = {}
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        """Ensure configuration directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create .gitignore to prevent accidental commits
        gitignore_path = self.config_dir / '.gitignore'
        if not gitignore_path.exists():
            with open(gitignore_path, 'w') as f:
                f.write('# GoDaddy CLI configuration\n')
                f.write('*.key\n')
                f.write('*.secret\n')
                f.write('config.yaml\n')
                f.write('profiles/\n')

    def load(self):
        """Load configuration from file"""
        if not self.config_file.exists():
            self._create_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.suffix.lower() == '.json':
                    self._config = json.load(f)
                elif self.config_file.suffix.lower() in ['.yml', '.yaml']:
                    self._config = yaml.safe_load(f) or {}
                elif self.config_file.suffix.lower() == '.toml':
                    self._config = toml.load(f)
                else:
                    self._config = yaml.safe_load(f) or {}

            self._load_profiles()
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            self._create_default_config()

    def _load_profiles(self):
        """Load profiles from configuration"""
        profiles_data = self._config.get('profiles', {})
        for name, data in profiles_data.items():
            profile = ProfileConfig.from_dict({'name': name, **data})
            # Load sensitive data from keyring
            profile.api_key = self._get_secure_value(f"{name}_api_key")
            profile.api_secret = self._get_secure_value(f"{name}_api_secret")
            self._profiles[name] = profile

        # Ensure default profile exists
        if 'default' not in self._profiles:
            self._profiles['default'] = ProfileConfig(name='default')

    def _create_default_config(self):
        """Create default configuration"""
        self._config = {
            'version': '2.0.0',
            'default_profile': 'default',
            'global': {
                'check_updates': True,
                'analytics': False,
                'color_output': True,
                'parallel_requests': 5,
                'cache_ttl': 300
            },
            'profiles': {
                'default': ProfileConfig(name='default').to_dict()
            }
        }
        self._profiles['default'] = ProfileConfig(name='default')
        self.save()

    def save(self):
        """Save configuration to file"""
        try:
            # Prepare config for saving (without sensitive data)
            config_to_save = self._config.copy()
            config_to_save['profiles'] = {}

            for name, profile in self._profiles.items():
                config_to_save['profiles'][name] = profile.to_dict()
                # Save sensitive data to keyring
                if profile.api_key:
                    self._set_secure_value(f"{name}_api_key", profile.api_key)
                if profile.api_secret:
                    self._set_secure_value(f"{name}_api_secret", profile.api_secret)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.suffix.lower() == '.json':
                    json.dump(config_to_save, f, indent=2)
                elif self.config_file.suffix.lower() in ['.yml', '.yaml']:
                    yaml.dump(config_to_save, f, default_flow_style=False, indent=2)
                elif self.config_file.suffix.lower() == '.toml':
                    toml.dump(config_to_save, f)
                else:
                    yaml.dump(config_to_save, f, default_flow_style=False, indent=2)

        except Exception as e:
            console.print(f"[red]Error saving config: {e}[/red]")
            raise

    def get_profile(self, name: Optional[str] = None) -> ProfileConfig:
        """Get profile configuration"""
        profile_name = name or self.profile
        if profile_name not in self._profiles:
            console.print(f"[yellow]Profile '{profile_name}' not found, creating default[/yellow]")
            self._profiles[profile_name] = ProfileConfig(name=profile_name)
        return self._profiles[profile_name]

    def set_profile(self, name: str, config: ProfileConfig):
        """Set profile configuration"""
        self._profiles[name] = config
        self.save()

    def delete_profile(self, name: str):
        """Delete a profile"""
        if name == 'default':
            raise ValueError("Cannot delete default profile")

        if name in self._profiles:
            # Remove from keyring
            self._delete_secure_value(f"{name}_api_key")
            self._delete_secure_value(f"{name}_api_secret")
            del self._profiles[name]
            self.save()

    def list_profiles(self) -> Dict[str, ProfileConfig]:
        """List all profiles"""
        return self._profiles.copy()

    def get_global_setting(self, key: str, default: Any = None) -> Any:
        """Get global setting"""
        return self._config.get('global', {}).get(key, default)

    def set_global_setting(self, key: str, value: Any):
        """Set global setting"""
        if 'global' not in self._config:
            self._config['global'] = {}
        self._config['global'][key] = value
        self.save()

    def _get_secure_value(self, key: str) -> Optional[str]:
        """Get secure value from keyring"""
        try:
            return keyring.get_password('godaddy-cli', key)
        except Exception:
            return None

    def _set_secure_value(self, key: str, value: str):
        """Set secure value in keyring"""
        try:
            keyring.set_password('godaddy-cli', key, value)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not store secure value: {e}[/yellow]")

    def _delete_secure_value(self, key: str):
        """Delete secure value from keyring"""
        try:
            keyring.delete_password('godaddy-cli', key)
        except Exception:
            pass

    def export_config(self, output_path: Path, include_secrets: bool = False) -> Path:
        """Export configuration to file"""
        config_to_export = self._config.copy()

        if include_secrets:
            # Include secrets (use with caution)
            for name, profile in self._profiles.items():
                profile_data = profile.to_dict()
                if profile.api_key:
                    profile_data['api_key'] = profile.api_key
                if profile.api_secret:
                    profile_data['api_secret'] = profile.api_secret
                config_to_export['profiles'][name] = profile_data

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_to_export, f, default_flow_style=False, indent=2)

        return output_path

    def import_config(self, input_path: Path, merge: bool = True):
        """Import configuration from file"""
        with open(input_path, 'r', encoding='utf-8') as f:
            imported_config = yaml.safe_load(f)

        if not merge:
            self._config = imported_config
        else:
            # Merge configurations
            self._config.update(imported_config)

        # Process profiles with potential secrets
        if 'profiles' in imported_config:
            for name, data in imported_config['profiles'].items():
                profile = ProfileConfig.from_dict({'name': name, **data})

                # Handle secrets if present in import
                if 'api_key' in data:
                    profile.api_key = data['api_key']
                if 'api_secret' in data:
                    profile.api_secret = data['api_secret']

                self._profiles[name] = profile

        self.save()

    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration"""
        issues = []
        warnings = []

        # Check profiles
        for name, profile in self._profiles.items():
            if not profile.api_key or not profile.api_secret:
                issues.append(f"Profile '{name}' missing API credentials")

            if profile.default_ttl < 300:
                warnings.append(f"Profile '{name}' has very low TTL ({profile.default_ttl}s)")

        # Check global settings
        parallel_requests = self.get_global_setting('parallel_requests', 5)
        if parallel_requests > 20:
            warnings.append(f"High parallel requests setting ({parallel_requests}) may cause rate limiting")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }