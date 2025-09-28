# API Reference

Complete reference for the GoDaddy DNS CLI Python API and REST API.

## Python API

### Core Client

#### GoDaddyAPIClient (Async)

```python
from godaddy_cli.core.api_client import GoDaddyAPIClient
from godaddy_cli.core.auth import AuthManager

# Initialize
auth = AuthManager()
client = GoDaddyAPIClient(auth)

# Use as async context manager
async with client as api:
    domains = await api.list_domains()
    records = await api.list_dns_records('example.com')
```

**Methods:**

- `list_domains() -> List[Domain]`
- `get_domain(domain: str) -> Domain`
- `list_dns_records(domain: str, record_type: str = None, name: str = None) -> List[DNSRecord]`
- `create_dns_record(domain: str, record: DNSRecord) -> bool`
- `update_dns_record(domain: str, record: DNSRecord) -> bool`
- `delete_dns_record(domain: str, record_type: str, name: str) -> bool`
- `bulk_update_records(domain: str, records: List[DNSRecord], batch_size: int = 10) -> Dict`

#### SyncGoDaddyAPIClient (Synchronous)

```python
from godaddy_cli.core.api_client import SyncGoDaddyAPIClient

# Initialize
client = SyncGoDaddyAPIClient(auth)

# Use directly (no async/await needed)
domains = client.list_domains()
records = client.list_dns_records('example.com')
```

### Data Models

#### DNSRecord

```python
from godaddy_cli.core.api_client import DNSRecord, RecordType

# Create A record
record = DNSRecord(
    name='www',
    type=RecordType.A,
    data='192.168.1.1',
    ttl=3600
)

# Create MX record
mx_record = DNSRecord(
    name='@',
    type=RecordType.MX,
    data='mail.example.com',
    ttl=3600,
    priority=10
)

# Create SRV record
srv_record = DNSRecord(
    name='_service._tcp',
    type=RecordType.SRV,
    data='target.example.com',
    ttl=3600,
    priority=10,
    weight=20,
    port=443
)
```

**Properties:**
- `name: str` - Record name
- `type: str` - Record type (A, AAAA, CNAME, MX, TXT, SRV, NS, PTR)
- `data: str` - Record data/value
- `ttl: int` - Time to live in seconds
- `priority: Optional[int]` - Priority (MX, SRV records)
- `weight: Optional[int]` - Weight (SRV records)
- `port: Optional[int]` - Port (SRV records)

**Methods:**
- `to_api_dict() -> Dict` - Convert to API format
- `from_api_dict(data: Dict) -> DNSRecord` - Create from API response
- `validate() -> bool` - Validate record data

#### Domain

```python
from godaddy_cli.core.api_client import Domain

# Domain properties
domain = Domain(
    domain='example.com',
    status='ACTIVE',
    expires='2024-12-31T23:59:59Z',
    created='2023-01-01T00:00:00Z',
    nameservers=['ns1.godaddy.com', 'ns2.godaddy.com'],
    privacy=True,
    locked=False
)
```

**Properties:**
- `domain: str` - Domain name
- `status: str` - Domain status
- `expires: str` - Expiration date
- `created: str` - Creation date
- `nameservers: List[str]` - Name servers
- `privacy: bool` - Privacy protection status
- `locked: bool` - Domain lock status

### Authentication

#### AuthManager

```python
from godaddy_cli.core.auth import AuthManager, APICredentials

# Initialize
auth = AuthManager()

# Set credentials
credentials = APICredentials(
    api_key='your-api-key',
    api_secret='your-api-secret'
)
auth.set_credentials(credentials)

# Get credentials
creds = auth.get_credentials()

# Test authentication
is_valid = auth.test_credentials()
```

### Configuration

#### ConfigManager

