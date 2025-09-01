# l8e-harbor Deployment Guide

This directory contains deployment configurations and scripts for running l8e-harbor in various environments.

## Deployment Options

l8e-harbor is designed to run anywhere - from development laptops to production Kubernetes clusters. Choose the deployment method that best fits your environment:

### Quick Start Options

| Method | Use Case | Setup Time | Production Ready |
|--------|----------|------------|------------------|
| [Docker Compose](#docker-compose) | Development, Testing | 2 minutes | ⚠️ With modifications |
| [Kubernetes + Helm](#kubernetes-helm) | Production, Staging | 5 minutes | ✅ Yes |
| [VM/Systemd](#vmsystemd) | Legacy systems, Bare metal | 10 minutes | ✅ Yes |

## Docker Compose

**Directory**: [`docker/`](docker/)

Perfect for development, testing, and small deployments.

### Quick Start

```bash
# Navigate to Docker deployment
cd deployments/docker

# Start with full stack (includes admin setup)
docker-compose -f docker-compose.full.yml up -d

# Wait for admin initialization
docker-compose -f docker-compose.full.yml logs admin-init

# Get admin credentials
docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) cat /app/shared/admin-credentials.json

# Test the gateway
curl http://localhost:18443/health

# Access the UI (if available)
open http://localhost:3000
```

### Available Configurations

- **`docker-compose.yml`** - Basic l8e-harbor only
- **`docker-compose.full.yml`** - Full stack with admin setup, monitoring
- **`docker-compose.dev.yml`** - Development setup with hot reload

### Admin Account Access

The system automatically generates a secure admin account:
- **Username**: `admin`
- **Password**: 32-character random string (see credentials file)
- **Role**: `harbor-master`

### Features Included

- ✅ Automatic admin account creation
- ✅ Persistent data volumes
- ✅ Health checks
- ✅ Network isolation
- ✅ Environment-based configuration
- ⚠️ HTTP only (enable TLS for production)

## Kubernetes + Helm

**Directory**: [`helm/`](helm/)

Production-ready Kubernetes deployment with Helm charts.

### Quick Start

```bash
# Install with Helm
helm install l8e-harbor ./deployments/helm \
  --set config.mode=k8s \
  --set config.secretProvider=kubernetes \
  --set config.routeStore=configmap

# Port forward to test
kubectl port-forward svc/l8e-harbor 8443:443
curl https://localhost:8443/health

# Get admin credentials
kubectl get secret l8e-harbor-admin-creds -o jsonpath='{.data.username}' | base64 -d
kubectl get secret l8e-harbor-admin-creds -o jsonpath='{.data.password}' | base64 -d
```

### Helm Configuration

**Values Overview**:
```yaml
# config/values.yaml
config:
  mode: k8s
  secretProvider: kubernetes
  routeStore: configmap
  
tls:
  enabled: true
  certManager: true  # Use cert-manager for TLS

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: harbor.example.com

monitoring:
  prometheus: true
  grafana: true

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
```

### Features Included

- ✅ Production TLS with cert-manager
- ✅ Horizontal Pod Autoscaling
- ✅ Prometheus metrics
- ✅ Ingress controllers
- ✅ RBAC integration
- ✅ ConfigMap route storage
- ✅ Secret management
- ✅ Rolling updates

## VM/Systemd

**Directory**: [`systemd/`](systemd/)

Traditional VM deployment using systemd for process management.

### Installation

```bash
# Install on VM
sudo ./deployments/systemd/install.sh

# Configure
sudo cp examples/config.yaml /etc/l8e-harbor/config.yaml
sudo systemctl edit l8e-harbor  # Override environment if needed

# Start service
sudo systemctl start l8e-harbor
sudo systemctl enable l8e-harbor  # Auto-start on boot

# Test
curl https://localhost:8443/health

# View logs
sudo journalctl -u l8e-harbor -f
```

### Admin Credentials

```bash
# View admin credentials
sudo cat /etc/l8e-harbor/secrets/admin-credentials.json

# Check initialization logs
sudo journalctl -u l8e-harbor-init | grep "admin credentials"
```

### Features Included

- ✅ Systemd service management
- ✅ Log rotation
- ✅ Auto-restart on failure
- ✅ Environment file configuration
- ✅ TLS certificate management
- ✅ User/group isolation
- ✅ File permission security

## Advanced Deployments

### Kubernetes CRD

**Directory**: [`kubernetes/`](kubernetes/)

Use Custom Resource Definitions for native Kubernetes route management:

```bash
# Apply CRDs
kubectl apply -f deployments/kubernetes/crds/

# Install with CRD support
helm install l8e-harbor ./deployments/helm \
  --set config.routeStore=crd

# Manage routes as Kubernetes resources
kubectl apply -f - <<EOF
apiVersion: harbor.l8e/v1
kind: Route
metadata:
  name: my-api-route
spec:
  path: /api/v1
  backends:
    - url: http://my-service.default.svc.cluster.local:8080
EOF
```

### Multi-Cluster Setup

For advanced multi-cluster deployments:

```bash
# Install on multiple clusters
for cluster in prod-us-east prod-eu-west; do
  kubectl config use-context $cluster
  helm install l8e-harbor-$cluster ./deployments/helm \
    --set config.clusterId=$cluster
done
```

## Production Considerations

### Security Checklist

- [ ] **TLS Enabled**: Always use HTTPS in production
- [ ] **Secret Management**: Use proper secret providers (Vault, K8s Secrets)
- [ ] **Authentication**: Configure proper auth adapters
- [ ] **Network Policies**: Restrict pod-to-pod communication (K8s)
- [ ] **RBAC**: Implement least-privilege access
- [ ] **Audit Logging**: Enable comprehensive audit trails

### Performance Tuning

```yaml
# Production performance settings
server:
  workers: 4  # Match CPU cores
  max_connections: 1000

route_store: sqlite  # Better performance than memory for large route sets

circuit_breaker:
  default_failure_threshold: 50
  default_timeout_ms: 30000

retry_policy:
  default_max_retries: 3
  default_backoff_ms: 100
```

### Monitoring Setup

All deployments include monitoring capabilities:

1. **Prometheus Metrics**: Available at `/metrics` endpoint
2. **Health Checks**: `/health` for load balancer probes
3. **Structured Logging**: JSON logs for centralized collection
4. **Distributed Tracing**: OpenTelemetry integration

### Backup and Recovery

```bash
# Backup routes (all deployment types)
harbor-ctl export routes -o backup-$(date +%Y%m%d).yaml

# Backup configuration
cp /etc/l8e-harbor/config.yaml config-backup-$(date +%Y%m%d).yaml

# Database backup (if using SQLite)
cp /var/lib/l8e-harbor/routes.db routes-backup-$(date +%Y%m%d).db
```

## Troubleshooting

### Common Issues

**Connection Refused**:
```bash
# Check service status
systemctl status l8e-harbor  # VM
kubectl get pods  # Kubernetes
docker-compose ps  # Docker

# Check logs
journalctl -u l8e-harbor -f  # VM
kubectl logs -f deployment/l8e-harbor  # Kubernetes
docker-compose logs -f  # Docker
```

**Admin Login Failed**:
```bash
# Verify admin credentials exist
cat /etc/l8e-harbor/secrets/admin-credentials.json  # VM
kubectl get secret l8e-harbor-admin-creds  # Kubernetes
docker exec container cat /app/shared/admin-credentials.json  # Docker
```

**Route Not Working**:
```bash
# Check route configuration
harbor-ctl get routes
harbor-ctl describe route <route-id>

# Check backend health
curl -I http://backend-url/health
```

### Log Locations

| Deployment | Log Location |
|-----------|--------------|
| Docker Compose | `docker-compose logs` |
| Kubernetes | `kubectl logs deployment/l8e-harbor` |
| Systemd | `/var/log/l8e-harbor/` or `journalctl -u l8e-harbor` |

## Migration Between Deployments

### Docker → Kubernetes

```bash
# Export routes from Docker setup
harbor-ctl export routes -o docker-routes.yaml

# Deploy to Kubernetes
helm install l8e-harbor ./deployments/helm

# Import routes
harbor-ctl import -f docker-routes.yaml
```

### VM → Kubernetes

```bash
# Backup VM deployment
sudo tar czf l8e-harbor-backup.tar.gz /etc/l8e-harbor/

# Extract routes
harbor-ctl export routes -o vm-routes.yaml

# Deploy and import to Kubernetes
helm install l8e-harbor ./deployments/helm
harbor-ctl import -f vm-routes.yaml
```

## Next Steps

- Choose your deployment method and follow the specific guide
- Review [example configurations](../examples/) for your use case
- Check the main [l8e-harbor documentation](../README.md) for API usage
- Set up monitoring and observability for your environment

## Support

- **Deployment Issues**: [GitHub Issues](https://github.com/example/l8e-harbor/issues)
- **Kubernetes Help**: Check [kubernetes/README.md](kubernetes/README.md)
- **Docker Help**: Check [docker/README.md](docker/README.md)
- **VM Help**: Check [systemd/README.md](systemd/README.md)