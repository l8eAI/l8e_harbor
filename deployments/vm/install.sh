#!/bin/bash
# l8e-harbor VM Installation Script
# Supports Ubuntu/Debian, RHEL/CentOS/Fedora, and macOS
set -e

# Configuration
L8E_VERSION="${L8E_VERSION:-latest}"
L8E_INSTALL_DIR="${L8E_INSTALL_DIR:-/opt/l8e-harbor}"
L8E_DATA_DIR="${L8E_DATA_DIR:-/var/lib/l8e-harbor}"
L8E_CONFIG_DIR="${L8E_CONFIG_DIR:-/etc/l8e-harbor}"
L8E_LOG_DIR="${L8E_LOG_DIR:-/var/log/l8e-harbor}"
L8E_USER="${L8E_USER:-l8e-harbor}"
L8E_GROUP="${L8E_GROUP:-l8e-harbor}"

ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
API_PORT="${API_PORT:-8443}"
UI_PORT="${UI_PORT:-3000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            OS_VERSION=$VERSION_ID
        else
            error "Cannot detect Linux distribution"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_VERSION=$(sw_vers -productVersion)
    else
        error "Unsupported operating system: $OSTYPE"
    fi
    
    log "Detected OS: $OS $OS_VERSION"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y curl wget jq openssl nginx python3 python3-pip python3-venv systemd
            ;;
        rhel|centos|fedora)
            if command -v dnf &> /dev/null; then
                dnf install -y curl wget jq openssl nginx python3 python3-pip systemd
            else
                yum install -y curl wget jq openssl nginx python3 python3-pip systemd
            fi
            ;;
        macos)
            if ! command -v brew &> /dev/null; then
                error "Homebrew is required on macOS. Please install it first: https://brew.sh"
            fi
            brew install curl wget jq openssl nginx python3
            ;;
        *)
            error "Unsupported OS for automatic dependency installation: $OS"
            ;;
    esac
}

# Create system user and directories
setup_user_and_dirs() {
    log "Setting up l8e-harbor user and directories..."
    
    # Create user and group
    if ! id "$L8E_USER" &>/dev/null; then
        if [[ "$OS" == "macos" ]]; then
            # macOS user creation
            NEXT_UID=$(dscl . -list /Users UniqueID | awk '{print $2}' | sort -n | tail -1)
            NEXT_UID=$((NEXT_UID + 1))
            dscl . -create /Users/$L8E_USER
            dscl . -create /Users/$L8E_USER UniqueID $NEXT_UID
            dscl . -create /Users/$L8E_USER PrimaryGroupID 20
            dscl . -create /Users/$L8E_USER UserShell /bin/bash
            dscl . -create /Users/$L8E_USER RealName "l8e-harbor Service User"
            dscl . -create /Users/$L8E_USER NFSHomeDirectory /var/empty
        else
            # Linux user creation
            groupadd -r "$L8E_GROUP" 2>/dev/null || true
            useradd -r -g "$L8E_GROUP" -d "$L8E_DATA_DIR" -s /bin/false -c "l8e-harbor Service User" "$L8E_USER" 2>/dev/null || true
        fi
    fi
    
    # Create directories
    mkdir -p "$L8E_INSTALL_DIR" "$L8E_DATA_DIR" "$L8E_CONFIG_DIR" "$L8E_LOG_DIR"
    mkdir -p "$L8E_DATA_DIR"/{secrets,jwt-keys,routes,users}
    mkdir -p "$L8E_CONFIG_DIR"/certs
    
    # Set ownership
    if [[ "$OS" != "macos" ]]; then
        chown -R "$L8E_USER:$L8E_GROUP" "$L8E_INSTALL_DIR" "$L8E_DATA_DIR" "$L8E_CONFIG_DIR" "$L8E_LOG_DIR"
    else
        chown -R "$L8E_USER:staff" "$L8E_INSTALL_DIR" "$L8E_DATA_DIR" "$L8E_CONFIG_DIR" "$L8E_LOG_DIR"
    fi
    
    chmod 750 "$L8E_DATA_DIR" "$L8E_CONFIG_DIR"
    chmod 700 "$L8E_DATA_DIR/secrets" "$L8E_DATA_DIR/jwt-keys"
}