```python
from godaddy_cli.core.config import ConfigManager

# Initialize
config = ConfigManager()

# Get configuration
profile_config = config.get_profile('production')
global_config = config.get_global_config()

# Set configuration
config.set_profile_setting('production', 'default_ttl', 7200)
config.set_global_setting('log_level', 'DEBUG')

# Save configuration
config.save()
```

### Convenience Methods

#### Quick DNS Operations

```python
# Add common record types
await client.add_a_record('example.com', 'www', '192.168.1.1')
await client.add_cname_record('example.com', 'blog', 'www.example.com')
await client.add_mx_record('example.com', '@', 'mail.example.com', priority=10)
await client.add_txt_record('example.com', '@', 'v=spf1 ~all')

# Bulk operations
results = await client.bulk_update_records('example.com', records, batch_size=5)
print(f"Success: {results['success']}, Failed: {results['failed']}")
```

### Error Handling

```python
from godaddy_cli.core.exceptions import APIError, ValidationError, AuthenticationError

try:
    records = await client.list_dns_records('example.com')
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except APIError as e:
    print(f"API error ({e.status_code}): {e.message}")
    print(f"Response data: {e.response_data}")
except ValidationError as e:
    print(f"Validation error: {e}")
```

## REST API

The web UI backend provides a REST API for integration.

### Starting the Server

```bash
# Start server
godaddy web --port 8080 --host 0.0.0.0

# With custom configuration
godaddy web --config /path/to/config.yaml --profile production
```

### Authentication

All API endpoints require authentication via API key header:

```bash
curl -H "X-API-Key: your-api-key" \
     -H "X-API-Secret: your-api-secret" \
     http://localhost:8080/api/domains
```

### Endpoints

#### Domains

**GET /api/domains**
List all domains

```bash
curl http://localhost:8080/api/domains
```

Response:
```json
{
  "domains": [
    {
      "domain": "example.com",
      "status": "ACTIVE",
      "expires": "2024-12-31T23:59:59Z",
      "nameservers": ["ns1.godaddy.com", "ns2.godaddy.com"]
    }
  ]
}
```

**GET /api/domains/{domain}**
Get domain details

```bash
curl http://localhost:8080/api/domains/example.com
```

#### DNS Records

**GET /api/domains/{domain}/records**
List DNS records

Query parameters:
- `type`: Filter by record type
- `name`: Filter by record name

```bash
curl "http://localhost:8080/api/domains/example.com/records?type=A"
```

Response:
```json
{
  "records": [
    {
      "name": "www",
      "type": "A",
      "data": "192.168.1.1",
      "ttl": 3600
    }
  ]
}
```

**POST /api/domains/{domain}/records**
Create DNS record

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{
       "name": "api",
       "type": "A",
       "data": "192.168.1.2",
       "ttl": 3600
     }' \
     http://localhost:8080/api/domains/example.com/records
```

**PUT /api/domains/{domain}/records/{type}/{name}**
Update DNS record

```bash
curl -X PUT \
     -H "Content-Type: application/json" \
     -d '{
       "data": "192.168.1.3",
       "ttl": 7200
     }' \
     http://localhost:8080/api/domains/example.com/records/A/api
```

**DELETE /api/domains/{domain}/records/{type}/{name}**
Delete DNS record

```bash
curl -X DELETE \
     http://localhost:8080/api/domains/example.com/records/A/api
```

#### Bulk Operations

**POST /api/domains/{domain}/records/bulk**
Bulk update records

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{
       "records": [
         {
           "name": "api",
           "type": "A",
           "data": "192.168.1.2",
           "ttl": 3600
         },
         {
           "name": "app",
           "type": "A",
           "data": "192.168.1.3",
           "ttl": 3600
         }
       ],
       "batch_size": 5
     }' \
     http://localhost:8080/api/domains/example.com/records/bulk
```

Response:
```json
{
  "success": 2,
  "failed": 0,
  "errors": [],
  "results": [
    {"record": "api.example.com", "status": "success"},
    {"record": "app.example.com", "status": "success"}
  ]
}
```

