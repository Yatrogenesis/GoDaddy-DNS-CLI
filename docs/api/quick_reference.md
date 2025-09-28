# GoDaddy DNS CLI - Quick Reference

## Essential Commands

```bash
# Setup
godaddy auth setup                    # Configure API credentials
godaddy auth test                     # Test connection

# Domains
godaddy domains list                  # List all domains
godaddy domains info example.com      # Domain details

# DNS Records
godaddy dns list example.com          # List DNS records
godaddy dns add example.com --name www --type A --data 1.2.3.4
godaddy dns update example.com --name www --type A --data 1.2.3.5
godaddy dns delete example.com --name old --type A

# Bulk Operations
godaddy bulk export example.com --format csv
godaddy bulk import example.com --file records.csv

# Templates
godaddy template list                 # Show available templates
godaddy template apply example.com web-app --var ip=1.2.3.4
```

## Common Record Types

| Type | Purpose | Example |
|------|---------|---------|
| A | IPv4 address | `192.168.1.1` |
| AAAA | IPv6 address | `2001:db8::1` |
| CNAME | Alias to another domain | `example.com` |
| MX | Mail server | `mail.example.com` (priority: 10) |
| TXT | Text data | `"v=spf1 mx ~all"` |
| SRV | Service location | `10 5 443 service.example.com` |
