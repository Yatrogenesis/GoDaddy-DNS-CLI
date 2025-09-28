"""
Integration tests for CLI commands
Tests the complete CLI workflow end-to-end
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from godaddy_cli.cli import cli
from godaddy_cli.core.config import ConfigManager


class TestCLIIntegration:
    """Test CLI commands as a complete system"""

    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.json"

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_workflow(self):
        """Test complete configuration workflow"""
        # Test config setup
        with patch('godaddy_cli.core.auth.AuthManager.test_connection') as mock_test:
            mock_test.return_value = True

            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                'auth', 'setup',
                '--api-key', 'test_key_123',
                '--api-secret', 'test_secret_456',
                '--no-test'
            ])

            assert result.exit_code == 0
            assert self.config_file.exists()

            # Verify config file content
            config_data = json.loads(self.config_file.read_text())
            assert 'profiles' in config_data
            assert 'default' in config_data['profiles']

    def test_dns_list_workflow(self):
        """Test DNS listing with different output formats"""
        # Setup mock config
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        # Mock API response
        mock_records = [
            {
                'name': '@',
                'type': 'A',
                'data': '192.168.1.1',
                'ttl': 3600,
                'priority': None,
                'weight': None,
                'port': None
            },
            {
                'name': 'www',
                'type': 'CNAME',
                'data': 'example.com',
                'ttl': 3600,
                'priority': None,
                'weight': None,
                'port': None
            }
        ]

        with patch('godaddy_cli.core.api_client.APIClient.get_records') as mock_get:
            mock_get.return_value = mock_records

            # Test table output
            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                'dns', 'list', 'example.com'
            ])

            assert result.exit_code == 0
            assert 'DNS Records' in result.output
            assert '192.168.1.1' in result.output
            assert 'www' in result.output

            # Test JSON output
            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                '--json',
                'dns', 'list', 'example.com'
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert len(output_data) == 2
            assert output_data[0]['type'] == 'A'

    def test_dns_add_workflow(self):
        """Test adding DNS records"""
        # Setup mock config
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        with patch('godaddy_cli.core.api_client.APIClient.add_record') as mock_add:
            mock_add.return_value = True

            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                'dns', 'add', 'example.com',
                '--name', 'test',
                '--type', 'A',
                '--data', '192.168.1.100',
                '--ttl', '3600'
            ])

            assert result.exit_code == 0
            mock_add.assert_called_once()

            # Verify the call was made with correct parameters
            call_args = mock_add.call_args[0]
            assert call_args[0] == 'example.com'  # domain
            record = call_args[1]  # record object
            assert record.name == 'test'
            assert record.type == 'A'
            assert record.data == '192.168.1.100'
            assert record.ttl == 3600

    def test_domain_list_workflow(self):
        """Test domain listing"""
        # Setup mock config
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        mock_domains = [
            {
                'domain': 'example.com',
                'status': 'ACTIVE',
                'expires': '2024-12-31T23:59:59Z',
                'privacy': True,
                'locked': False
            },
            {
                'domain': 'test.com',
                'status': 'ACTIVE',
                'expires': '2025-06-15T23:59:59Z',
                'privacy': False,
                'locked': True
            }
        ]

        with patch('godaddy_cli.core.api_client.APIClient.get_domains') as mock_get:
            mock_get.return_value = mock_domains

            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                'domains', 'list'
            ])

            assert result.exit_code == 0
            assert 'example.com' in result.output
            assert 'test.com' in result.output
            assert 'ACTIVE' in result.output

    def test_error_handling_workflow(self):
        """Test error handling in CLI commands"""
        # Setup mock config
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'invalid_key',
                    'api_secret': 'invalid_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        # Test API authentication failure
        with patch('godaddy_cli.core.api_client.APIClient.get_records') as mock_get:
            mock_get.side_effect = Exception("Authentication failed")

            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                'dns', 'list', 'example.com'
            ])

            assert result.exit_code == 1
            assert 'Authentication failed' in result.output

    def test_status_command_workflow(self):
        """Test status command with different scenarios"""
        # Test with no config
        result = self.runner.invoke(cli, [
            '--config-file', str(self.config_file),
            'status'
        ])

        assert result.exit_code == 0
        assert 'API Configured' in result.output
        assert '✗' in result.output  # Should show not configured

        # Test with valid config
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        with patch('godaddy_cli.core.auth.AuthManager.test_connection') as mock_test:
            mock_test.return_value = True

            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                'status'
            ])

            assert result.exit_code == 0
            assert 'API Configured' in result.output
            assert '✓ Connected' in result.output

    def test_bulk_operations_workflow(self):
        """Test bulk operations from CSV"""
        # Setup mock config
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        # Create test CSV file
        csv_content = """name,type,data,ttl,priority,weight,port
