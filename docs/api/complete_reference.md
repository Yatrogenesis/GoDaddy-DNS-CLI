# GoDaddy DNS CLI - Complete API Reference

*Generated on: 2025-09-28 04:21:54*

## Table of Contents

1. [API Reference](#api-reference)
2. [CLI Commands](#cli-commands)
3. [Utilities](#utilities)
4. [Examples](#examples)

## API Reference

### SimpleAPIClient

Enhanced synchronous GoDaddy API client

#### Methods

##### `add_record(self, domain: str, record: godaddy_cli.core.simple_api_client.DNSRecord) -> bool`

Add DNS record

##### `bulk_add_records(self, domain: str, records: List[godaddy_cli.core.simple_api_client.DNSRecord]) -> Dict[str, Any]`

Add multiple DNS records

##### `bulk_update_records(self, domain: str, records: List[godaddy_cli.core.simple_api_client.DNSRecord]) -> Dict[str, Any]`

Update multiple DNS records

##### `close(self)`

Close the session

##### `delete_record(self, domain: str, record_type: str, name: str) -> bool`

Delete DNS record

##### `get_domain(self, domain: str) -> godaddy_cli.core.simple_api_client.Domain`

Get specific domain information

##### `get_domains(self) -> List[godaddy_cli.core.simple_api_client.Domain]`

Get all domains

##### `get_records(self, domain: str, record_type: str = None, name: str = None) -> List[godaddy_cli.core.simple_api_client.DNSRecord]`

Get DNS records for domain

##### `test_connection(self) -> bool`

Test API connection

##### `update_record(self, domain: str, record: godaddy_cli.core.simple_api_client.DNSRecord) -> bool`

Update DNS record

##### `validate_records(self, records: List[godaddy_cli.core.simple_api_client.DNSRecord]) -> Dict[str, Any]`

Validate DNS records before submission

### DNSRecord

DNS record data structure

#### Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `name` | `str` | Record name |  |
| `type` | `str` | Record type (A, AAAA, CNAME, etc.) |  |
| `data` | `str` | Record data/value |  |
| `ttl` | `int` | Time to live in seconds | `3600` |
| `priority` | `Optional[int]` | Priority for MX/SRV records |  |
| `port` | `Optional[int]` | Port for SRV records |  |
| `weight` | `Optional[int]` | Weight for SRV records |  |

### Domain

Domain information structure

#### Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `domain` | `str` | Domain name |  |
| `status` | `str` | Domain status |  |
| `expires` | `str` | Expiration date |  |
| `privacy` | `bool` | Privacy protection enabled |  |
| `locked` | `bool` | Domain locked status |  |

## CLI Commands

### `godaddy dns`

DNS record management commands

#### `godaddy dns list`

List DNS records for a domain

**Usage:** `godaddy dns list DOMAIN [OPTIONS]`

**Options:**

- `--type`: Filter by record type
- `--name`: Filter by record name
- `--format`: Output format (table, json, yaml, csv)
- `--export`: Export to file

**Examples:**

```bash
godaddy dns list example.com
godaddy dns list example.com --type A
godaddy dns list example.com --format json
godaddy dns list example.com --export records.csv
```

#### `godaddy dns add`

Add a DNS record

**Usage:** `godaddy dns add DOMAIN --name NAME --type TYPE --data DATA [OPTIONS]`

**Options:**

- `--name`: Record name *(required)*
- `--type`: Record type *(required)*
- `--data`: Record data *(required)*
- `--ttl`: Time to live (default: 3600)
- `--priority`: Priority for MX records

**Examples:**

```bash
godaddy dns add example.com --name www --type A --data 192.168.1.1
godaddy dns add example.com --name mail --type MX --data mail.example.com --priority 10
godaddy dns add example.com --name @ --type TXT --data "v=spf1 mx ~all"
```

#### `godaddy dns update`

Update an existing DNS record

**Usage:** `godaddy dns update DOMAIN --name NAME --type TYPE --data DATA [OPTIONS]`

**Options:**

- `--name`: Record name *(required)*
- `--type`: Record type *(required)*
- `--data`: New record data *(required)*
- `--ttl`: Time to live

**Examples:**

```bash
godaddy dns update example.com --name www --type A --data 192.168.1.2
godaddy dns update example.com --name @ --type A --data 192.168.1.1 --ttl 7200
```

#### `godaddy dns delete`

Delete a DNS record

**Usage:** `godaddy dns delete DOMAIN --name NAME --type TYPE [OPTIONS]`

**Options:**

- `--name`: Record name *(required)*
- `--type`: Record type *(required)*
- `--force`: Skip confirmation

**Examples:**

```bash
godaddy dns delete example.com --name old --type A
godaddy dns delete example.com --name test --type CNAME --force
```

### `godaddy domains`

Domain management commands

#### `godaddy domains list`

List all domains in your account

**Usage:** `godaddy domains list [OPTIONS]`

**Options:**

- `--format`: Output format (table, json)
- `--status`: Filter by status

**Examples:**

```bash
godaddy domains list
godaddy domains list --format json
godaddy domains list --status ACTIVE
```

#### `godaddy domains info`

Get detailed information about a domain

**Usage:** `godaddy domains info DOMAIN`

**Examples:**

```bash
godaddy domains info example.com
```

### `godaddy auth`

Authentication and credential management

#### `godaddy auth setup`

Configure API credentials

**Usage:** `godaddy auth setup [OPTIONS]`

**Options:**

- `--api-key`: GoDaddy API key
- `--api-secret`: GoDaddy API secret
- `--profile`: Configuration profile name

**Examples:**

```bash
godaddy auth setup
godaddy auth setup --profile production
```

#### `godaddy auth test`

Test API connection

**Usage:** `godaddy auth test`

**Examples:**

```bash
godaddy auth test
```

### `godaddy bulk`

Bulk operations for multiple DNS records

#### `godaddy bulk import`

Import DNS records from CSV file

**Usage:** `godaddy bulk import DOMAIN --file FILE [OPTIONS]`

**Options:**

- `--file`: CSV file path *(required)*
- `--dry-run`: Show what would be imported
- `--replace`: Replace existing records

**Examples:**

```bash
godaddy bulk import example.com --file records.csv
godaddy bulk import example.com --file records.csv --dry-run
```

#### `godaddy bulk export`

Export DNS records to file

**Usage:** `godaddy bulk export DOMAIN [OPTIONS]`

**Options:**

- `--format`: Export format (csv, json, yaml)
- `--output`: Output file path

**Examples:**

```bash
godaddy bulk export example.com --format csv
godaddy bulk export example.com --output backup.json
```

## Utilities

### validators

Input validation utilities

#### `validate_domain()`

Validate domain name format

**Parameters:**

- `domain` (str): Domain to validate

**Returns:** bool - True if valid

**Examples:**

```python
validate_domain("example.com")  # True
```

#### `validate_ip()`

Validate IP address format

**Parameters:**

- `ip` (str): IP address to validate

**Returns:** bool - True if valid

**Examples:**

```python
validate_ip("192.168.1.1")  # True
```

#### `validate_ttl()`

Validate TTL value

**Parameters:**

- `ttl` (int): TTL value to validate

**Returns:** bool - True if valid (300-604800)

**Examples:**

```python
validate_ttl(3600)  # True
```

### formatters

Output formatting utilities

#### `format_dns_table()`

Format DNS records as a table

**Parameters:**

- `records` (List[DNSRecord]): DNS records to format
- `title` (str): Table title

**Returns:** str - Formatted table string

#### `format_json_output()`

Format data as JSON

**Parameters:**

- `data` (Any): Data to format
- `pretty` (bool): Pretty print format

**Returns:** str - JSON string

### error_handlers

Enhanced error handling utilities

## Examples

### Getting Started

#### Step 1: Install the CLI

```bash
pip install godaddy-dns-cli
# or install from source
git clone https://github.com/Yatrogenesis/GoDaddy-DNS-CLI.git
cd GoDaddy-DNS-CLI
pip install -e .
```

#### Step 2: Configure API credentials

```bash
godaddy auth setup
# Follow the prompts to enter your API key and secret
```

**Notes:**

- Get your API credentials from https://developer.godaddy.com/keys
- Choose "Production" for live domains or "OTE" for testing

#### Step 3: Test connection

```bash
godaddy auth test
```

#### Step 4: List your domains

```bash
godaddy domains list
```

#### Step 5: Manage DNS records

```bash
godaddy dns list example.com
godaddy dns add example.com --name www --type A --data 192.168.1.1
```

### Common DNS Management Tasks

#### Setting up a web server

Configure DNS for a typical web application

```bash
# Add main domain A record
godaddy dns add example.com --name @ --type A --data 192.168.1.1

# Add www subdomain
godaddy dns add example.com --name www --type CNAME --data example.com

# Add API subdomain
godaddy dns add example.com --name api --type A --data 192.168.1.2
```

#### Email server setup

Configure DNS records for email hosting

```bash
# Add MX record
godaddy dns add example.com --name @ --type MX --data mail.example.com --priority 10

# Add mail server A record
godaddy dns add example.com --name mail --type A --data 192.168.1.10

# Add SPF record
godaddy dns add example.com --name @ --type TXT --data "v=spf1 mx ~all"

# Add DMARC record
godaddy dns add example.com --name _dmarc --type TXT --data "v=DMARC1; p=none; rua=mailto:dmarc@example.com"
```

#### Bulk operations

Import/export multiple DNS records

```bash
# Export existing records
godaddy bulk export example.com --format csv --output backup.csv

# Import records from CSV
godaddy bulk import example.com --file new-records.csv

# Dry run to preview changes
godaddy bulk import example.com --file new-records.csv --dry-run
```

### Advanced Features

#### Using templates

Apply pre-configured DNS setups

```bash
# List available templates
godaddy template list

# Apply web application template
godaddy template apply example.com web-app --var app_ip=192.168.1.1
```

#### Monitoring and validation

Monitor DNS health and validate configuration

```bash
# Validate DNS configuration
godaddy dns validate example.com

# Start monitoring
godaddy monitor start example.com --interval 300
```

#### Multiple profiles

Manage multiple accounts or environments

```bash
# Setup production profile
godaddy auth setup --profile production

# Setup development profile
godaddy auth setup --profile development

# Use specific profile
godaddy --profile production dns list example.com
```
