"""
Simplified synchronous API client with enhanced error handling
"""

import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from godaddy_cli.core.auth import AuthManager
from godaddy_cli.core.exceptions import APIError, NetworkError, TimeoutError
from godaddy_cli.utils.error_handlers import UserFriendlyErrorHandler, create_error_context


@dataclass
class DNSRecord:
    """DNS record data structure"""
    name: str
    type: str
    data: str
    ttl: int = 3600
    priority: Optional[int] = None
    port: Optional[int] = None
    weight: Optional[int] = None

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> 'DNSRecord':
        """Create record from API response"""
        return cls(
            name=data.get('name', ''),
            type=data.get('type', ''),
            data=data.get('data', ''),
            ttl=data.get('ttl', 3600),
            priority=data.get('priority'),
            port=data.get('port'),
            weight=data.get('weight')
        )

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API format"""
        result = {
            'name': self.name,
            'type': self.type,
            'data': self.data,
            'ttl': self.ttl
        }
        if self.priority is not None:
            result['priority'] = self.priority
        if self.port is not None:
            result['port'] = self.port
        if self.weight is not None:
            result['weight'] = self.weight
        return result


@dataclass
class Domain:
    """Domain data structure"""
    domain: str
    status: str
    expires: str
    privacy: bool
    locked: bool

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> 'Domain':
        """Create domain from API response"""
        return cls(
            domain=data.get('domain', ''),
            status=data.get('status', ''),
            expires=data.get('expires', ''),
            privacy=data.get('privacy', False),
            locked=data.get('locked', False)
        )


class APIClient:
    """Enhanced synchronous GoDaddy API client"""

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.godaddy.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'sso-key {api_key}:{api_secret}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request with enhanced error handling"""
        url = f"{self.base_url}/v1{endpoint}"

        try:
            response = self.session.request(method, url, timeout=30, **kwargs)

            # Handle successful responses
            if response.status_code < 400:
                if response.content:
                    return response.json()
                return {}

            # Handle error responses with context
            context = kwargs.get('error_context', {})
            UserFriendlyErrorHandler.handle_api_response_error(response, context)

        except requests.exceptions.Timeout as e:
            raise UserFriendlyErrorHandler.handle_network_error(e, "API request")
        except requests.exceptions.ConnectionError as e:
            raise UserFriendlyErrorHandler.handle_network_error(e, "API request")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {str(e)}")
        except ValueError as e:
            raise APIError(f"Invalid JSON response: {str(e)}")

    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            self._request('GET', '/domains', error_context=create_error_context('test_connection'))
            return True
        except Exception:
            return False

    def get_domains(self) -> List[Domain]:
        """Get all domains"""
        context = create_error_context('get_domains')
        response = self._request('GET', '/domains', error_context=context)
        return [Domain.from_api_dict(domain_data) for domain_data in response]

    def get_domain(self, domain: str) -> Domain:
        """Get specific domain information"""
        context = create_error_context('get_domain', domain=domain)
        response = self._request('GET', f'/domains/{domain}', error_context=context)
        return Domain.from_api_dict(response)

    def get_records(self, domain: str, record_type: str = None, name: str = None) -> List[DNSRecord]:
        """Get DNS records for domain"""
        endpoint = f'/domains/{domain}/records'

        if record_type:
            endpoint += f'/{record_type.upper()}'
        if name:
            endpoint += f'/{name}'

        context = create_error_context('get_records', domain=domain, record_type=record_type, record_name=name)
        response = self._request('GET', endpoint, error_context=context)
        return [DNSRecord.from_api_dict(record) for record in response]

    def add_record(self, domain: str, record: DNSRecord) -> bool:
        """Add DNS record"""
        context = create_error_context('add_record', domain=domain, record_type=record.type, record_name=record.name)

        try:
            self._request(
                'PATCH',
                f'/domains/{domain}/records',
                json=[record.to_api_dict()],
                error_context=context
            )
            return True
        except Exception:
            return False

    def update_record(self, domain: str, record: DNSRecord) -> bool:
        """Update DNS record"""
        context = create_error_context('update_record', domain=domain, record_type=record.type, record_name=record.name)

        try:
            self._request(
                'PUT',
                f'/domains/{domain}/records/{record.type.upper()}/{record.name}',
                json=[record.to_api_dict()],
                error_context=context
            )
            return True
        except Exception:
            return False

    def delete_record(self, domain: str, record_type: str, name: str) -> bool:
        """Delete DNS record"""
        context = create_error_context('delete_record', domain=domain, record_type=record_type, record_name=name)

        try:
            self._request(
                'DELETE',
                f'/domains/{domain}/records/{record_type.upper()}/{name}',
                error_context=context
            )
            return True
        except Exception:
            return False

    def bulk_add_records(self, domain: str, records: List[DNSRecord]) -> Dict[str, Any]:
        """Add multiple DNS records"""
        context = create_error_context('bulk_add_records', domain=domain)
        results = {'success': 0, 'failed': 0, 'errors': []}

        for record in records:
            try:
                record_context = create_error_context(
                    'add_record',
                    domain=domain,
                    record_type=record.type,
                    record_name=record.name
                )

                self._request(
                    'PATCH',
                    f'/domains/{domain}/records',
                    json=[record.to_api_dict()],
                    error_context=record_context
                )
                results['success'] += 1

            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{record.name} ({record.type}): {str(e)}")

        return results

    def bulk_update_records(self, domain: str, records: List[DNSRecord]) -> Dict[str, Any]:
        """Update multiple DNS records"""
        results = {'success': 0, 'failed': 0, 'errors': []}

        for record in records:
            try:
                if self.update_record(domain, record):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{record.name} ({record.type}): Update failed")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{record.name} ({record.type}): {str(e)}")

        return results

    def validate_records(self, records: List[DNSRecord]) -> Dict[str, Any]:
        """Validate DNS records before submission"""
        results = {}

        for record in records:
            record_key = f"{record.name}.{record.type}"
            validation_result = {'valid': True, 'errors': []}

            # Validate TTL
            if record.ttl < 300 or record.ttl > 604800:
                validation_result['valid'] = False
                validation_result['errors'].append("TTL must be between 300 and 604800 seconds")

            # Validate record type specific data
            if record.type == 'A':
                if not self._is_valid_ipv4(record.data):
                    validation_result['valid'] = False
                    validation_result['errors'].append("Invalid IPv4 address format")

            elif record.type == 'AAAA':
                if not self._is_valid_ipv6(record.data):
                    validation_result['valid'] = False
                    validation_result['errors'].append("Invalid IPv6 address format")

            elif record.type == 'MX':
                if record.priority is None:
                    validation_result['valid'] = False
                    validation_result['errors'].append("MX records require a priority value")

            # Validate name format
            if not self._is_valid_record_name(record.name):
                validation_result['valid'] = False
                validation_result['errors'].append("Invalid record name format")

            validation_result['message'] = '; '.join(validation_result['errors']) if validation_result['errors'] else 'Valid'
            results[record_key] = validation_result

        return results

    def _is_valid_ipv4(self, ip: str) -> bool:
        """Validate IPv4 address"""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, AttributeError):
            return False

    def _is_valid_ipv6(self, ip: str) -> bool:
        """Validate IPv6 address"""
        try:
            import ipaddress
            ipaddress.IPv6Address(ip)
            return True
        except ValueError:
            return False

    def _is_valid_record_name(self, name: str) -> bool:
        """Validate DNS record name"""
        if not name or len(name) > 253:
            return False

        if name == '@':  # Root domain
            return True

        # Check for valid characters and format
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, name))

    def close(self):
        """Close the session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()