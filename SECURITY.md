# l8e-harbor Security Guide

Comprehensive security configuration and best practices for l8e-harbor deployments.

## Security Architecture

l8e-harbor follows a security-first design with multiple layers of protection:

- **Authentication**: Pluggable auth adapters (local, K8s, OIDC)
- **Authorization**: Role-based access control (RBAC)
- **Transport Security**: TLS required for production
- **Secret Management**: Secure storage for credentials and keys
- **Audit Logging**: Comprehensive activity tracking

## Authentication & Authorization

### Authentication Adapters

l8e-harbor supports multiple authentication methods depending on your deployment environment:

#### 1. Local Users (VM/Development)

Best for standalone deployments and development environments.

```yaml
auth_adapter: local
auth_config:
  jwt_secret_key: "your-secure-jwt-secret"  # Auto-generated if not provided
  token_expire_hours: 24
  password_hash_rounds: 12  # bcrypt rounds (higher = more secure, slower)
  
  # Password policy
  password_min_length: 12
  password_require_special: true
  password_require_numbers: true
  password_require_uppercase: true
```

**Features:**
- Username/password with bcrypt hashing
- JWT tokens with RSA256 signing
- Role-based permissions
- Password policy enforcement

#### 2. Kubernetes ServiceAccounts

Native Kubernetes authentication using ServiceAccount tokens.

```yaml
auth_adapter: k8s_sa
auth_config:
  cluster_name: "production"
  validate_namespace: true
  allowed_namespaces: ["l8e-harbor", "default"]
  
  # RBAC mapping
  role_mappings:
    "system:admin": "harbor-master"
    "l8e-harbor:operator": "captain"
    "l8e-harbor:readonly": "crew"
```

**Features:**
- No separate credential management
- Automatic role mapping from K8s RBAC
- Namespace-based access control
- ServiceAccount token validation

#### 3. OAuth2/OIDC

Enterprise identity provider integration.

```yaml
auth_adapter: oidc
auth_config:
  issuer_url: "https://accounts.google.com"
  client_id: "your-oidc-client-id"
  client_secret: "your-oidc-client-secret"  # Store in secrets
  redirect_uri: "https://harbor.example.com/auth/callback"
  
  scopes: ["openid", "email", "profile"]
  
  # Claims mapping
  role_claim: "harbor_role"
  username_claim: "email"
  
  # Role mapping from claims
  role_mappings:
    "admin": "harbor-master"
    "operator": "captain"
    "viewer": "crew"
```

**Features:**
- Single Sign-On (SSO) integration
- Claims-based role mapping
- External identity provider support
- Session management

#### 4. Pre-shared Tokens

API-only authentication for service-to-service communication.

```yaml
auth_adapter: opaque
auth_config:
  tokens:
    - token: "service-1-token-here"
      user: "service-1"
      role: "captain"
    - token: "monitoring-token-here"
      user: "prometheus"
      role: "crew"
```

### Role-Based Access Control (RBAC)

l8e-harbor implements a three-tier role system:

#### Harbor Master (Admin)
- Full system access
- User management
- Route management
- System configuration
- Audit log access

#### Captain (Operator)
- Route management
- Limited user operations
- Monitoring access
- No system configuration

#### Crew (Read-only)
- View routes
- View system status
- No modifications allowed

### Role Configuration

```yaml
# In route middleware
middleware:
  - name: auth
    config:
      require_auth: true
      require_role: ["captain", "harbor-master"]
      
      # Per-path role requirements
      path_roles:
        "/admin/*": ["harbor-master"]
        "/api/routes": ["captain", "harbor-master"]
        "/api/status": ["crew", "captain", "harbor-master"]
      
      # Anonymous access paths
      allow_anonymous_paths: ["/health", "/metrics"]
```

## Transport Security (TLS)

### TLS Configuration

TLS is **required** for production deployments:

