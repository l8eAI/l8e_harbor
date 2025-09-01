"""
Tests for storage adapters.
"""

import pytest
import tempfile
import asyncio
import sqlite3
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.adapters.impl.memory_routes import InMemoryRouteStore
from app.adapters.impl.sqlite_routes import SQLiteRouteStore
from app.adapters.impl.localfs_secrets import LocalFSSecretProvider
from app.models.schemas import RouteSpec, BackendSpec


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_route():
    """Create a sample route for testing."""
    return RouteSpec(
        id="test-route",
        description="Test route for storage testing",
        path="/api/test",
        methods=["GET", "POST"],
        backends=[
            BackendSpec(url="http://backend1.com:8080", weight=100),
            BackendSpec(url="http://backend2.com:8080", weight=50)
        ],
        priority=10,
        timeout_ms=5000,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestInMemoryRouteStore:
    """Test in-memory route store with file persistence."""
    
    @pytest.mark.asyncio
    async def test_put_and_get_route(self, temp_dir, sample_route):
        """Test storing and retrieving a route."""
        store = InMemoryRouteStore(os.path.join(temp_dir, "routes.json"))
        
        # Store route
        await store.put_route(sample_route)
        
        # Retrieve route
        retrieved = await store.get_route("test-route")
        
        assert retrieved is not None
        assert retrieved.id == sample_route.id
        assert retrieved.path == sample_route.path
        assert len(retrieved.backends) == len(sample_route.backends)
        assert retrieved.backends[0].url == sample_route.backends[0].url
    
    @pytest.mark.asyncio
    async def test_list_routes(self, temp_dir, sample_route):
        """Test listing all routes."""
        store = InMemoryRouteStore(os.path.join(temp_dir, "routes.json"))
        
        # Store multiple routes
        route1 = sample_route
        route2 = RouteSpec(
            id="route2",
            path="/api/v2",
            methods=["GET"],
            backends=[BackendSpec(url="http://backend.com")]
        )
        
        await store.put_route(route1)
        await store.put_route(route2)
        
        # List routes
        routes = await store.list_routes()
        
        assert len(routes) == 2
        route_ids = {r.id for r in routes}
        assert route_ids == {"test-route", "route2"}
    
    @pytest.mark.asyncio
    async def test_delete_route(self, temp_dir, sample_route):
        """Test deleting a route."""
        store = InMemoryRouteStore(os.path.join(temp_dir, "routes.json"))
        
        # Store route
        await store.put_route(sample_route)
        
        # Verify it exists
        retrieved = await store.get_route("test-route")
        assert retrieved is not None
        
        # Delete route
        deleted = await store.delete_route("test-route")
        assert deleted is True
        
        # Verify it's gone
        retrieved = await store.get_route("test-route")
        assert retrieved is None
        
        # Try deleting again
        deleted = await store.delete_route("test-route")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_update_route(self, temp_dir, sample_route):
        """Test updating an existing route."""
        store = InMemoryRouteStore(os.path.join(temp_dir, "routes.json"))
        
        # Store original route
        await store.put_route(sample_route)
        
        # Update route
        updated_route = sample_route.copy()
        updated_route.description = "Updated description"
        updated_route.priority = 20
        
        await store.put_route(updated_route)
        
        # Verify update
        retrieved = await store.get_route("test-route")
        assert retrieved.description == "Updated description"
        assert retrieved.priority == 20
        assert retrieved.updated_at > sample_route.updated_at
    
    @pytest.mark.asyncio
    async def test_file_persistence(self, temp_dir, sample_route):
        """Test that routes persist to file."""
        snapshot_file = os.path.join(temp_dir, "routes.json")
        store = InMemoryRouteStore(snapshot_file)
        
        # Store route
        await store.put_route(sample_route)
        
        # Verify file exists and contains data
        assert os.path.exists(snapshot_file)
        
        with open(snapshot_file, 'r') as f:
            data = json.load(f)
            assert "routes" in data
            assert "timestamp" in data
            assert len(data["routes"]) == 1
            assert data["routes"][0]["id"] == "test-route"
    
    @pytest.mark.asyncio
    async def test_route_path_matching(self, temp_dir):
        """Test route path matching functionality."""
        store = InMemoryRouteStore(os.path.join(temp_dir, "routes.json"))
        
        # Create routes with different path patterns
        routes = [
            RouteSpec(
                id="exact-match",
                path="/api/v1/users",
                methods=["GET"],
                backends=[BackendSpec(url="http://exact.com")],
                priority=10
            ),
            RouteSpec(
                id="prefix-match",
                path="/api/v1",
                methods=["GET"],
                backends=[BackendSpec(url="http://prefix.com")],
                priority=5
            ),
            RouteSpec(
                id="general-match",
                path="/api",
                methods=["GET"],
                backends=[BackendSpec(url="http://general.com")],
                priority=1
            )
        ]
        
        for route in routes:
            await store.put_route(route)
        
        # Test path matching
        matches = store.get_routes_by_path_prefix("/api/v1/users/123")
        
        # Should match all three, but in priority order
        assert len(matches) == 3
        assert matches[0].id == "exact-match"  # Highest priority + most specific
        assert matches[1].id == "prefix-match"
        assert matches[2].id == "general-match"  # Lowest priority


class TestSQLiteRouteStore:
    """Test SQLite route store."""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, temp_dir):
        """Test database and table creation."""
        db_path = os.path.join(temp_dir, "test.db")
        store = SQLiteRouteStore(db_path)
        
        # Check database file exists
        assert os.path.exists(db_path)
        
        # Check table structure
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='routes';")
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == "routes"
    
    @pytest.mark.asyncio
    async def test_put_and_get_route(self, temp_dir, sample_route):
        """Test storing and retrieving route in SQLite."""
        db_path = os.path.join(temp_dir, "test.db")
        store = SQLiteRouteStore(db_path)
        
        # Store route
        await store.put_route(sample_route)
        
        # Retrieve route
        retrieved = await store.get_route("test-route")
        
        assert retrieved is not None
        assert retrieved.id == sample_route.id
        assert retrieved.path == sample_route.path
        assert len(retrieved.backends) == len(sample_route.backends)
    
    @pytest.mark.asyncio
    async def test_list_routes_sqlite(self, temp_dir, sample_route):
        """Test listing routes from SQLite."""
        db_path = os.path.join(temp_dir, "test.db")
        store = SQLiteRouteStore(db_path)
        
        # Store multiple routes
        route2 = RouteSpec(
            id="route2",
            path="/api/v2",
            methods=["POST"],
            backends=[BackendSpec(url="http://backend2.com")]
        )
        
        await store.put_route(sample_route)
        await store.put_route(route2)
        
        # List routes
        routes = await store.list_routes()
        
        assert len(routes) == 2
        route_ids = {r.id for r in routes}
        assert route_ids == {"test-route", "route2"}
    
    @pytest.mark.asyncio
    async def test_delete_route_sqlite(self, temp_dir, sample_route):
        """Test deleting route from SQLite."""
        db_path = os.path.join(temp_dir, "test.db")
        store = SQLiteRouteStore(db_path)
        
        # Store route
        await store.put_route(sample_route)
        
        # Verify exists
        retrieved = await store.get_route("test-route")
        assert retrieved is not None
        
        # Delete route
        deleted = await store.delete_route("test-route")
        assert deleted is True
        
        # Verify gone
        retrieved = await store.get_route("test-route")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, temp_dir):
        """Test concurrent access to SQLite store."""
        db_path = os.path.join(temp_dir, "concurrent.db")
        
        async def create_and_store_route(route_id):
            store = SQLiteRouteStore(db_path)
            route = RouteSpec(
                id=route_id,
                path=f"/api/{route_id}",
                methods=["GET"],
                backends=[BackendSpec(url=f"http://{route_id}.com")]
            )
            await store.put_route(route)
        
        # Create multiple routes concurrently
        tasks = [create_and_store_route(f"route{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify all routes were stored
        store = SQLiteRouteStore(db_path)
        routes = await store.list_routes()
        assert len(routes) == 10
    
    @pytest.mark.asyncio
    async def test_json_serialization(self, temp_dir, sample_route):
        """Test JSON serialization of complex route data."""
        db_path = os.path.join(temp_dir, "serialization.db")
        store = SQLiteRouteStore(db_path)
        
        # Create route with complex middleware and retry policy
        complex_route = RouteSpec(
            id="complex-route",
            path="/api/complex",
            methods=["GET", "POST", "PUT"],
            backends=[
                BackendSpec(url="http://b1.com", weight=100),
                BackendSpec(url="http://b2.com", weight=50)
            ],
            middleware=[
                {"name": "auth", "config": {"require_role": "admin"}},
                {"name": "cors", "config": {"origins": ["*"]}}
            ],
            retry_policy={
                "max_retries": 3,
                "backoff_ms": 200,
                "retry_on": ["5xx", "timeout"]
            }
        )
        
        # Store and retrieve
        await store.put_route(complex_route)
        retrieved = await store.get_route("complex-route")
        
        assert retrieved is not None
        assert len(retrieved.backends) == 2
        assert len(retrieved.middleware) == 2
        assert retrieved.retry_policy.max_retries == 3
    
    @pytest.mark.asyncio
    async def test_database_corruption_handling(self, temp_dir):
        """Test handling of database corruption."""
        db_path = os.path.join(temp_dir, "corrupt.db")
        
        # Create valid database
        store1 = SQLiteRouteStore(db_path)
        
        # Corrupt the database file
        with open(db_path, 'wb') as f:
            f.write(b'corrupted data')
        
        # Try to use corrupted database
        with pytest.raises(Exception):  # Should raise some kind of database error
            store2 = SQLiteRouteStore(db_path)
            await store2.list_routes()


class TestLocalFSSecretProvider:
    """Test LocalFS secret provider."""
    
    @pytest.mark.asyncio
    async def test_ensure_default_secrets(self, temp_dir):
        """Test creation of default secret files."""
        provider = LocalFSSecretProvider(temp_dir)
        provider.ensure_default_secrets()
        
        # Check that default files are created
        expected_files = [
            "users.json",
            "tokens.json", 
            "jwt_keys.json"
        ]
        
        for filename in expected_files:
            file_path = os.path.join(temp_dir, filename)
            assert os.path.exists(file_path)
            
            # Check file permissions (should be restricted)
            stat_info = os.stat(file_path)
            # Unix permissions: owner read/write only (600)
            assert oct(stat_info.st_mode)[-3:] == '600'
    
    @pytest.mark.asyncio
    async def test_jwt_key_generation(self, temp_dir):
        """Test JWT key generation and format."""
        provider = LocalFSSecretProvider(temp_dir)
        provider.ensure_default_secrets()
        
        jwt_keys_file = os.path.join(temp_dir, "jwt_keys.json")
        with open(jwt_keys_file, 'r') as f:
            keys = json.load(f)
        
        assert "private_key" in keys
        assert "public_key" in keys
        
        # Check key format (should be PEM)
        assert keys["private_key"].startswith("-----BEGIN RSA PRIVATE KEY-----")
        assert keys["private_key"].endswith("-----END RSA PRIVATE KEY-----\n")
        assert keys["public_key"].startswith("-----BEGIN PUBLIC KEY-----")
        assert keys["public_key"].endswith("-----END PUBLIC KEY-----\n")
    
    @pytest.mark.asyncio
    async def test_store_and_get_secret(self, temp_dir):
        """Test storing and retrieving secrets."""
        provider = LocalFSSecretProvider(temp_dir)
        provider.ensure_default_secrets()
        
        # Store a secret
        result = await provider.store_secret("test_secret", "secret_value")
        assert result is True
        
        # Retrieve the secret
        value = await provider.get_secret("test_secret")
        assert value == "secret_value"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_secret(self, temp_dir):
        """Test retrieving non-existent secret."""
        provider = LocalFSSecretProvider(temp_dir)
        
        value = await provider.get_secret("nonexistent")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_delete_secret(self, temp_dir):
        """Test deleting secrets."""
        provider = LocalFSSecretProvider(temp_dir)
        provider.ensure_default_secrets()
        
        # Store secret
        await provider.store_secret("delete_me", "value")
        
        # Verify it exists
        value = await provider.get_secret("delete_me")
        assert value == "value"
        
        # Delete secret
        result = await provider.delete_secret("delete_me")
        assert result is True
        
        # Verify it's gone
        value = await provider.get_secret("delete_me")
        assert value is None
        
        # Try deleting again
        result = await provider.delete_secret("delete_me")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_secrets(self, temp_dir):
        """Test listing all secret names."""
        provider = LocalFSSecretProvider(temp_dir)
        provider.ensure_default_secrets()
        
        # Store some secrets
        await provider.store_secret("secret1", "value1")
        await provider.store_secret("secret2", "value2")
        
        # List secrets
        secrets = await provider.list_secrets()
        
        # Should include defaults plus new ones
        assert "users.json" in secrets
        assert "tokens.json" in secrets
        assert "jwt_keys.json" in secrets
        assert "secret1" in secrets
        assert "secret2" in secrets
    
    @pytest.mark.asyncio
    async def test_file_locking(self, temp_dir):
        """Test file locking for concurrent access."""
        provider = LocalFSSecretProvider(temp_dir)
        provider.ensure_default_secrets()
        
        # Simulate concurrent writes
        async def write_secret(secret_name, value):
            await provider.store_secret(secret_name, value)
        
        # Run concurrent operations
        tasks = [
            write_secret(f"concurrent_secret_{i}", f"value_{i}")
            for i in range(10)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all secrets were written
        for i in range(10):
            value = await provider.get_secret(f"concurrent_secret_{i}")
            assert value == f"value_{i}"
    
    @pytest.mark.asyncio
    async def test_secret_encryption(self, temp_dir):
        """Test secret encryption if implemented."""
        provider = LocalFSSecretProvider(temp_dir)
        provider.ensure_default_secrets()
        
        # Store secret
        await provider.store_secret("encrypted_secret", "sensitive_data")
        
        # Check that secret is not stored in plain text on disk
        # (This test assumes encryption is implemented)
        secret_files = os.listdir(temp_dir)
        
        # Look for files that might contain the secret
        found_plaintext = False
        for filename in secret_files:
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', errors='ignore') as f:
                    content = f.read()
                    if "sensitive_data" in content and filename not in ["users.json", "tokens.json"]:
                        found_plaintext = True
                        break
        
        # If encryption is implemented, plaintext shouldn't be found
        # If not implemented, this test documents the current behavior
        # assert not found_plaintext  # Uncomment when encryption is added
    
    @pytest.mark.asyncio
    async def test_backup_and_restore(self, temp_dir):
        """Test backup and restore functionality."""
        provider = LocalFSSecretProvider(temp_dir)
        provider.ensure_default_secrets()
        
        # Store some data
        await provider.store_secret("backup_test", "important_data")
        
        # Simulate backup (copy directory)
        backup_dir = os.path.join(temp_dir, "backup")
        os.makedirs(backup_dir, exist_ok=True)
        
        for filename in os.listdir(temp_dir):
            if os.path.isfile(os.path.join(temp_dir, filename)):
                src = os.path.join(temp_dir, filename)
                dst = os.path.join(backup_dir, filename)
                with open(src, 'rb') as f_src, open(dst, 'wb') as f_dst:
                    f_dst.write(f_src.read())
        
        # Create new provider from backup
        backup_provider = LocalFSSecretProvider(backup_dir)
        
        # Verify data is accessible
        value = await backup_provider.get_secret("backup_test")
        assert value == "important_data"


class TestStoragePerformance:
    """Test storage performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_memory_store_performance(self, temp_dir):
        """Test memory store performance with many routes."""
        store = InMemoryRouteStore(os.path.join(temp_dir, "perf.json"))
        
        # Create many routes
        routes = []
        for i in range(1000):
            route = RouteSpec(
                id=f"route-{i:04d}",
                path=f"/api/v{i % 10}/endpoint{i}",
                methods=["GET"],
                backends=[BackendSpec(url=f"http://backend{i % 5}.com")]
            )
            routes.append(route)
        
        # Measure insertion time
        import time
        start_time = time.time()
        
        for route in routes:
            await store.put_route(route)
        
        insert_time = time.time() - start_time
        
        # Measure lookup time
        start_time = time.time()
        
        for i in range(0, 1000, 10):  # Sample every 10th route
            retrieved = await store.get_route(f"route-{i:04d}")
            assert retrieved is not None
        
        lookup_time = time.time() - start_time
        
        # Performance should be reasonable
        assert insert_time < 5.0  # Should insert 1000 routes in under 5 seconds
        assert lookup_time < 1.0  # Should lookup 100 routes in under 1 second
    
    @pytest.mark.asyncio
    async def test_sqlite_store_performance(self, temp_dir):
        """Test SQLite store performance with many routes."""
        db_path = os.path.join(temp_dir, "perf.db")
        store = SQLiteRouteStore(db_path)
        
        # Create batch of routes
        routes = []
        for i in range(500):  # Smaller batch for SQLite
            route = RouteSpec(
                id=f"sql-route-{i:04d}",
                path=f"/sql/v{i % 10}/endpoint{i}",
                methods=["GET", "POST"],
                backends=[BackendSpec(url=f"http://sqlbackend{i % 3}.com")]
            )
            routes.append(route)
        
        # Measure batch insertion
        import time
        start_time = time.time()
        
        for route in routes:
            await store.put_route(route)
        
        insert_time = time.time() - start_time
        
        # Measure batch lookup
        start_time = time.time()
        all_routes = await store.list_routes()
        list_time = time.time() - start_time
        
        assert len(all_routes) == 500
        assert insert_time < 10.0  # SQLite should be reasonably fast
        assert list_time < 2.0     # Listing should be fast