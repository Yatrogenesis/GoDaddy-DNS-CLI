"""
GoDaddy API Client
High-performance, rate-limited client for GoDaddy DNS API
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from godaddy_cli.core.auth import AuthManager, APICredentials
from godaddy_cli.utils.error_handlers import UserFriendlyErrorHandler, create_error_context

console = Console()
logger = logging.getLogger(__name__)

class RecordType(Enum):
    """DNS record types supported by GoDaddy"""
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    SRV = "SRV"
    NS = "NS"
    PTR = "PTR"
    CAA = "CAA"

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
    service: Optional[str] = None
    protocol: Optional[str] = None

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to GoDaddy API format"""
        result = {
            'name': self.name,
            'type': self.type,
            'data': self.data,
            'ttl': self.ttl
        }

        # Add optional fields for specific record types
        if self.type == 'MX' and self.priority is not None:
            result['priority'] = self.priority
        elif self.type == 'SRV':
            if self.priority is not None:
                result['priority'] = self.priority
            if self.weight is not None:
                result['weight'] = self.weight
            if self.port is not None:
                result['port'] = self.port

        return result

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> 'DNSRecord':
        """Create from GoDaddy API response"""
        return cls(
            name=data['name'],
            type=data['type'],
            data=data['data'],
            ttl=data.get('ttl', 3600),
            priority=data.get('priority'),
            port=data.get('port'),
            weight=data.get('weight')
        )

@dataclass
class Domain:
    """Domain information"""
    domain: str
    status: str
    expires: Optional[str] = None
    created: Optional[str] = None
    nameservers: Optional[List[str]] = None
    privacy: bool = False
    locked: bool = False

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> 'Domain':
        """Create from GoDaddy API response"""
        return cls(
            domain=data['domain'],
            status=data.get('status', 'UNKNOWN'),
            expires=data.get('expires'),
            created=data.get('createdAt'),
            nameservers=data.get('nameServers'),
            privacy=data.get('privacy', False),
            locked=data.get('locked', False)
        )

