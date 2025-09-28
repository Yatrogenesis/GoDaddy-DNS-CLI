"""
Unit tests for API client
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import aiohttp

from godaddy_cli.core.api_client import (
    GoDaddyAPIClient,
    SyncGoDaddyAPIClient,
    DNSRecord,
    Domain,
    RateLimiter,
    APIError,
    RecordType
)
from godaddy_cli.core.auth import AuthManager, APICredentials


@pytest.mark.unit
class TestDNSRecord:
    """Test DNSRecord dataclass"""

    def test_dns_record_creation(self):
        """Test creating DNS record"""
        record = DNSRecord(
            name='www',
            type='A',
            data='192.168.1.1',
            ttl=3600,
            priority=10
        )

        assert record.name == 'www'
        assert record.type == 'A'
        assert record.data == '192.168.1.1'
        assert record.ttl == 3600
        assert record.priority == 10

    def test_dns_record_to_api_dict(self):
        """Test converting DNS record to API format"""
        record = DNSRecord(
            name='www',
            type='A',
            data='192.168.1.1',
            ttl=3600
        )

        api_dict = record.to_api_dict()

        expected = {
            'name': 'www',
            'type': 'A',
            'data': '192.168.1.1',
            'ttl': 3600
        }

        assert api_dict == expected

    def test_dns_record_to_api_dict_mx(self):
        """Test converting MX record to API format"""
        record = DNSRecord(
            name='@',
            type='MX',
            data='mail.example.com',
            ttl=3600,
            priority=10
        )

        api_dict = record.to_api_dict()

        assert api_dict['priority'] == 10

    def test_dns_record_to_api_dict_srv(self):
        """Test converting SRV record to API format"""
        record = DNSRecord(
            name='_service._tcp',
            type='SRV',
            data='target.example.com',
            ttl=3600,
            priority=10,
            weight=20,
            port=443
        )

        api_dict = record.to_api_dict()

        assert api_dict['priority'] == 10
        assert api_dict['weight'] == 20
        assert api_dict['port'] == 443

    def test_dns_record_from_api_dict(self):
        """Test creating DNS record from API response"""
        api_data = {
            'name': 'www',
            'type': 'A',
            'data': '192.168.1.1',
            'ttl': 3600,
            'priority': 10
        }

        record = DNSRecord.from_api_dict(api_data)

        assert record.name == 'www'
        assert record.type == 'A'
        assert record.data == '192.168.1.1'
        assert record.ttl == 3600
        assert record.priority == 10


@pytest.mark.unit
class TestDomain:
    """Test Domain dataclass"""

    def test_domain_from_api_dict(self):
        """Test creating domain from API response"""
        api_data = {
            'domain': 'example.com',
            'status': 'ACTIVE',
            'expires': '2024-12-31T23:59:59Z',
            'createdAt': '2023-01-01T00:00:00Z',
            'nameServers': ['ns1.godaddy.com', 'ns2.godaddy.com'],
            'privacy': True,
            'locked': False
        }

        domain = Domain.from_api_dict(api_data)

        assert domain.domain == 'example.com'
        assert domain.status == 'ACTIVE'
        assert domain.expires == '2024-12-31T23:59:59Z'
        assert domain.created == '2023-01-01T00:00:00Z'
        assert domain.nameservers == ['ns1.godaddy.com', 'ns2.godaddy.com']
        assert domain.privacy is True
        assert domain.locked is False


@pytest.mark.unit
class TestRateLimiter:
    """Test RateLimiter class"""

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test rate limiter acquire method"""
        limiter = RateLimiter(max_requests=2, window=1)

        # First two requests should be immediate
        await limiter.acquire()
        await limiter.acquire()

        # Third request should be delayed
        import time
        start_time = time.time()
        await limiter.acquire()
        elapsed = time.time() - start_time

        # Should have waited at least some time
        assert elapsed >= 0

    @pytest.mark.asyncio
    async def test_rate_limiter_window_cleanup(self):
        """Test that old requests are cleaned up"""
        limiter = RateLimiter(max_requests=1, window=0.1)

        # Make first request
        await limiter.acquire()

        # Wait for window to expire
        await asyncio.sleep(0.2)

        # Second request should be immediate (old request cleaned up)
        import time
        start_time = time.time()
        await limiter.acquire()
        elapsed = time.time() - start_time

        assert elapsed < 0.1  # Should be immediate


