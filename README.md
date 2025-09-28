# GoDaddy DNS CLI

🚀 **Enterprise-grade CLI tool for GoDaddy DNS management** - Like `wrangler` but for GoDaddy

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GoDaddy API](https://img.shields.io/badge/GoDaddy-API%20v1-green.svg)](https://developer.godaddy.com/)

## ✨ Features

- **🔧 Automated DNS Management** - Configure DNS records with single commands
- **📊 Real-time Monitoring** - Track DNS propagation across global servers
- **💾 Backup & Restore** - Full DNS configuration backup and restoration
- **🏢 Enterprise Setup** - Bulk subdomain configuration for organizations
- **🎬 Demo Mode** - Test all features without API keys
- **🔍 Propagation Tracking** - Monitor DNS changes in real-time
- **🛡️ Error Handling** - Robust error handling and validation

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Yatrogenesis/GoDaddy-DNS-CLI.git
cd GoDaddy-DNS-CLI

# Install dependencies
pip install requests

# Run demo (no API keys required)
python GODADDY_CLI_DEMO.py
```

### Get API Credentials

1. Go to [GoDaddy Developer Portal](https://developer.godaddy.com)
2. Create account/login
3. Navigate to "API Keys"
4. Create new Production key
5. Copy API Key and Secret

### Configure Credentials

```bash
# Windows
set GODADDY_API_KEY=your_api_key
set GODADDY_API_SECRET=your_api_secret

# Linux/Mac
export GODADDY_API_KEY=your_api_key
export GODADDY_API_SECRET=your_api_secret
```

## 📋 Commands

### Basic DNS Operations

```bash
# Configure CNAME record
python GODADDY_AUTO_SETUP.py cname example.com subdomain target.example.com

# List all DNS records
python GODADDY_AUTO_SETUP.py list example.com

# Get domain information
python GODADDY_AUTO_SETUP.py info example.com

# Delete DNS record
python GODADDY_AUTO_SETUP.py delete example.com CNAME subdomain
```

### Advanced Features

```bash
# Auto-configure with monitoring
python GODADDY_AUTO_SETUP.py setup-creator

# Enterprise bulk setup
python GODADDY_AUTO_SETUP.py setup-aion-complete

# Monitor DNS propagation
python GODADDY_AUTO_SETUP.py monitor subdomain.example.com

# Backup DNS configuration
python GODADDY_AUTO_SETUP.py backup example.com

# Restore from backup
python GODADDY_AUTO_SETUP.py restore dns_backup_example.com_20240927.json

# Enterprise setup from config
python GODADDY_AUTO_SETUP.py enterprise-setup example.com enterprise_config.json
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