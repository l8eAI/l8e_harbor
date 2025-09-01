"""
Tests for API endpoints.
"""

import pytest
import tempfile
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from app.core.dependencies import get_auth_adapter, get_secret_provider, get_route_store
from app.adapters.impl.simple_auth import SimpleLocalAuthAdapter
from app.adapters.impl.localfs_secrets import LocalFSSecretProvider
from app.adapters.impl.memory_routes import InMemoryRouteStore
from app.models.schemas import RouteSpec, BackendSpec


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_secret_provider(temp_dir):
    """Create a mock secret provider."""
    provider = LocalFSSecretProvider(temp_dir)
    provider.ensure_default_secrets()
    return provider


@pytest.fixture
def mock_auth_adapter(mock_secret_provider):
    """Create a mock auth adapter."""
    return SimpleLocalAuthAdapter(
        secret_provider=mock_secret_provider,
        jwt_ttl_seconds=900
    )


@pytest.fixture
def mock_route_store():
    """Create a mock route store."""
    return InMemoryRouteStore("/tmp/test_routes.json")


@pytest.fixture
def test_client(mock_auth_adapter, mock_secret_provider, mock_route_store):
    """Create a test client with mocked dependencies."""
    
    # Override dependencies
    app.dependency_overrides[get_auth_adapter] = lambda: mock_auth_adapter
    app.dependency_overrides[get_secret_provider] = lambda: mock_secret_provider
    app.dependency_overrides[get_route_store] = lambda: mock_route_store
    
    client = TestClient(app)
    yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(mock_auth_adapter):
    """Create an admin user for testing."""
    await mock_auth_adapter.create_user("admin", "admin123", "harbor-master")
    return await mock_auth_adapter.authenticate_user("admin", "admin123")