```yaml
tls:
  enabled: true
  cert_file: /etc/l8e-harbor/tls/tls.crt
  key_file: /etc/l8e-harbor/tls/tls.key
  ca_file: /etc/l8e-harbor/tls/ca.crt  # Optional for client cert validation
  
  # Security settings
  min_version: "1.2"  # Minimum TLS 1.2
  prefer_server_ciphers: true
  
  # Cipher suites (restrict to secure ciphers)
  ciphers:
    - "TLS_AES_256_GCM_SHA384"
    - "TLS_CHACHA20_POLY1305_SHA256"
    - "TLS_AES_128_GCM_SHA256"
  
  # Client certificate validation
  client_cert_auth: false  # Set to true for mutual TLS
  client_ca_file: /etc/l8e-harbor/tls/client-ca.crt
```

### Certificate Management

#### Self-Signed Certificates (Development Only)

```bash
# Generate CA key and certificate
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -key ca-key.pem -out ca.pem -days 365 \
  -subj "/CN=l8e-harbor-ca"

# Generate server key and certificate
openssl genrsa -out server-key.pem 4096
openssl req -new -key server-key.pem -out server.csr \
  -subj "/CN=localhost"
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca-key.pem \
  -CAcreateserial -out server.pem -days 365
```

#### Production Certificates

Use certificates from a trusted CA or cert-manager in Kubernetes:

```yaml
# Kubernetes cert-manager
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: l8e-harbor-tls
spec:
  secretName: l8e-harbor-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - harbor.example.com
```

### Mutual TLS (mTLS)

For high-security environments:

```yaml
tls:
  enabled: true
  client_cert_auth: true
  client_ca_file: /etc/l8e-harbor/tls/client-ca.crt
  
  # Client certificate validation
  verify_client_cert: true
  client_cert_optional: false  # Require client certificates
```

## Secret Management

### Secret Providers

Choose the appropriate secret provider for your environment:

#### 1. Local Filesystem (Development/VM)

```yaml
secret_provider: localfs
secret_path: /etc/l8e-harbor/secrets
secret_config:
  file_mode: 0600  # Restrictive file permissions
  backup_count: 5
  encryption: true  # Encrypt secrets at rest
  encryption_key_file: /etc/l8e-harbor/encryption.key
```

**Security Features:**
- File-level encryption
- Restrictive permissions (0600)
- Backup rotation
- Automatic key generation

#### 2. Kubernetes Secrets

```yaml
secret_provider: kubernetes
secret_config:
  namespace: l8e-harbor-system
  secret_name: l8e-harbor-secrets
  
  # Encryption at rest (configure in K8s)
  encryption_provider: "kms"  # or "aescbc"
```

#### 3. HashiCorp Vault

```yaml
secret_provider: vault
secret_config:
  vault_addr: "https://vault.example.com:8200"
  auth_method: "kubernetes"  # or "token", "aws", "gcp"
  
  # Kubernetes auth
  kubernetes_role: "l8e-harbor"
  
  # Secret paths
  mount_path: "secret/"
  key_prefix: "l8e-harbor/"
  
  # Token renewal
  token_ttl: 3600
  renew_token: true
```

#### 4. Cloud Providers

**AWS Secrets Manager:**
```yaml
secret_provider: aws
secret_config:
  region: us-west-2
  secret_prefix: "l8e-harbor/"
  
  # KMS encryption
  kms_key_id: "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
  
  # IAM role for access
  role_arn: "arn:aws:iam::123456789012:role/l8e-harbor-secrets"
```

**GCP Secret Manager:**
```yaml
secret_provider: gcp
secret_config:
  project_id: "my-project"
  secret_prefix: "l8e-harbor-"
  
  # Service account for access
  service_account_file: /etc/gcp/service-account.json
```

### Secret Types

l8e-harbor manages these secret types:

- **JWT Signing Keys**: RSA private keys for token signing
- **User Credentials**: Bcrypt hashed passwords
- **TLS Certificates**: SSL/TLS certificate and key pairs
- **External API Keys**: Third-party service credentials
- **Encryption Keys**: Data encryption keys

