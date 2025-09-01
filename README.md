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

Choose your deployment method:

| Method | Use Case | Setup Time |
|--------|----------|------------|
| [Docker Compose](deployments/#docker-compose) | Development, Testing | 2 minutes |
| [Kubernetes + Helm](deployments/#kubernetes-helm) | Production, Staging | 5 minutes |
| [VM/Systemd](deployments/#vmsystemd) | Legacy systems, Bare metal | 10 minutes |

### Quick Deploy with Docker Compose

```bash
# Clone and start
git clone https://github.com/example/l8e-harbor.git
cd l8e-harbor/deployments/docker
docker-compose -f docker-compose.full.yml up -d

# Get admin credentials and test
docker-compose -f docker-compose.full.yml logs admin-init
curl http://localhost:18443/health
```

> 📖 **For complete deployment options and production setup**: [`deployments/README.md`](deployments/README.md)

## Examples

Practical examples and configurations are available to help you get started:

- **Calculator MCP Service**: Complete production example with observability
- **Configuration Templates**: Ready-to-use YAML configurations  
- **Route Definitions**: Advanced routing examples with middleware

> 📁 **Explore all examples**: [`examples/README.md`](examples/README.md)

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

l8e-harbor automatically generates secure admin credentials during bootstrap. The admin account has the `harbor-master` role with full system access.

### Getting Admin Credentials

Retrieve generated admin credentials based on your deployment:

```bash
# Docker Compose
docker-compose logs admin-init
docker exec container cat /app/shared/admin-credentials.json

# Kubernetes
kubectl get secret l8e-harbor-admin-creds -o yaml

# VM/Systemd  
sudo cat /etc/l8e-harbor/secrets/admin-credentials.json
```

> 📖 **Complete admin management guide**: [`deployments/README.md#admin-account-access`](deployments/README.md#admin-account-access)

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

### harbor-ctl CLI

The `harbor-ctl` command-line interface provides convenient management capabilities:

```bash
# Install and use
poetry install
poetry run harbor-ctl --help

# Basic operations
harbor-ctl login --server https://localhost:8443 --username admin
harbor-ctl get routes
harbor-ctl apply -f examples/mcp-route.yaml
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

See [`deployments/README.md`](deployments/README.md) for development environment setup.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Documentation

- **Examples & Tutorials**: [`examples/README.md`](examples/README.md)
- **Deployment Guides**: [`deployments/README.md`](deployments/README.md)  
- **API Documentation**: [docs/](docs/)

## Support

- **Issues**: [GitHub Issues](https://github.com/example/l8e-harbor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/example/l8e-harbor/discussions)

---

**l8e-harbor**: Where AI services dock safely ⚓