class RateLimiter:
    """Rate limiter for API requests"""

    def __init__(self, max_requests: int = 60, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire rate limit token"""
        async with self._lock:
            now = time.time()

            # Remove old requests outside the window
            self.requests = [req_time for req_time in self.requests
                           if now - req_time < self.window]

            # Check if we can make a request
            if len(self.requests) >= self.max_requests:
                sleep_time = self.window - (now - self.requests[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()

            # Record this request
            self.requests.append(now)

class GoDaddyAPIClient:
    """High-performance async client for GoDaddy DNS API"""

    def __init__(self, auth_manager: AuthManager, profile: Optional[str] = None):
        self.auth_manager = auth_manager
        self.profile = profile
        self.credentials = auth_manager.get_credentials(profile)
        self.rate_limiter = RateLimiter()
        self._session: Optional[aiohttp.ClientSession] = None

        if not self.credentials:
            raise ValueError("No API credentials configured")

    async def __aenter__(self):
        """Async context manager entry"""
        self._session = aiohttp.ClientSession(
            headers={
                'Authorization': self.credentials.auth_header,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()

    async def _request(self, method: str, endpoint: str,
                      params: Optional[Dict] = None,
                      json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make rate-limited API request"""
        await self.rate_limiter.acquire()

        url = f"{self.credentials.base_url}/v1{endpoint}"

        try:
            async with self._session.request(
                method, url, params=params, json=json_data
            ) as response:
                response_data = await response.json()

                if response.status >= 400:
                    error_msg = response_data.get('message', f'API error: {response.status}')
                    raise APIError(error_msg, response.status, response_data)

                return response_data

        except aiohttp.ClientError as e:
            raise APIError(f"Network error: {str(e)}", 0)

    # Domain operations
    async def list_domains(self) -> List[Domain]:
        """List all domains"""
        response = await self._request('GET', '/domains')
        return [Domain.from_api_dict(domain_data) for domain_data in response]

    async def get_domain(self, domain: str) -> Domain:
        """Get domain details"""
        response = await self._request('GET', f'/domains/{domain}')
        return Domain.from_api_dict(response)

    async def check_domain_availability(self, domain: str) -> Dict[str, Any]:
        """Check if domain is available for purchase"""
        response = await self._request('GET', f'/domains/available',
                                     params={'domain': domain})
        return response

    # DNS record operations
    async def list_dns_records(self, domain: str,
                              record_type: Optional[str] = None,
                              name: Optional[str] = None) -> List[DNSRecord]:
        """List DNS records for domain"""
        endpoint = f'/domains/{domain}/records'

        params = {}
        if record_type:
            endpoint += f'/{record_type.upper()}'
        if name:
            endpoint += f'/{name}'

        response = await self._request('GET', endpoint, params=params)
        return [DNSRecord.from_api_dict(record) for record in response]

    async def get_dns_record(self, domain: str, record_type: str, name: str) -> List[DNSRecord]:
        """Get specific DNS record"""
        response = await self._request('GET',
                                     f'/domains/{domain}/records/{record_type.upper()}/{name}')
        return [DNSRecord.from_api_dict(record) for record in response]

    async def create_dns_record(self, domain: str, record: DNSRecord) -> bool:
        """Create new DNS record"""
        try:
            await self._request('PATCH', f'/domains/{domain}/records',
                              json_data=[record.to_api_dict()])
            return True
        except APIError:
            return False

    async def update_dns_record(self, domain: str, record: DNSRecord) -> bool:
        """Update existing DNS record"""
        try:
            await self._request('PUT',
                              f'/domains/{domain}/records/{record.type.upper()}/{record.name}',
                              json_data=[record.to_api_dict()])
            return True
        except APIError:
            return False

    async def delete_dns_record(self, domain: str, record_type: str, name: str) -> bool:
        """Delete DNS record"""
        try:
            await self._request('DELETE',
                              f'/domains/{domain}/records/{record_type.upper()}/{name}')
            return True
        except APIError:
            return False

    async def replace_all_records(self, domain: str, records: List[DNSRecord]) -> bool:
        """Replace all DNS records for domain"""
        try:
            records_data = [record.to_api_dict() for record in records]
            await self._request('PUT', f'/domains/{domain}/records',
                              json_data=records_data)
            return True
        except APIError:
            return False

    async def bulk_update_records(self, domain: str, records: List[DNSRecord],
                                 batch_size: int = 50) -> Dict[str, Any]:
        """Bulk update DNS records with batching"""
        results = {'success': 0, 'failed': 0, 'errors': []}

        # Process in batches
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            try:
                records_data = [record.to_api_dict() for record in batch]
                await self._request('PATCH', f'/domains/{domain}/records',
                                  json_data=records_data)
                results['success'] += len(batch)
            except APIError as e:
                results['failed'] += len(batch)
                results['errors'].append(f"Batch {i//batch_size + 1}: {str(e)}")

        return results

    # Convenience methods
    async def add_a_record(self, domain: str, name: str, ip: str, ttl: int = 3600) -> bool:
        """Add A record"""
        record = DNSRecord(name=name, type='A', data=ip, ttl=ttl)
        return await self.create_dns_record(domain, record)

    async def add_cname_record(self, domain: str, name: str, target: str, ttl: int = 3600) -> bool:
        """Add CNAME record"""
        record = DNSRecord(name=name, type='CNAME', data=target, ttl=ttl)
        return await self.create_dns_record(domain, record)

    async def add_mx_record(self, domain: str, name: str, mail_server: str,
                           priority: int = 10, ttl: int = 3600) -> bool:
        """Add MX record"""
        record = DNSRecord(name=name, type='MX', data=mail_server,
                          priority=priority, ttl=ttl)
        return await self.create_dns_record(domain, record)

    async def add_txt_record(self, domain: str, name: str, content: str, ttl: int = 3600) -> bool:
        """Add TXT record"""
        record = DNSRecord(name=name, type='TXT', data=content, ttl=ttl)
        return await self.create_dns_record(domain, record)

    # Batch operations with progress
    async def batch_operation(self, operations: List[Dict[str, Any]],
                            progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """Execute batch operations with progress tracking"""
        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing operations...", total=len(operations))

            for i, operation in enumerate(operations):
                try:
                    method = operation['method']
                    args = operation.get('args', [])
                    kwargs = operation.get('kwargs', {})

                    # Execute operation
                    if hasattr(self, method):
                        result = await getattr(self, method)(*args, **kwargs)
                        results.append({'success': True, 'result': result})
                    else:
                        results.append({'success': False, 'error': f'Unknown method: {method}'})

                except Exception as e:
                    results.append({'success': False, 'error': str(e)})

                progress.update(task, advance=1)

                if progress_callback:
                    progress_callback(i + 1, len(operations))

        return results

class APIError(Exception):
    """GoDaddy API error"""

    def __init__(self, message: str, status_code: int, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}

    def __str__(self):
        return f"API Error ({self.status_code}): {self.message}"

# Synchronous wrapper for backward compatibility
class SyncGoDaddyAPIClient:
    """Synchronous wrapper for GoDaddyAPIClient"""

    def __init__(self, auth_manager: AuthManager, profile: Optional[str] = None):
        self.auth_manager = auth_manager
        self.profile = profile

    def _run_async(self, coro):
        """Run async coroutine in sync context"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    async def _execute_with_client(self, func, *args, **kwargs):
        """Execute function with async client"""
        async with GoDaddyAPIClient(self.auth_manager, self.profile) as client:
            return await func(client, *args, **kwargs)

    def list_domains(self) -> List[Domain]:
        """List all domains"""
        return self._run_async(
            self._execute_with_client(lambda client: client.list_domains())
        )

    def list_dns_records(self, domain: str, record_type: Optional[str] = None) -> List[DNSRecord]:
        """List DNS records"""
        return self._run_async(
            self._execute_with_client(
                lambda client: client.list_dns_records(domain, record_type)
            )
        )

    def create_dns_record(self, domain: str, record: DNSRecord) -> bool:
        """Create DNS record"""
        return self._run_async(
            self._execute_with_client(
                lambda client: client.create_dns_record(domain, record)
            )
        )