# Download and install l8e-harbor
install_l8e_harbor() {
    log "Installing l8e-harbor..."
    
    cd "$L8E_INSTALL_DIR"
    
    # For now, we'll create a Python virtual environment and install from source
    # In a real scenario, you'd download pre-built binaries
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Install Python dependencies (this would normally be from a wheel/package)
    cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
bcrypt==4.1.2
kubernetes==28.1.0
aiofiles==23.2.1
watchfiles==0.21.0
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
typer==0.9.0
rich==13.7.0
pyyaml==6.0.1
jinja2==3.1.2
httpx==0.25.2
asyncpg==0.29.0
redis==5.0.1
EOF
    
    pip install -r requirements.txt
    
    # Create a simple launcher script (in production, this would be the actual binary)
    cat > l8e-harbor << 'EOF'
#!/bin/bash
cd /opt/l8e-harbor
source venv/bin/activate
export L8E_CONFIG_FILE="${L8E_CONFIG_FILE:-/etc/l8e-harbor/harbor.yaml}"
export L8E_DATA_DIR="${L8E_DATA_DIR:-/var/lib/l8e-harbor}"
python -m app.main "$@"
EOF
    
    cat > harbor-ctl << 'EOF'
#!/bin/bash
cd /opt/l8e-harbor
source venv/bin/activate
python -m app.cli "$@"
EOF
    
    chmod +x l8e-harbor harbor-ctl
    
    # Create symlinks in /usr/local/bin
    ln -sf "$L8E_INSTALL_DIR/l8e-harbor" /usr/local/bin/l8e-harbor
    ln -sf "$L8E_INSTALL_DIR/harbor-ctl" /usr/local/bin/harbor-ctl
}

# Generate SSL certificates
generate_ssl_certs() {
    log "Generating self-signed SSL certificates..."
    
    CERT_DIR="$L8E_CONFIG_DIR/certs"
    
    # Generate private key
    openssl genpkey -algorithm RSA -out "$CERT_DIR/server.key" -pkcs8 2>/dev/null
    
    # Generate certificate signing request
    openssl req -new -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" -subj "/C=US/ST=State/L=City/O=l8e-harbor/CN=localhost" 2>/dev/null
    
    # Generate self-signed certificate
    openssl x509 -req -in "$CERT_DIR/server.csr" -signkey "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" -days 365 2>/dev/null
    
    # Clean up CSR
    rm "$CERT_DIR/server.csr"
    
    # Set permissions
    chmod 600 "$CERT_DIR/server.key"
    chmod 644 "$CERT_DIR/server.crt"
    
    if [[ "$OS" != "macos" ]]; then
        chown "$L8E_USER:$L8E_GROUP" "$CERT_DIR"/server.*
    else
        chown "$L8E_USER:staff" "$CERT_DIR"/server.*
    fi
}

# Generate JWT keys and admin credentials
generate_admin_setup() {
    log "Generating JWT keys and admin credentials..."
    
    JWT_DIR="$L8E_DATA_DIR/jwt-keys"
    
    # Generate JWT key pair
    openssl genpkey -algorithm RSA -out "$JWT_DIR/jwt-private.pem" -pkcs8 2>/dev/null
    openssl pkey -in "$JWT_DIR/jwt-private.pem" -pubout -out "$JWT_DIR/jwt-public.pem" 2>/dev/null
    
    chmod 600 "$JWT_DIR"/jwt-*.pem
    if [[ "$OS" != "macos" ]]; then
        chown "$L8E_USER:$L8E_GROUP" "$JWT_DIR"/jwt-*.pem
    else
        chown "$L8E_USER:staff" "$JWT_DIR"/jwt-*.pem
    fi
    
    # Generate secure admin password
    ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    # Create admin credentials file
    cat > "$L8E_DATA_DIR/admin-credentials.json" << EOF
{
    "username": "$ADMIN_USERNAME",
    "password": "$ADMIN_PASSWORD",
    "role": "harbor-master",
    "api_url": "https://localhost:$API_PORT",
    "ui_url": "http://localhost:$UI_PORT",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "created_by": "vm-installer",
    "login_instructions": {
        "web_ui": "Open http://localhost:$UI_PORT and login with the above credentials",
        "cli": "Use 'harbor-ctl login --server=https://localhost:$API_PORT --username=$ADMIN_USERNAME' and enter the password when prompted"
    }
}
EOF
    
    chmod 600 "$L8E_DATA_DIR/admin-credentials.json"
    if [[ "$OS" != "macos" ]]; then
        chown "$L8E_USER:$L8E_GROUP" "$L8E_DATA_DIR/admin-credentials.json"
    else
        chown "$L8E_USER:staff" "$L8E_DATA_DIR/admin-credentials.json"
    fi
    
    # Create initial users file with admin
    ADMIN_PASSWORD_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw('$ADMIN_PASSWORD'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))")
    
    cat > "$L8E_DATA_DIR/users/users.json" << EOF
{
    "users": [
        {
            "username": "$ADMIN_USERNAME",
            "password_hash": "$ADMIN_PASSWORD_HASH",
            "role": "harbor-master",
            "meta": {
                "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
                "created_by": "vm-installer"
            }
        }
    ]
}
EOF
    
    chmod 600 "$L8E_DATA_DIR/users/users.json"
    if [[ "$OS" != "macos" ]]; then
        chown "$L8E_USER:$L8E_GROUP" "$L8E_DATA_DIR/users/users.json"
    else
        chown "$L8E_USER:staff" "$L8E_DATA_DIR/users/users.json"
    fi
    
    log "Admin credentials generated and stored in $L8E_DATA_DIR/admin-credentials.json"
}

