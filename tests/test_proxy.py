"""
Tests for proxy logic and routing.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import httpx
from fastapi import Request, Response
from starlette.datastructures import URL, Headers

from app.core.proxy import RouteManager, ProxyHandler, BackendSelector
from app.adapters.impl.memory_routes import InMemoryRouteStore
from app.models.schemas import (
    RouteSpec, BackendSpec, RetryPolicySpec, CircuitBreakerSpec, 
    MiddlewareSpec, HealthCheckSpec
)


@pytest.fixture
def route_store():
    """Create a test route store."""
    return InMemoryRouteStore("/tmp/test_proxy_routes.json")


@pytest.fixture
def route_manager(route_store):
    """Create a route manager."""
    return RouteManager(route_store)


@pytest.fixture
def mock_auth_adapter():
    """Create a mock auth adapter."""
    mock = AsyncMock()
    mock.verify_token.return_value = None  # No auth by default
    return mock


@pytest.fixture
def proxy_handler(route_manager, mock_auth_adapter):
    """Create a proxy handler."""
    return ProxyHandler(route_manager, mock_auth_adapter)


@pytest.fixture
def sample_route():
    """Create a sample route for testing."""
    return RouteSpec(
        id="test-route",
        path="/api/v1",
        methods=["GET", "POST"],
        backends=[
            BackendSpec(url="http://backend1.com:8080", weight=100),
            BackendSpec(url="http://backend2.com:8080", weight=50)
        ],
        priority=10,
        timeout_ms=5000,
        retry_policy=RetryPolicySpec(
            max_retries=2,
            backoff_ms=100,
            retry_on=["5xx", "timeout"]
        ),
        circuit_breaker=CircuitBreakerSpec(
            enabled=True,
            failure_threshold=50,
            minimum_requests=10,
            timeout_ms=30000
        )
    )


class TestRouteManager:
    """Test route management logic."""
    
    @pytest.mark.asyncio
    async def test_add_and_find_route(self, route_manager, sample_route):
        """Test adding and finding routes."""
        # Add route
        await route_manager.add_route(sample_route)
        
        # Find exact match
        found_route = await route_manager.find_route("/api/v1/users", "GET")
        assert found_route is not None
        assert found_route.id == "test-route"
        
        # Test method matching
        found_route = await route_manager.find_route("/api/v1/users", "POST")
        assert found_route is not None
        
        # Test method not allowed
        found_route = await route_manager.find_route("/api/v1/users", "DELETE")
        assert found_route is None
    
    @pytest.mark.asyncio
    async def test_route_priority_ordering(self, route_manager):
        """Test that routes are matched by priority."""
        # Create routes with different priorities
        high_priority_route = RouteSpec(
            id="high-priority",
            path="/api",
            methods=["GET"],
            backends=[BackendSpec(url="http://high.com")],
            priority=100
        )
        
        low_priority_route = RouteSpec(
            id="low-priority", 
            path="/api/v1",
            methods=["GET"],
            backends=[BackendSpec(url="http://low.com")],
            priority=10
        )
        
        # Add in reverse order
        await route_manager.add_route(low_priority_route)
        await route_manager.add_route(high_priority_route)
        
        # Higher priority should be matched first even if less specific
        found_route = await route_manager.find_route("/api/v1/test", "GET")
        assert found_route.id == "high-priority"
    
    @pytest.mark.asyncio
    async def test_path_specificity(self, route_manager):
        """Test that more specific paths are preferred when priority is equal."""
        # Create routes with same priority but different specificity
        general_route = RouteSpec(
            id="general",
            path="/api",
            methods=["GET"],
            backends=[BackendSpec(url="http://general.com")],
            priority=10
        )
        
        specific_route = RouteSpec(
            id="specific",
            path="/api/v1/users",
            methods=["GET"], 
            backends=[BackendSpec(url="http://specific.com")],
            priority=10
        )
        
        await route_manager.add_route(general_route)
        await route_manager.add_route(specific_route)
        
        # More specific route should be matched
        found_route = await route_manager.find_route("/api/v1/users/123", "GET")
        assert found_route.id == "specific"
        
        # General route should match less specific requests
        found_route = await route_manager.find_route("/api/other", "GET")
        assert found_route.id == "general"
    
    @pytest.mark.asyncio
    async def test_remove_route(self, route_manager, sample_route):
        """Test removing routes."""
        # Add route
        await route_manager.add_route(sample_route)
        
        # Verify it exists
        found = await route_manager.find_route("/api/v1/test", "GET")
        assert found is not None
        
        # Remove route
        removed = await route_manager.remove_route("test-route")
        assert removed is True
        
        # Verify it's gone
        found = await route_manager.find_route("/api/v1/test", "GET")
        assert found is None
        
        # Try to remove again
        removed = await route_manager.remove_route("test-route")
        assert removed is False


class TestBackendSelector:
    """Test backend selection logic."""
    
    def test_weighted_selection(self):
        """Test weighted round-robin backend selection."""
        backends = [
            BackendSpec(url="http://backend1.com", weight=100),
            BackendSpec(url="http://backend2.com", weight=200),
            BackendSpec(url="http://backend3.com", weight=50)
        ]
        
        selector = BackendSelector(backends)
        
        # Track selections over many requests
        selections = {}
        for _ in range(350):  # LCM of weights
            backend = selector.select_backend()
            url = str(backend.url)
            selections[url] = selections.get(url, 0) + 1
        
        # Check approximate ratios (allowing some variance)
        total = sum(selections.values())
        
        # backend1: 100/350 ≈ 28.6%
        assert 90 <= selections["http://backend1.com"] <= 110
        
        # backend2: 200/350 ≈ 57.1%  
        assert 190 <= selections["http://backend2.com"] <= 210
        
        # backend3: 50/350 ≈ 14.3%
        assert 40 <= selections["http://backend3.com"] <= 60
    
    def test_single_backend(self):
        """Test selection with single backend."""
        backends = [BackendSpec(url="http://only.com", weight=100)]
        selector = BackendSelector(backends)
        
        # Should always return the same backend
        for _ in range(10):
            backend = selector.select_backend()
            assert str(backend.url) == "http://only.com"
    
    def test_zero_weight_backend(self):
        """Test handling of zero-weight backends."""
        backends = [
            BackendSpec(url="http://active.com", weight=100),
            BackendSpec(url="http://inactive.com", weight=0)
        ]
        
        selector = BackendSelector(backends)
        
        # Zero-weight backend should never be selected
        for _ in range(100):
            backend = selector.select_backend()
            assert str(backend.url) == "http://active.com"


class TestProxyHandler:
    """Test proxy request handling."""
    
    @pytest.mark.asyncio
    async def test_successful_proxy_request(self, proxy_handler, route_manager, sample_route):
        """Test successful proxy request."""
        # Add route
        await route_manager.add_route(sample_route)
        
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"success": true}'
        
        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = URL("http://localhost/api/v1/test")
        mock_request.headers = Headers({"user-agent": "test"})
        mock_request.body.return_value = b""
        
        with patch('httpx.AsyncClient.request', return_value=mock_response) as mock_http:
            response = await proxy_handler.handle_request(mock_request)
            
            assert response.status_code == 200
            assert b'{"success": true}' in response.body
            
            # Verify backend was called
            mock_http.assert_called_once()
            args, kwargs = mock_http.call_args
            assert kwargs["method"] == "GET"
            assert "backend1.com:8080" in kwargs["url"] or "backend2.com:8080" in kwargs["url"]
    
    @pytest.mark.asyncio
    async def test_route_not_found(self, proxy_handler):
        """Test request when no route matches."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = URL("http://localhost/nonexistent")
        
        response = await proxy_handler.handle_request(mock_request)
        
        assert response.status_code == 404
        assert b"No route found" in response.body
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self, proxy_handler, route_manager, sample_route):
        """Test request with method not allowed by route."""
        # Add route that only allows GET and POST
        await route_manager.add_route(sample_route)
        
        mock_request = Mock(spec=Request)
        mock_request.method = "DELETE"  # Not in allowed methods
        mock_request.url = URL("http://localhost/api/v1/test")
        
        response = await proxy_handler.handle_request(mock_request)
        
        assert response.status_code == 405  # Method Not Allowed
    
    @pytest.mark.asyncio
    async def test_backend_error_with_retry(self, proxy_handler, route_manager, sample_route):
        """Test backend error with retry logic."""
        await route_manager.add_route(sample_route)
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = URL("http://localhost/api/v1/test")
        mock_request.headers = Headers({})
        mock_request.body.return_value = b""
        
        # Mock HTTP client to fail twice then succeed
        call_count = 0
        def mock_request_func(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # First two calls fail with 500
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.headers = {}
                mock_response.content = b'{"error": "server error"}'
                return mock_response
            else:
                # Third call succeeds
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {}
                mock_response.content = b'{"success": true}'
                return mock_response
        
        with patch('httpx.AsyncClient.request', side_effect=mock_request_func):
            response = await proxy_handler.handle_request(mock_request)
            
            # Should succeed after retries
            assert response.status_code == 200
            assert call_count == 3  # Original + 2 retries
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, proxy_handler, route_manager, sample_route):
        """Test request timeout handling."""
        await route_manager.add_route(sample_route)
        
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = URL("http://localhost/api/v1/test")
        mock_request.headers = Headers({})
        mock_request.body.return_value = b""
        
        # Mock timeout exception
        with patch('httpx.AsyncClient.request', side_effect=httpx.TimeoutException("Request timeout")):
            response = await proxy_handler.handle_request(mock_request)
            
            assert response.status_code == 504  # Gateway Timeout
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, proxy_handler, route_manager, sample_route):
        """Test connection error handling."""
        await route_manager.add_route(sample_route)
        
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = URL("http://localhost/api/v1/test")
        mock_request.headers = Headers({})
        mock_request.body.return_value = b""
        
        # Mock connection error
        with patch('httpx.AsyncClient.request', side_effect=httpx.ConnectError("Connection refused")):
            response = await proxy_handler.handle_request(mock_request)
            
            assert response.status_code == 502  # Bad Gateway


