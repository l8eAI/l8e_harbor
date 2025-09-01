# l8e-harbor Observability Guide

Comprehensive monitoring, logging, and tracing configuration for l8e-harbor deployments.

## Overview

l8e-harbor provides enterprise-grade observability features:

- **Metrics**: Prometheus-compatible metrics for monitoring
- **Structured Logging**: JSON logs with request tracing
- **Distributed Tracing**: OpenTelemetry integration
- **Health Checks**: Service and backend health monitoring
- **Audit Logging**: Security and compliance tracking

## Metrics

### Prometheus Integration

l8e-harbor exposes Prometheus metrics on the `/metrics` endpoint:

```yaml
enable_metrics: true
metrics:
  listen_addr: "0.0.0.0:9090"
  endpoint: "/metrics"
  
  # Custom labels for all metrics
  default_labels:
    environment: "production"
    cluster: "us-west-2"
    version: "1.0.0"
    
  # Histogram buckets for request duration (seconds)
  request_duration_buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
  
  # Histogram buckets for request size (bytes)  
  request_size_buckets: [100, 1000, 10000, 100000, 1000000, 10000000]
```

### Available Metrics

#### Request Metrics

```prometheus
# Request count by route, method, status
l8e_proxy_requests_total{route_id="api-v1",method="POST",status_code="200",backend="service-1"} 1547

# Request duration histogram
l8e_proxy_request_duration_seconds{route_id="api-v1",backend="service-1",quantile="0.95"} 0.045

# Request size histogram  
l8e_proxy_request_size_bytes{route_id="api-v1",quantile="0.99"} 2048

# Response size histogram
l8e_proxy_response_size_bytes{route_id="api-v1",quantile="0.99"} 8192

# Active connections
l8e_proxy_active_connections{route_id="api-v1"} 12
```

#### System Metrics

```prometheus
# Route count
l8e_routes_total 15

# Backend health status
l8e_backend_up{route_id="api-v1",backend="service-1.example.com:8080"} 1

# Circuit breaker state (0=closed, 1=half-open, 2=open)
l8e_circuit_breaker_state{route_id="api-v1",backend="service-1"} 0

# Circuit breaker events
l8e_circuit_breaker_events_total{route_id="api-v1",backend="service-1",event="success"} 1000
l8e_circuit_breaker_events_total{route_id="api-v1",backend="service-1",event="failure"} 25
```

#### Authentication Metrics

```prometheus
# Authentication attempts
l8e_auth_attempts_total{adapter_type="local",status="success"} 145
l8e_auth_attempts_total{adapter_type="local",status="failed"} 5

# Active sessions
l8e_auth_active_sessions{adapter_type="local"} 23

# Token operations
l8e_auth_token_operations_total{operation="issue",adapter_type="local"} 145
l8e_auth_token_operations_total{operation="refresh",adapter_type="local"} 67
l8e_auth_token_operations_total{operation="revoke",adapter_type="local"} 12
```

#### Rate Limiting Metrics

```prometheus
# Rate limit events
l8e_rate_limit_events_total{route_id="api-v1",action="allowed"} 9500
l8e_rate_limit_events_total{route_id="api-v1",action="limited"} 47

# Current rate limit usage
l8e_rate_limit_current{route_id="api-v1",window="minute"} 85
```

### Prometheus Configuration

**prometheus.yml**:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
- job_name: 'l8e-harbor'
  static_configs:
  - targets: ['harbor.example.com:9090']
  scrape_interval: 5s
  metrics_path: /metrics
  
  # Optional: Basic auth if metrics endpoint is protected
  basic_auth:
    username: prometheus
    password_file: /etc/prometheus/harbor-password
```

### Grafana Dashboards

#### Key Dashboard Panels

**Request Rate**:
```promql
sum(rate(l8e_proxy_requests_total[5m])) by (route_id)
```

**Error Rate**:
```promql
sum(rate(l8e_proxy_requests_total{status_code=~"5.."}[5m])) by (route_id) / 
sum(rate(l8e_proxy_requests_total[5m])) by (route_id) * 100
```

**Response Time (95th percentile)**:
```promql
histogram_quantile(0.95, sum(rate(l8e_proxy_request_duration_seconds_bucket[5m])) by (route_id, le))
```

**Backend Health**:
```promql
l8e_backend_up
```

**Circuit Breaker Status**:
```promql
l8e_circuit_breaker_state
```

## Structured Logging

### Logging Configuration

```yaml
log_level: INFO              # DEBUG, INFO, WARNING, ERROR
log_format: json            # json, text
log_output: stdout          # stdout, stderr, file
log_file: /var/log/l8e-harbor/app.log