## Network Security

### Firewall Configuration

Recommended firewall rules:

```bash
# Management API (restrict to admin networks)
iptables -A INPUT -p tcp --dport 8443 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8443 -j DROP

# Proxy traffic (allow from load balancers)
iptables -A INPUT -p tcp --dport 8080 -s 10.0.0.0/8 -j ACCEPT

# Metrics (restrict to monitoring)
iptables -A INPUT -p tcp --dport 9090 -s 10.0.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 9090 -j DROP
```

### Network Policies (Kubernetes)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: l8e-harbor-network-policy
spec:
  podSelector:
    matchLabels:
      app: l8e-harbor
  policyTypes:
  - Ingress
  - Egress
  
  ingress:
  # Allow ingress controller
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  
  # Allow monitoring
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  
  egress:
  # Allow DNS
  - to: []
    ports:
    - protocol: UDP
      port: 53
  
  # Allow backend services
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 8080
```

## Security Headers

Configure security headers for enhanced protection:

```yaml
# In route middleware
middleware:
  - name: security-headers
    config:
      headers:
        # Prevent clickjacking
        X-Frame-Options: "DENY"
        
        # XSS protection
        X-XSS-Protection: "1; mode=block"
        
        # Content type sniffing
        X-Content-Type-Options: "nosniff"
        
        # HTTPS enforcement
        Strict-Transport-Security: "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        Content-Security-Policy: "default-src 'self'"
        
        # Referrer policy
        Referrer-Policy: "strict-origin-when-cross-origin"
        
        # Remove server identification
        Server: ""
      
      # Remove potentially sensitive headers
      remove_headers:
        - "X-Powered-By"
        - "X-AspNet-Version"
```

## Audit Logging

### Audit Configuration

```yaml
audit_logging:
  enabled: true
  log_file: /var/log/l8e-harbor/audit.log
  log_format: json
  
  # Events to log
  events:
    - "auth.login"
    - "auth.logout"
    - "auth.failed"
    - "route.create"
    - "route.update"
    - "route.delete"
    - "user.create"
    - "user.update"
    - "user.delete"
    - "config.update"
  
  # Additional context
  include_request_body: false  # Security risk
  include_response_body: false # Security risk
  include_headers: ["Authorization", "User-Agent"]
  
  # Retention
  retention_days: 90
  max_file_size_mb: 100
```

### Audit Log Format

```json
{
  "timestamp": "2025-09-01T10:30:00Z",
  "level": "AUDIT",
  "event": "route.create",
  "user": "admin",
  "user_role": "harbor-master",
  "source_ip": "10.0.1.100",
  "user_agent": "harbor-ctl/1.0.0",
  "resource": "route",
  "resource_id": "api-v1",
  "action": "create",
  "outcome": "success",
  "request_id": "req_abc123"
}
```

## Security Hardening

### Process Security

```yaml
# Run with non-root user
security:
  run_as_user: 1001
  run_as_group: 1001
  drop_capabilities: ["ALL"]
  add_capabilities: ["NET_BIND_SERVICE"]  # Only if binding to port < 1024
  
  # Resource limits
  limits:
    memory: "512Mi"
    cpu: "500m"
  
  # Read-only filesystem
  read_only_root_filesystem: true
  tmp_dir: /tmp/l8e-harbor
```

### Input Validation

```yaml
security:
  # Request size limits
  max_request_size: "10MB"
  max_header_size: "8KB"
  
  # Rate limiting
  global_rate_limit:
    requests_per_second: 1000
    burst_size: 2000
  
  # Path validation
  allowed_paths_regex: "^[a-zA-Z0-9/_-]+$"
  blocked_user_agents: ["scanner", "bot"]
