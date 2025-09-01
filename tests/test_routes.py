"""
Tests for route management functionality.
"""

import pytest
from datetime import datetime
from app.models.schemas import RouteSpec, BackendSpec
from app.adapters.impl.memory_routes import InMemoryRouteStore


@pytest.fixture
def route_store():
    """Create a test route store."""
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        store = InMemoryRouteStore(f.name)
        yield store
        # Cleanup
        import os
        try:
            os.unlink(f.name)
        except FileNotFoundError:
            pass


@pytest.fixture
def sample_route():
    """Create a sample route."""
    return RouteSpec(
        id="test-route",
        path="/api/v1",
        methods=["GET", "POST"],
        backends=[
            BackendSpec(url="http://example.com:8080")
        ],
        priority=10,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestInMemoryRouteStore:
    """Test in-memory route store."""
    
    @pytest.mark.asyncio
    async def test_put_and_get_route(self, route_store, sample_route):
        """Test storing and retrieving a route."""
        await route_store.put_route(sample_route)
        retrieved_route = await route_store.get_route("test-route")
        
        assert retrieved_route is not None
        assert retrieved_route.id == "test-route"
        assert retrieved_route.path == "/api/v1"
        assert len(retrieved_route.backends) == 1
    
    @pytest.mark.asyncio
    async def test_list_routes(self, route_store, sample_route):
        """Test listing routes."""
        await route_store.put_route(sample_route)
        routes = await route_store.list_routes()
        
        assert len(routes) == 1
        assert routes[0].id == "test-route"
    
    @pytest.mark.asyncio
    async def test_delete_route(self, route_store, sample_route):
        """Test deleting a route."""
        await route_store.put_route(sample_route)
        
        # Verify route exists
        route = await route_store.get_route("test-route")
        assert route is not None
        
        # Delete route
        deleted = await route_store.delete_route("test-route")
        assert deleted is True
        
        # Verify route is gone
        route = await route_store.get_route("test-route")
        assert route is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_route(self, route_store):
        """Test deleting a non-existent route."""
        deleted = await route_store.delete_route("nonexistent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_route_matching(self, route_store):
        """Test route matching by path prefix."""
        # Create test routes
        route1 = RouteSpec(
            id="api-route",
            path="/api",
            methods=["GET"],
            backends=[BackendSpec(url="http://api.example.com")],
            priority=10
        )
        
        route2 = RouteSpec(
            id="api-v1-route", 
            path="/api/v1",
            methods=["GET"],
            backends=[BackendSpec(url="http://v1.example.com")],
            priority=20
        )
        
        await route_store.put_route(route1)
        await route_store.put_route(route2)
        
        # Test path matching
        matches = route_store.get_routes_by_path_prefix("/api/v1/users")
        
        # Should match both routes, but v1 route should be first (higher priority, longer path)
        assert len(matches) == 2
        assert matches[0].id == "api-v1-route"  # Higher priority and longer path
        assert matches[1].id == "api-route"


class TestRouteSpec:
    """Test route specification model."""
    
    def test_valid_route_creation(self):
        """Test creating a valid route."""
        route = RouteSpec(
            id="test-route",
            path="/test",
            methods=["GET", "POST"],
            backends=[BackendSpec(url="http://example.com")]
        )
        
        assert route.id == "test-route"
        assert route.path == "/test"
        assert route.methods == ["GET", "POST"]
        assert len(route.backends) == 1
        assert route.priority == 0  # default
        assert route.strip_prefix is True  # default
    
    def test_invalid_route_id(self):
        """Test that invalid route IDs are rejected."""
        with pytest.raises(ValueError):
            RouteSpec(
                id="Invalid_Route_ID",  # Contains uppercase and underscore
                path="/test",
                backends=[BackendSpec(url="http://example.com")]
            )
    
    def test_invalid_path(self):
        """Test that invalid paths are rejected."""
        with pytest.raises(ValueError):
            RouteSpec(
                id="test-route",
                path="invalid-path",  # Must start with /
                backends=[BackendSpec(url="http://example.com")]
            )
    
    def test_invalid_methods(self):
        """Test that invalid HTTP methods are rejected."""
        with pytest.raises(ValueError):
            RouteSpec(
                id="test-route",
                path="/test",
                methods=["INVALID"],  # Invalid HTTP method
                backends=[BackendSpec(url="http://example.com")]
            )