# Log rotation (if using file output)
log_rotation:
  max_size_mb: 100          # Max file size before rotation
  max_files: 10             # Number of backup files
  max_days: 30              # Max age of log files

# Request logging
request_logging:
  enabled: true
  log_headers: false        # Security risk - may contain sensitive data
  log_body: false          # Security risk - may contain sensitive data
  log_response: false      # Log response body (performance impact)
  
  # Paths to exclude from request logging
  exclude_paths: 
    - "/health"
    - "/metrics"
    - "/favicon.ico"
  
  # Additional fields
  include_user_agent: true
  include_remote_addr: true
  include_request_id: true
```

### Log Formats

#### Request Logs

```json
{
  "timestamp": "2025-09-01T12:00:05.123Z",
  "level": "INFO",
  "logger": "l8e.proxy",
  "message": "Request completed",
  
  "request_id": "req_abc123def456",
  "method": "POST",
  "path": "/api/v1/users",
  "query_string": "filter=active",
  "status_code": 201,
  "duration_ms": 45.2,
  
  "route_id": "api-v1",
  "backend": "http://user-service:8080",
  "backend_duration_ms": 38.7,
  
  "user": "alice@example.com",
  "user_role": "captain",
  "remote_addr": "10.0.1.100",
  "user_agent": "MyApp/1.0.0",
  
  "request_size": 256,
  "response_size": 1024,
  
  "middleware": ["auth", "cors", "logging"],
  "retry_count": 0,
  "circuit_breaker": "closed"
}
```

#### Error Logs

```json
{
  "timestamp": "2025-09-01T12:00:10.456Z",
  "level": "ERROR",
  "logger": "l8e.proxy",
  "message": "Backend request failed",
  
  "request_id": "req_def789ghi012",
  "route_id": "api-v1",
  "backend": "http://user-service:8080",
  "error": "connection timeout after 5000ms",
  "error_type": "timeout",
  
  "retry_count": 2,
  "max_retries": 3,
  "will_retry": true,
  "next_retry_in_ms": 400,
  
  "circuit_breaker": "closed",
  "failure_count": 3,
  "failure_threshold": 10
}
```

#### System Logs

```json
{
  "timestamp": "2025-09-01T12:00:00.000Z",
  "level": "INFO", 
  "logger": "l8e.system",
  "message": "Route configuration updated",
  
  "event": "route.update",
  "route_id": "api-v1",
  "user": "admin",
  "changes": {
    "backends": ["added http://new-service:8080"],
    "timeout_ms": "5000 -> 10000"
  }
}
```

### Centralized Logging

#### ELK Stack Integration

**Filebeat Configuration**:
```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/l8e-harbor/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "l8e-harbor-%{+yyyy.MM.dd}"

processors:
- add_host_metadata:
    when.not.contains.tags: forwarded
```

**Logstash Filter**:
```ruby
filter {
  if [logger] =~ /^l8e\./ {
    mutate {
      add_field => { "service" => "l8e-harbor" }
    }
    
    if [request_id] {
      mutate {
        add_field => { "trace_id" => "%{request_id}" }
      }
    }
  }
}
```

#### Fluentd Integration

```yaml
# fluent.conf
<source>
  @type tail
  path /var/log/l8e-harbor/app.log
  pos_file /var/log/fluentd/l8e-harbor.log.pos
  tag l8e.harbor
  format json
</source>

<match l8e.harbor>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name l8e-harbor
  type_name logs
</match>
```

## Distributed Tracing

### OpenTelemetry Configuration

```yaml
enable_tracing: true
tracing:
  service_name: "l8e-harbor"
  service_version: "1.0.0"
  
  # Jaeger configuration
  jaeger:
    agent_host: "jaeger-agent"
    agent_port: 6831
    collector_endpoint: "http://jaeger-collector:14268/api/traces"
    
  # Sampling configuration
  sampling_rate: 0.1        # Sample 10% of requests
  sampling_rules:
    - service: "l8e-harbor"
      operation: "GET /health"
      sample_rate: 0.01       # Sample health checks less frequently
    - service: "l8e-harbor"
      operation: "POST /api/*"
      sample_rate: 1.0        # Sample all API requests
  
  # Custom tags
  default_tags:
    environment: "production"
    cluster: "us-west-2"
    deployment: "blue"
    
  # Resource attributes
  resource_attributes:
    service.name: "l8e-harbor"
    service.version: "1.0.0"
    deployment.environment: "production"
