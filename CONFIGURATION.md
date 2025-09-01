# l8e-harbor Configuration Guide

Complete configuration reference for l8e-harbor deployment and runtime settings.

## Configuration Files

Example configurations are available in the [`examples/`](examples/) directory:

- **[`examples/config.yaml`](examples/config.yaml)** - Minimal development configuration with HTTP and local file storage
- **[`examples/mcp-route.yaml`](examples/mcp-route.yaml)** - Complete route definition with middleware and health checks  
- **[`examples/routes-backup.yaml`](examples/routes-backup.yaml)** - Route export/backup format example

## Basic Configuration

### Development Setup

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
  workers: 4  # Match CPU cores
  max_connections: 1000

tls:
  enabled: true
  cert_file: /etc/l8e-harbor/tls/tls.crt
  key_file: /etc/l8e-harbor/tls/tls.key

secret_provider: localfs  # or kubernetes, vault, aws, gcp
secret_path: /etc/l8e-harbor/secrets
route_store: sqlite  # or memory, configmap, crd
route_store_path: /var/lib/l8e-harbor/routes.db
auth_adapter: local  # or k8s_sa, oidc, opaque

log_level: INFO
enable_metrics: true
enable_tracing: true

# Default circuit breaker settings
circuit_breaker:
  default_failure_threshold: 50
  default_timeout_ms: 30000

# Default retry policy
retry_policy:
  default_max_retries: 3
  default_backoff_ms: 100
```

## Configuration Precedence

Settings are applied in this order (highest to lowest priority):

1. **CLI flags** - `--port 8443`
2. **Environment variables** - `L8E_HARBOR_PORT=8443`
3. **Config file** - `port: 8443` in config.yaml
4. **Defaults** - Built-in default values

## Server Configuration

### Basic Server Settings

```yaml
server:
  host: 0.0.0.0        # Bind address
  port: 8443           # Listen port
  workers: 4           # Worker processes (default: CPU cores)
  max_connections: 1000 # Max concurrent connections
  keepalive_timeout: 65 # HTTP keepalive timeout (seconds)
  request_timeout: 30   # Request timeout (seconds)
```

### TLS Configuration

```yaml
tls:
  enabled: true
  cert_file: /path/to/tls.crt
  key_file: /path/to/tls.key
  ca_file: /path/to/ca.crt  # Optional client cert validation
  
  # TLS settings
  min_version: "1.2"  # Minimum TLS version
  ciphers:            # Optional cipher suite restriction
    - "TLS_AES_256_GCM_SHA384"
    - "TLS_CHACHA20_POLY1305_SHA256"
```

## Adapter Configuration

### Authentication Adapters

#### Local Authentication

```yaml
auth_adapter: local
auth_config:
  jwt_secret_key: "your-jwt-secret"  # Auto-generated if not provided
  token_expire_hours: 24
  password_hash_rounds: 12  # bcrypt rounds
```

#### Kubernetes ServiceAccount

```yaml
auth_adapter: k8s_sa
auth_config:
  cluster_name: "production"
  validate_namespace: true
  allowed_namespaces: ["default", "kube-system"]
```

#### OIDC/OAuth2

```yaml
auth_adapter: oidc
auth_config:
  issuer_url: "https://accounts.google.com"
  client_id: "your-client-id"
  client_secret: "your-client-secret"
  redirect_uri: "https://harbor.example.com/auth/callback"
  scopes: ["openid", "email", "profile"]
```

### Secret Providers

#### Local Filesystem

```yaml
secret_provider: localfs
secret_path: /etc/l8e-harbor/secrets
secret_config:
  file_mode: 0600  # File permissions
  backup_count: 5  # Backup rotation count
```

#### Kubernetes Secrets

```yaml
secret_provider: kubernetes
secret_config:
  namespace: l8e-harbor-system
  secret_name: l8e-harbor-secrets
```

#### HashiCorp Vault

```yaml
secret_provider: vault
secret_config:
  vault_addr: "https://vault.example.com:8200"
  vault_token: "your-vault-token"
  mount_path: "secret/"
  key_prefix: "l8e-harbor/"
```

#### AWS Secrets Manager

```yaml
secret_provider: aws
secret_config:
  region: us-west-2
  secret_prefix: "l8e-harbor/"
  kms_key_id: "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