```

### Backend Security

```yaml
# In route configuration
spec:
  backends:
    - url: https://backend.internal:8443
      tls:
        enabled: true
        verify_ssl: true
        ca_cert_file: /etc/ssl/certs/ca-certificates.crt
        client_cert_file: /etc/l8e-harbor/client.crt
        client_key_file: /etc/l8e-harbor/client.key
      
      # Security headers for backend requests
      headers:
        add:
          X-Forwarded-Proto: "https"
          X-Real-IP: "{client_ip}"
        remove:
          - "X-Debug"
          - "Authorization"  # Don't forward client auth to backend
```

## Security Monitoring

### Key Metrics to Monitor

```prometheus
# Authentication failures
l8e_auth_attempts_total{status="failed"}

# Unusual request patterns
l8e_proxy_requests_total{status_code="403"}
l8e_proxy_requests_total{status_code="401"}

# Backend failures
l8e_backend_up{backend="critical-service"} == 0

# Rate limit hits
l8e_rate_limit_exceeded_total
```

### Alerting Rules

```yaml
groups:
- name: l8e-harbor-security
  rules:
  - alert: HighAuthFailureRate
    expr: rate(l8e_auth_attempts_total{status="failed"}[5m]) > 10
    labels:
      severity: warning
    annotations:
      summary: "High authentication failure rate detected"
  
  - alert: UnauthorizedAccessAttempts
    expr: rate(l8e_proxy_requests_total{status_code="403"}[5m]) > 5
    labels:
      severity: critical
    annotations:
      summary: "High rate of unauthorized access attempts"
```

## Security Checklist

### Pre-Production

- [ ] **TLS Enabled**: HTTPS required for all production traffic
- [ ] **Strong Passwords**: Enforce password policy for local users
- [ ] **Secret Management**: Use proper secret provider (not localfs in prod)
- [ ] **Role Separation**: Follow principle of least privilege
- [ ] **Audit Logging**: Enable comprehensive audit trails
- [ ] **Network Security**: Implement firewall rules and network policies
- [ ] **Input Validation**: Set request size limits and validation rules
- [ ] **Security Headers**: Configure security headers for responses
- [ ] **Monitoring**: Set up security monitoring and alerting

### Ongoing Security

- [ ] **Regular Updates**: Keep l8e-harbor updated to latest version
- [ ] **Certificate Rotation**: Rotate TLS certificates before expiry
- [ ] **Credential Rotation**: Regular rotation of API keys and passwords
- [ ] **Log Monitoring**: Review audit logs for suspicious activity
- [ ] **Vulnerability Scanning**: Regular security scans of deployment
- [ ] **Access Review**: Periodic review of user access and roles
- [ ] **Backup Security**: Secure backup of configurations and secrets

## Incident Response

### Security Event Response

1. **Immediate Actions**:
   ```bash
   # Block suspicious IPs
   iptables -A INPUT -s <suspicious-ip> -j DROP
   
   # Revoke compromised tokens
   harbor-ctl revoke token <token-id>
   
   # Disable compromised users
   harbor-ctl disable user <username>
   ```

2. **Investigation**:
   ```bash
   # Check audit logs
   grep "auth.failed" /var/log/l8e-harbor/audit.log
   
   # Review access patterns
   harbor-ctl audit --user <username> --since 24h
   ```

3. **Recovery**:
   ```bash
   # Rotate secrets
   harbor-ctl rotate secrets --all
   
   # Update certificates
   harbor-ctl update cert --cert-file new-cert.pem
   ```

## Compliance

### GDPR Considerations

- Configure data retention policies
- Implement user data deletion capabilities
- Ensure audit logs comply with data protection requirements
- Review what personal data is logged

### SOC 2 / ISO 27001

- Enable comprehensive audit logging
- Implement access controls and user management
- Set up monitoring and alerting
- Document security procedures and incident response

## Next Steps

- Review [CONFIGURATION.md](CONFIGURATION.md) for detailed config options
- Check [deployments/](deployments/README.md) for deployment-specific security
- See [OBSERVABILITY.md](OBSERVABILITY.md) for security monitoring setup