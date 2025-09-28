# Configuration Guide

This guide covers the comprehensive configuration system of the GoDaddy DNS CLI.

## Configuration Files

The CLI supports multiple configuration formats and locations:

### Default Locations

- **Linux/macOS**: `~/.godaddy-cli/config.yaml`
- **Windows**: `%USERPROFILE%\.godaddy-cli\config.yaml`
- **Custom**: Use `--config` flag or `GODADDY_CLI_CONFIG` environment variable

### Supported Formats

#### YAML (Recommended)
```yaml
# ~/.godaddy-cli/config.yaml
profiles:
  production:
    api_key: "your-prod-key"
    api_secret: "your-prod-secret"
    api_url: "https://api.godaddy.com"
    default_ttl: 3600
    rate_limit: 1000
    timeout: 30
    retry_count: 3

  staging:
    api_key: "your-staging-key"
    api_secret: "your-staging-secret"
    api_url: "https://api.ote-godaddy.com"
    default_ttl: 300
    rate_limit: 100
    timeout: 10
    retry_count: 2

current_profile: production

# Global settings
log_level: "INFO"
output_format: "table"
color_output: true
auto_backup: true
backup_retention: 30

# Web UI settings
web:
  host: "127.0.0.1"
  port: 8080
  cors_origins: ["http://localhost:3000"]
  session_timeout: 3600

# Monitoring settings
monitoring:
  default_interval: 300
  dns_servers:
    - "8.8.8.8"
    - "1.1.1.1"
    - "208.67.222.222"
  max_concurrent_checks: 10

# Template settings
templates:
  default_ttl: 3600
  validation_strict: true
  allow_overwrite: false
```

#### JSON
```json
{
  "profiles": {
    "production": {
      "api_key": "your-prod-key",
      "api_secret": "your-prod-secret",
      "api_url": "https://api.godaddy.com",
      "default_ttl": 3600,
      "rate_limit": 1000
    }
  },
  "current_profile": "production",
  "log_level": "INFO"
}
```

#### TOML
```toml
current_profile = "production"
log_level = "INFO"

[profiles.production]
api_key = "your-prod-key"
api_secret = "your-prod-secret"
api_url = "https://api.godaddy.com"
default_ttl = 3600
rate_limit = 1000

[web]
host = "127.0.0.1"
port = 8080
```

## Profile Management

### Creating Profiles

```bash
# Interactive profile creation
godaddy config profile create production

# Create with specific settings
godaddy config profile create staging \
  --api-key "your-staging-key" \
  --api-secret "your-staging-secret" \
  --api-url "https://api.ote-godaddy.com"
```

### Switching Profiles

```bash
# Switch to different profile
godaddy config profile use staging

# List all profiles
godaddy config profile list

# Show current profile details
godaddy config profile show
```

### Profile-specific Settings

```bash
# Set profile-specific configuration
godaddy config set --profile production default_ttl 7200
godaddy config set --profile staging rate_limit 50

# Get profile configuration
godaddy config get --profile production
```

## Authentication

### Credential Storage

Credentials are securely stored using the system keyring:

```bash
# Set credentials for current profile
godaddy auth set-key YOUR_API_KEY YOUR_API_SECRET

# Set credentials for specific profile
godaddy auth set-key --profile staging YOUR_API_KEY YOUR_API_SECRET

# Test authentication
godaddy auth test

# Rotate credentials
godaddy auth rotate
```

### Environment Variables

Override credentials using environment variables:

```bash
# For all profiles
export GODADDY_API_KEY="your-api-key"
export GODADDY_API_SECRET="your-api-secret"

# Profile-specific
export GODADDY_PRODUCTION_API_KEY="prod-key"
export GODADDY_STAGING_API_KEY="staging-key"
```

## Configuration Commands

### Setting Values

```bash
# Set global configuration
godaddy config set log_level DEBUG
godaddy config set output_format json
godaddy config set auto_backup false

# Set profile-specific configuration
godaddy config set --profile production default_ttl 7200
godaddy config set --profile staging timeout 5

# Set nested configuration
godaddy config set web.port 9090
godaddy config set monitoring.default_interval 600
```

### Getting Values

```bash
# Get all configuration
godaddy config show

# Get specific value
godaddy config get default_ttl
godaddy config get web.port

# Get profile-specific value
godaddy config get --profile staging rate_limit
```

### Removing Values

```bash
# Remove configuration value
godaddy config unset auto_backup

# Remove profile-specific value
godaddy config unset --profile staging custom_setting
```