```

### Route Storage

#### In-Memory with File Snapshots

```yaml
route_store: memory
route_store_path: /var/lib/l8e-harbor/routes-snapshot.yaml
route_store_config:
  snapshot_interval: 300  # Seconds between snapshots
  backup_count: 10        # Number of backup files to keep
```

#### SQLite Database

```yaml
route_store: sqlite
route_store_path: /var/lib/l8e-harbor/routes.db
route_store_config:
  wal_mode: true          # Write-Ahead Logging
  cache_size: 10000       # Page cache size
  busy_timeout: 30000     # Busy timeout (ms)
```

#### Kubernetes ConfigMaps

```yaml
route_store: configmap
route_store_config:
  namespace: l8e-harbor-system
  configmap_name: l8e-harbor-routes
  watch_changes: true     # Watch for external changes
```

#### Kubernetes CRDs

```yaml
route_store: crd
route_store_config:
  namespace: l8e-harbor-system  # Empty for cluster-wide
  watch_changes: true
  reconcile_interval: 60        # Seconds
```

## Route Configuration

### Basic Route Definition

```yaml
apiVersion: harbor.l8e/v1
kind: Route
metadata:
  name: my-api-route
spec:
  id: my-api
  description: "My API service route"
  path: /api/v1
  methods: ["GET", "POST", "PUT", "DELETE"]
  priority: 100           # Lower number = higher priority
  timeout_ms: 5000        # Request timeout
```

### Backend Configuration

```yaml
spec:
  backends:
    - url: http://primary-backend:8080
      weight: 100                    # Load balancing weight
      health_check:
        enabled: true
        path: /healthz
        interval_seconds: 30
        timeout_seconds: 5
        healthy_threshold: 2
        unhealthy_threshold: 3
        expected_status: [200, 204]
    
    - url: http://secondary-backend:8080
      weight: 50
      tls:
        enabled: true
        verify_ssl: true
        ca_cert_file: /path/to/ca.crt
```

### Advanced Route Features

```yaml
spec:
  # Path matching
  matchers:
    - name: header
      key: "X-API-Version"
      value: "v2"
      op: "equals"          # equals, contains, regex, prefix, suffix
    
    - name: query
      key: "format"
      value: "json"
      op: "equals"

  # Request modification
  strip_prefix: true        # Remove matched path from upstream request
  add_prefix: "/v1"        # Add prefix to upstream request
  
  # Session management
  sticky_session: true      # Session affinity
  session_cookie: "session_id"
  
  # Rate limiting
  rate_limit:
    requests_per_minute: 100
    burst_size: 20
    key_by: "ip"           # ip, user, header
```

### Retry Policy

```yaml
spec:
  retry_policy:
    max_retries: 3
    backoff_ms: 100           # Initial backoff
    backoff_multiplier: 2.0   # Exponential backoff
    max_backoff_ms: 5000      # Maximum backoff
    retry_on: 
      - "5xx"                 # HTTP status codes
      - "timeout" 
      - "connection_error"
      - "reset"
```

### Circuit Breaker

```yaml
spec:
  circuit_breaker:
    enabled: true
    failure_threshold: 50     # Percentage
    minimum_requests: 20      # Minimum requests before evaluation
    timeout_ms: 30000         # Circuit open timeout
    half_open_requests: 5     # Requests to test recovery
```

## Middleware Configuration

### Authentication Middleware

```yaml
spec:
  middleware:
    - name: auth
      enabled: true
      config:
        require_auth: true
        require_role: ["captain", "harbor-master"]
        allow_anonymous_paths: ["/health", "/metrics"]
        jwt_cookie_name: "auth_token"
```

### CORS Middleware

```yaml
    - name: cors
      config:
        allow_origins: ["https://myapp.com", "https://admin.myapp.com"]
        allow_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        allow_headers: ["Authorization", "Content-Type", "X-Requested-With"]
        expose_headers: ["X-Total-Count"]
        allow_credentials: true
        max_age: 86400  # Preflight cache (seconds)
```

### Header Manipulation

```yaml
    - name: header-rewrite
      config:
        set:
          X-Service: "my-service"
          X-Version: "1.0.0"
        add:
          X-Request-ID: "{request_id}"  # Template variables
          X-User: "{user}"
        remove: ["X-Debug", "X-Internal"]
