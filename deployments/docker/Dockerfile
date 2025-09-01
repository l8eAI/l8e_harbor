# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml poetry.lock* ./

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --without dev --no-root

# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r l8eharbor && useradd -r -g l8eharbor l8eharbor

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create directories
RUN mkdir -p /etc/l8e-harbor/secrets /etc/l8e-harbor/tls /var/lib/l8e-harbor /tmp && \
    chown -R l8eharbor:l8eharbor /etc/l8e-harbor /var/lib/l8e-harbor /tmp

# Copy application code
WORKDIR /app
COPY app/ ./app/
COPY pyproject.toml ./

# Generate self-signed certificate for testing
RUN openssl req -x509 -newkey rsa:2048 -keyout /etc/l8e-harbor/tls/tls.key -out /etc/l8e-harbor/tls/tls.crt -days 365 -nodes -subj "/CN=l8e-harbor" && \
    chown l8eharbor:l8eharbor /etc/l8e-harbor/tls/tls.key /etc/l8e-harbor/tls/tls.crt && \
    chmod 600 /etc/l8e-harbor/tls/tls.key

# Generate JWT keys
RUN openssl genrsa -out /etc/l8e-harbor/secrets/jwt_private.pem 2048 && \
    openssl rsa -in /etc/l8e-harbor/secrets/jwt_private.pem -pubout -out /etc/l8e-harbor/secrets/jwt_public.pem && \
    chown l8eharbor:l8eharbor /etc/l8e-harbor/secrets/jwt_private.pem /etc/l8e-harbor/secrets/jwt_public.pem && \
    chmod 600 /etc/l8e-harbor/secrets/jwt_private.pem

# Switch to non-root user
USER l8eharbor

# Expose ports
EXPOSE 8443 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('https://localhost:8443/healthz', context=__import__('ssl').create_default_context(check_hostname=False, verify_mode=__import__('ssl').CERT_NONE))"

# Default command
CMD ["python", "-m", "app.main"]