```

### Trace Context

l8e-harbor automatically propagates trace context:

```http
# Incoming request headers
X-Trace-Id: 1234567890abcdef
X-Span-Id: abcdef1234567890

# Outgoing request headers (to backends)
X-Trace-Id: 1234567890abcdef
X-Parent-Span-Id: abcdef1234567890
X-Span-Id: fedcba0987654321
```

### Custom Spans

```yaml
# In route configuration
spec:
  middleware:
    - name: tracing
      config:
        create_spans: true
        span_name_template: "{method} {path}"
        
        # Custom attributes
        span_attributes:
          route.id: "{route_id}"
          backend.url: "{backend_url}"
          user.id: "{user}"
```

## Health Checks

### Service Health

l8e-harbor exposes multiple health endpoints:

```yaml
health_checks:
  enabled: true
  endpoints:
    # Liveness probe
    - path: "/health"
      type: "liveness"
      
    # Readiness probe  
    - path: "/ready"
      type: "readiness"
      
    # Detailed health status
    - path: "/health/detailed"
      type: "detailed"
      auth_required: true
```

#### Health Check Responses

**Basic Health (`/health`)**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-01T12:00:00Z"
}
```

**Readiness Check (`/ready`)**:
```json
{
  "status": "ready",
  "timestamp": "2025-09-01T12:00:00Z",
  "checks": {
    "routes": "healthy",
    "auth": "healthy",
    "secrets": "healthy"
  }
}
```

**Detailed Health (`/health/detailed`)**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-01T12:00:00Z",
  "version": "1.0.0",
  "uptime": "2d3h45m12s",
  
  "components": {
    "route_store": {
      "status": "healthy",
      "route_count": 15,
      "last_update": "2025-09-01T11:30:00Z"
    },
    "auth_adapter": {
      "status": "healthy",
      "type": "local",
      "active_sessions": 23
    },
    "secret_provider": {
      "status": "healthy", 
      "type": "kubernetes"
    }
  },
  
  "backends": {
    "user-service": {
      "status": "healthy",
      "url": "http://user-service:8080",
      "last_check": "2025-09-01T11:59:30Z",
      "response_time_ms": 12
    },
    "api-service": {
      "status": "unhealthy",
      "url": "http://api-service:8080", 
      "last_check": "2025-09-01T11:59:30Z",
      "error": "connection refused"
    }
  }
}
```

### Backend Health Monitoring

```yaml
# In route configuration
spec:
  backends:
    - url: http://backend-service:8080
      health_check:
        enabled: true
        path: /healthz
        interval_seconds: 30
        timeout_seconds: 5
        healthy_threshold: 2    # Consecutive successful checks to mark healthy
        unhealthy_threshold: 3  # Consecutive failed checks to mark unhealthy
        expected_status: [200, 204]
        
        # Custom health check headers
        headers:
          User-Agent: "l8e-harbor-health-check/1.0"
          X-Health-Check: "true"
```

### Kubernetes Integration

```yaml
# Deployment health checks
apiVersion: apps/v1
kind: Deployment
metadata:
  name: l8e-harbor
spec:
  template:
    spec:
      containers:
      - name: l8e-harbor
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Alerting

### Prometheus Alerting Rules

```yaml
# alerts.yml
groups:
- name: l8e-harbor
  rules:
  
  # High error rate
  - alert: HighErrorRate
    expr: |
      (
        sum(rate(l8e_proxy_requests_total{status_code=~"5.."}[5m])) by (route_id) /
        sum(rate(l8e_proxy_requests_total[5m])) by (route_id)
      ) * 100 > 5
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate on route {{ $labels.route_id }}"
      description: "Error rate is {{ $value }}% for route {{ $labels.route_id }}"
  
  # High response time
  - alert: HighResponseTime
    expr: |
      histogram_quantile(0.95, 
        sum(rate(l8e_proxy_request_duration_seconds_bucket[5m])) by (route_id, le)
      ) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time on route {{ $labels.route_id }}"
      description: "95th percentile response time is {{ $value }}s"
  
  # Backend down
  - alert: BackendDown
    expr: l8e_backend_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Backend {{ $labels.backend }} is down"
      description: "Backend {{ $labels.backend }} for route {{ $labels.route_id }} is unhealthy"
  
  # Circuit breaker open
  - alert: CircuitBreakerOpen
    expr: l8e_circuit_breaker_state == 2
    labels:
      severity: warning
    annotations:
      summary: "Circuit breaker open for {{ $labels.route_id }}"
      description: "Circuit breaker is open for route {{ $labels.route_id }}, backend {{ $labels.backend }}"
```