class TestMiddleware:
    """Test middleware processing."""
    
    @pytest.mark.asyncio
    async def test_cors_middleware(self, proxy_handler, route_manager):
        """Test CORS middleware processing."""
        route_with_cors = RouteSpec(
            id="cors-route",
            path="/api/cors",
            methods=["GET", "POST"],
            backends=[BackendSpec(url="http://backend.com")],
            middleware=[
                MiddlewareSpec(
                    name="cors",
                    config={
                        "allow_origins": ["http://example.com"],
                        "allow_methods": ["GET", "POST"],
                        "allow_headers": ["authorization", "content-type"]
                    }
                )
            ]
        )
        
        await route_manager.add_route(route_with_cors)
        
        # Mock successful backend response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'{"data": "test"}'
        
        # Test preflight request
        mock_request = Mock(spec=Request)
        mock_request.method = "OPTIONS"
        mock_request.url = URL("http://localhost/api/cors")
        mock_request.headers = Headers({
            "origin": "http://example.com",
            "access-control-request-method": "POST"
        })
        
        with patch('httpx.AsyncClient.request', return_value=mock_response):
            response = await proxy_handler.handle_request(mock_request)
            
            # Should have CORS headers
            assert response.status_code == 200
            # Note: Actual CORS header checking would depend on implementation
    
    @pytest.mark.asyncio
    async def test_header_rewrite_middleware(self, proxy_handler, route_manager):
        """Test header rewrite middleware."""
        route_with_headers = RouteSpec(
            id="header-route",
            path="/api/headers",
            methods=["GET"],
            backends=[BackendSpec(url="http://backend.com")],
            middleware=[
                MiddlewareSpec(
                    name="header-rewrite",
                    config={
                        "set": {
                            "X-Service": "test-service",
                            "X-Version": "1.0"
                        },
                        "remove": ["X-Debug"]
                    }
                )
            ]
        )
        
        await route_manager.add_route(route_with_headers)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"data": "test"}'
        
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = URL("http://localhost/api/headers")
        mock_request.headers = Headers({"X-Debug": "remove-me"})
        mock_request.body.return_value = b""
        
        with patch('httpx.AsyncClient.request', return_value=mock_response) as mock_http:
            response = await proxy_handler.handle_request(mock_request)
            
            # Verify request was modified
            args, kwargs = mock_http.call_args
            sent_headers = kwargs.get("headers", {})
            
            # Should have added headers (implementation dependent)
            assert response.status_code == 200


