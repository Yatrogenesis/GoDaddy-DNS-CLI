#!/bin/bash

# Deploy Staging Environment DNS Configuration
# This script demonstrates automated DNS deployment for staging environments

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Configuration
DOMAIN="${DOMAIN:-example.com}"
PROFILE="${PROFILE:-staging}"
API_ENDPOINT="${API_ENDPOINT:-api-staging.cloudprovider.com}"
APP_ENDPOINT="${APP_ENDPOINT:-app-staging.cloudprovider.com}"
CDN_IP="${CDN_IP:-203.0.113.101}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARN: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if godaddy CLI is installed
    if ! command -v godaddy &> /dev/null; then
        error "GoDaddy CLI not found. Please install it first."
        exit 1
    fi

    # Check CLI version
    local version=$(godaddy --version | cut -d' ' -f2)
    log "GoDaddy CLI version: $version"

    # Check authentication
    if ! godaddy auth test --profile "$PROFILE" &> /dev/null; then
        error "Authentication failed for profile '$PROFILE'"
        error "Please run: godaddy auth setup --profile $PROFILE"
        exit 1
    fi

    success "Prerequisites check passed"
}

# Backup existing DNS records
backup_dns() {
    log "Creating backup of existing DNS records..."

    local backup_file="dns-backup-${DOMAIN}-$(date +%Y%m%d-%H%M%S).json"

    if godaddy bulk export "$DOMAIN" \
        --profile "$PROFILE" \
        --format json \
        --output "backups/$backup_file"; then
        success "DNS backup created: backups/$backup_file"
        echo "$backup_file" > .last-backup
    else
        error "Failed to create DNS backup"
        exit 1
    fi
}

# Validate DNS records before deployment
validate_records() {
    log "Validating DNS records..."

    # Create temporary staging records file
    cat > staging-records.json << EOF
{
  "records": [
    {
      "name": "staging",
      "type": "A",
      "data": "$CDN_IP",
      "ttl": 300
    },
    {
      "name": "api-staging",
      "type": "CNAME",
      "data": "$API_ENDPOINT",
      "ttl": 300
    },
    {
      "name": "app-staging",
      "type": "CNAME",
      "data": "$APP_ENDPOINT",
      "ttl": 300
    },
    {
      "name": "admin-staging",
      "type": "CNAME",
      "data": "$APP_ENDPOINT",
      "ttl": 300
    },
    {
      "name": "docs-staging",
      "type": "CNAME",
      "data": "docs-staging.pages.dev",
      "ttl": 300
    }
  ]
}
EOF

    if godaddy dns validate "$DOMAIN" staging-records.json \
        --profile "$PROFILE" \
        --strict; then
        success "DNS records validation passed"
    else
        error "DNS records validation failed"
        exit 1
    fi
}

# Deploy DNS records
deploy_dns() {
    log "Deploying DNS records for staging environment..."

    # Deploy using bulk import
    if godaddy bulk import "$DOMAIN" staging-records.json \
        --profile "$PROFILE" \
        --batch-size 5 \
        --parallel 2 \
        --dry-run; then
        log "Dry run successful, proceeding with actual deployment..."

        if godaddy bulk import "$DOMAIN" staging-records.json \
            --profile "$PROFILE" \
            --batch-size 5 \
            --parallel 2 \
            --force; then
            success "DNS records deployed successfully"
        else
            error "Failed to deploy DNS records"
            return 1
        fi
    else
        error "Dry run failed, aborting deployment"
        return 1
    fi
}

# Verify DNS propagation
verify_propagation() {
    log "Verifying DNS propagation..."

    local records=("staging.$DOMAIN" "api-staging.$DOMAIN" "app-staging.$DOMAIN")
    local timeout=300
    local start_time=$(date +%s)

    for record in "${records[@]}"; do
        log "Checking propagation for $record..."

        if godaddy monitor check "$record" \
            --profile "$PROFILE" \
            --timeout "$timeout" \
            --dns-servers "8.8.8.8,1.1.1.1,208.67.222.222"; then
            success "Propagation verified for $record"
        else
            warn "Propagation check failed for $record (this is normal and may take time)"
        fi
    done

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log "Propagation check completed in ${duration}s"
}

# Test deployed endpoints
test_endpoints() {
    log "Testing deployed endpoints..."

    local endpoints=(
        "http://staging.$DOMAIN"
        "https://api-staging.$DOMAIN/health"
        "https://app-staging.$DOMAIN"
    )

    for endpoint in "${endpoints[@]}"; do
        log "Testing $endpoint..."

        if curl -f -s -o /dev/null -w "%{http_code}" "$endpoint" | grep -q "200\|301\|302"; then
            success "Endpoint $endpoint is responding"
        else
            warn "Endpoint $endpoint is not responding (this may be expected during initial deployment)"
        fi
    done
}

# Generate deployment report
generate_report() {
    log "Generating deployment report..."

    local report_file="staging-deployment-report-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" << EOF
# Staging Environment Deployment Report

**Domain:** $DOMAIN
**Profile:** $PROFILE
**Date:** $(date)
**CDN IP:** $CDN_IP
**API Endpoint:** $API_ENDPOINT
**App Endpoint:** $APP_ENDPOINT

## Deployed Records

| Name | Type | Data | TTL |
|------|------|------|-----|
| staging | A | $CDN_IP | 300 |
| api-staging | CNAME | $API_ENDPOINT | 300 |
| app-staging | CNAME | $APP_ENDPOINT | 300 |
| admin-staging | CNAME | $APP_ENDPOINT | 300 |
| docs-staging | CNAME | docs-staging.pages.dev | 300 |

## DNS Status

\`\`\`bash
# Check current DNS records
godaddy dns list $DOMAIN --profile $PROFILE --filter staging

# Monitor propagation
godaddy monitor start staging.$DOMAIN --profile $PROFILE --interval 60
\`\`\`

## Rollback Command

If needed, restore from backup:

\`\`\`bash
godaddy bulk import $DOMAIN backups/$(cat .last-backup) --profile $PROFILE --force
\`\`\`

## Next Steps

1. Verify application deployment
2. Run integration tests
3. Update monitoring alerts
4. Notify team of staging environment readiness

---
*Generated by GoDaddy DNS CLI deployment script*
EOF

    success "Deployment report generated: $report_file"
}

# Cleanup temporary files
cleanup() {
    log "Cleaning up temporary files..."
    rm -f staging-records.json
}

# Main deployment function
main() {
    log "Starting staging environment DNS deployment..."
    log "Domain: $DOMAIN"
    log "Profile: $PROFILE"
    log "CDN IP: $CDN_IP"
    log "API Endpoint: $API_ENDPOINT"
    log "App Endpoint: $APP_ENDPOINT"

    # Create backup directory if it doesn't exist
    mkdir -p backups

    # Run deployment steps
    check_prerequisites
    backup_dns
    validate_records
    deploy_dns
    verify_propagation
    test_endpoints
    generate_report
    cleanup

    success "Staging environment DNS deployment completed successfully!"
    success "Check the deployment report for details and next steps."
}

# Error handling
trap 'error "Deployment failed on line $LINENO"; cleanup; exit 1' ERR
trap 'cleanup' EXIT

# Run main function
main "$@"