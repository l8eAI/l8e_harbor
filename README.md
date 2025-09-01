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

l8e-harbor uses YAML configuration files with pluggable backends:

```yaml
# Basic configuration
mode: vm  # or k8s, hybrid
server:
  host: 0.0.0.0
  port: 8443
tls:
  enabled: true
secret_provider: localfs  # or kubernetes, vault, aws, gcp
route_store: sqlite      # or memory, configmap, crd
auth_adapter: local      # or k8s_sa, oidc, opaque
```

> 📖 **Complete configuration guide**: [`CONFIGURATION.md`](CONFIGURATION.md)

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

### CLI Management

```bash
# Login and manage routes
harbor-ctl login --username admin
harbor-ctl apply -f examples/mcp-route.yaml
harbor-ctl get routes
```

### API Management

```bash
# Authenticate and create routes via REST API
curl -X POST https://localhost:18443/api/v1/auth/login \
  -d '{"username":"admin","password":"[PASSWORD]"}'
  
curl -X PUT https://localhost:18443/api/v1/routes/my-route \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"path":"/api","backends":[{"url":"http://backend:8080"}]}'
```

## Route Configuration

Routes support advanced features like load balancing, circuit breakers, and middleware:

```yaml
spec:
  id: advanced-route
  path: /api/v2
  backends:
    - url: http://primary-backend:8080
      weight: 100
      health_check_path: /healthz
  retry_policy:
    max_retries: 2
    backoff_ms: 200
  circuit_breaker:
    enabled: true
    failure_threshold: 50
  middleware:
    - name: auth
      config:
        require_role: ["captain"]
    - name: cors
```

## Security

**Multi-layered security architecture:**
- **Authentication**: Local users, Kubernetes ServiceAccounts, OAuth2/OIDC
- **Authorization**: Role-based access control (RBAC)
- **Transport**: TLS required for production
- **Secrets**: Pluggable secret management (filesystem, K8s, Vault, cloud)
- **Audit**: Comprehensive activity logging

> 🔒 **Complete security guide**: [`SECURITY.md`](SECURITY.md)

## Observability

**Enterprise-grade monitoring and tracing:**
- **Metrics**: Prometheus-compatible metrics with request rate, latency, errors
- **Logging**: Structured JSON logs with request tracing
- **Tracing**: OpenTelemetry distributed tracing support
- **Health Checks**: Service and backend health monitoring
- **Dashboards**: Pre-built Grafana dashboards and alerts

> 📊 **Complete observability guide**: [`OBSERVABILITY.md`](OBSERVABILITY.md)

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

**Quick development setup:**

```bash
# Setup development environment
git clone https://github.com/example/l8e-harbor.git
cd l8e-harbor
poetry install

# Run with auto-reload
poetry run python -m app.main --reload

# Run tests and quality checks
poetry run pytest
poetry run ruff check app/
```

> 🛠️ **Complete development guide**: [`DEVELOPMENT.md`](DEVELOPMENT.md)

### CLI Tool

The `harbor-ctl` CLI provides convenient management:

```bash
# Install and basic usage
poetry install
harbor-ctl login --server https://localhost:8443
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

| Topic | Link |
|-------|------|
| **Examples & Tutorials** | [`examples/README.md`](examples/README.md) |
| **Deployment Guides** | [`deployments/README.md`](deployments/README.md) |
| **Configuration** | [`CONFIGURATION.md`](CONFIGURATION.md) |
| **Security** | [`SECURITY.md`](SECURITY.md) |
| **Monitoring** | [`OBSERVABILITY.md`](OBSERVABILITY.md) |
| **Development** | [`DEVELOPMENT.md`](DEVELOPMENT.md) |

## Support

- **Issues**: [GitHub Issues](https://github.com/example/l8e-harbor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/example/l8e-harbor/discussions)

---

**l8e-harbor**: Where AI services dock safely ⚓