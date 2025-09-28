# Deployment Guide

Comprehensive deployment guide for the GoDaddy DNS CLI in various environments.

## Installation Methods

### Production Deployment

#### PyPI Installation
```bash
# Install latest stable version
pip install godaddy-dns-cli

# Install specific version
pip install godaddy-dns-cli==2.0.0

# Install with all optional dependencies
pip install godaddy-dns-cli[all]
```

#### Pre-built Executables

Download from [GitHub Releases](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/releases):

**Windows:**
```powershell
# Download and install
Invoke-WebRequest -Uri "https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/releases/latest/download/godaddy-dns-cli-windows-x64.exe" -OutFile "godaddy.exe"

# Add to PATH (optional)
$env:PATH += ";C:\tools"
```

**macOS:**
```bash
# Download and install
curl -L -o godaddy-cli.dmg "https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/releases/latest/download/godaddy-dns-cli-macos-x64.dmg"
hdiutil attach godaddy-cli.dmg
cp "/Volumes/GoDaddy DNS CLI/godaddy" /usr/local/bin/
```

**Linux:**
```bash
# Download AppImage
curl -L -o godaddy-cli.AppImage "https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/releases/latest/download/godaddy-dns-cli-linux-x64.AppImage"
chmod +x godaddy-cli.AppImage
sudo mv godaddy-cli.AppImage /usr/local/bin/godaddy

# Or install DEB package
wget "https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/releases/latest/download/godaddy-dns-cli_2.0.0_amd64.deb"
sudo dpkg -i godaddy-dns-cli_2.0.0_amd64.deb
```

## Docker Deployment

### Basic Container

```bash
# Pull image
docker pull yatrogenesis/godaddy-dns-cli:latest

# Run CLI
docker run -it --rm \
  -v ~/.godaddy-cli:/home/godaddy/.godaddy-cli \
  yatrogenesis/godaddy-dns-cli:latest

# Run web UI
docker run -d \
  --name godaddy-dns-web \
  -p 8080:8080 \
  -v ~/.godaddy-cli:/home/godaddy/.godaddy-cli \
  yatrogenesis/godaddy-dns-cli:latest web --host 0.0.0.0
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  godaddy-dns-cli:
    image: yatrogenesis/godaddy-dns-cli:latest
    container_name: godaddy-dns-web
    ports:
      - "8080:8080"
    volumes:
      - ./config:/home/godaddy/.godaddy-cli
      - ./backups:/app/backups
    environment:
      - GODADDY_API_KEY=${GODADDY_API_KEY}
      - GODADDY_API_SECRET=${GODADDY_API_SECRET}
      - GODADDY_LOG_LEVEL=INFO
    command: ["web", "--host", "0.0.0.0", "--port", "8080"]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "godaddy", "--help"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: godaddy-dns-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - godaddy-dns-cli
    restart: unless-stopped
```

```bash
# Deploy with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f godaddy-dns-cli

# Update
docker-compose pull
docker-compose up -d
```

## Kubernetes Deployment

### Basic Deployment

```yaml
# godaddy-dns-cli.yaml
apiVersion: v1
kind: Secret
metadata:
  name: godaddy-credentials
  namespace: default
type: Opaque
stringData:
  api-key: your-api-key
  api-secret: your-api-secret

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: godaddy-cli-config
  namespace: default
data:
  config.yaml: |
    profiles:
      production:
        api_url: "https://api.godaddy.com"
        default_ttl: 3600
        rate_limit: 1000
    current_profile: production
    log_level: INFO
    web:
      host: "0.0.0.0"
      port: 8080

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: godaddy-dns-cli
  namespace: default
  labels:
    app: godaddy-dns-cli
spec:
  replicas: 2
  selector:
    matchLabels:
      app: godaddy-dns-cli
  template:
    metadata:
      labels:
        app: godaddy-dns-cli
    spec:
      containers:
      - name: godaddy-dns-cli
        image: yatrogenesis/godaddy-dns-cli:latest
        ports:
        - containerPort: 8080
          name: web
        env:
        - name: GODADDY_API_KEY
          valueFrom:
            secretKeyRef:
              name: godaddy-credentials
              key: api-key
        - name: GODADDY_API_SECRET
          valueFrom:
            secretKeyRef:
              name: godaddy-credentials
              key: api-secret
        volumeMounts:
        - name: config
          mountPath: /home/godaddy/.godaddy-cli
          readOnly: true
        command: ["godaddy", "web", "--host", "0.0.0.0", "--port", "8080"]
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: godaddy-cli-config

---
apiVersion: v1
kind: Service
metadata:
  name: godaddy-dns-cli-service
  namespace: default
spec:
  selector:
    app: godaddy-dns-cli
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
    name: web
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: godaddy-dns-cli-ingress
  namespace: default
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  tls:
  - hosts:
    - dns.example.com
    secretName: godaddy-dns-cli-tls
  rules:
  - host: dns.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: godaddy-dns-cli-service
            port:
              number: 80
```

Deploy:
```bash
kubectl apply -f godaddy-dns-cli.yaml
kubectl get pods -l app=godaddy-dns-cli
kubectl logs -l app=godaddy-dns-cli
```

### Helm Chart

```yaml
# values.yaml
replicaCount: 2

image:
  repository: yatrogenesis/godaddy-dns-cli
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8080

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: dns.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: godaddy-dns-cli-tls
      hosts:
        - dns.example.com

config:
  logLevel: INFO
  profiles:
    production:
      apiUrl: "https://api.godaddy.com"
      defaultTtl: 3600
      rateLimit: 1000

credentials:
  apiKey: ""  # Set via --set or sealed-secrets
  apiSecret: ""  # Set via --set or sealed-secrets

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
```

Install:
```bash
helm install godaddy-dns-cli ./helm-chart \
  --set credentials.apiKey=your-api-key \
  --set credentials.apiSecret=your-api-secret
```

## Cloud Deployment

### AWS ECS

```json
{
  "family": "godaddy-dns-cli",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "godaddy-dns-cli",
      "image": "yatrogenesis/godaddy-dns-cli:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GODADDY_API_KEY",
          "value": "your-api-key"
        },
        {
          "name": "GODADDY_API_SECRET",
          "value": "your-api-secret"
        }
      ],
      "command": ["godaddy", "web", "--host", "0.0.0.0"],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/godaddy-dns-cli",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "godaddy --help || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Google Cloud Run

```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: godaddy-dns-cli
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "512Mi"
        run.googleapis.com/cpu: "1000m"
    spec:
      containers:
      - image: yatrogenesis/godaddy-dns-cli:latest
        ports:
        - containerPort: 8080
        env:
        - name: GODADDY_API_KEY
          valueFrom:
            secretKeyRef:
              name: godaddy-credentials
              key: api-key
        - name: GODADDY_API_SECRET
          valueFrom:
            secretKeyRef:
              name: godaddy-credentials
              key: api-secret
        command: ["godaddy", "web", "--host", "0.0.0.0", "--port", "8080"]
        resources:
          limits:
            memory: "512Mi"
            cpu: "1000m"
        startupProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          periodSeconds: 10
```

Deploy:
```bash
# Create secret
kubectl create secret generic godaddy-credentials \
  --from-literal=api-key=your-api-key \
  --from-literal=api-secret=your-api-secret

# Deploy service
gcloud run services replace service.yaml --region=us-central1
```

### Azure Container Instances

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-12-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "apiKey": {
      "type": "securestring"
    },
    "apiSecret": {
      "type": "securestring"
    }
  },
  "resources": [
    {
      "type": "Microsoft.ContainerInstance/containerGroups",
      "apiVersion": "2019-12-01",
      "name": "godaddy-dns-cli",
      "location": "East US",
      "properties": {
        "containers": [
          {
            "name": "godaddy-dns-cli",
            "properties": {
              "image": "yatrogenesis/godaddy-dns-cli:latest",
              "ports": [
                {
                  "port": 8080,
                  "protocol": "TCP"
                }
              ],
              "environmentVariables": [
                {
                  "name": "GODADDY_API_KEY",
                  "secureValue": "[parameters('apiKey')]"
                },
                {
                  "name": "GODADDY_API_SECRET",
                  "secureValue": "[parameters('apiSecret')]"
                }
              ],
              "command": ["godaddy", "web", "--host", "0.0.0.0"],
              "resources": {
                "requests": {
                  "cpu": 0.5,
                  "memoryInGB": 0.5
                }
              }
            }
          }
        ],
        "osType": "Linux",
        "ipAddress": {
          "type": "Public",
          "ports": [
            {
              "port": 8080,
              "protocol": "TCP"
            }
          ]
        },
        "restartPolicy": "Always"
      }
    }
  ]
}
```