@pytest.fixture
async def admin_token(mock_auth_adapter, admin_user):
    """Create an admin JWT token."""
    token_data = await mock_auth_adapter.issue_token(admin_user)
    return token_data["access_token"]


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "l8e-harbor"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
    
    def test_health_endpoint(self, test_client):
        """Test health endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_healthz_endpoint(self, test_client):
        """Test Kubernetes-style health endpoint."""
        response = test_client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_readyz_endpoint(self, test_client):
        """Test readiness endpoint."""
        response = test_client.get("/readyz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, test_client, mock_auth_adapter):
        """Test successful login."""
        # Create a user first
        await mock_auth_adapter.create_user("testuser", "testpass", "captain")
        
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpass"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, test_client):
        """Test login with invalid credentials."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "invalid", "password": "invalid"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid credentials" in data["detail"]
    
    def test_login_missing_fields(self, test_client):
        """Test login with missing fields."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser"}  # Missing password
        )
        
        assert response.status_code == 422  # Validation error


class TestBootstrapEndpoint:
    """Test bootstrap endpoint."""
    
    def test_bootstrap_success(self, test_client):
        """Test successful bootstrap."""
        response = test_client.post(
            "/api/v1/bootstrap",
            json={
                "admin_username": "admin",
                "admin_password": "admin123456"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["admin_user_created"] is True
        assert "message" in data
    
    def test_bootstrap_weak_password(self, test_client):
        """Test bootstrap with weak password."""
        response = test_client.post(
            "/api/v1/bootstrap",
            json={
                "admin_username": "admin", 
                "admin_password": "weak"  # Too short
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestRouteEndpoints:
    """Test route management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_routes_empty(self, test_client, admin_token):
        """Test listing routes when none exist."""
        response = test_client.get(
            "/api/v1/routes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    @pytest.mark.asyncio
    async def test_create_route(self, test_client, admin_token, mock_route_store):
        """Test creating a route."""
        route_data = {
            "id": "test-route",
            "path": "/test",
            "methods": ["GET", "POST"],
            "backends": [{"url": "http://example.com:8080"}],
            "priority": 10
        }
        
        response = test_client.put(
            "/api/v1/routes/test-route",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=route_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-route"
        assert data["path"] == "/test"
        
        # Verify route was stored
        routes = await mock_route_store.list_routes()
        assert len(routes) == 1
        assert routes[0].id == "test-route"
    
    @pytest.mark.asyncio
    async def test_get_route(self, test_client, admin_token, mock_route_store):
        """Test getting a specific route."""
        # Create a route first
        route = RouteSpec(
            id="test-route",
            path="/test",
            methods=["GET"],
            backends=[BackendSpec(url="http://example.com")]
        )
        await mock_route_store.put_route(route)
        
        response = test_client.get(
            "/api/v1/routes/test-route",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-route"
        assert data["path"] == "/test"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_route(self, test_client, admin_token):
        """Test getting a non-existent route."""
        response = test_client.get(
            "/api/v1/routes/nonexistent",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_route(self, test_client, admin_token, mock_route_store):
        """Test deleting a route."""
        # Create a route first
        route = RouteSpec(
            id="delete-me",
            path="/delete",
            methods=["GET"],
            backends=[BackendSpec(url="http://example.com")]
        )
        await mock_route_store.put_route(route)
        
        response = test_client.delete(
            "/api/v1/routes/delete-me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify route was deleted
        deleted_route = await mock_route_store.get_route("delete-me")
        assert deleted_route is None
    
    def test_unauthorized_access(self, test_client):
        """Test accessing routes without authentication."""
        response = test_client.get("/api/v1/routes")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_route_data(self, test_client, admin_token):
        """Test creating route with invalid data."""
        invalid_route = {
            "id": "invalid-route",
            "path": "invalid-path",  # Should start with /
            "methods": ["INVALID_METHOD"],  # Invalid HTTP method
            "backends": []  # Empty backends
        }
        
        response = test_client.put(
            "/api/v1/routes/invalid-route",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=invalid_route
        )
        
        assert response.status_code == 422  # Validation error


class TestBulkOperations:
    """Test bulk route operations."""
    
    @pytest.mark.asyncio
    async def test_bulk_apply_routes(self, test_client, admin_token):
        """Test applying multiple routes at once."""
        routes_data = {
            "routes": [
                {
                    "id": "route1",
                    "path": "/api/v1",
                    "methods": ["GET"],
                    "backends": [{"url": "http://service1.com"}]
                },
                {
                    "id": "route2",
                    "path": "/api/v2",
                    "methods": ["POST"],
                    "backends": [{"url": "http://service2.com"}]
                }
            ]
        }
        
        response = test_client.post(
            "/api/v1/routes:bulk-apply",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=routes_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["applied"] == 2
        assert data["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_export_routes(self, test_client, admin_token, mock_route_store):
        """Test exporting routes."""
        # Create some routes first
        route1 = RouteSpec(
            id="route1",
            path="/api/v1",
            methods=["GET"],
            backends=[BackendSpec(url="http://service1.com")]
        )
        route2 = RouteSpec(
            id="route2", 
            path="/api/v2",
            methods=["POST"],
            backends=[BackendSpec(url="http://service2.com")]
        )
        await mock_route_store.put_route(route1)
        await mock_route_store.put_route(route2)
        
        response = test_client.get(
            "/api/v1/routes:export",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-yaml"
        
        # Response should contain YAML data
        content = response.content.decode()
        assert "apiVersion: harbor.l8e/v1" in content
        assert "kind: RouteList" in content
        assert "route1" in content
        assert "route2" in content


class TestAdminEndpoints:
    """Test admin endpoints."""
    
    @pytest.mark.asyncio
    async def test_admin_status(self, test_client, admin_token):
        """Test admin status endpoint."""
        response = test_client.get(
            "/api/v1/admin/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "uptime" in data
        assert "routes_count" in data
    
    @pytest.mark.asyncio
    async def test_list_users(self, test_client, admin_token, mock_auth_adapter):
        """Test listing users."""
        # Create some users
        await mock_auth_adapter.create_user("user1", "pass1", "captain")
        await mock_auth_adapter.create_user("user2", "pass2", "harbor-master")
        
        response = test_client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "admin" in data  # Bootstrap admin user
        assert "user1" in data
        assert "user2" in data
    
    @pytest.mark.asyncio
    async def test_create_user_via_api(self, test_client, admin_token):
        """Test creating user via admin API."""
        user_data = {
            "username": "newuser",
            "password": "newpass123",
            "role": "captain"
        }
        
        response = test_client.post(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=user_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "captain"
        assert "password" not in data  # Password should not be returned
    
    @pytest.mark.asyncio
    async def test_update_user_via_api(self, test_client, admin_token, mock_auth_adapter):
        """Test updating user via admin API."""
        # Create user first
        await mock_auth_adapter.create_user("updateme", "oldpass", "captain")
        
        update_data = {
            "role": "harbor-master"
        }
        
        response = test_client.patch(
            "/api/v1/admin/users/updateme",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "harbor-master"
    
    @pytest.mark.asyncio
    async def test_delete_user_via_api(self, test_client, admin_token, mock_auth_adapter):
        """Test deleting user via admin API."""
        # Create user first
        await mock_auth_adapter.create_user("deleteme", "pass123", "captain")
        
        response = test_client.delete(
            "/api/v1/admin/users/deleteme",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 204
        
        # Verify user was deleted
        users = await mock_auth_adapter.list_users()
        assert "deleteme" not in users


class TestJWKSEndpoint:
    """Test JWKS endpoint for JWT verification."""
    
    def test_jwks_endpoint(self, test_client):
        """Test JWKS endpoint returns public keys."""
        response = test_client.get("/api/v1/.well-known/jwks.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) >= 1
        
        # Check key format
        key = data["keys"][0]
        assert "kty" in key  # Key type
        assert "use" in key  # Key use
        assert "kid" in key  # Key ID
        assert "n" in key    # RSA modulus
        assert "e" in key    # RSA exponent


class TestCORSHeaders:
    """Test CORS header handling."""
    
    def test_cors_preflight(self, test_client):
        """Test CORS preflight request."""
        response = test_client.options(
            "/api/v1/routes",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization"
            }
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers