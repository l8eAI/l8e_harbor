# l8e-harbor

**Open, Pluggable, Deployment-Agnostic AI Gateway**

l8e-harbor is a secure, high-performance AI gateway designed to run anywhere - from Kubernetes clusters to bare metal VMs. It provides pluggable authentication, flexible routing, and comprehensive observability for AI services.

## Features

### Core Capabilities
- **Universal Deployment**: Runs on Kubernetes or VMs with the same binary
- **Pluggable Architecture**: Swap authentication, secrets, and storage backends
- **Advanced Routing**: Path-based routing with middleware, retries, and circuit breakers
- **Security First**: JWT-based auth, TLS required, least-privilege design
- **Production Ready**: Metrics, tracing, health checks, and audit logging

### Supported Backends

**Authentication:**
- Local users with JWT tokens (VM/dev)
- Kubernetes ServiceAccount tokens 
- OAuth2/OIDC (optional)
- Pre-shared tokens

**Secret Management:**
- Local filesystem (VM)
- Kubernetes Secrets
- HashiCorp Vault (adapter)
- AWS Secrets Manager (adapter)
- GCP Secret Manager (adapter)

**Route Storage:**
- In-memory with file snapshots
- SQLite database
- Kubernetes ConfigMaps
- Custom Resource Definitions (K8s)

## Quick Start

### Option 1: Docker Compose (Development)

```bash
# Clone repository
git clone https://github.com/example/l8e-harbor.git
cd l8e-harbor

# Start with Docker Compose (includes automatic admin setup)
cd deployments/docker
docker-compose -f docker-compose.full.yml up -d

# Wait for admin initialization to complete
docker-compose -f docker-compose.full.yml logs admin-init

# Get admin credentials (generated randomly)
docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) cat /app/shared/admin-credentials.json

# Test the gateway
curl http://localhost:18443/health

# Access the UI
open http://localhost:3000
```

**Admin Account Access:**
The system automatically generates a secure admin account during bootstrap:
- **Username**: `admin`
- **Password**: 32-character random string (see credentials file)
- **Role**: `harbor-master`

### Option 2: Kubernetes with Helm

```bash
# Install with Helm
helm install l8e-harbor ./deployments/helm \
  --set config.mode=k8s \
  --set config.secretProvider=kubernetes \
  --set config.routeStore=configmap

# Port forward to test
kubectl port-forward svc/l8e-harbor 8443:443
curl http://localhost:8443/health
```

### Option 3: VM/Systemd Installation

```bash
# Install on VM
sudo ./deployments/systemd/install.sh

# Start service
sudo systemctl start l8e-harbor

# Test
curl http://localhost:8443/health
```

## Example: Calculator MCP Service

This example demonstrates l8e-harbor's efficacy by proxying a Model Context Protocol (MCP) service with comprehensive logging, metrics, and reliability features.

> 📁 **Complete example available in [`examples/calculator-mcp/`](examples/calculator-mcp/)**

### Quick Start

1. **Navigate to the example directory**:
   ```bash
   cd examples/calculator-mcp
   ```

2. **Start all services with Docker Compose**:
   ```bash
   docker-compose up --build -d
   ```

3. **Test the MCP service through l8e-harbor**:
   ```bash
   # List available tools
   curl -X POST http://localhost:18080/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list",
       "params": {}
     }'

   # Call the calculator
   curl -X POST http://localhost:18080/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "calculator",
         "arguments": {
           "expression": "2 + 3 * 4"
         }
       }
     }'
   ```

### What's Included

The complete example demonstrates:

- **Production-Ready MCP Service**: Full JSON-RPC 2.0 implementation with calculator and unit conversion tools
- **Complete Docker Setup**: Multi-container orchestration with health checks and networking
- **Advanced l8e-harbor Config**: Circuit breaker, rate limiting, retries, middleware stack
- **Observability Stack**: Structured logging, Prometheus metrics, error tracking
- **Real-World Scenarios**: Error handling, health monitoring, load balancing

### Example Response Flow