## Server Deployment

### Systemd Service (Linux)

```ini
# /etc/systemd/system/godaddy-dns-cli.service
[Unit]
Description=GoDaddy DNS CLI Web Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=godaddy-cli
Group=godaddy-cli
WorkingDirectory=/opt/godaddy-dns-cli
Environment=GODADDY_API_KEY=your-api-key
Environment=GODADDY_API_SECRET=your-api-secret
Environment=PYTHONPATH=/opt/godaddy-dns-cli
ExecStart=/opt/godaddy-dns-cli/venv/bin/godaddy web --host 0.0.0.0 --port 8080
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Setup:
```bash
# Create user
sudo useradd -r -s /bin/false godaddy-cli

# Install application
sudo mkdir -p /opt/godaddy-dns-cli
sudo chown godaddy-cli:godaddy-cli /opt/godaddy-dns-cli

# Create virtual environment
sudo -u godaddy-cli python3 -m venv /opt/godaddy-dns-cli/venv
sudo -u godaddy-cli /opt/godaddy-dns-cli/venv/bin/pip install godaddy-dns-cli

# Enable and start service
sudo systemctl enable godaddy-dns-cli.service
sudo systemctl start godaddy-dns-cli.service
sudo systemctl status godaddy-dns-cli.service
```

### Windows Service

```powershell
# Install using sc command
sc create "GoDaddyDNSCLI" binPath="C:\Program Files\GoDaddy DNS CLI\godaddy.exe web --host 0.0.0.0 --port 8080" start=auto

# Or using PowerShell
New-Service -Name "GoDaddyDNSCLI" -BinaryPathName "C:\Program Files\GoDaddy DNS CLI\godaddy.exe web --host 0.0.0.0 --port 8080" -StartupType Automatic
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/godaddy-dns-cli
server {
    listen 80;
    server_name dns.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dns.example.com;

    ssl_certificate /etc/letsencrypt/live/dns.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dns.example.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;

        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Environment Configuration

### Production Environment

```yaml
# production.yaml
profiles:
  production:
    api_url: "https://api.godaddy.com"
    default_ttl: 3600
    rate_limit: 1000
    timeout: 30
    retry_count: 5

current_profile: production
log_level: "INFO"
auto_backup: true
backup_retention: 90

web:
  host: "0.0.0.0"
  port: 8080
  cors_origins: ["https://dns.example.com"]
  session_timeout: 3600

monitoring:
  default_interval: 300
  max_concurrent_checks: 20
  alert_webhooks:
    - url: "https://alerts.company.com/webhook"
      secret: "webhook-secret"

security:
  enable_audit_log: true
  audit_log_file: "/var/log/godaddy-cli-audit.log"
  max_session_duration: 28800
```

### Staging Environment

```yaml
# staging.yaml
profiles:
  staging:
    api_url: "https://api.ote-godaddy.com"
    default_ttl: 300
    rate_limit: 100
    timeout: 10

current_profile: staging
log_level: "DEBUG"
auto_backup: false

web:
  host: "127.0.0.1"
  port: 8080
  debug_mode: true
```

### Development Environment

```yaml
# development.yaml
profiles:
  development:
    api_url: "https://api.ote-godaddy.com"
    default_ttl: 60
    rate_limit: 50
    debug: true

current_profile: development
log_level: "DEBUG"
color_output: true

web:
  host: "127.0.0.1"
  port: 3000
  hot_reload: true
  debug_mode: true
```

## Monitoring and Observability

### Prometheus Metrics

The web server exposes metrics at `/metrics`:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'godaddy-dns-cli'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

Available metrics:
- `godaddy_api_requests_total`
- `godaddy_api_request_duration_seconds`
- `godaddy_dns_records_total`
- `godaddy_bulk_operations_total`
- `godaddy_template_applications_total`

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "GoDaddy DNS CLI",
    "panels": [
      {
        "title": "API Requests",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(godaddy_api_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Times",
        "type": "graph",
        "targets": [
          {
            "expr": "godaddy_api_request_duration_seconds",
            "legendFormat": "{{quantile}}"
          }
        ]
      }
    ]
  }
}
```

### Health Checks

```bash
# Basic health check
curl http://localhost:8080/health

