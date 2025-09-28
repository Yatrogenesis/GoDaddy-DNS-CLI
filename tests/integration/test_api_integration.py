"""
Integration tests for API client
Tests actual API interactions with proper mocking
"""

import pytest
import requests
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError, ConnectionError, Timeout

from godaddy_cli.core.api_client import APIClient, DNSRecord, Domain
from godaddy_cli.core.exceptions import (
    APIError, AuthenticationError, RecordNotFoundError,
    ValidationError, RateLimitError
)


class TestAPIIntegration:
    """Test API client integration scenarios"""

    def setup_method(self):
        """Setup for each test"""
        self.client = APIClient("test_key", "test_secret")

    def test_authentication_flow(self):
        """Test authentication scenarios"""
        # Test successful authentication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"domain": "example.com"}]

        with patch('requests.get', return_value=mock_response) as mock_get:
            domains = self.client.get_domains()
            assert len(domains) >= 0

            # Verify authentication headers were sent
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            assert 'Authorization' in headers
            assert headers['Authorization'].startswith('sso-key')

    def test_authentication_failure(self):
        """Test authentication failure scenarios"""
        # Test 401 Unauthorized
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_response.text = "Invalid API key or secret"

        with patch('requests.get', return_value=mock_response):
            with pytest.raises(AuthenticationError) as exc_info:
                self.client.get_domains()

            assert "authentication" in str(exc_info.value).lower()

    def test_rate_limiting_scenarios(self):
        """Test rate limiting handling"""
        # Test 429 Too Many Requests
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_response.headers = {'Retry-After': '60'}

        with patch('requests.get', return_value=mock_response):
            with pytest.raises(RateLimitError) as exc_info:
                self.client.get_domains()

            assert "rate limit" in str(exc_info.value).lower()

    def test_network_error_scenarios(self):
        """Test network error handling"""
        # Test connection timeout
        with patch('requests.get', side_effect=Timeout("Connection timeout")):
            with pytest.raises(APIError) as exc_info:
                self.client.get_domains()

            assert "timeout" in str(exc_info.value).lower()

        # Test connection error
        with patch('requests.get', side_effect=ConnectionError("Network unreachable")):
            with pytest.raises(APIError) as exc_info:
                self.client.get_domains()

            assert "connection" in str(exc_info.value).lower()

    def test_record_not_found_scenarios(self):
        """Test record not found handling"""
        # Test 404 for specific record
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")

        with patch('requests.get', return_value=mock_response):
            with pytest.raises(RecordNotFoundError):
                self.client.get_records("example.com", record_type="A", name="nonexistent")

    def test_validation_error_scenarios(self):
        """Test validation error handling"""
        # Test 400 Bad Request
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = HTTPError("400 Bad Request")
        mock_response.json.return_value = {
            "code": "INVALID_BODY",
            "message": "Invalid TTL value"
        }

        record = DNSRecord(
            name="test",
            type="A",
            data="192.168.1.1",
            ttl=-1  # Invalid TTL
        )

        with patch('requests.patch', return_value=mock_response):
            with pytest.raises(ValidationError) as exc_info:
                self.client.update_record("example.com", record)

            assert "ttl" in str(exc_info.value).lower()

    def test_domain_operations_flow(self):
        """Test complete domain operations workflow"""
        # Mock domain list response
        mock_domains_response = MagicMock()
        mock_domains_response.status_code = 200
        mock_domains_response.json.return_value = [
            {
                "domain": "example.com",
                "status": "ACTIVE",
                "expires": "2024-12-31T23:59:59Z",
                "privacy": True,
                "locked": False
            },
            {
                "domain": "test.org",
                "status": "ACTIVE",
                "expires": "2025-06-15T23:59:59Z",
                "privacy": False,
                "locked": True
            }
        ]

        with patch('requests.get', return_value=mock_domains_response) as mock_get:
            domains = self.client.get_domains()

            assert len(domains) == 2
            assert domains[0].domain == "example.com"
            assert domains[0].status == "ACTIVE"
            assert domains[1].privacy is False
            assert domains[1].locked is True

    def test_dns_records_flow(self):
        """Test complete DNS records workflow"""
        # Mock records list response
        mock_records_response = MagicMock()
        mock_records_response.status_code = 200
        mock_records_response.json.return_value = [
            {
                "name": "@",
                "type": "A",
                "data": "192.168.1.1",
                "ttl": 3600,
                "priority": 0,
                "weight": 0,
                "port": 0
            },
            {
                "name": "www",
                "type": "CNAME",
                "data": "example.com",
                "ttl": 3600,
                "priority": 0,
                "weight": 0,
                "port": 0
            }
        ]

        # Mock successful add response
        mock_add_response = MagicMock()
        mock_add_response.status_code = 200

        # Mock successful update response
        mock_update_response = MagicMock()
        mock_update_response.status_code = 200

        # Mock successful delete response
        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 204

        with patch('requests.get', return_value=mock_records_response):
            # Test get records
            records = self.client.get_records("example.com")
            assert len(records) == 2
            assert records[0].type == "A"
            assert records[1].type == "CNAME"

        with patch('requests.patch', return_value=mock_add_response):
            # Test add record
            new_record = DNSRecord(
                name="api",
                type="A",
                data="192.168.1.2",
                ttl=3600
            )
            result = self.client.add_record("example.com", new_record)
            assert result is True

        with patch('requests.put', return_value=mock_update_response):
            # Test update record
            updated_record = DNSRecord(
                name="api",
                type="A",
                data="192.168.1.3",
                ttl=7200
            )
            result = self.client.update_record("example.com", updated_record)
            assert result is True

        with patch('requests.delete', return_value=mock_delete_response):
            # Test delete record
            result = self.client.delete_record("example.com", "api", "A")
            assert result is True

    def test_bulk_operations_flow(self):
        """Test bulk operations with partial failures"""
        records = [
            DNSRecord("test1", "A", "192.168.1.1", 3600),
            DNSRecord("test2", "A", "192.168.1.2", 3600),
            DNSRecord("test3", "A", "invalid-ip", 3600)  # This should fail
        ]

        # Mock responses: 2 successful, 1 failure
        success_response = MagicMock()
        success_response.status_code = 200

        failure_response = MagicMock()
        failure_response.status_code = 400
        failure_response.raise_for_status.side_effect = HTTPError("400 Bad Request")

        responses = [success_response, success_response, failure_response]

        with patch('requests.patch', side_effect=responses):
            results = self.client.bulk_add_records("example.com", records)

            assert results['success'] == 2
            assert results['failed'] == 1
            assert len(results['errors']) == 1

    def test_api_response_validation(self):
        """Test API response validation"""
        # Test malformed JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch('requests.get', return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                self.client.get_domains()

            assert "json" in str(exc_info.value).lower()

    def test_request_retries(self):
        """Test request retry logic"""
        # First call fails with 500, second succeeds
        failure_response = MagicMock()
        failure_response.status_code = 500
        failure_response.raise_for_status.side_effect = HTTPError("500 Internal Server Error")

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = []

        with patch('requests.get', side_effect=[failure_response, success_response]) as mock_get:
            # Should retry and eventually succeed
            domains = self.client.get_domains()
            assert domains == []
            assert mock_get.call_count == 2

    def test_concurrent_requests_handling(self):
        """Test concurrent request scenarios"""
        import threading
        import time

        results = []
        errors = []

        def make_request():
            try:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = [{"domain": "example.com"}]

                with patch('requests.get', return_value=mock_response):
                    domains = self.client.get_domains()
                    results.append(len(domains))
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert len(results) == 5

    def test_api_versioning(self):
        """Test API versioning headers"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch('requests.get', return_value=mock_response) as mock_get:
            self.client.get_domains()

            # Verify API version header
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            assert 'Accept' in headers
            assert 'application/json' in headers['Accept']

    def test_large_response_handling(self):
        """Test handling of large API responses"""
        # Create a large mock response (1000 domains)
        large_domains = []
        for i in range(1000):
            large_domains.append({
                "domain": f"example{i}.com",
                "status": "ACTIVE",
                "expires": "2024-12-31T23:59:59Z",
                "privacy": True,
                "locked": False
            })

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = large_domains

        with patch('requests.get', return_value=mock_response):
            domains = self.client.get_domains()
            assert len(domains) == 1000
            assert all(isinstance(d, Domain) for d in domains)