**Request**:
```bash
curl -X POST http://localhost:18080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "calculator",
      "arguments": {
        "expression": "sqrt(16) + pow(2, 3)"
      }
    }
  }'
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Result: 12.0"
      }
    ]
  }
}
```

**l8e-harbor Logs**:
```json
{
  "timestamp": "2025-09-01T12:00:05Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "req_002",
  "method": "POST",
  "path": "/mcp",
  "status_code": 200,
  "duration_ms": 21.8,
  "route_id": "calculator-mcp",
  "backend": "http://calculator-mcp:3000",
  "user": "anonymous"
}
```

**MCP Service Logs**:
```
2025-09-01 12:00:05 [INFO] calculator-mcp: Calculator: 'sqrt(16) + pow(2, 3)' = 12.0
```

### Observability Features

**Prometheus Metrics** (available at http://localhost:9090):
```prometheus
# Request rate and latency
l8e_proxy_requests_total{route_id="calculator-mcp",method="POST",status_code="200"} 156
l8e_proxy_request_duration_seconds{route_id="calculator-mcp",quantile="0.95"} 0.025

# Reliability metrics
l8e_circuit_breaker_state{route_id="calculator-mcp"} 0  # 0=closed, 1=open
l8e_backend_up{route_id="calculator-mcp",backend="calculator-mcp:3000"} 1
```

### Advanced Features Demonstrated

1. **Circuit Breaker**: Automatically opens at 50% failure rate, protects against cascading failures
2. **Rate Limiting**: 100 requests/minute with burst allowance
3. **Health Checks**: Continuous backend monitoring with auto-failover
4. **Retry Policy**: Intelligent retry on 5xx errors with exponential backoff
5. **Structured Logging**: JSON logs ready for ELK/Loki ingestion
6. **Security**: CORS handling, header filtering, TLS termination

### Service Endpoints

- **MCP Service (via l8e-harbor)**: http://localhost:18080/mcp
- **l8e-harbor Management**: https://localhost:18443
- **Prometheus Dashboard**: http://localhost:9090
- **Direct MCP Access**: http://localhost:3001 (for debugging)

### Key Benefits

✅ **Zero Code Changes**: Existing MCP service works unchanged  
✅ **Enterprise Observability**: Structured logs, metrics, distributed tracing ready  
✅ **Production Reliability**: Circuit breaker, retries, health checks, rate limiting  
✅ **Operational Excellence**: Easy deployment, monitoring, and debugging  
✅ **Security**: TLS termination, header filtering, authentication ready

> 📖 **See the complete example with detailed instructions**: [`examples/calculator-mcp/README.md`](examples/calculator-mcp/README.md)

## Configuration

l8e-harbor uses a simple YAML configuration file. Example configurations are available in the [`examples/`](examples/) directory:

- **[`examples/config.yaml`](examples/config.yaml)** - Minimal development configuration with HTTP and local file storage
- **[`examples/mcp-route.yaml`](examples/mcp-route.yaml)** - Complete route definition with middleware and health checks  
- **[`examples/routes-backup.yaml`](examples/routes-backup.yaml)** - Route export/backup format example

### Basic Configuration

```yaml
# examples/config.yaml - Minimal l8e-harbor configuration for testing
mode: vm
server:
  host: 0.0.0.0
  port: 8443

# TLS - use HTTP for testing
tls:
  enabled: false

# Use local file-based providers for testing
secret_provider: localfs
secret_path: ./data/secrets
route_store: memory
route_store_path: ./data/routes
auth_adapter: local

# Logging
log_level: INFO
enable_metrics: false
enable_tracing: false

# Default routes for testing
routes: []
```

### Production Configuration

```yaml
# /etc/l8e-harbor/config.yaml - Production configuration
mode: vm  # or k8s, hybrid
server:
  host: 0.0.0.0
  port: 8443
tls:
  enabled: true
  cert_file: /etc/l8e-harbor/tls/tls.crt
  key_file: /etc/l8e-harbor/tls/tls.key
secret_provider: localfs  # or kubernetes, vault, aws, gcp
secret_path: /etc/l8e-harbor/secrets
route_store: sqlite  # or memory, configmap, crd
auth_adapter: local  # or k8s_sa, oidc, opaque
log_level: INFO
enable_metrics: true
enable_tracing: true
```

Configuration precedence: CLI flags → Environment variables → Config file → Defaults

## Admin Account Management

### Getting Admin Credentials

l8e-harbor automatically generates secure admin credentials during the initial bootstrap process.

#### Docker Compose Deployment

After running `docker-compose -f docker-compose.full.yml up -d` from the `deployments/docker` directory, retrieve admin credentials:

```bash
# Run these commands from the deployments/docker directory
cd deployments/docker

# Method 1: View the complete credentials file
docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) cat /app/shared/admin-credentials.json

# Method 2: Check the admin-init logs for credentials
docker-compose -f docker-compose.full.yml logs admin-init

# Method 3: View the summary file
docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) cat /app/shared/admin-setup-summary.txt
```

#### Kubernetes Deployment

```bash
# Get admin credentials from Kubernetes Secret
kubectl get secret l8e-harbor-admin-creds -o jsonpath='{.data.username}' | base64 -d
kubectl get secret l8e-harbor-admin-creds -o jsonpath='{.data.password}' | base64 -d

# Or view the complete secret
kubectl get secret l8e-harbor-admin-creds -o yaml
```

#### VM/Systemd Deployment

```bash
# View admin credentials
sudo cat /etc/l8e-harbor/secrets/admin-credentials.json

# Check initialization logs
sudo journalctl -u l8e-harbor-init | grep "admin credentials"
```

### Admin Credential Security

- **Random Generation**: Admin password is cryptographically secure (32+ characters)
- **One-Time Display**: Credentials are logged once during initialization
- **Secure Storage**: Stored with restrictive file permissions (600)
- **Rotation Support**: Password can be rotated without service restart
- **Role-Based**: Admin has `harbor-master` role with full system access

### First Login Process

1. **Get Credentials**: Use one of the methods above to retrieve the admin password
2. **Web UI Login**: 
   - Navigate to `http://localhost:3000` (Docker Compose)
   - Username: `admin`
   - Password: [from credentials file]
3. **CLI Login**:
   ```bash
   harbor-ctl login --server=http://localhost:18443 --username=admin
   ```
4. **API Login**:
   ```bash
   curl -X POST http://localhost:18443/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"[admin-password]"}'
   ```

### Password Reset

To reset the admin password:

```bash
# For Docker Compose
docker-compose -f docker-compose.full.yml down -v
docker-compose -f docker-compose.full.yml up -d

# For Kubernetes
kubectl delete secret l8e-harbor-admin-creds
helm upgrade l8e-harbor ./deployments/helm

# For VM
sudo systemctl stop l8e-harbor
sudo rm -f /etc/l8e-harbor/secrets/users.json
sudo systemctl start l8e-harbor
```

## Managing Routes

### Using harbor-ctl CLI

```bash
# Login
harbor-ctl login --username admin

# Create a route (see examples/mcp-route.yaml for complete example)
harbor-ctl apply -f examples/mcp-route.yaml

# List routes
harbor-ctl get routes

# Export all routes
harbor-ctl export routes -o backup.yaml
```

### Using Management API

```bash
# Get JWT token (use actual admin password from credentials file)
curl -k -X POST https://localhost:18443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"[ADMIN_PASSWORD_FROM_BOOTSTRAP]"}'

# Create route
curl -k -X PUT https://localhost:18443/api/v1/routes/my-route \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/api/v1",
    "backends": [{"url": "http://backend:8080"}],
    "middleware": [{"name": "logging"}]
  }'
```

## Route Configuration

Routes support extensive configuration options:

```yaml
spec:
  id: advanced-route
  description: "Advanced API route with all features"
  path: /api/v2
  methods: ["GET", "POST", "PUT", "DELETE"]
  backends:
    - url: http://primary-backend:8080
      weight: 100
      health_check_path: /healthz
    - url: http://secondary-backend:8080
      weight: 50
  priority: 10
  timeout_ms: 5000
  retry_policy:
    max_retries: 2
    backoff_ms: 200
    retry_on: ["5xx", "timeout"]
  circuit_breaker:
    enabled: true
    failure_threshold: 50
    minimum_requests: 20
  middleware:
    - name: auth
      config:
        require_role: ["captain"]
    - name: header-rewrite
      config:
        set:
          X-Service: "my-service"
        remove: ["X-Debug"]
  matchers:
    - name: header
      value: "X-Version"
      op: "equals"
```

## Security

### Authentication & Authorization

l8e-harbor supports multiple authentication methods:

1. **Local Users** (VM/development):
   - Username/password with bcrypt hashing
   - JWT tokens with RSA256 signing
   - Role-based access control

2. **Kubernetes ServiceAccounts**:
   - Native K8s token validation
   - Automatic role mapping
   - RBAC integration

3. **OAuth2/OIDC** (optional):
   - External identity providers
   - Claims-based role mapping

### TLS & Transport Security

- TLS required for Management API in production
- Support for custom certificates or auto-generated
- cert-manager integration in Kubernetes

### Secrets Management

Sensitive data is stored securely:
- JWT signing keys
- User credentials (bcrypt hashed)
- TLS certificates
- Backend credentials (future)

## Observability

### Metrics

Prometheus metrics exposed on `/metrics`:

```
# Request metrics
l8e_proxy_requests_total{route_id,method,status_code,backend}
l8e_proxy_request_duration_seconds{route_id,backend}

# System metrics
l8e_routes_total
l8e_backend_up{backend,route_id}
l8e_circuit_breaker_state{backend,route_id}
l8e_auth_attempts_total{adapter_type,status}
```

### Structured Logging

JSON structured logs with request tracing:

```json
{
  "timestamp": "2024-08-31T10:30:00Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "req_123",
  "method": "GET",
  "path": "/api/v1/data",
  "status_code": 200,
  "duration_ms": 45.2,
  "route_id": "api-route",
  "backend": "http://service:8080",
  "user": "alice"
}
```

### Distributed Tracing

OpenTelemetry support with:
- FastAPI auto-instrumentation
- Custom spans for routing logic
- Backend call tracing
- Jaeger integration

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Clients       │───▶│   l8e-harbor     │───▶│   Backends      │
│                 │    │                  │    │                 │
│ • Web Apps      │    │ • Route Matching │    │ • AI Services   │
│ • APIs          │    │ • Authentication │    │ • HTTP APIs     │
│ • CLIs          │    │ • Load Balancing │    │ • gRPC Services │
└─────────────────┘    │ • Circuit Breaking│    └─────────────────┘
                       │ • Observability  │
                       └──────────────────┘
                               │
                       ┌──────────────────┐
                       │   Adapters       │
                       │                  │
                       │ • Auth: Local/K8s│
                       │ • Secrets: FS/K8s│
                       │ • Storage: DB/CM │
                       └──────────────────┘
```

## Development

### Prerequisites

- Python 3.9+
- Poetry for dependency management
- Docker (optional)
- Kubernetes cluster (for K8s features)

### Setup

```bash
# Clone and setup
git clone https://github.com/example/l8e-harbor.git
cd l8e-harbor

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run locally
poetry run python -m app.main --reload
```

### Running Tests

```bash
# Unit tests
poetry run pytest tests/

# Integration tests (requires Docker)
docker-compose -f deployments/docker/docker-compose.yaml up -d
poetry run pytest tests/integration/

# Linting and type checking
poetry run ruff check app/
poetry run mypy app/
poetry run bandit -r app/
```

### Building harbor-ctl CLI

The `harbor-ctl` command-line interface provides convenient management capabilities for l8e-harbor. Here are several ways to build and install it:

#### Option 1: Install with Poetry (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/example/l8e-harbor.git
cd l8e-harbor

# Install dependencies and development environment
poetry install

# Use harbor-ctl directly with poetry
poetry run harbor-ctl --help
poetry run harbor-ctl login --server https://localhost:8443

# Or activate the virtual environment
poetry shell
harbor-ctl --help
```

#### Option 2: Build Standalone Binary with PyInstaller

```bash
# Install PyInstaller in the development environment
poetry run pip install pyinstaller

# Build standalone executable
poetry run pyinstaller \
    --onefile \
    --name harbor-ctl \
    --add-data "app:app" \
    app/cli.py

# The binary will be in dist/harbor-ctl
./dist/harbor-ctl --help
```

#### Option 3: Install as Python Package

```bash
# Build wheel package
poetry build

# Install the wheel (creates harbor-ctl command)
pip install dist/l8e_harbor-*.whl

# Or install directly from source
pip install .

# Now harbor-ctl is available system-wide
harbor-ctl --help
```

#### Option 4: Docker-based CLI

Create a containerized version of harbor-ctl:

```dockerfile
# Dockerfile.cli
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml poetry.lock ./
COPY app/ ./app/

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

ENTRYPOINT ["harbor-ctl"]
```

```bash
# Build the CLI container
docker build -f Dockerfile.cli -t harbor-ctl .

# Use as a command
docker run --rm harbor-ctl --help
docker run --rm -it harbor-ctl login --server https://host.docker.internal:8443
```

#### Option 5: Cross-platform Builds

For distributing harbor-ctl across platforms:

```bash
# Install cross-platform build tools
poetry run pip install pyinstaller

# Build for current platform
poetry run pyinstaller --onefile app/cli.py --name harbor-ctl

# For cross-compilation, use Docker with different base images
docker run --rm -v $(pwd):/workspace python:3.11-slim bash -c "
cd /workspace && 
pip install poetry pyinstaller && 
poetry install --no-dev && 
poetry run pyinstaller --onefile app/cli.py --name harbor-ctl-linux
"
```

#### Verification

Test your harbor-ctl installation:

```bash
# Check version and help
harbor-ctl --help
harbor-ctl --version

# Test connection (replace with your l8e-harbor instance)
harbor-ctl login --server https://localhost:8443 --username admin

# Test basic operations
harbor-ctl get routes
harbor-ctl get users
```

#### harbor-ctl Features

The CLI provides comprehensive management capabilities:

**Authentication:**
```bash
harbor-ctl login --server https://localhost:8443 --username admin
harbor-ctl logout
```

**Route Management:**
```bash
# List all routes
harbor-ctl get routes

# Create route from YAML
harbor-ctl apply -f route.yaml

# Export routes
harbor-ctl export routes -o backup.yaml

# Delete route
harbor-ctl delete route my-route-id
```

**User Management:**
```bash
# List users
harbor-ctl get users

# Create user
harbor-ctl create user alice --role captain

# Update user role
harbor-ctl update user alice --role harbor-master
```

**System Operations:**
```bash
# Health check
harbor-ctl health

# View system metrics
harbor-ctl metrics

# Configuration validation
harbor-ctl validate -f config.yaml
```

#### Distribution

For teams and production deployments:

1. **GitHub Releases**: Attach pre-built binaries to releases
2. **Package Repositories**: Publish to PyPI for `pip install harbor-ctl`  
3. **Container Registry**: Push CLI container for easy distribution
4. **Package Managers**: Create packages for apt, yum, brew, chocolatey

Example release script:
```bash
#!/bin/bash
# scripts/build-release.sh

VERSION=$(poetry version -s)

# Build wheel
poetry build

# Build binaries for multiple platforms
for platform in linux macos windows; do
    echo "Building for $platform..."
    # Platform-specific build commands here
done

# Create release
gh release create "v$VERSION" \
    dist/l8e_harbor-$VERSION-py3-none-any.whl \
    dist/harbor-ctl-linux \
    dist/harbor-ctl-macos \
    dist/harbor-ctl-windows.exe
```

## Roadmap

- [ ] gRPC proxy support
- [ ] Advanced load balancing algorithms
- [ ] Rate limiting middleware
- [ ] WebSocket proxying
- [ ] Multi-cluster routing
- [ ] Admin UI dashboard
- [ ] Terraform modules
- [ ] Performance benchmarks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/example/l8e-harbor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/example/l8e-harbor/discussions)

---

**l8e-harbor**: Where AI services dock safely ⚓