# Detailed health check
curl http://localhost:8080/health/detailed
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "2.0.0",
  "checks": {
    "api_connectivity": "ok",
    "authentication": "ok",
    "database": "ok"
  }
}
```

## Load Balancing

### HAProxy Configuration

```haproxy
# /etc/haproxy/haproxy.cfg
global
    daemon
    log stdout local0

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend godaddy_dns_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/dns.example.com.pem
    redirect scheme https if !{ ssl_fc }
    default_backend godaddy_dns_backend

backend godaddy_dns_backend
    balance roundrobin
    option httpchk GET /health
    server cli1 10.0.1.10:8080 check
    server cli2 10.0.1.11:8080 check
    server cli3 10.0.1.12:8080 check
```

## Security Considerations

### SSL/TLS Configuration

```yaml
# Secure configuration
web:
  ssl:
    enabled: true
    cert_file: "/etc/ssl/certs/server.crt"
    key_file: "/etc/ssl/private/server.key"
    protocols: ["TLSv1.2", "TLSv1.3"]
    ciphers: "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"

security:
  cors_origins: ["https://dns.example.com"]
  session_security:
    secure_cookies: true
    samesite: "strict"
    csrf_protection: true
  rate_limiting:
    requests_per_minute: 60
    burst_limit: 100
```

### Firewall Rules

```bash
# iptables rules
iptables -A INPUT -p tcp --dport 8080 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP

# ufw rules
ufw allow from 10.0.0.0/8 to any port 8080
ufw deny 8080
```

## Backup and Recovery

### Automated Backups

```bash
# Schedule daily backups
crontab -e

# Add this line for daily backup at 2 AM
0 2 * * * /usr/local/bin/godaddy bulk export-all --format json --output /backups/dns-backup-$(date +\%Y\%m\%d).json
```

### Configuration Backup

```bash
# Backup configuration
godaddy config export --output config-backup-$(date +%Y%m%d).yaml

# Backup with encrypted credentials
godaddy config export --include-secrets --encrypt --output secure-backup.yaml.enc
```

### Disaster Recovery

```bash
# Full system restore
godaddy config import production-config.yaml
godaddy auth import-keys production-keys.json
godaddy bulk import example.com dns-backup.json --verify --dry-run
godaddy bulk import example.com dns-backup.json --apply
```

## Performance Optimization

### Tuning Parameters

```yaml
# High-performance configuration
profiles:
  production:
    rate_limit: 5000
    timeout: 60
    retry_count: 5
    connection_pool_size: 20
    max_concurrent_requests: 100

bulk_operations:
  default_batch_size: 20
  max_parallel_batches: 10
  retry_failed_batches: true

caching:
  enabled: true
  ttl: 300
  max_size: 1000
```

### Resource Limits

```yaml
# Container resource limits
resources:
  limits:
    memory: "1Gi"
    cpu: "1000m"
  requests:
    memory: "256Mi"
    cpu: "200m"

# Application limits
limits:
  max_domains_per_request: 100
  max_records_per_bulk_operation: 1000
  max_template_size: "1MB"
  max_concurrent_monitors: 50
```

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Monitor memory usage
godaddy status --metrics

# Adjust batch sizes
godaddy config set bulk_operations.default_batch_size 10
godaddy config set bulk_operations.max_parallel_batches 5
```

#### Connection Issues
```bash
# Test connectivity
godaddy auth test --verbose

# Check proxy settings
godaddy config get proxy

# Test with different timeout
godaddy config set timeout 60
```

#### Performance Issues
```bash
# Enable performance profiling
export GODADDY_PROFILE=1
godaddy dns list example.com

# Check rate limiting
godaddy config get rate_limit
godaddy status --rate-limit
```

### Logging

```bash
# Enable debug logging
export GODADDY_LOG_LEVEL=DEBUG
export GODADDY_LOG_FILE=/tmp/godaddy-debug.log

# Structured logging
export GODADDY_LOG_FORMAT=json
godaddy dns list example.com
```

### Support

For deployment issues:
- Check [troubleshooting guide](TROUBLESHOOTING.md)
- Review [GitHub Issues](https://github.com/Yatrogenesis/GoDaddy-DNS-CLI/issues)
- Enable debug logging and provide logs
- Include deployment environment details