# Create configuration file
create_config() {
    log "Creating l8e-harbor configuration..."
    
    cat > "$L8E_CONFIG_DIR/harbor.yaml" << EOF
# l8e-harbor Configuration
server:
  host: "0.0.0.0"
  port: $API_PORT
  ssl:
    enabled: true
    cert_file: "$L8E_CONFIG_DIR/certs/server.crt"
    key_file: "$L8E_CONFIG_DIR/certs/server.key"

auth:
  adapter: "local"
  local:
    users_file: "$L8E_DATA_DIR/users/users.json"
  jwt:
    private_key_file: "$L8E_DATA_DIR/jwt-keys/jwt-private.pem"
    public_key_file: "$L8E_DATA_DIR/jwt-keys/jwt-public.pem"
    issuer: "l8e-harbor"
    audience: ["l8e-harbor-api", "l8e-harbor-ui"]
    expires_in: 3600

secrets:
  provider: "file"
  file:
    secrets_dir: "$L8E_DATA_DIR/secrets"

routes:
  store: "file"
  file:
    routes_file: "$L8E_DATA_DIR/routes/routes.json"
    watch: true

observability:
  metrics:
    enabled: true
    path: "/metrics"
    port: 9090
  logging:
    level: "info"
    format: "json"
    file: "$L8E_LOG_DIR/l8e-harbor.log"

proxy:
  timeout: 30s
  max_retries: 3
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    timeout: 60s

cors:
  allowed_origins:
    - "http://localhost:$UI_PORT"
    - "https://localhost:$UI_PORT"
  allowed_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  allowed_headers: ["Authorization", "Content-Type", "X-Requested-With"]

bootstrap:
  enabled: true
  allow_admin_creation: true
EOF
    
    chmod 640 "$L8E_CONFIG_DIR/harbor.yaml"
    if [[ "$OS" != "macos" ]]; then
        chown "root:$L8E_GROUP" "$L8E_CONFIG_DIR/harbor.yaml"
    else
        chown "root:staff" "$L8E_CONFIG_DIR/harbor.yaml"
    fi
}

# Create systemd service (Linux only)
create_systemd_service() {
    if [[ "$OS" == "macos" ]]; then
        return 0  # Skip systemd on macOS
    fi
    
    log "Creating systemd service..."
    
    cat > /etc/systemd/system/l8e-harbor.service << EOF
[Unit]
Description=l8e-harbor AI Gateway
Documentation=https://github.com/example/l8e-harbor
After=network.target

[Service]
Type=exec
User=$L8E_USER
Group=$L8E_GROUP
ExecStart=/usr/local/bin/l8e-harbor
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=l8e-harbor

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$L8E_DATA_DIR $L8E_LOG_DIR
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

# Environment
Environment=L8E_CONFIG_FILE=$L8E_CONFIG_DIR/harbor.yaml
Environment=L8E_DATA_DIR=$L8E_DATA_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable l8e-harbor.service
}

# Create launchd service (macOS only)
create_launchd_service() {
    if [[ "$OS" != "macos" ]]; then
        return 0  # Skip launchd on Linux
    fi
    
    log "Creating launchd service..."
    
    cat > /Library/LaunchDaemons/com.l8e-harbor.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.l8e-harbor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/l8e-harbor</string>
    </array>
    <key>UserName</key>
    <string>$L8E_USER</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>L8E_CONFIG_FILE</key>
        <string>$L8E_CONFIG_DIR/harbor.yaml</string>
        <key>L8E_DATA_DIR</key>
        <string>$L8E_DATA_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$L8E_LOG_DIR/l8e-harbor.log</string>
    <key>StandardErrorPath</key>
    <string>$L8E_LOG_DIR/l8e-harbor.error.log</string>
</dict>
</plist>
EOF
    
    launchctl load /Library/LaunchDaemons/com.l8e-harbor.plist
}

