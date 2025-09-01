#!/bin/bash

# Installation script for l8e-harbor on VM/systemd

set -euo pipefail

HARBOR_USER="l8e-harbor"
HARBOR_GROUP="l8e-harbor"
CONFIG_DIR="/etc/l8e-harbor"
DATA_DIR="/var/lib/l8e-harbor"
LOG_DIR="/var/log/l8e-harbor"
BIN_PATH="/usr/local/bin/l8e-harbor"
SERVICE_FILE="/etc/systemd/system/l8e-harbor.service"

echo "Installing l8e-harbor..."

# Create user and group
if ! id "$HARBOR_USER" &>/dev/null; then
    echo "Creating user $HARBOR_USER..."
    useradd --system --shell /bin/false --home-dir "$DATA_DIR" --create-home "$HARBOR_USER"
fi

# Create directories
echo "Creating directories..."
mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
mkdir -p "$CONFIG_DIR/secrets" "$CONFIG_DIR/tls"

# Set ownership and permissions
chown -R "$HARBOR_USER:$HARBOR_GROUP" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
chmod 700 "$CONFIG_DIR/secrets"
chmod 755 "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

# Copy binary (assuming it's in the current directory)
if [ -f "./l8e-harbor" ]; then
    echo "Installing l8e-harbor binary..."
    cp ./l8e-harbor "$BIN_PATH"
    chmod 755 "$BIN_PATH"
else
    echo "Warning: l8e-harbor binary not found in current directory"
fi

# Create default configuration
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo "Creating default configuration..."
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
mode: vm
server:
  host: 0.0.0.0
  port: 8443
tls:
  cert_file: /etc/l8e-harbor/tls/tls.crt
  key_file: /etc/l8e-harbor/tls/tls.key
secret_provider: localfs
secret_path: /etc/l8e-harbor/secrets
route_store: sqlite
route_store_path: /var/lib/l8e-harbor/routes.db
auth_adapter: local
jwt_ttl_seconds: 900
log_level: INFO
enable_metrics: true
enable_tracing: false
EOF
fi

# Generate self-signed certificate if not exists
if [ ! -f "$CONFIG_DIR/tls/tls.crt" ]; then
    echo "Generating self-signed TLS certificate..."
    openssl req -x509 -newkey rsa:4096 -keyout "$CONFIG_DIR/tls/tls.key" -out "$CONFIG_DIR/tls/tls.crt" -days 365 -nodes -subj "/CN=l8e-harbor"
    chown "$HARBOR_USER:$HARBOR_GROUP" "$CONFIG_DIR/tls/tls.key" "$CONFIG_DIR/tls/tls.crt"
    chmod 600 "$CONFIG_DIR/tls/tls.key"
    chmod 644 "$CONFIG_DIR/tls/tls.crt"
fi

# Generate JWT keys if not exists
if [ ! -f "$CONFIG_DIR/secrets/jwt_private.pem" ]; then
    echo "Generating JWT keys..."
    openssl genrsa -out "$CONFIG_DIR/secrets/jwt_private.pem" 2048
    openssl rsa -in "$CONFIG_DIR/secrets/jwt_private.pem" -pubout -out "$CONFIG_DIR/secrets/jwt_public.pem"
    chown "$HARBOR_USER:$HARBOR_GROUP" "$CONFIG_DIR/secrets/jwt_private.pem" "$CONFIG_DIR/secrets/jwt_public.pem"
    chmod 600 "$CONFIG_DIR/secrets/jwt_private.pem"
    chmod 644 "$CONFIG_DIR/secrets/jwt_public.pem"
fi

# Create default users file if not exists
if [ ! -f "$CONFIG_DIR/secrets/users.yaml" ]; then
    echo "Creating default users file..."
    # Generate bcrypt hash for password "admin123"
    ADMIN_HASH='$2b$12$rQg7B5jKEe4.gDZRMmx4R.e4kGZ4gQ9YKZ4vL8rTmKr4cL2gM3.6i'
    cat > "$CONFIG_DIR/secrets/users.yaml" << EOF
users:
  admin:
    password_hash: "$ADMIN_HASH"
    role: harbor-master
EOF
    chown "$HARBOR_USER:$HARBOR_GROUP" "$CONFIG_DIR/secrets/users.yaml"
    chmod 600 "$CONFIG_DIR/secrets/users.yaml"
    echo "Default admin user created with password: admin123"
fi

# Install systemd service
echo "Installing systemd service..."
cp ./l8e-harbor.service "$SERVICE_FILE"
systemctl daemon-reload

# Enable and start service
echo "Enabling l8e-harbor service..."
systemctl enable l8e-harbor

echo "Installation complete!"
echo ""
echo "To start l8e-harbor: sudo systemctl start l8e-harbor"
echo "To check status: sudo systemctl status l8e-harbor"
echo "To view logs: sudo journalctl -u l8e-harbor -f"
echo ""
echo "Default admin credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "Configuration file: $CONFIG_DIR/config.yaml"
echo "Data directory: $DATA_DIR"
echo "Log directory: $LOG_DIR"