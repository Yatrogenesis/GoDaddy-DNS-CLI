"""
Test configuration and fixtures for GoDaddy DNS CLI
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List

from godaddy_cli.core.config import ConfigManager, ProfileConfig
from godaddy_cli.core.auth import AuthManager, APICredentials
from godaddy_cli.core.api_client import DNSRecord, Domain


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_config(temp_config_dir):
    """Mock configuration manager"""
    config_file = temp_config_dir / 'config.yaml'
    config = ConfigManager(config_path=config_file)

    # Set up test profile
    test_profile = ProfileConfig(
        name='test',
        api_key='test_api_key',
        api_secret='test_api_secret',
        default_domain='example.com',
        sandbox_mode=True
    )
    config.set_profile('test', test_profile)

    return config


@pytest.fixture
def mock_auth(mock_config):
    """Mock authentication manager"""
    auth = AuthManager(mock_config)
    return auth


@pytest.fixture
def mock_credentials():
    """Mock API credentials"""
    return APICredentials(
        api_key='test_key_12345',
        api_secret='test_secret_67890',
        environment='ote'
    )


@pytest.fixture
def sample_dns_records():
    """Sample DNS records for testing"""
    return [
        DNSRecord(
            name='@',
            type='A',
            data='192.168.1.1',
            ttl=3600
        ),
        DNSRecord(
            name='www',
            type='A',
            data='192.168.1.1',
            ttl=3600
        ),
        DNSRecord(
            name='mail',
            type='MX',
            data='mail.example.com',
            ttl=3600,
            priority=10
        ),
        DNSRecord(
            name='@',
            type='TXT',
            data='v=spf1 include:_spf.google.com ~all',
            ttl=3600
        ),
        DNSRecord(
            name='blog',
            type='CNAME',
            data='www.example.com',
            ttl=3600
        )
    ]


@pytest.fixture
def sample_domains():
    """Sample domains for testing"""
    return [
        Domain(
            domain='example.com',
            status='ACTIVE',
            expires='2024-12-31T23:59:59Z',
            created='2023-01-01T00:00:00Z',
            privacy=True,
            locked=False
        ),
        Domain(
            domain='test.com',
            status='ACTIVE',
            expires='2025-06-30T23:59:59Z',
            created='2023-06-01T00:00:00Z',
            privacy=False,
            locked=True
        )
    ]


@pytest.fixture
def mock_api_response():
    """Mock API response data"""
    def _response(data: Any, status_code: int = 200):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = data
        response.headers = {
            'X-RateLimit-Remaining': '59',
            'X-RateLimit-Limit': '60',
            'X-RateLimit-Reset': '3600'
        }
        return response
    return _response


@pytest.fixture
def mock_async_api_client():
    """Mock async API client"""
    client = AsyncMock()

    # Configure common methods
    client.list_domains = AsyncMock()
    client.list_dns_records = AsyncMock()
    client.create_dns_record = AsyncMock(return_value=True)
    client.update_dns_record = AsyncMock(return_value=True)
    client.delete_dns_record = AsyncMock(return_value=True)
    client.replace_all_records = AsyncMock(return_value=True)
    client.bulk_update_records = AsyncMock(return_value={
        'success': 5,
        'failed': 0,
        'errors': []
    })

    return client


@pytest.fixture
def sample_template_data():
    """Sample template data for testing"""
    return {
        'name': 'Basic Web Server',
        'description': 'Standard DNS setup for web server',
        'version': '1.0.0',
        'variables': {
            'required': ['domain', 'server_ip'],
            'optional': ['mail_server'],
            'defaults': {
                'mail_server': 'mail.{{ domain }}'
            }
        },
        'records': [
            {
                'name': '@',
                'type': 'A',
                'data': '{{ server_ip }}',
                'ttl': 3600
            },
            {
                'name': 'www',
                'type': 'A',
                'data': '{{ server_ip }}',
                'ttl': 3600
            },
            {
                'name': '@',
                'type': 'MX',
                'data': '{{ mail_server }}',
                'ttl': 3600,
                'priority': 10
            }
        ]
    }


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter that doesn't actually limit"""
    limiter = Mock()
    limiter.acquire = AsyncMock()
    return limiter


@pytest.fixture(autouse=True)
def disable_keyring():
    """Disable keyring operations in tests"""
    import godaddy_cli.core.config

    original_get = godaddy_cli.core.config.ConfigManager._get_secure_value
    original_set = godaddy_cli.core.config.ConfigManager._set_secure_value
    original_delete = godaddy_cli.core.config.ConfigManager._delete_secure_value

    godaddy_cli.core.config.ConfigManager._get_secure_value = Mock(return_value=None)
    godaddy_cli.core.config.ConfigManager._set_secure_value = Mock()
    godaddy_cli.core.config.ConfigManager._delete_secure_value = Mock()

    yield

    godaddy_cli.core.config.ConfigManager._get_secure_value = original_get
    godaddy_cli.core.config.ConfigManager._set_secure_value = original_set
    godaddy_cli.core.config.ConfigManager._delete_secure_value = original_delete


class MockRequestsResponse:
    """Mock requests response"""

    def __init__(self, json_data: Dict[str, Any], status_code: int = 200, headers: Dict[str, str] = None):
        self.json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_requests_get(monkeypatch):
    """Mock requests.get method"""
    def _mock_get(responses: List[MockRequestsResponse]):
        response_iter = iter(responses)

        def mock_get(*args, **kwargs):
            try:
                return next(response_iter)
            except StopIteration:
                return MockRequestsResponse({}, 404)

        monkeypatch.setattr('requests.get', mock_get)
        return mock_get

    return _mock_get


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session"""
    session = AsyncMock()

    # Mock request method
    async def mock_request(method, url, **kwargs):
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={'status': 'success'})
        return response

    session.request = mock_request

    # Mock context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    return session


@pytest.fixture
def cli_runner():
    """Click CLI test runner"""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def isolated_filesystem(cli_runner):
    """Isolated filesystem for CLI tests"""
    with cli_runner.isolated_filesystem():
        yield


# Test data generators

def generate_test_records(count: int = 10) -> List[DNSRecord]:
    """Generate test DNS records"""
    records = []
    record_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT']

    for i in range(count):
        record_type = record_types[i % len(record_types)]

        if record_type == 'A':
            data = f"192.168.1.{i + 1}"
        elif record_type == 'AAAA':
            data = f"2001:db8::{i + 1:x}"
        elif record_type == 'CNAME':
            data = "www.example.com"
        elif record_type == 'MX':
            data = f"mail{i}.example.com"
        else:  # TXT
            data = f"test-record-{i}"

        record = DNSRecord(
            name=f"test{i}" if i > 0 else "@",
            type=record_type,
            data=data,
            ttl=3600,
            priority=10 if record_type == 'MX' else None
        )
        records.append(record)

    return records


def generate_test_domains(count: int = 5) -> List[Domain]:
    """Generate test domains"""
    domains = []

    for i in range(count):
        domain = Domain(
            domain=f"test{i}.com",
            status='ACTIVE',
            expires=f"202{4 + i}-12-31T23:59:59Z",
            created=f"202{3 + i}-01-01T00:00:00Z",
            privacy=i % 2 == 0,
            locked=i % 3 == 0
        )
        domains.append(domain)

    return domains


# Pytest markers for test categories

pytest_plugins = []

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require API access"
    )
    config.addinivalue_line(
        "markers", "cli: marks tests for CLI commands"
    )
    config.addinivalue_line(
        "markers", "web: marks tests for web interface"
    )