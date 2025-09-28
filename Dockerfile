# Multi-stage build for GoDaddy DNS CLI
FROM node:18-alpine AS web-builder

# Build web UI
WORKDIR /app/web-ui
COPY web-ui/package*.json ./
RUN npm ci --only=production

COPY web-ui/ ./
RUN npm run build

# Python application stage
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Create app directory
WORKDIR /app

# Copy Python requirements
COPY requirements*.txt ./
COPY pyproject.toml setup.py ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY godaddy_cli/ ./godaddy_cli/
COPY --from=web-builder /app/godaddy_cli/web/static ./godaddy_cli/web/static

# Build package
RUN python -m build

# Production stage
FROM python:3.11-alpine AS production

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    curl \
    && update-ca-certificates

# Create non-root user
RUN addgroup -g 1001 -S godaddy && \
    adduser -S godaddy -u 1001 -G godaddy

# Set working directory
WORKDIR /app

# Copy built package from builder stage
COPY --from=builder /app/dist/*.whl ./

# Install the package
RUN pip install --no-cache-dir *.whl && \
    rm *.whl

# Create config directory
RUN mkdir -p /home/godaddy/.godaddy-cli && \
    chown -R godaddy:godaddy /home/godaddy

# Switch to non-root user
USER godaddy

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD godaddy --help || exit 1

# Set default entrypoint
ENTRYPOINT ["godaddy"]
CMD ["--help"]

# Metadata
LABEL maintainer="Yatrogenesis" \
      description="Enterprise-grade CLI tool for GoDaddy DNS management" \
      version="2.0.0" \
      org.opencontainers.image.source="https://github.com/Yatrogenesis/GoDaddy-DNS-CLI"