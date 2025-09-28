"""
Unit tests for configuration management
"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

from godaddy_cli.core.config import ConfigManager, ProfileConfig


@pytest.mark.unit
class TestProfileConfig:
    """Test ProfileConfig dataclass"""

    def test_profile_config_creation(self):
        """Test creating a profile configuration"""
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456',
            default_domain='example.com',
            default_ttl=7200
        )

        assert profile.name == 'test'
        assert profile.api_key == 'key123'
        assert profile.api_secret == 'secret456'
        assert profile.default_domain == 'example.com'
        assert profile.default_ttl == 7200
        assert profile.timeout == 30  # default value
        assert not profile.sandbox_mode  # default value

    def test_profile_to_dict(self):
        """Test converting profile to dictionary (excluding sensitive data)"""
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456',
            default_domain='example.com'
        )

        data = profile.to_dict()

        assert 'name' in data
        assert 'default_domain' in data
        assert 'api_key' not in data  # should be excluded
        assert 'api_secret' not in data  # should be excluded

    def test_profile_from_dict(self):
        """Test creating profile from dictionary"""
        data = {
            'name': 'test',
            'default_domain': 'example.com',
            'default_ttl': 7200,
            'sandbox_mode': True
        }

        profile = ProfileConfig.from_dict(data)

        assert profile.name == 'test'
        assert profile.default_domain == 'example.com'
        assert profile.default_ttl == 7200
        assert profile.sandbox_mode is True


@pytest.mark.unit
class TestConfigManager:
    """Test ConfigManager class"""

    def test_config_manager_creation(self, temp_config_dir):
        """Test creating config manager"""
        config_file = temp_config_dir / 'test_config.yaml'
        config = ConfigManager(profile='test', config_path=config_file)

        assert config.profile == 'test'
        assert config.config_file == config_file
        assert config.config_dir == temp_config_dir

    def test_ensure_config_dir_creation(self, temp_config_dir):
        """Test that config directory is created"""
        config_file = temp_config_dir / 'subdir' / 'config.yaml'
        ConfigManager(config_path=config_file)

        assert config_file.parent.exists()
        gitignore_path = config_file.parent / '.gitignore'
        assert gitignore_path.exists()

    def test_create_default_config(self, temp_config_dir):
        """Test creating default configuration"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        assert config_file.exists()
        assert 'default' in config._profiles
        assert config._config['version'] == '2.0.0'

    def test_load_config_yaml(self, temp_config_dir):
        """Test loading YAML configuration"""
        config_file = temp_config_dir / 'config.yaml'

        # Create test config
        test_config = {
            'version': '2.0.0',
            'profiles': {
                'test': {
                    'name': 'test',
                    'default_domain': 'example.com',
                    'default_ttl': 7200
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)

        config = ConfigManager(config_path=config_file)

        assert config._config['version'] == '2.0.0'
        assert 'test' in config._profiles
        assert config._profiles['test'].default_domain == 'example.com'

    def test_load_config_json(self, temp_config_dir):
        """Test loading JSON configuration"""
        config_file = temp_config_dir / 'config.json'

        test_config = {
            'version': '2.0.0',
            'profiles': {
                'test': {
                    'name': 'test',
                    'default_domain': 'example.com'
                }
            }
        }

        with open(config_file, 'w') as f:
            json.dump(test_config, f)

        config = ConfigManager(config_path=config_file)

        assert config._config['version'] == '2.0.0'
        assert 'test' in config._profiles

    def test_save_config(self, temp_config_dir):
        """Test saving configuration"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        # Add a test profile
        test_profile = ProfileConfig(name='test', default_domain='example.com')
        config.set_profile('test', test_profile)

        # Verify file was updated
        assert config_file.exists()

        # Load and verify content
        with open(config_file, 'r') as f:
            saved_config = yaml.safe_load(f)

        assert 'profiles' in saved_config
        assert 'test' in saved_config['profiles']
        assert saved_config['profiles']['test']['default_domain'] == 'example.com'

    def test_get_profile(self, temp_config_dir):
        """Test getting profile configuration"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        # Get default profile
        default_profile = config.get_profile('default')
        assert default_profile.name == 'default'

        # Get non-existent profile (should create it)
        new_profile = config.get_profile('new')
        assert new_profile.name == 'new'

    def test_set_profile(self, temp_config_dir):
        """Test setting profile configuration"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        test_profile = ProfileConfig(
            name='test',
            default_domain='example.com',
            default_ttl=7200
        )

        config.set_profile('test', test_profile)

        # Verify profile was set
        retrieved_profile = config.get_profile('test')
        assert retrieved_profile.default_domain == 'example.com'
        assert retrieved_profile.default_ttl == 7200

    def test_delete_profile(self, temp_config_dir):
        """Test deleting profile"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        # Add test profile
        test_profile = ProfileConfig(name='test')
        config.set_profile('test', test_profile)

        # Delete profile
        config.delete_profile('test')

        # Verify profile was deleted
        assert 'test' not in config._profiles

    def test_delete_default_profile_error(self, temp_config_dir):
        """Test that deleting default profile raises error"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        with pytest.raises(ValueError, match="Cannot delete default profile"):
            config.delete_profile('default')

    def test_list_profiles(self, temp_config_dir):
        """Test listing all profiles"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        # Add test profiles
        config.set_profile('test1', ProfileConfig(name='test1'))
        config.set_profile('test2', ProfileConfig(name='test2'))

        profiles = config.list_profiles()

        assert 'default' in profiles
        assert 'test1' in profiles
        assert 'test2' in profiles
        assert len(profiles) >= 3

    def test_global_settings(self, temp_config_dir):
        """Test global settings management"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        # Test setting global setting
        config.set_global_setting('test_setting', 'test_value')
        assert config.get_global_setting('test_setting') == 'test_value'

        # Test default value
        assert config.get_global_setting('non_existent', 'default') == 'default'

    def test_export_config(self, temp_config_dir):
        """Test exporting configuration"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        # Add test profile
        test_profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        config.set_profile('test', test_profile)

        # Export without secrets
        export_file = temp_config_dir / 'export.yaml'
        config.export_config(export_file, include_secrets=False)

        with open(export_file, 'r') as f:
            exported = yaml.safe_load(f)

        assert 'api_key' not in exported['profiles']['test']
        assert 'api_secret' not in exported['profiles']['test']

        # Export with secrets
        export_with_secrets = temp_config_dir / 'export_secrets.yaml'
        config.export_config(export_with_secrets, include_secrets=True)

        with open(export_with_secrets, 'r') as f:
            exported = yaml.safe_load(f)

        assert exported['profiles']['test']['api_key'] == 'key123'
        assert exported['profiles']['test']['api_secret'] == 'secret456'

    def test_import_config(self, temp_config_dir):
        """Test importing configuration"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        # Create import file
        import_data = {
            'profiles': {
                'imported': {
                    'name': 'imported',
                    'default_domain': 'imported.com'
                }
            }
        }

        import_file = temp_config_dir / 'import.yaml'
        with open(import_file, 'w') as f:
            yaml.dump(import_data, f)

        # Import configuration
        config.import_config(import_file)

        # Verify import
        assert 'imported' in config._profiles
        assert config._profiles['imported'].default_domain == 'imported.com'

    def test_validate_config(self, temp_config_dir):
        """Test configuration validation"""
        config_file = temp_config_dir / 'config.yaml'
        config = ConfigManager(config_path=config_file)

        # Test with invalid profile (no API credentials)
        validation = config.validate_config()
        assert not validation['valid']
        assert len(validation['issues']) > 0

        # Add valid profile
        test_profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        config.set_profile('test', test_profile)

        validation = config.validate_config()
        assert validation['valid']

    def test_config_error_handling(self, temp_config_dir):
        """Test configuration error handling"""
        config_file = temp_config_dir / 'invalid.yaml'

        # Create invalid YAML file
        with open(config_file, 'w') as f:
            f.write('invalid: yaml: content: [')

        # Should handle invalid YAML gracefully
        config = ConfigManager(config_path=config_file)
        assert 'default' in config._profiles