#### Templates

**GET /api/templates**
List templates

**GET /api/templates/{template_id}**
Get template details

**POST /api/templates**
Create template

**POST /api/domains/{domain}/templates/{template_id}/apply**
Apply template to domain

#### Monitoring

**GET /api/domains/{domain}/monitoring**
Get monitoring status

**POST /api/domains/{domain}/monitoring**
Start monitoring

**DELETE /api/domains/{domain}/monitoring**
Stop monitoring

### WebSocket API

Real-time updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Real-time update:', data);
};

// Subscribe to domain events
ws.send(JSON.stringify({
    action: 'subscribe',
    domain: 'example.com'
}));
```

Events:
- `record_created`
- `record_updated`
- `record_deleted`
- `monitoring_alert`
- `bulk_operation_progress`

### Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid record type",
    "details": {
      "field": "type",
      "value": "INVALID"
    }
  }
}
```

Common error codes:
- `AUTHENTICATION_ERROR` (401)
- `AUTHORIZATION_ERROR` (403)
- `VALIDATION_ERROR` (400)
- `NOT_FOUND` (404)
- `RATE_LIMIT_EXCEEDED` (429)
- `API_ERROR` (500)

### Rate Limiting

API endpoints are rate limited:

Response headers:
- `X-RateLimit-Limit`: Requests per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset time (Unix timestamp)

When rate limit is exceeded:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60
  }
}
```

## Integration Examples

### Python Integration

```python
import asyncio
from godaddy_cli.core.api_client import SyncGoDaddyAPIClient
from godaddy_cli.core.auth import AuthManager

def update_dns_records():
    auth = AuthManager()
    client = SyncGoDaddyAPIClient(auth)

    # Add A record
    record = DNSRecord(
        name='api',
        type='A',
        data='192.168.1.100',
        ttl=3600
    )

    success = client.create_dns_record('example.com', record)
    return success

# Use in your application
if update_dns_records():
    print("DNS record updated successfully")
```

### JavaScript/Node.js Integration

```javascript
const axios = require('axios');

class GoDaddyDNSClient {
    constructor(apiKey, apiSecret, baseUrl = 'http://localhost:8080') {
        this.apiKey = apiKey;
        this.apiSecret = apiSecret;
        this.baseUrl = baseUrl;
    }

    async listRecords(domain) {
        const response = await axios.get(
            `${this.baseUrl}/api/domains/${domain}/records`,
            {
                headers: {
                    'X-API-Key': this.apiKey,
                    'X-API-Secret': this.apiSecret
                }
            }
        );
        return response.data.records;
    }

    async createRecord(domain, record) {
        const response = await axios.post(
            `${this.baseUrl}/api/domains/${domain}/records`,
            record,
            {
                headers: {
                    'X-API-Key': this.apiKey,
                    'X-API-Secret': this.apiSecret,
                    'Content-Type': 'application/json'
                }
            }
        );
        return response.data;
    }
}

// Usage
const client = new GoDaddyDNSClient('your-key', 'your-secret');
client.createRecord('example.com', {
    name: 'api',
    type: 'A',
    data: '192.168.1.100',
    ttl: 3600
});
```

### Shell/Bash Integration

```bash
#!/bin/bash

API_KEY="your-api-key"
API_SECRET="your-api-secret"
BASE_URL="http://localhost:8080"

# Function to create DNS record
create_record() {
    local domain=$1
    local name=$2
    local type=$3
    local data=$4
    local ttl=${5:-3600}

    curl -s -X POST \
        -H "X-API-Key: $API_KEY" \
        -H "X-API-Secret: $API_SECRET" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"$name\",
            \"type\": \"$type\",
            \"data\": \"$data\",
            \"ttl\": $ttl
        }" \
        "$BASE_URL/api/domains/$domain/records"
}

# Usage
create_record "example.com" "api" "A" "192.168.1.100" 3600
```