# GoDaddy DNS CLI

[![CI/CD Pipeline](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/actions/workflows/ci.yml/badge.svg)](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/actions/workflows/ci.yml)
[![Release Pipeline](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/actions/workflows/release.yml/badge.svg)](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/actions/workflows/release.yml)
[![codecov](https://codecov.io/gh/Yatrogenesis/GoDaddy-DNS-CLI/branch/main/graph/badge.svg)](https://codecov.io/gh/Yatrogenesis/GoDaddy-DNS-CLI)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/godaddy-dns-cli.svg)](https://badge.fury.io/py/godaddy-dns-cli)

Enterprise-grade command-line interface for managing GoDaddy DNS records with modern web UI, automation capabilities, and enterprise features.

## Features

### Core CLI Features
- **Complete DNS Management**: A, AAAA, CNAME, MX, TXT, SRV, NS, PTR records
- **Bulk Operations**: Import/export from CSV, JSON, YAML
- **Template System**: Reusable DNS configurations with variables
- **Profile Management**: Multiple environments and credential sets
- **Monitoring & Alerts**: DNS record change detection
- **Validation**: DNS record syntax and propagation validation

### Enterprise Features
- **Web UI**: Modern React/TypeScript interface
- **Authentication**: Secure API key management with keyring storage
- **Rate Limiting**: Intelligent API throttling
- **Async Operations**: High-performance concurrent processing
- **Configuration**: Multiple formats (YAML, JSON, TOML)
- **Extensibility**: Plugin architecture for custom commands

### DevOps Integration
- **CI/CD Ready**: GitHub Actions workflows included
- **Docker Support**: Multi-stage containerized deployment
- **Multi-Platform**: Windows, macOS, Linux executables
- **Package Distribution**: PyPI, GitHub Releases, Docker Hub

## Quick Start

### Installation

#### PyPI (Recommended)
```bash
pip install godaddy-dns-cli
```

#### GitHub Releases
Download pre-built executables from [releases](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/releases).

#### Docker
```bash
docker run -it yatrogenesis/godaddy-dns-cli
```

#### Development Installation
```bash
git clone https://github.com/Yatrogenesis/GoDaddy-DNS-CLI.git
cd GoDaddy-DNS-CLI
pip install -e .[dev,all]
```

### Initial Setup
```bash
# Configure API credentials
godaddy init

# List your domains
godaddy domains list

# Start web UI
godaddy web --port 8080
```

## Usage Examples

### Basic DNS Operations
```bash
# List all DNS records for a domain
godaddy dns list example.com

# Add an A record
godaddy dns add example.com A www 192.168.1.1 --ttl 3600

# Update a CNAME record
godaddy dns update example.com CNAME blog www.example.com

# Delete a record
godaddy dns delete example.com A www

# Validate records before applying
godaddy dns validate example.com records.json
```

### Bulk Operations
```bash
# Import records from CSV
godaddy bulk import example.com records.csv

# Export all records to JSON
godaddy bulk export example.com --format json --output backup.json

# Apply bulk changes with progress tracking
godaddy bulk apply example.com changes.yaml --parallel 5
```

### Template System
```bash
# Create a template
godaddy template create web-stack template.yaml

# Apply template to domain
godaddy template apply example.com web-stack --vars env=prod

# List available templates
godaddy template list
```

### Profile Management
```bash
# Create production profile
godaddy config profile create production

# Switch profiles
godaddy config profile use production

# List profiles
godaddy config profile list
```

### Monitoring
```bash
# Monitor domain for changes
godaddy monitor start example.com --interval 300

# View monitoring status
godaddy monitor status

# Set up alerts
godaddy monitor alert example.com webhook https://alerts.company.com
```

## 📁 Files

| File | Description |
|------|-------------|
| `GODADDY_AUTO_SETUP.py` | Main CLI tool with full API integration |
| `GODADDY_CLI_DEMO.py` | Demo version (no API keys required) |
| `aion_enterprise_config.json` | Example enterprise configuration |
| `INSTALL_COMPLETE_CLI.bat` | Windows installation script |

## 🏢 Enterprise Features

### Bulk Subdomain Configuration

Create `enterprise_config.json`:

```json
{
  "api": "api-server.example.com",
  "app": "app-server.example.com",
  "admin": "admin-panel.example.com",
  "docs": "documentation.example.com",
  "status": "status-page.example.com"
}
```

Run enterprise setup:

```bash
python GODADDY_AUTO_SETUP.py enterprise-setup yourdomain.com enterprise_config.json
```

### DNS Backup & Disaster Recovery

```bash
# Create backup
python GODADDY_AUTO_SETUP.py backup yourdomain.com

# Restore configuration
python GODADDY_AUTO_SETUP.py restore dns_backup_yourdomain.com_20240927.json
```

### Real-time Monitoring

```bash
# Monitor DNS propagation with custom timeout
python GODADDY_AUTO_SETUP.py monitor subdomain.example.com --timeout 900
```

## 🎬 Demo Mode

Try all features without API keys:

```bash
python GODADDY_CLI_DEMO.py
```

**Demo includes:**
- DNS record configuration simulation
- Propagation monitoring demo
- Backup/restore workflow
- Enterprise setup preview

## 🔍 DNS Propagation Monitoring

The CLI includes real-time DNS propagation monitoring:

- ✅ Automatic verification across multiple DNS servers
- ⏱️ Real-time progress tracking
- 🌐 HTTPS connectivity testing
- 📊 Detailed propagation reports

## 🛡️ Error Handling

- **API Rate Limiting** - Automatic delays between requests
- **Network Resilience** - Retry logic for failed requests
- **Validation** - Input validation before API calls
- **Detailed Logging** - Clear error messages and debugging info

## 📚 Examples

### Configure a subdomain for Cloudflare Pages

```bash
python GODADDY_AUTO_SETUP.py cname yourdomain.com app your-project.pages.dev
```

### Setup complete infrastructure

```bash
# Create config file
echo '{
  "api": "your-api.workers.dev",
  "app": "your-app.pages.dev",
  "docs": "your-docs.pages.dev"
}' > my_config.json

# Deploy all at once
python GODADDY_AUTO_SETUP.py enterprise-setup yourdomain.com my_config.json
```

### Monitor deployment

```bash
python GODADDY_AUTO_SETUP.py monitor app.yourdomain.com
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Cloudflare Wrangler](https://github.com/cloudflare/workers-sdk) - CLI for Cloudflare Workers
- [GoDaddy API Documentation](https://developer.godaddy.com/doc)

## 🆘 Support

- 📧 Create an [Issue](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/issues)
- 📖 Check [GoDaddy API Docs](https://developer.godaddy.com/doc)
- 💬 Discussion in [Issues](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/issues)

## 🌟 Star History

If this project helped you, please ⭐ star it on GitHub!

---

**Built with ❤️ for the DevOps community**