### Alert Manager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@example.com'

route:
  group_by: ['alertname', 'route_id']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'admin@example.com'
    subject: 'l8e-harbor Alert: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
  
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#alerts'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

1. **Request Rate**: Requests per second by route
2. **Error Rate**: Percentage of failed requests
3. **Response Time**: 95th percentile latency
4. **Backend Health**: Percentage of healthy backends
5. **Circuit Breaker Events**: Frequency of circuit breaker activations

### Performance Queries

```promql
# Request rate (RPS)
sum(rate(l8e_proxy_requests_total[1m])) by (route_id)

# Error rate (%)
sum(rate(l8e_proxy_requests_total{status_code=~"5.."}[5m])) by (route_id) /
sum(rate(l8e_proxy_requests_total[5m])) by (route_id) * 100

# Apdex score (Application Performance Index)
(
  sum(rate(l8e_proxy_request_duration_seconds_bucket{le="0.1"}[5m])) by (route_id) +
  sum(rate(l8e_proxy_request_duration_seconds_bucket{le="0.4"}[5m])) by (route_id)
) / 2 / sum(rate(l8e_proxy_requests_total[5m])) by (route_id)

# Throughput by backend
sum(rate(l8e_proxy_requests_total[5m])) by (backend)
```

## Debugging and Troubleshooting

### Debug Logging

Enable detailed logging for troubleshooting:

```yaml
log_level: DEBUG
request_logging:
  enabled: true
  log_headers: true        # Only for debugging - security risk
  log_body: true          # Only for debugging - performance impact
  include_request_id: true

# Component-specific debug levels
debug_components:
  - "router"
  - "auth"
  - "circuit_breaker"
  - "health_check"
```

### Log Analysis

```bash
# Find requests by trace ID
grep "req_abc123def456" /var/log/l8e-harbor/app.log

# Find all errors for a specific route
jq 'select(.route_id == "api-v1" and .level == "ERROR")' /var/log/l8e-harbor/app.log

# Find slow requests (>1 second)
jq 'select(.duration_ms > 1000)' /var/log/l8e-harbor/app.log

# Authentication failures
jq 'select(.logger == "l8e.auth" and .level == "ERROR")' /var/log/l8e-harbor/app.log
```

### Metrics Troubleshooting

```bash
# Check metric endpoint
curl http://localhost:9090/metrics

# Verify specific metrics
curl -s http://localhost:9090/metrics | grep l8e_proxy_requests_total

# Test with Prometheus query
curl 'http://prometheus:9090/api/v1/query?query=l8e_proxy_requests_total'
```

## Best Practices

### Monitoring Strategy

1. **Start with Golden Signals**: Request rate, error rate, duration, saturation
2. **Use SLIs/SLOs**: Define Service Level Indicators and Objectives
3. **Alert on User Impact**: Focus on customer-facing issues
4. **Monitor Business Metrics**: Not just technical metrics
5. **Regular Review**: Continuously improve monitoring and alerting

### Log Management

1. **Structured Logging**: Always use JSON format in production
2. **Log Levels**: Use appropriate levels (DEBUG only for development)
3. **Sensitive Data**: Never log passwords, tokens, or PII
4. **Performance**: Be mindful of logging overhead
5. **Retention**: Set appropriate log retention policies

### Metrics Guidelines

1. **Naming Convention**: Use consistent metric naming
2. **Labels**: Keep cardinality low, avoid high-cardinality labels
3. **Aggregation**: Design metrics for easy aggregation
4. **Documentation**: Document custom metrics and their purpose

## Next Steps

- Set up [Grafana dashboards](https://grafana.com/grafana/dashboards/) for visualization
- Configure [alert routing](https://prometheus.io/docs/alerting/latest/configuration/) based on severity
- Integrate with your existing monitoring stack
- Review [SECURITY.md](SECURITY.md) for security monitoring
- Check [deployments/](deployments/README.md) for deployment-specific monitoring setup