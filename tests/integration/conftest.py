"""
Pytest configuration for integration tests
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_config_file(temp_config_dir):
    """Create a mock configuration file"""
    config_data = {
        'profiles': {
            'default': {
                'api_key': 'test_key_123',
                'api_secret': 'test_secret_456'
            },
            'production': {
                'api_key': 'prod_key_789',
                'api_secret': 'prod_secret_012'
            }
        }
    }

    config_file = temp_config_dir / "config.json"
    config_file.write_text(json.dumps(config_data, indent=2))
    return config_file


@pytest.fixture
def mock_api_success():
    """Mock successful API responses"""
    def _mock_requests(method, url, **kwargs):
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 200

        if 'domains' in url:
            mock_response.json.return_value = [
                {
                    "domain": "example.com",
                    "status": "ACTIVE",
                    "expires": "2024-12-31T23:59:59Z",
                    "privacy": True,
                    "locked": False
                }
            ]
        elif 'records' in url:
            mock_response.json.return_value = [
                {
                    "name": "@",
                    "type": "A",
                    "data": "192.168.1.1",
                    "ttl": 3600,
                    "priority": 0,
                    "weight": 0,
                    "port": 0
                }
            ]
        else:
            mock_response.json.return_value = {}

        return mock_response

    with patch('requests.get', side_effect=_mock_requests), \
         patch('requests.post', side_effect=_mock_requests), \
         patch('requests.put', side_effect=_mock_requests), \
         patch('requests.patch', side_effect=_mock_requests), \
         patch('requests.delete', side_effect=_mock_requests):
        yield


@pytest.fixture
def sample_dns_records():
    """Sample DNS records for testing"""
    return [
        {
            "name": "@",
            "type": "A",
            "data": "192.168.1.1",
            "ttl": 3600,
            "priority": None,
            "weight": None,
            "port": None
        },
        {
            "name": "www",
            "type": "CNAME",
            "data": "example.com",
            "ttl": 3600,
            "priority": None,
            "weight": None,
            "port": None
        },
        {
            "name": "mail",
            "type": "MX",
            "data": "mail.example.com",
            "ttl": 3600,
            "priority": 10,
            "weight": None,
            "port": None
        }
    ]


@pytest.fixture
def sample_csv_records(temp_config_dir):
    """Create a sample CSV file with DNS records"""
    csv_content = """name,type,data,ttl,priority,weight,port
@,A,192.168.1.1,3600,,,
www,CNAME,example.com,3600,,,
mail,MX,mail.example.com,3600,10,,
api,A,192.168.1.2,7200,,,
ftp,CNAME,example.com,3600,,,"""

    csv_file = temp_config_dir / "test_records.csv"
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def sample_template(temp_config_dir):
    """Create a sample DNS template"""
    template_data = {
        "name": "web-app",
        "description": "Standard web application DNS setup",
        "version": "1.0.0",
        "author": "GoDaddy DNS CLI",
        "variables": [
            {
                "name": "app_ip",
                "description": "Application server IP address",
                "required": True,
                "type": "ipv4"
            },
            {
                "name": "backup_ip",
                "description": "Backup server IP address",
                "required": False,
                "type": "ipv4",
                "default": "192.168.1.100"
            }
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
            },
            {
                "name": "backup",
                "type": "A",
                "data": "{{ backup_ip }}",
                "ttl": 7200
            }
        ]
    }

    template_file = temp_config_dir / "web-app.json"
    template_file.write_text(json.dumps(template_data, indent=2))
    return template_file


@pytest.fixture(autouse=True)
def cleanup_env_vars():
    """Clean up environment variables after each test"""
    import os
    original_env = os.environ.copy()
    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def cli_runner():
    """Provide a CLI test runner"""
    from click.testing import CliRunner
    return CliRunner()