```

### Rate Limiting Middleware

```yaml
    - name: rate-limit
      config:
        requests_per_minute: 100
        burst_size: 20
        key_by: "ip"              # ip, user, header:<name>
        error_status: 429
        error_message: "Rate limit exceeded"
        whitelist_ips: ["10.0.0.0/8", "192.168.0.0/16"]
```

### Request/Response Transformation

```yaml
    - name: transform
      config:
        request:
          body_template: |
            {
              "original": {{ .body }},
              "metadata": {
                "user": "{{ .user }}",
                "timestamp": "{{ .timestamp }}"
              }
            }
        response:
          headers:
            set:
              Cache-Control: "no-cache"
```

## Logging Configuration

```yaml
log_level: INFO              # DEBUG, INFO, WARNING, ERROR
log_format: json            # json, text
log_output: stdout          # stdout, stderr, file
log_file: /var/log/l8e-harbor/app.log
log_rotation:
  max_size_mb: 100
  max_files: 10
  max_days: 30

# Request logging
request_logging:
  enabled: true
  log_headers: false        # Log request headers (security risk)
  log_body: false          # Log request body (security risk)
  log_response: false      # Log response body
  exclude_paths: ["/health", "/metrics"]
```

## Metrics Configuration

```yaml
enable_metrics: true
metrics:
  listen_addr: "0.0.0.0:9090"
  endpoint: "/metrics"
  
  # Custom labels
  default_labels:
    environment: "production"
    cluster: "us-west-2"
    
  # Histogram buckets (seconds)
  request_duration_buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
```

## Distributed Tracing

```yaml
enable_tracing: true
tracing:
  service_name: "l8e-harbor"
  jaeger:
    agent_host: "jaeger-agent"
    agent_port: 6831
    collector_endpoint: "http://jaeger-collector:14268/api/traces"
  
  # Sampling
  sampling_rate: 0.1        # Sample 10% of requests
  
  # Custom tags
  default_tags:
    version: "1.0.0"
    deployment: "production"
```

## Environment Variables

Override any configuration value using environment variables with the `L8E_HARBOR_` prefix:

```bash
# Server settings
export L8E_HARBOR_SERVER_HOST=0.0.0.0
export L8E_HARBOR_SERVER_PORT=8443

# TLS settings
export L8E_HARBOR_TLS_ENABLED=true
export L8E_HARBOR_TLS_CERT_FILE=/path/to/cert.pem

# Auth settings
export L8E_HARBOR_AUTH_ADAPTER=local
export L8E_HARBOR_SECRET_PROVIDER=kubernetes

# Logging
export L8E_HARBOR_LOG_LEVEL=DEBUG
export L8E_HARBOR_ENABLE_METRICS=true
```

## Configuration Validation

Validate your configuration before deployment:

```bash
# Using harbor-ctl
harbor-ctl validate -f config.yaml

# Using the binary directly
l8e-harbor validate --config config.yaml

# Check specific route configuration
harbor-ctl validate route -f route.yaml
```

## Configuration Templates

### High Availability Setup

```yaml
mode: k8s
server:
  workers: 8
  max_connections: 2000

route_store: sqlite
route_store_config:
  wal_mode: true

# Enable all observability
enable_metrics: true
enable_tracing: true
log_level: INFO

# Default reliability settings
circuit_breaker:
  default_failure_threshold: 30
  default_timeout_ms: 60000

retry_policy:
  default_max_retries: 5
  default_backoff_ms: 50
```

### Development Setup

```yaml
mode: vm
server:
  host: 127.0.0.1
  port: 8080

tls:
  enabled: false

secret_provider: localfs
route_store: memory
auth_adapter: local

log_level: DEBUG
enable_metrics: false
enable_tracing: false

# Relaxed settings for development
circuit_breaker:
  default_failure_threshold: 80
  
retry_policy:
  default_max_retries: 1
```

## Next Steps

- See [examples/](examples/README.md) for practical configuration examples
- Review [SECURITY.md](SECURITY.md) for security-specific configuration
- Check [deployments/](deployments/README.md) for deployment-specific settings