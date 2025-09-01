# l8e-harbor

**Open, Pluggable, Deployment-Agnostic AI Gateway**

l8e-harbor is a secure, high-performance AI gateway designed to run anywhere. It acts as a smart, unified front door for all your AI services, giving you centralized control over authentication, routing, security, and observability.

## What is l8e-harbor?

Managing access to multiple AI models and services (like OpenAI, Anthropic, Cohere, or custom-built tools) can be complex. Each has different authentication methods, logging formats, and security requirements.

l8e-harbor solves this by providing a single, consistent entry point. Think of it as an airport control tower for your AI traffic: it inspects incoming requests, ensures they are authorized, applies rules and transformations, and then directs them safely to the correct backend service.

This centralizes complex logic, simplifies your client applications, and gives you a powerful control plane for all your AI operations.

## How It Works: The Core Concepts

l8e-harbor's behavior is defined by a few key concepts:

### 1. Routes: The Heart of the Gateway

A **Route** is the fundamental rule that tells l8e-harbor how to handle an incoming request. It maps a public-facing path to a private, backend AI service.

Each route defines:
- **Path**: The public URL path your users will request (e.g., `/mcp/jira/search`)
- **Target**: The internal address of the backend service to which the request should be forwarded (e.g., `http://jira-mcp-service:8080`)
- **Middleware**: A chain of actions to execute before the request is forwarded

### 2. Middleware: The Brains of the Operation

**Middleware** are plugins that inspect and modify requests as they pass through the gateway. This is where l8e-harbor's power lies. You can chain middleware together to:
- **Authenticate**: Verify JWTs, API keys, or handle complex OAuth 2.0 flows
- **Rate Limit**: Protect your backend services from abuse
- **Log & Audit**: Create a detailed, consistent log of all AI requests
- **Add Retries & Circuit Breakers**: Improve the reliability of your system

### 3. Pluggable Backends: Ultimate Flexibility

l8e-harbor is designed to be deployment-agnostic. You can swap out its core components to fit your exact infrastructure needs for authentication, secret management, and route storage.

## A Concrete Example: Route Configuration

Here's a simple YAML configuration to illustrate how a route works:

```yaml
# l8e-harbor-config.yaml
routes:
  # ROUTE 1: A simple proxy to a generic language model
  - path: "/v1/chat/generic"
    target: "https://api.openserver.ai/v1/chat"
    middleware:
      # Middleware 1: Check for a valid API Key in the header
      - name: "authentication"
        config:
          provider: "preshared-token"
      # Middleware 2: Log the request details
      - name: "audit-log"

  # ROUTE 2: A protected route for a Jira MCP tool
  - path: "/mcp/jira"
    target: "http://my-jira-mcp-container:8080"
    middleware:
      # This middleware handles the entire OAuth 2.0 flow for Jira.
      # The end-user doesn't need to manage tokens; the gateway does it for them.
      - name: "oauth2"
        config:
          provider: "atlassian-jira"
          clientId: "{{secret:jira_client_id}}"      # Securely load secrets
          clientSecret: "{{secret:jira_client_secret}}"
          scopes: ["read:jira-work", "manage:jira-project"]
```

## Key Features

- **Universal Deployment**: Runs on Kubernetes or VMs with the same binary
- **Pluggable Architecture**: Swap authentication, secrets, and storage backends
- **Advanced Routing**: Path-based routing with a powerful middleware system
- **Security First**: JWT-based auth, TLS required, least-privilege design
- **Production Ready**: Metrics, tracing, health checks, and audit logging

## Supported Backends

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
# Clone repository and navigate into it
git clone https://github.com/l8eAI/l8e_harbor.git
cd l8e_harbor

# Start with Docker Compose (includes automatic admin setup)
cd deployments/docker
docker-compose -f docker-compose.full.yml up -d

# Wait for admin initialization to complete and get credentials
docker-compose -f docker-compose.full.yml logs admin-init
docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) cat /app/shared/admin-credentials.json

# Test the gateway
curl http://localhost:18443/health
```

### Option 2: Kubernetes with Helm

```bash
# Install with Helm
helm install l8e-harbor ./deployments/helm \
  --set config.mode=k8s \
  --set config.secretProvider=kubernetes \
  --set config.routeStore=configmap

# Port forward to test
kubectl port-forward svc/l8e-harbor 8443:443
curl https://localhost:8443/health --insecure
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

> 📖 **For complete deployment options and production setup**: [`deployments/README.md`](deployments/README.md)

## Example In Action: Calculator MCP Service

To see l8e-harbor in a real-world scenario, check out our example of proxying a Model Context Protocol (MCP) service with comprehensive logging, metrics, and reliability features.

> 📁 **Complete example available in [`examples/calculator-mcp/`](examples/calculator-mcp/)**

This example demonstrates:
- A **production-ready MCP Service**
- An **advanced l8e-harbor config** with circuit breakers, rate limiting, and retries
- A **full observability stack** with logs and Prometheus metrics

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