# Setup nginx for UI (optional)
setup_nginx_ui() {
    log "Setting up nginx for UI (optional)..."
    
    # This is a placeholder - in a real deployment, you'd:
    # 1. Download and extract the UI build
    # 2. Configure nginx to serve it
    # 3. Set up reverse proxy to API
    
    warn "UI setup skipped - manual configuration required"
    warn "Please download and configure the l8e-harbor UI separately"
}

# Validate installation
validate_installation() {
    log "Validating installation..."
    
    # Check if files exist
    for file in "$L8E_INSTALL_DIR/l8e-harbor" "$L8E_CONFIG_DIR/harbor.yaml" "$L8E_DATA_DIR/admin-credentials.json"; do
        if [[ ! -f "$file" ]]; then
            error "Missing file: $file"
        fi
    done
    
    # Start service
    if [[ "$OS" == "macos" ]]; then
        log "Starting l8e-harbor via launchd..."
        launchctl start com.l8e-harbor
        sleep 5
    else
        log "Starting l8e-harbor via systemd..."
        systemctl start l8e-harbor.service
        sleep 5
        
        # Check service status
        if systemctl is-active --quiet l8e-harbor.service; then
            log "✓ l8e-harbor service is running"
        else
            warn "Service may not be running. Check with: systemctl status l8e-harbor.service"
        fi
    fi
    
    # Test API connectivity
    log "Testing API connectivity..."
    sleep 5  # Give service time to start
    
    if curl -k -f "https://localhost:$API_PORT/health" >/dev/null 2>&1; then
        log "✓ API health check passed"
    else
        warn "API health check failed - service may still be starting"
    fi
}

# Print installation summary
print_summary() {
    log "Installation completed!"
    echo ""
    echo "=========================================="
    echo "l8e-harbor Installation Summary"
    echo "=========================================="
    echo ""
    echo "Installation Directory: $L8E_INSTALL_DIR"
    echo "Data Directory: $L8E_DATA_DIR"
    echo "Configuration Directory: $L8E_CONFIG_DIR"
    echo "Log Directory: $L8E_LOG_DIR"
    echo ""
    echo "API URL: https://localhost:$API_PORT"
    echo "UI URL: http://localhost:$UI_PORT (manual setup required)"
    echo ""
    echo "Admin credentials stored in:"
    echo "  $L8E_DATA_DIR/admin-credentials.json"
    echo ""
    echo "Service Management:"
    if [[ "$OS" == "macos" ]]; then
        echo "  Start:   sudo launchctl start com.l8e-harbor"
        echo "  Stop:    sudo launchctl stop com.l8e-harbor"
        echo "  Logs:    tail -f $L8E_LOG_DIR/l8e-harbor.log"
    else
        echo "  Start:   sudo systemctl start l8e-harbor.service"
        echo "  Stop:    sudo systemctl stop l8e-harbor.service"
        echo "  Status:  sudo systemctl status l8e-harbor.service"
        echo "  Logs:    sudo journalctl -u l8e-harbor.service -f"
    fi
    echo ""
    echo "CLI Commands:"
    echo "  harbor-ctl --help"
    echo "  harbor-ctl login --server=https://localhost:$API_PORT"
    echo ""
    echo "To view admin credentials:"
    echo "  sudo cat $L8E_DATA_DIR/admin-credentials.json | jq ."
    echo ""
    echo "Next Steps:"
    echo "1. Review configuration: $L8E_CONFIG_DIR/harbor.yaml"
    echo "2. Set up UI manually (see documentation)"
    echo "3. Configure routes using harbor-ctl or API"
    echo "4. Set up monitoring and backups"
    echo "=========================================="
}

# Main installation function
main() {
    log "Starting l8e-harbor installation..."
    
    detect_os
    check_root
    install_dependencies
    setup_user_and_dirs
    install_l8e_harbor
    generate_ssl_certs
    generate_admin_setup
    create_config
    
    if [[ "$OS" == "macos" ]]; then
        create_launchd_service
    else
        create_systemd_service
    fi
    
    setup_nginx_ui
    validate_installation
    print_summary
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi