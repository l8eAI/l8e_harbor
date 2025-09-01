# l8e-harbor Examples

This directory contains practical examples and configurations for l8e-harbor.

## Configuration Examples

- **[`config.yaml`](config.yaml)** - Minimal development configuration with HTTP and local file storage
- **[`mcp-route.yaml`](mcp-route.yaml)** - Complete route definition with middleware and health checks  
- **[`routes-backup.yaml`](routes-backup.yaml)** - Route export/backup format example

## Calculator MCP Service Example

This example demonstrates l8e-harbor's efficacy by proxying a Model Context Protocol (MCP) service with comprehensive logging, metrics, and reliability features.

> 📁 **Complete example available in [`calculator-mcp/`](calculator-mcp/)**

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

> 📖 **See the complete example with detailed instructions**: [`calculator-mcp/README.md`](calculator-mcp/README.md)

## Using Example Configurations

### Basic Development Setup

Use the minimal configuration for local development:

```bash
# Start l8e-harbor with example config
l8e-harbor --config examples/config.yaml
```

### Creating Routes

Apply example route configurations:

```bash
# Using harbor-ctl CLI
harbor-ctl apply -f examples/mcp-route.yaml

# Using the Management API
curl -k -X PUT https://localhost:18443/api/v1/routes/calculator-mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @examples/mcp-route.yaml
```

### Route Backup and Restore

Export and import route configurations:

```bash
# Export all routes (creates format like routes-backup.yaml)
harbor-ctl export routes -o backup.yaml

# Import routes
harbor-ctl import -f backup.yaml
```

## Next Steps

- Explore the complete [Calculator MCP example](calculator-mcp/)
- Check [deployment options](../deployments/) for production setups
- Review the main [l8e-harbor documentation](../README.md)