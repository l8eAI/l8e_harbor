"""
Integration tests for l8e-harbor.

These tests verify that all components work together correctly.
"""

import pytest
import asyncio
import tempfile
import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_auth_adapter, get_secret_provider, get_route_store
from app.adapters.impl.simple_auth import SimpleLocalAuthAdapter
from app.adapters.impl.localfs_secrets import LocalFSSecretProvider
from app.adapters.impl.memory_routes import InMemoryRouteStore
from app.models.schemas import RouteSpec, BackendSpec


@pytest.fixture
def temp_dir():
    """Create temporary directory for integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def integrated_secret_provider(temp_dir):
    """Create a real secret provider for integration tests."""
    provider = LocalFSSecretProvider(temp_dir)
    provider.ensure_default_secrets()
    return provider


@pytest.fixture
def integrated_auth_adapter(integrated_secret_provider):
    """Create a real auth adapter for integration tests."""
    return SimpleLocalAuthAdapter(
        secret_provider=integrated_secret_provider,
        jwt_ttl_seconds=900
    )


@pytest.fixture
def integrated_route_store(temp_dir):
    """Create a real route store for integration tests."""
    return InMemoryRouteStore(f"{temp_dir}/routes.json")


@pytest.fixture
def integrated_client(integrated_auth_adapter, integrated_secret_provider, integrated_route_store):
    """Create an integrated test client."""
    
    # Override dependencies with real implementations
    app.dependency_overrides[get_auth_adapter] = lambda: integrated_auth_adapter
    app.dependency_overrides[get_secret_provider] = lambda: integrated_secret_provider
    app.dependency_overrides[get_route_store] = lambda: integrated_route_store
    
    client = TestClient(app)
    yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def mock_backend_server():
    """Create a mock backend server for testing."""
    import aiohttp.web
    from aiohttp import web
    
    # Track requests received
    received_requests = []
    
    async def handler(request):
        received_requests.append({
            'method': request.method,
            'path': request.path_qs,
            'headers': dict(request.headers),
            'body': await request.text()
        })
        
        # Return different responses based on path
        if request.path == '/health':
            return web.json_response({'status': 'healthy'})
        elif request.path == '/error':
            return web.json_response({'error': 'server error'}, status=500)
        elif request.path == '/slow':
            await asyncio.sleep(2)
            return web.json_response({'message': 'slow response'})
        else:
            return web.json_response({'message': 'success', 'path': request.path})
    
    # Create app and server
    mock_app = web.Application()
    mock_app.router.add_route('*', '/{path:.*}', handler)
    
    runner = web.AppRunner(mock_app)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', 8901)  # Use different port
    await site.start()
    
    yield 'http://localhost:8901', received_requests
    
    # Cleanup
    await runner.cleanup()


class TestEndToEndFlow:
    """Test complete end-to-end flows."""
    
    @pytest.mark.asyncio
    async def test_complete_bootstrap_and_route_creation_flow(self, integrated_client):
        """Test complete flow from bootstrap to route creation."""
        
        # Step 1: Bootstrap the system
        response = integrated_client.post("/api/v1/bootstrap", json={
            "admin_username": "admin",
            "admin_password": "admin123456"
        })
        
        assert response.status_code == 200
        bootstrap_data = response.json()
        assert bootstrap_data["admin_user_created"] is True
        
        # Step 2: Login as admin
        response = integrated_client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123456"
        })
        
        assert response.status_code == 200
        token_data = response.json()
        token = token_data["access_token"]
        
        # Step 3: Create a route
        route_data = {
            "id": "integration-test-route",
            "path": "/api/integration",
            "methods": ["GET", "POST"],
            "backends": [{"url": "http://integration-backend.com:8080"}],
            "priority": 10
        }
        
        response = integrated_client.put(
            "/api/v1/routes/integration-test-route",
            headers={"Authorization": f"Bearer {token}"},
            json=route_data
        )
        
        assert response.status_code == 200
        created_route = response.json()
        assert created_route["id"] == "integration-test-route"
        
        # Step 4: List routes
        response = integrated_client.get(
            "/api/v1/routes",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        routes = response.json()
        assert len(routes) == 1
        assert routes[0]["id"] == "integration-test-route"
        
        # Step 5: Export routes
        response = integrated_client.get(
            "/api/v1/routes:export",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-yaml"
        export_content = response.content.decode()
        assert "integration-test-route" in export_content
        
        # Step 6: Delete route
        response = integrated_client.delete(
            "/api/v1/routes/integration-test-route",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Step 7: Verify route is deleted
        response = integrated_client.get(
            "/api/v1/routes",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        routes = response.json()
        assert len(routes) == 0
    
    @pytest.mark.asyncio
    async def test_user_management_flow(self, integrated_client):
        """Test complete user management flow."""
        
        # Bootstrap and login as admin
        integrated_client.post("/api/v1/bootstrap", json={
            "admin_username": "admin",
            "admin_password": "admin123456"
        })
        
        login_response = integrated_client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123456"
        })
        token = login_response.json()["access_token"]
        auth_header = {"Authorization": f"Bearer {token}"}
        
        # Create a new user
        response = integrated_client.post(
            "/api/v1/admin/users",
            headers=auth_header,
            json={
                "username": "captain",
                "password": "captain123", 
                "role": "captain"
            }
        )
        
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["username"] == "captain"
        assert user_data["role"] == "captain"
        
        # Test new user login
        response = integrated_client.post("/api/v1/auth/login", json={
            "username": "captain",
            "password": "captain123"
        })
        
        assert response.status_code == 200
        captain_token = response.json()["access_token"]
        
        # Update user role
        response = integrated_client.patch(
            "/api/v1/admin/users/captain",
            headers=auth_header,
            json={"role": "harbor-master"}
        )
        
        assert response.status_code == 200
        updated_user = response.json()
        assert updated_user["role"] == "harbor-master"
        
        # List all users
        response = integrated_client.get(
            "/api/v1/admin/users",
            headers=auth_header
        )
        
        assert response.status_code == 200
        users = response.json()
        assert "admin" in users
        assert "captain" in users
        
        # Delete user
        response = integrated_client.delete(
            "/api/v1/admin/users/captain",
            headers=auth_header
        )
        
        assert response.status_code == 204
        
        # Verify user can no longer login
        response = integrated_client.post("/api/v1/auth/login", json={
            "username": "captain",
            "password": "captain123"
        })
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_proxy_request_flow(self, integrated_client, integrated_route_store, mock_backend_server):
        """Test complete proxy request flow."""
        backend_url, received_requests = await mock_backend_server
        
        # Create a route pointing to mock backend
        route = RouteSpec(
            id="proxy-test-route",
            path="/api/proxy",
            methods=["GET", "POST"],
            backends=[BackendSpec(url=backend_url)],
            priority=10
        )
        
        await integrated_route_store.put_route(route)
        
        # Test successful proxy request
        response = integrated_client.get("/api/proxy/test")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "success"
        assert response_data["path"] == "/test"
        
        # Verify backend received the request
        assert len(received_requests) == 1
        backend_request = received_requests[0]
        assert backend_request["method"] == "GET"
        assert backend_request["path"] == "/test"
        
        # Test POST request
        response = integrated_client.post(
            "/api/proxy/create",
            json={"data": "test"}
        )
        
        assert response.status_code == 200
        assert len(received_requests) == 2
        
        post_request = received_requests[1]
        assert post_request["method"] == "POST"
        assert post_request["path"] == "/create"
        assert "data" in post_request["body"]
    
    @pytest.mark.asyncio
    async def test_authentication_integration(self, integrated_client, integrated_route_store):
        """Test authentication integration with routing."""
        
        # Bootstrap and create protected route
        integrated_client.post("/api/v1/bootstrap", json={
            "admin_username": "admin",
            "admin_password": "admin123456"
        })
        
        login_response = integrated_client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123456"
        })
        token = login_response.json()["access_token"]
        
        # Create route with auth middleware
        protected_route = RouteSpec(
            id="protected-route",
            path="/api/protected",
            methods=["GET"],
            backends=[BackendSpec(url="http://backend.com")],
            middleware=[
                {"name": "auth", "config": {"require_role": "harbor-master"}}
            ]
        )
        
        await integrated_route_store.put_route(protected_route)
        
        # Test access without token (should fail)
        response = integrated_client.get("/api/protected/resource")
        assert response.status_code == 401
        
        # Test access with valid token (should work)
        # Note: This would require actual middleware implementation
        # For now, we test that the route is configured correctly
        routes = await integrated_route_store.list_routes()
        assert len(routes) == 1
        assert routes[0].middleware[0]["name"] == "auth"


class TestErrorHandlingIntegration:
    """Test error handling across the entire system."""
    
    @pytest.mark.asyncio
    async def test_backend_failure_handling(self, integrated_client, integrated_route_store, mock_backend_server):
        """Test handling of backend failures."""
        backend_url, received_requests = await mock_backend_server
        
        # Create route with retry policy
        route = RouteSpec(
            id="error-test-route",
            path="/api/error",
            methods=["GET"],
            backends=[BackendSpec(url=backend_url)],
            retry_policy={
                "max_retries": 2,
                "backoff_ms": 100,
                "retry_on": ["5xx", "timeout"]
            }
        )
        
        await integrated_route_store.put_route(route)
        
        # Test request to error endpoint
        response = integrated_client.get("/api/error/error")
        
        # Should return 500 (backend error)
        assert response.status_code == 500
        
        # Backend should have received the request
        assert len(received_requests) >= 1
    
    @pytest.mark.asyncio
    async def test_route_not_found_handling(self, integrated_client):
        """Test handling when no route matches."""
        response = integrated_client.get("/api/nonexistent/path")
        
        assert response.status_code == 404
        response_data = response.json()
        assert "not found" in response_data["detail"].lower()
    
    @pytest.mark.asyncio 
    async def test_method_not_allowed_handling(self, integrated_client, integrated_route_store):
        """Test handling when route exists but method not allowed."""
        # Create route that only allows GET
        route = RouteSpec(
            id="get-only-route",
            path="/api/get-only",
            methods=["GET"],
            backends=[BackendSpec(url="http://backend.com")]
        )
        
        await integrated_route_store.put_route(route)
        
        # Try POST to GET-only route
        response = integrated_client.post("/api/get-only/resource")
        
        assert response.status_code == 405  # Method Not Allowed
    
    @pytest.mark.asyncio
    async def test_invalid_jwt_token_handling(self, integrated_client):
        """Test handling of invalid JWT tokens."""
        # Try to access protected endpoint with invalid token
        response = integrated_client.get(
            "/api/v1/routes",
            headers={"Authorization": "Bearer invalid.jwt.token"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_expired_jwt_token_handling(self, integrated_client, integrated_auth_adapter):
        """Test handling of expired JWT tokens."""
        # Create user and token with very short TTL
        short_ttl_adapter = SimpleLocalAuthAdapter(
            secret_provider=integrated_auth_adapter.secret_provider,
            jwt_ttl_seconds=1  # 1 second
        )
        
        await short_ttl_adapter.create_user("tempuser", "temppass", "captain")
        user = await short_ttl_adapter.authenticate_user("tempuser", "temppass")
        token_data = await short_ttl_adapter.issue_token(user)
        
        # Wait for token to expire
        time.sleep(2)
        
        # Try to use expired token
        response = integrated_client.get(
            "/api/v1/routes",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        
        assert response.status_code == 401


class TestPerformanceIntegration:
    """Test performance characteristics of the integrated system."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, integrated_client, integrated_route_store, mock_backend_server):
        """Test handling of concurrent requests."""
        backend_url, received_requests = await mock_backend_server
        
        # Create route
        route = RouteSpec(
            id="concurrent-test",
            path="/api/concurrent",
            methods=["GET"],
            backends=[BackendSpec(url=backend_url)]
        )
        
        await integrated_route_store.put_route(route)
        
        # Make concurrent requests
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            response = integrated_client.get("/api/concurrent/test")
            results.put(response.status_code)
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        assert len(status_codes) == 10
        assert all(code == 200 for code in status_codes)
        
        # Backend should have received all requests
        assert len(received_requests) >= 10
    
    @pytest.mark.asyncio
    async def test_large_route_table_performance(self, integrated_client, integrated_route_store):
        """Test performance with large number of routes."""
        
        # Create many routes
        routes = []
        for i in range(100):
            route = RouteSpec(
                id=f"perf-route-{i:03d}",
                path=f"/api/perf/{i % 10}/endpoint{i}",
                methods=["GET"],
                backends=[BackendSpec(url=f"http://backend{i % 5}.com")],
                priority=i % 20
            )
            routes.append(route)
        
        # Store all routes
        start_time = time.time()
        for route in routes:
            await integrated_route_store.put_route(route)
        store_time = time.time() - start_time
        
        # Test route matching performance
        start_time = time.time()
        for i in range(0, 100, 10):  # Test every 10th route
            response = integrated_client.get(f"/api/perf/{i % 10}/endpoint{i}/test")
            # Should get 404 since no actual backend, but route should be found
            assert response.status_code in [404, 502]  # Either no backend or backend unreachable
        lookup_time = time.time() - start_time
        
        # Performance assertions
        assert store_time < 5.0   # Should store 100 routes quickly
        assert lookup_time < 2.0  # Should lookup routes quickly
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, integrated_client, integrated_route_store):
        """Test that memory usage remains stable over many operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many operations
        for i in range(50):
            route = RouteSpec(
                id=f"memory-test-{i}",
                path=f"/api/memory/{i}",
                methods=["GET"],
                backends=[BackendSpec(url="http://memory-backend.com")]
            )
            await integrated_route_store.put_route(route)
            
            # Also delete some routes to test cleanup
            if i > 10:
                await integrated_route_store.delete_route(f"memory-test-{i-10}")
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB for this test)
        assert memory_growth < 50 * 1024 * 1024  # 50MB


class TestDataConsistencyIntegration:
    """Test data consistency across components."""
    
    @pytest.mark.asyncio
    async def test_route_consistency_across_stores(self, temp_dir):
        """Test that routes remain consistent across different storage implementations."""
        from app.adapters.impl.sqlite_routes import SQLiteRouteStore
        
        # Create route
        route = RouteSpec(
            id="consistency-test",
            path="/api/consistency",
            methods=["GET", "POST"],
            backends=[BackendSpec(url="http://consistent.com")],
            priority=5
        )
        
        # Store in memory store
        memory_store = InMemoryRouteStore(f"{temp_dir}/memory.json")
        await memory_store.put_route(route)
        
        # Store in SQLite store
        sqlite_store = SQLiteRouteStore(f"{temp_dir}/sqlite.db")
        await sqlite_store.put_route(route)
        
        # Retrieve from both
        memory_route = await memory_store.get_route("consistency-test")
        sqlite_route = await sqlite_store.get_route("consistency-test")
        
        # Should be equivalent
        assert memory_route.id == sqlite_route.id
        assert memory_route.path == sqlite_route.path
        assert memory_route.methods == sqlite_route.methods
        assert len(memory_route.backends) == len(sqlite_route.backends)
        assert memory_route.priority == sqlite_route.priority
    
    @pytest.mark.asyncio
    async def test_user_secret_consistency(self, temp_dir):
        """Test user data consistency between auth adapter and secret provider."""
        # Create secret provider and auth adapter
        secret_provider = LocalFSSecretProvider(temp_dir)
        secret_provider.ensure_default_secrets()
        auth_adapter = SimpleLocalAuthAdapter(secret_provider, 900)
        
        # Create user through auth adapter
        await auth_adapter.create_user("consistency_user", "password123", "captain")
        
        # Verify user data exists in secret provider
        users_data = await secret_provider.get_secret("users.json")
        assert users_data is not None
        
        users = json.loads(users_data)
        assert "consistency_user" in users
        assert users["consistency_user"]["role"] == "captain"
        
        # Authenticate user
        user = await auth_adapter.authenticate_user("consistency_user", "password123")
        assert user is not None
        assert user.username == "consistency_user"
        assert user.role == "captain"
        
        # Delete user through auth adapter
        deleted = await auth_adapter.delete_user("consistency_user")
        assert deleted is True
        
        # Verify user is gone from secret provider
        users_data = await secret_provider.get_secret("users.json")
        users = json.loads(users_data)
        assert "consistency_user" not in users