## Configuration Validation

### Validate Configuration

```bash
# Validate current configuration
godaddy config validate

# Validate specific file
godaddy config validate --file custom-config.yaml

# Validate with detailed output
godaddy config validate --verbose
```

### Configuration Schema

The CLI validates configuration against a strict schema:

```yaml
# Schema example
profiles:
  type: object
  properties:
    production:
      type: object
      required: [api_key, api_secret]
      properties:
        api_key:
          type: string
          pattern: '^[a-zA-Z0-9_-]+$'
        api_secret:
          type: string
          pattern: '^[a-zA-Z0-9_-]+$'
        api_url:
          type: string
          format: uri
        default_ttl:
          type: integer
          minimum: 300
          maximum: 86400
        rate_limit:
          type: integer
          minimum: 1
          maximum: 10000
```

## Advanced Configuration

### Custom API Endpoints

```yaml
profiles:
  custom:
    api_url: "https://custom-proxy.company.com/godaddy"
    headers:
      X-Custom-Header: "value"
      User-Agent: "CustomClient/1.0"
```

### Proxy Configuration

```yaml
# HTTP/HTTPS proxy
proxy:
  http_proxy: "http://proxy.company.com:8080"
  https_proxy: "https://proxy.company.com:8080"
  no_proxy: "localhost,127.0.0.1,.local"

# SOCKS proxy
proxy:
  proxy_url: "socks5://proxy.company.com:1080"
```

### SSL/TLS Configuration

```yaml
ssl:
  verify_ssl: true
  ca_bundle: "/path/to/ca-bundle.crt"
  client_cert: "/path/to/client.crt"
  client_key: "/path/to/client.key"
```

### Logging Configuration

```yaml
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "/var/log/godaddy-cli.log"
  max_size: "10MB"
  backup_count: 5
  console_output: true
```

## Import/Export Configuration

### Export Configuration

```bash
# Export all configuration
godaddy config export --output config-backup.yaml

# Export specific profile
godaddy config export --profile production --output prod-config.yaml

# Export without sensitive data
godaddy config export --no-secrets --output public-config.yaml
```

### Import Configuration

```bash
# Import configuration
godaddy config import config-backup.yaml

# Import and merge with existing
godaddy config import --merge config-update.yaml

# Import specific profile
godaddy config import --profile production prod-config.yaml
```

## Environment-specific Configuration

### Development Environment

```yaml
profiles:
  development:
    api_url: "https://api.ote-godaddy.com"
    default_ttl: 300
    rate_limit: 100
    debug: true
    log_level: "DEBUG"
```

### Production Environment

```yaml
profiles:
  production:
    api_url: "https://api.godaddy.com"
    default_ttl: 3600
    rate_limit: 1000
    retry_count: 5
    timeout: 30
    log_level: "INFO"
```

### CI/CD Environment

```yaml
profiles:
  ci:
    api_url: "https://api.ote-godaddy.com"
    rate_limit: 500
    timeout: 60
    retry_count: 3
    output_format: "json"
    color_output: false
```

## Configuration Best Practices

### Security
- Store API credentials in keyring, not config files
- Use environment-specific profiles
- Regularly rotate API credentials
- Limit rate limits to prevent API abuse

### Performance
- Set appropriate timeouts for your network
- Configure rate limits based on your API tier
- Use connection pooling for bulk operations
- Enable caching for read-heavy workloads

### Monitoring
- Enable audit logging in production
- Set up monitoring alerts for API errors
- Configure backup retention policies
- Use structured logging for analysis

### Team Collaboration
- Use version-controlled config templates
- Document profile purposes and settings
- Standardize naming conventions
- Share non-sensitive configuration templates

## Troubleshooting

### Common Issues

#### Invalid Configuration
```bash
# Check configuration syntax
godaddy config validate

# Reset to defaults
godaddy config reset

# Recreate profile
godaddy config profile delete broken-profile
godaddy config profile create fixed-profile
```

#### Authentication Errors
```bash
# Clear stored credentials
godaddy auth clear

# Re-authenticate
godaddy auth setup

# Test with specific profile
godaddy auth test --profile production
```

#### Permission Issues
```bash
# Check file permissions
ls -la ~/.godaddy-cli/

# Fix permissions
chmod 600 ~/.godaddy-cli/config.yaml
chmod 700 ~/.godaddy-cli/
```

### Debug Mode

```bash
# Enable debug logging
export GODADDY_DEBUG=1
godaddy config show

# Verbose configuration validation
godaddy config validate --verbose --debug
```