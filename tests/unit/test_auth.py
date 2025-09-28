"""
Unit tests for authentication management
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import requests

from godaddy_cli.core.auth import AuthManager, APICredentials
from godaddy_cli.core.config import ConfigManager, ProfileConfig


@pytest.mark.unit
class TestAPICredentials:
    """Test APICredentials class"""

    def test_api_credentials_creation(self):
        """Test creating API credentials"""
        creds = APICredentials(
            api_key='key123',
            api_secret='secret456',
            environment='production'
        )

        assert creds.api_key == 'key123'
        assert creds.api_secret == 'secret456'
        assert creds.environment == 'production'

    def test_base_url_production(self):
        """Test base URL for production environment"""
        creds = APICredentials(
            api_key='key',
            api_secret='secret',
            environment='production'
        )

        assert creds.base_url == 'https://api.godaddy.com'

    def test_base_url_sandbox(self):
        """Test base URL for sandbox environment"""
        creds = APICredentials(
            api_key='key',
            api_secret='secret',
            environment='ote'
        )

        assert creds.base_url == 'https://api.ote-godaddy.com'

    def test_auth_header(self):
        """Test authorization header generation"""
        creds = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        expected = 'sso-key key123:secret456'
        assert creds.auth_header == expected


@pytest.mark.unit
class TestAuthManager:
    """Test AuthManager class"""

    def test_auth_manager_creation(self, mock_config):
        """Test creating auth manager"""
        auth = AuthManager(mock_config)

        assert auth.config == mock_config
        assert isinstance(auth._credentials_cache, dict)

    def test_is_configured_true(self, mock_config):
        """Test is_configured returns True when credentials exist"""
        # Set up profile with credentials
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        mock_config.set_profile('test', profile)

        auth = AuthManager(mock_config)

        assert auth.is_configured('test') is True

    def test_is_configured_false(self, mock_config):
        """Test is_configured returns False when credentials missing"""
        # Profile without credentials
        profile = ProfileConfig(name='test')
        mock_config.set_profile('test', profile)

        auth = AuthManager(mock_config)

        assert auth.is_configured('test') is False

    def test_get_credentials_success(self, mock_config):
        """Test getting credentials successfully"""
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456',
            sandbox_mode=True
        )
        mock_config.set_profile('test', profile)

        auth = AuthManager(mock_config)
        creds = auth.get_credentials('test')

        assert creds is not None
        assert creds.api_key == 'key123'
        assert creds.api_secret == 'secret456'
        assert creds.environment == 'ote'

    def test_get_credentials_none(self, mock_config):
        """Test getting credentials returns None when not configured"""
        profile = ProfileConfig(name='test')
        mock_config.set_profile('test', profile)

        auth = AuthManager(mock_config)
        creds = auth.get_credentials('test')

        assert creds is None

    def test_credentials_caching(self, mock_config):
        """Test that credentials are cached"""
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        mock_config.set_profile('test', profile)

        auth = AuthManager(mock_config)

        # First call
        creds1 = auth.get_credentials('test')
        # Second call (should use cache)
        creds2 = auth.get_credentials('test')

        assert creds1 is creds2  # Same object (cached)

    def test_set_credentials(self, mock_config):
        """Test setting credentials"""
        auth = AuthManager(mock_config)

        auth.set_credentials(
            api_key='new_key',
            api_secret='new_secret',
            profile='test',
            sandbox=True
        )

        # Verify credentials were set
        profile = mock_config.get_profile('test')
        assert profile.api_key == 'new_key'
        assert profile.api_secret == 'new_secret'
        assert profile.sandbox_mode is True

        # Verify cache was updated
        creds = auth.get_credentials('test')
        assert creds.api_key == 'new_key'
        assert creds.environment == 'ote'

    def test_remove_credentials(self, mock_config):
        """Test removing credentials"""
        # Set up profile with credentials
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        mock_config.set_profile('test', profile)

        auth = AuthManager(mock_config)

        # Remove credentials
        auth.remove_credentials('test')

        # Verify credentials were removed
        profile = mock_config.get_profile('test')
        assert profile.api_key is None
        assert profile.api_secret is None

        # Verify cache was cleared
        assert 'test' not in auth._credentials_cache

    @patch('requests.get')
    def test_test_connection_success(self, mock_get, mock_config):
        """Test successful connection test"""
        # Set up credentials
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        mock_config.set_profile('test', profile)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        auth = AuthManager(mock_config)
        result = auth.test_connection('test')

        assert result is True
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_test_connection_invalid_credentials(self, mock_get, mock_config):
        """Test connection test with invalid credentials"""
        profile = ProfileConfig(
            name='test',
            api_key='invalid_key',
            api_secret='invalid_secret'
        )
        mock_config.set_profile('test', profile)

        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        auth = AuthManager(mock_config)

        with pytest.raises(ValueError, match="Invalid API credentials"):
            auth.test_connection('test')

    @patch('requests.get')
    def test_test_connection_forbidden(self, mock_get, mock_config):
        """Test connection test with forbidden response"""
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        mock_config.set_profile('test', profile)

        # Mock 403 response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        auth = AuthManager(mock_config)

        with pytest.raises(ValueError, match="API access forbidden"):
            auth.test_connection('test')

    @patch('requests.get')
    def test_test_connection_network_error(self, mock_get, mock_config):
        """Test connection test with network error"""
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        mock_config.set_profile('test', profile)

        # Mock network error
        mock_get.side_effect = requests.RequestException("Network error")

        auth = AuthManager(mock_config)

        with pytest.raises(ValueError, match="Connection failed"):
            auth.test_connection('test')

    def test_test_connection_no_credentials(self, mock_config):
        """Test connection test without credentials"""
        profile = ProfileConfig(name='test')
        mock_config.set_profile('test', profile)

        auth = AuthManager(mock_config)

        with pytest.raises(ValueError, match="No API credentials configured"):
            auth.test_connection('test')

    @patch('requests.get')
    def test_get_rate_limit_info(self, mock_get, mock_config):
        """Test getting rate limit information"""
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456'
        )
        mock_config.set_profile('test', profile)

        # Mock response with rate limit headers
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'X-RateLimit-Remaining': '45',
            'X-RateLimit-Limit': '60',
            'X-RateLimit-Reset': '3600',
            'Retry-After': '10'
        }
        mock_get.return_value = mock_response

        auth = AuthManager(mock_config)
        rate_info = auth.get_rate_limit_info('test')

        assert rate_info['remaining'] == 45
        assert rate_info['limit'] == 60
        assert rate_info['reset'] == 3600
        assert rate_info['retry_after'] == 10

    def test_validate_api_key_format(self, mock_config):
        """Test API key format validation"""
        auth = AuthManager(mock_config)

        # Valid keys
        assert auth.validate_api_key_format('abcdef1234567890abcdef1234567890') is True
        assert auth.validate_api_key_format('valid_key_with_underscores_123') is True

        # Invalid keys
        assert auth.validate_api_key_format('short') is False
        assert auth.validate_api_key_format('') is False
        assert auth.validate_api_key_format('key with spaces') is False

    def test_validate_api_secret_format(self, mock_config):
        """Test API secret format validation"""
        auth = AuthManager(mock_config)

        # Valid secrets
        assert auth.validate_api_secret_format('abcdef1234567890abcdef1234567890') is True
        assert auth.validate_api_secret_format('valid_secret_with_underscores_123') is True

        # Invalid secrets
        assert auth.validate_api_secret_format('short') is False
        assert auth.validate_api_secret_format('') is False
        assert auth.validate_api_secret_format('secret with spaces') is False

    @patch('builtins.open', create=True)
    @patch('json.dump')
    @patch('time.time', return_value=1234567890)
    def test_export_credentials(self, mock_time, mock_json_dump, mock_open, mock_config):
        """Test exporting credentials"""
        profile = ProfileConfig(
            name='test',
            api_key='key123',
            api_secret='secret456',
            sandbox_mode=True
        )
        mock_config.set_profile('test', profile)

        auth = AuthManager(mock_config)

        # Mock user confirmation
        with patch('godaddy_cli.core.auth.Confirm.ask', return_value=True):
            result = auth.export_credentials(Path('/tmp/export.json'), 'test')

        assert result is True
        mock_json_dump.assert_called_once()

        # Verify export data structure
        call_args = mock_json_dump.call_args[0]
        export_data = call_args[0]

        assert export_data['profile'] == 'test'
        assert export_data['api_key'] == 'key123'
        assert export_data['api_secret'] == 'secret456'
        assert export_data['environment'] == 'ote'
        assert export_data['exported_at'] == 1234567890

    @patch('builtins.open', create=True)
    @patch('json.load')
    def test_import_credentials(self, mock_json_load, mock_open, mock_config):
        """Test importing credentials"""
        # Mock import data
        import_data = {
            'api_key': 'imported_key',
            'api_secret': 'imported_secret',
            'environment': 'production'
        }
        mock_json_load.return_value = import_data

        auth = AuthManager(mock_config)
        result = auth.import_credentials(Path('/tmp/import.json'), 'test')

        assert result is True

        # Verify credentials were set
        profile = mock_config.get_profile('test')
        assert profile.api_key == 'imported_key'
        assert profile.api_secret == 'imported_secret'
        assert profile.sandbox_mode is False  # production environment

    @patch('builtins.input')
    @patch('getpass.getpass')
    @patch.object(AuthManager, 'test_connection')
    def test_interactive_setup_success(self, mock_test, mock_getpass, mock_input, mock_config):
        """Test successful interactive setup"""
        # Mock user inputs
        mock_getpass.side_effect = ['test_key', 'test_secret']
        mock_input.return_value = 'n'  # no sandbox

        # Mock successful connection test
        mock_test.return_value = True

        auth = AuthManager(mock_config)

        with patch('godaddy_cli.core.auth.Prompt.ask') as mock_prompt:
            with patch('godaddy_cli.core.auth.Confirm.ask') as mock_confirm:
                mock_prompt.side_effect = ['test_key', 'test_secret']
                mock_confirm.return_value = False  # no sandbox

                result = auth.interactive_setup('test')

        assert result is True

        # Verify credentials were set
        profile = mock_config.get_profile('test')
        assert profile.api_key == 'test_key'
        assert profile.api_secret == 'test_secret'