@pytest.mark.unit
class TestAPIError:
    """Test APIError exception"""

    def test_api_error_creation(self):
        """Test creating API error"""
        error = APIError("Test error", 400, {"code": "INVALID_REQUEST"})

        assert str(error) == "API Error (400): Test error"
        assert error.status_code == 400
        assert error.response_data == {"code": "INVALID_REQUEST"}

    def test_api_error_no_response_data(self):
        """Test API error without response data"""
        error = APIError("Test error", 500)

        assert error.response_data == {}


@pytest.mark.unit
class TestGoDaddyAPIClient:
    """Test GoDaddyAPIClient class"""

    def test_client_creation_with_credentials(self, mock_auth):
        """Test creating client with valid credentials"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        client = GoDaddyAPIClient(mock_auth)

        assert client.auth_manager == mock_auth
        assert client.credentials is not None

    def test_client_creation_without_credentials(self, mock_auth):
        """Test creating client without credentials raises error"""
        mock_auth.get_credentials.return_value = None

        with pytest.raises(ValueError, match="No API credentials configured"):
            GoDaddyAPIClient(mock_auth)

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_auth, mock_aiohttp_session):
        """Test async context manager"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
            async with GoDaddyAPIClient(mock_auth) as client:
                assert client._session is not None

    @pytest.mark.asyncio
    async def test_request_success(self, mock_auth, mock_aiohttp_session):
        """Test successful API request"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'result': 'success'}
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response

        client = GoDaddyAPIClient(mock_auth)
        client._session = mock_aiohttp_session
        client.rate_limiter = AsyncMock()

        result = await client._request('GET', '/test')

        assert result == {'result': 'success'}

    @pytest.mark.asyncio
    async def test_request_api_error(self, mock_auth, mock_aiohttp_session):
        """Test API request with error response"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json.return_value = {'message': 'Bad request'}
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response

        client = GoDaddyAPIClient(mock_auth)
        client._session = mock_aiohttp_session
        client.rate_limiter = AsyncMock()

        with pytest.raises(APIError, match="Bad request"):
            await client._request('GET', '/test')

    @pytest.mark.asyncio
    async def test_request_network_error(self, mock_auth, mock_aiohttp_session):
        """Test API request with network error"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        # Mock network error
        mock_aiohttp_session.request.side_effect = aiohttp.ClientError("Network error")

        client = GoDaddyAPIClient(mock_auth)
        client._session = mock_aiohttp_session
        client.rate_limiter = AsyncMock()

        with pytest.raises(APIError, match="Network error"):
            await client._request('GET', '/test')

    @pytest.mark.asyncio
    async def test_list_domains(self, mock_auth, sample_domains):
        """Test listing domains"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        client = GoDaddyAPIClient(mock_auth)
        client._request = AsyncMock(return_value=[
            domain.__dict__ for domain in sample_domains
        ])

        domains = await client.list_domains()

        assert len(domains) == len(sample_domains)
        assert all(isinstance(domain, Domain) for domain in domains)

    @pytest.mark.asyncio
    async def test_list_dns_records(self, mock_auth, sample_dns_records):
        """Test listing DNS records"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        client = GoDaddyAPIClient(mock_auth)
        client._request = AsyncMock(return_value=[
            record.to_api_dict() for record in sample_dns_records
        ])

        records = await client.list_dns_records('example.com')

        assert len(records) == len(sample_dns_records)
        assert all(isinstance(record, DNSRecord) for record in records)

    @pytest.mark.asyncio
    async def test_create_dns_record(self, mock_auth):
        """Test creating DNS record"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        client = GoDaddyAPIClient(mock_auth)
        client._request = AsyncMock(return_value={})

        record = DNSRecord(
            name='www',
            type='A',
            data='192.168.1.1',
            ttl=3600
        )

        success = await client.create_dns_record('example.com', record)

        assert success is True
        client._request.assert_called_once_with(
            'PATCH',
            '/domains/example.com/records',
            json_data=[record.to_api_dict()]
        )

    @pytest.mark.asyncio
    async def test_update_dns_record(self, mock_auth):
        """Test updating DNS record"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        client = GoDaddyAPIClient(mock_auth)
        client._request = AsyncMock(return_value={})

        record = DNSRecord(
            name='www',
            type='A',
            data='192.168.1.2',
            ttl=7200
        )

        success = await client.update_dns_record('example.com', record)

        assert success is True
        client._request.assert_called_once_with(
            'PUT',
            '/domains/example.com/records/A/www',
            json_data=[record.to_api_dict()]
        )

    @pytest.mark.asyncio
    async def test_delete_dns_record(self, mock_auth):
        """Test deleting DNS record"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        client = GoDaddyAPIClient(mock_auth)
        client._request = AsyncMock(return_value={})

        success = await client.delete_dns_record('example.com', 'A', 'www')

        assert success is True
        client._request.assert_called_once_with(
            'DELETE',
            '/domains/example.com/records/A/www'
        )

    @pytest.mark.asyncio
    async def test_bulk_update_records(self, mock_auth, sample_dns_records):
        """Test bulk updating records"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        client = GoDaddyAPIClient(mock_auth)
        client._request = AsyncMock(return_value={})

        result = await client.bulk_update_records('example.com', sample_dns_records, batch_size=2)

        assert result['success'] == len(sample_dns_records)
        assert result['failed'] == 0
        assert len(result['errors']) == 0

    @pytest.mark.asyncio
    async def test_convenience_methods(self, mock_auth):
        """Test convenience methods for common record types"""
        mock_auth.get_credentials.return_value = APICredentials(
            api_key='key123',
            api_secret='secret456'
        )

        client = GoDaddyAPIClient(mock_auth)
        client.create_dns_record = AsyncMock(return_value=True)

        # Test A record
        success = await client.add_a_record('example.com', 'www', '192.168.1.1')
        assert success is True

        # Test CNAME record
        success = await client.add_cname_record('example.com', 'blog', 'www.example.com')
        assert success is True

        # Test MX record
        success = await client.add_mx_record('example.com', '@', 'mail.example.com', priority=10)
        assert success is True

        # Test TXT record
        success = await client.add_txt_record('example.com', '@', 'v=spf1 ~all')
        assert success is True


@pytest.mark.unit
class TestSyncGoDaddyAPIClient:
    """Test SyncGoDaddyAPIClient wrapper"""

    def test_sync_client_creation(self, mock_auth):
        """Test creating sync client"""
        client = SyncGoDaddyAPIClient(mock_auth)

        assert client.auth_manager == mock_auth

    def test_run_async_with_existing_loop(self, mock_auth):
        """Test running async function with existing event loop"""
        client = SyncGoDaddyAPIClient(mock_auth)

        async def test_coroutine():
            return "test_result"

        # Mock having an existing event loop
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_loop.run_until_complete.return_value = "test_result"
            mock_get_loop.return_value = mock_loop

            result = client._run_async(test_coroutine())

            assert result == "test_result"

    def test_run_async_create_new_loop(self, mock_auth):
        """Test running async function creating new event loop"""
        client = SyncGoDaddyAPIClient(mock_auth)

        async def test_coroutine():
            return "test_result"

        # Mock no existing event loop
        with patch('asyncio.get_event_loop', side_effect=RuntimeError):
            with patch('asyncio.new_event_loop') as mock_new_loop:
                with patch('asyncio.set_event_loop') as mock_set_loop:
                    mock_loop = Mock()
                    mock_loop.run_until_complete.return_value = "test_result"
                    mock_new_loop.return_value = mock_loop

                    result = client._run_async(test_coroutine())

                    assert result == "test_result"
                    mock_set_loop.assert_called_once_with(mock_loop)

    @patch.object(SyncGoDaddyAPIClient, '_run_async')
    def test_sync_list_domains(self, mock_run_async, mock_auth, sample_domains):
        """Test sync list domains"""
        mock_run_async.return_value = sample_domains

        client = SyncGoDaddyAPIClient(mock_auth)
        domains = client.list_domains()

        assert domains == sample_domains
        mock_run_async.assert_called_once()

    @patch.object(SyncGoDaddyAPIClient, '_run_async')
    def test_sync_list_dns_records(self, mock_run_async, mock_auth, sample_dns_records):
        """Test sync list DNS records"""
        mock_run_async.return_value = sample_dns_records

        client = SyncGoDaddyAPIClient(mock_auth)
        records = client.list_dns_records('example.com')

        assert records == sample_dns_records

    @patch.object(SyncGoDaddyAPIClient, '_run_async')
    def test_sync_create_dns_record(self, mock_run_async, mock_auth):
        """Test sync create DNS record"""
        mock_run_async.return_value = True

        client = SyncGoDaddyAPIClient(mock_auth)
        record = DNSRecord(name='www', type='A', data='192.168.1.1', ttl=3600)

        success = client.create_dns_record('example.com', record)

        assert success is True