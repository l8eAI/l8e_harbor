"""
Prometheus metrics collection for l8e-harbor.
"""

import time
from typing import Dict, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


class MetricsCollector:
    """Centralized metrics collection."""
    
    def __init__(self):
        # Request metrics
        self.requests_total = Counter(
            'l8e_proxy_requests_total',
            'Total proxy requests',
            ['route_id', 'method', 'status_code', 'backend']
        )
        
        self.request_duration = Histogram(
            'l8e_proxy_request_duration_seconds',
            'Request duration in seconds',
            ['route_id', 'backend'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        
        # Route metrics
        self.routes_count = Gauge(
            'l8e_routes_total',
            'Total number of routes configured'
        )
        
        # Backend metrics
        self.backend_up = Gauge(
            'l8e_backend_up',
            'Backend health status (1 = up, 0 = down)',
            ['backend', 'route_id']
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'l8e_circuit_breaker_state',
            'Circuit breaker state (0 = closed, 1 = open, 2 = half-open)',
            ['backend', 'route_id']
        )
        
        # Authentication metrics
        self.auth_attempts = Counter(
            'l8e_auth_attempts_total',
            'Total authentication attempts',
            ['adapter_type', 'status']
        )
        
        # Route store metrics
        self.route_store_operations = Counter(
            'l8e_route_store_operations_total',
            'Route store operations',
            ['operation', 'status']
        )
        
        self.route_store_sync_time = Histogram(
            'l8e_route_store_sync_time_seconds',
            'Time taken to sync route store'
        )
        
        # Active connections
        self.active_connections = Gauge(
            'l8e_active_connections',
            'Number of active proxy connections'
        )
    
    def record_request(
        self,
        route_id: str,
        method: str,
        status_code: int,
        backend: str,
        duration: float
    ):
        """Record a proxy request."""
        self.requests_total.labels(
            route_id=route_id,
            method=method,
            status_code=str(status_code),
            backend=backend
        ).inc()
        
        self.request_duration.labels(
            route_id=route_id,
            backend=backend
        ).observe(duration)
    
    def record_auth_attempt(self, adapter_type: str, success: bool):
        """Record an authentication attempt."""
        status = "success" if success else "failure"
        self.auth_attempts.labels(
            adapter_type=adapter_type,
            status=status
        ).inc()
    
    def set_routes_count(self, count: int):
        """Set the total number of routes."""
        self.routes_count.set(count)
    
    def set_backend_status(self, backend: str, route_id: str, is_up: bool):
        """Set backend health status."""
        self.backend_up.labels(
            backend=backend,
            route_id=route_id
        ).set(1 if is_up else 0)
    
    def set_circuit_breaker_state(self, backend: str, route_id: str, state: str):
        """Set circuit breaker state."""
        state_value = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}.get(state, 0)
        self.circuit_breaker_state.labels(
            backend=backend,
            route_id=route_id
        ).set(state_value)
    
    def record_route_store_operation(self, operation: str, success: bool):
        """Record a route store operation."""
        status = "success" if success else "failure"
        self.route_store_operations.labels(
            operation=operation,
            status=status
        ).inc()
    
    def time_route_store_sync(self):
        """Return a timer for route store sync operations."""
        return self.route_store_sync_time.time()
    
    def inc_active_connections(self):
        """Increment active connections counter."""
        self.active_connections.inc()
    
    def dec_active_connections(self):
        """Decrement active connections counter."""
        self.active_connections.dec()
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest().decode('utf-8')


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


class RequestMetricsContext:
    """Context manager for tracking request metrics."""
    
    def __init__(self, route_id: str, method: str, backend: str):
        self.route_id = route_id
        self.method = method
        self.backend = backend
        self.start_time = None
        self.status_code = None
        self.metrics = get_metrics_collector()
    
    def __enter__(self):
        self.start_time = time.time()
        self.metrics.inc_active_connections()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        status_code = self.status_code or (500 if exc_type else 200)
        
        self.metrics.record_request(
            self.route_id,
            self.method,
            status_code,
            self.backend,
            duration
        )
        self.metrics.dec_active_connections()
    
    def set_status_code(self, status_code: int):
        """Set the response status code."""
        self.status_code = status_code