www,A,192.168.1.1,3600,,,
mail,MX,mail.example.com,3600,10,,
api,CNAME,example.com,3600,,,"""

        csv_file = Path(self.temp_dir) / "test_records.csv"
        csv_file.write_text(csv_content)

        with patch('godaddy_cli.core.api_client.APIClient.add_record') as mock_add:
            mock_add.return_value = True

            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                'bulk', 'import', 'example.com',
                '--file', str(csv_file)
            ])

            assert result.exit_code == 0
            assert mock_add.call_count == 3  # Should add 3 records

    def test_template_workflow(self):
        """Test template operations"""
        # Setup mock config
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        # Create test template
        template_content = {
            "name": "web-app",
            "description": "Standard web application DNS setup",
            "version": "1.0.0",
            "variables": [
                {"name": "app_ip", "description": "Application server IP", "required": True},
                {"name": "cdn_url", "description": "CDN URL", "required": False}
            ],
            "records": [
                {
                    "name": "@",
                    "type": "A",
                    "data": "{{ app_ip }}",
                    "ttl": 3600
                },
                {
                    "name": "www",
                    "type": "CNAME",
                    "data": "{{ domain }}",
                    "ttl": 3600
                }
            ]
        }

        template_file = Path(self.temp_dir) / "web-app.json"
        template_file.write_text(json.dumps(template_content, indent=2))

        # Test template validation
        result = self.runner.invoke(cli, [
            '--config-file', str(self.config_file),
            'template', 'validate',
            str(template_file)
        ])

        assert result.exit_code == 0
        assert 'Template validation successful' in result.output

    def test_config_profiles_workflow(self):
        """Test multiple configuration profiles"""
        # Setup config with multiple profiles
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'default_key',
                    'api_secret': 'default_secret'
                },
                'production': {
                    'api_key': 'prod_key',
                    'api_secret': 'prod_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        # Test using different profile
        with patch('godaddy_cli.core.api_client.APIClient.get_domains') as mock_get:
            mock_get.return_value = []

            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                '--profile', 'production',
                'domains', 'list'
            ])

            assert result.exit_code == 0

    def test_export_import_workflow(self):
        """Test export and import operations"""
        # Setup mock config
        config_data = {
            'profiles': {
                'default': {
                    'api_key': 'test_key',
                    'api_secret': 'test_secret'
                }
            }
        }
        self.config_file.write_text(json.dumps(config_data))

        mock_records = [
            {
                'name': '@',
                'type': 'A',
                'data': '192.168.1.1',
                'ttl': 3600,
                'priority': None,
                'weight': None,
                'port': None
            }
        ]

        with patch('godaddy_cli.core.api_client.APIClient.get_records') as mock_get:
            mock_get.return_value = mock_records

            # Test export to JSON
            export_file = Path(self.temp_dir) / "export.json"
            result = self.runner.invoke(cli, [
                '--config-file', str(self.config_file),
                'export', 'json', 'example.com',
                '--output', str(export_file)
            ])

            assert result.exit_code == 0
            assert export_file.exists()

            exported_data = json.loads(export_file.read_text())
            assert len(exported_data) == 1
            assert exported_data[0]['type'] == 'A'