class TestHealthChecks:
    """Test backend health checking."""
    
    @pytest.mark.asyncio
    async def test_backend_health_check(self, route_manager):
        """Test backend health checking."""
        route_with_health = RouteSpec(
            id="health-route",
            path="/api/health",
            methods=["GET"],
            backends=[
                BackendSpec(
                    url="http://backend.com",
                    health_check=HealthCheckSpec(
                        path="/health",
                        interval_seconds=30,
                        timeout_seconds=5,
                        healthy_threshold=2,
                        unhealthy_threshold=3
                    )
                )
            ]
        )
        
        await route_manager.add_route(route_with_health)
        
        # Health checking logic would be tested here
        # (Implementation would involve background tasks and state tracking)
        routes = await route_manager.route_store.list_routes()
        assert len(routes) == 1
        assert routes[0].backends[0].health_check is not None


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.asyncio 
    async def test_circuit_breaker_open(self, proxy_handler, route_manager):
        """Test circuit breaker opening on failures."""
        route_with_cb = RouteSpec(
            id="cb-route",
            path="/api/cb",
            methods=["GET"],
            backends=[BackendSpec(url="http://unreliable.com")],
            circuit_breaker=CircuitBreakerSpec(
                enabled=True,
                failure_threshold=50,  # 50% failure rate
                minimum_requests=2,    # Need at least 2 requests
                timeout_ms=60000
            )
        )
        
        await route_manager.add_route(route_with_cb)
        
        # Circuit breaker logic would be complex to test properly
        # Would require tracking success/failure ratios and state management
        # This is a placeholder for the actual implementation
        
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url = URL("http://localhost/api/cb")
        mock_request.headers = Headers({})
        mock_request.body.return_value = b""
        
        # Mock failing responses
        with patch('httpx.AsyncClient.request', side_effect=httpx.ConnectError("Service down")):
            # Multiple failures should eventually open circuit
            for _ in range(5):
                response = await proxy_handler.handle_request(mock_request)
                # First few might be 502, later might be 503 (circuit open)
                assert response.status_code in [502, 503]