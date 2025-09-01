# Calculator MCP Example

This example demonstrates how to use l8e-harbor to proxy a Model Context Protocol (MCP) service with full observability, metrics, and logging.

## Overview

The example includes:
- **Calculator MCP Service**: A FastAPI-based MCP server providing calculator and unit conversion tools
- **l8e-harbor Proxy**: Routes requests with logging, metrics, circuit breaker, and rate limiting
- **Prometheus**: Collects and stores metrics from l8e-harbor
- **Docker Compose**: Orchestrates all services with proper networking and health checks

## Quick Start

1. **Clone and navigate to the example**:
   ```bash
   cd examples/calculator-mcp
   ```

2. **Build and start all services**:
   ```bash
   docker-compose up --build -d
   ```

3. **Wait for services to be healthy** (check logs):
   ```bash
   docker-compose logs -f
   ```

4. **Test the MCP service through l8e-harbor**:
   
   List available tools:
   ```bash
   curl -X POST http://localhost:18080/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list",
       "params": {}
     }'
   ```

   Call the calculator:
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
           "expression": "2 + 3 * 4"
         }
       }
     }'
   ```

   Convert units:
   ```bash
   curl -X POST http://localhost:18080/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 3, 
       "method": "tools/call",
       "params": {
         "name": "convert_units",
         "arguments": {
           "value": 100,
           "from_unit": "celsius", 
           "to_unit": "fahrenheit"
         }
       }
     }'
   ```

## Service Endpoints

- **Calculator MCP Service**: http://localhost:3001 (direct access)
- **l8e-harbor Proxy**: http://localhost:18080/mcp (proxied access)
- **l8e-harbor Management**: https://localhost:18443 (admin API)
- **Prometheus**: http://localhost:9090 (metrics dashboard)

## Observability Features

### Structured Logs

Both l8e-harbor and the MCP service produce structured logs:

**l8e-harbor logs**:
```json
{
  "timestamp": "2025-09-01T12:00:01Z",
  "level": "INFO",
  "message": "Request completed",
  "request_id": "req_001",
  "method": "POST", 
  "path": "/mcp",
  "status_code": 200,
  "duration_ms": 15.2,
  "route_id": "calculator-mcp",
  "backend": "http://calculator-mcp:3000"
}
```

**MCP service logs**:
```
2025-09-01 12:00:01 [INFO] calculator-mcp: Calculator: '2 + 3 * 4' = 14
```

### Prometheus Metrics

Access metrics at http://localhost:9090 or https://localhost:18443/metrics:

```prometheus
# Request rate by route
l8e_proxy_requests_total{route_id="calculator-mcp",method="POST",status_code="200"} 45

# Response time percentiles  
l8e_proxy_request_duration_seconds{route_id="calculator-mcp",quantile="0.95"} 0.025

# Circuit breaker status
l8e_circuit_breaker_state{route_id="calculator-mcp",backend="calculator-mcp:3000"} 0

# Backend health
l8e_backend_up{route_id="calculator-mcp",backend="calculator-mcp:3000"} 1
```

### Error Handling

Test error scenarios:

```bash
# Invalid expression
curl -X POST http://localhost:18080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call", 
    "params": {
      "name": "calculator",
      "arguments": {
        "expression": "invalid_expression"
      }
    }
  }'
```

Response shows proper error handling:
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "error": {
    "code": -32000,
    "message": "Calculation error", 
    "data": "Error evaluating 'invalid_expression': name 'invalid_expression' is not defined"
  }
}
```

## Configuration Features Demonstrated

### Circuit Breaker
- Automatically opens when failure rate exceeds 50%
- Prevents cascading failures
- Auto-recovery after timeout

### Rate Limiting  
- 100 requests per minute per client
- Burst allowance of 20 requests
- Protects backend from overload

### Health Checks
- Automatic backend health monitoring
- Removes unhealthy backends from rotation
- Configurable check intervals and thresholds

### Retry Policy
- Automatic retry on 5xx errors, timeouts, connection errors
- Exponential backoff
- Prevents client-side failures from transient issues

## Development

### Running Services Individually

**Calculator MCP service**:
```bash
cd examples/calculator-mcp
pip install -r requirements.txt
python calculator_mcp.py
```

**l8e-harbor with example config**:
```bash
l8e-harbor --config-file examples/calculator-mcp/harbor-config.yaml
```

### Testing

**Direct MCP service test**:
```bash
curl -X POST http://localhost:3000 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'
```

**Health checks**:
```bash
curl http://localhost:3000/health          # MCP service
curl -k https://localhost:18443/health     # l8e-harbor
```

### Monitoring

View real-time logs:
```bash
docker-compose logs -f l8e-harbor calculator-mcp
```

Monitor metrics in Prometheus:
```bash
open http://localhost:9090
# Query: rate(l8e_proxy_requests_total[5m])
```

## Cleanup

```bash
docker-compose down -v  # Remove containers and volumes
docker system prune     # Clean up Docker resources
```

## Key Benefits Demonstrated

1. **Zero Code Changes**: MCP service runs unchanged behind l8e-harbor
2. **Enterprise Observability**: Structured logs, metrics, tracing ready
3. **Production Reliability**: Circuit breaker, retries, health checks
4. **Security**: Rate limiting, header filtering, TLS termination
5. **Operational Excellence**: Easy deployment, monitoring, debugging

This example shows how l8e-harbor transforms any HTTP service into a production-ready, observable, and resilient service with minimal configuration.