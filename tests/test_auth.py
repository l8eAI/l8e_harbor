"""
Tests for authentication system.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import jwt

from app.adapters.impl.simple_auth import SimpleLocalAuthAdapter
from app.adapters.impl.localfs_secrets import LocalFSSecretProvider


@pytest.fixture
def temp_secrets_dir():
    """Create a temporary directory for secrets."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def secret_provider(temp_secrets_dir):
    """Create a LocalFS secret provider."""
    provider = LocalFSSecretProvider(temp_secrets_dir)
    provider.ensure_default_secrets()
    return provider


@pytest.fixture
def auth_adapter(secret_provider):
    """Create a SimpleLocalAuthAdapter."""
    return SimpleLocalAuthAdapter(
        secret_provider=secret_provider,
        jwt_ttl_seconds=900
    )


class TestSimpleLocalAuthAdapter:
    """Test the SimpleLocalAuthAdapter."""
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, auth_adapter):
        """Test creating a new user."""
        result = await auth_adapter.create_user(
            username="testuser",
            password="testpass123",
            role="captain"
        )
        
        assert result is True
        
        # Verify user exists
        users = await auth_adapter.list_users()
        assert "testuser" in users
        assert users["testuser"]["role"] == "captain"
        assert "password_hash" in users["testuser"]
        assert users["testuser"]["password_hash"] != "testpass123"  # Should be hashed
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate(self, auth_adapter):
        """Test creating a duplicate user fails."""
        # Create first user
        await auth_adapter.create_user("testuser", "pass123", "captain")
        
        # Try to create duplicate
        result = await auth_adapter.create_user("testuser", "newpass", "harbor-master")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_adapter):
        """Test successful user authentication."""
        # Create user
        await auth_adapter.create_user("testuser", "testpass123", "captain")
        
        # Authenticate
        user = await auth_adapter.authenticate_user("testuser", "testpass123")
        
        assert user is not None
        assert user.username == "testuser"
        assert user.role == "captain"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, auth_adapter):
        """Test authentication with invalid password."""
        # Create user
        await auth_adapter.create_user("testuser", "correctpass", "captain")
        
        # Try with wrong password
        user = await auth_adapter.authenticate_user("testuser", "wrongpass")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent(self, auth_adapter):
        """Test authentication of non-existent user."""
        user = await auth_adapter.authenticate_user("nonexistent", "anypass")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_user_password(self, auth_adapter):
        """Test updating user password."""
        # Create user
        await auth_adapter.create_user("testuser", "oldpass", "captain")
        
        # Update password
        result = await auth_adapter.update_user("testuser", password="newpass123")
        assert result is True
        
        # Verify old password doesn't work
        user = await auth_adapter.authenticate_user("testuser", "oldpass")
        assert user is None
        
        # Verify new password works
        user = await auth_adapter.authenticate_user("testuser", "newpass123")
        assert user is not None
    
    @pytest.mark.asyncio
    async def test_update_user_role(self, auth_adapter):
        """Test updating user role."""
        # Create user
        await auth_adapter.create_user("testuser", "pass123", "captain")
        
        # Update role
        result = await auth_adapter.update_user("testuser", role="harbor-master")
        assert result is True
        
        # Verify role updated
        user = await auth_adapter.authenticate_user("testuser", "pass123")
        assert user is not None
        assert user.role == "harbor-master"
    
    @pytest.mark.asyncio
    async def test_delete_user(self, auth_adapter):
        """Test deleting a user."""
        # Create user
        await auth_adapter.create_user("testuser", "pass123", "captain")
        
        # Verify user exists
        users = await auth_adapter.list_users()
        assert "testuser" in users
        
        # Delete user
        result = await auth_adapter.delete_user("testuser")
        assert result is True
        
        # Verify user gone
        users = await auth_adapter.list_users()
        assert "testuser" not in users
        
        # Verify authentication fails
        user = await auth_adapter.authenticate_user("testuser", "pass123")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, auth_adapter):
        """Test deleting a non-existent user."""
        result = await auth_adapter.delete_user("nonexistent")
        assert result is False


class TestJWTTokens:
    """Test JWT token operations."""
    
    @pytest.mark.asyncio
    async def test_issue_token_success(self, auth_adapter):
        """Test successful token issuance."""
        # Create user
        await auth_adapter.create_user("testuser", "pass123", "captain")
        user = await auth_adapter.authenticate_user("testuser", "pass123")
        
        # Issue token
        token_data = await auth_adapter.issue_token(user)
        
        assert "access_token" in token_data
        assert "expires_in" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] == 900  # 15 minutes
        
        # Token should be a valid JWT
        token = token_data["access_token"]
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_adapter):
        """Test successful token verification."""
        # Create user and issue token
        await auth_adapter.create_user("testuser", "pass123", "captain")
        user = await auth_adapter.authenticate_user("testuser", "pass123")
        token_data = await auth_adapter.issue_token(user)
        
        # Verify token
        verified_user = await auth_adapter.verify_token(token_data["access_token"])
        
        assert verified_user is not None
        assert verified_user.username == "testuser"
        assert verified_user.role == "captain"
    
    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, auth_adapter):
        """Test verification of invalid token."""
        result = await auth_adapter.verify_token("invalid.jwt.token")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_verify_expired_token(self, auth_adapter):
        """Test verification of expired token."""
        # Create auth adapter with very short TTL
        short_ttl_adapter = SimpleLocalAuthAdapter(
            secret_provider=auth_adapter.secret_provider,
            jwt_ttl_seconds=1  # 1 second
        )
        
        # Create user and issue token
        await short_ttl_adapter.create_user("testuser", "pass123", "captain")
        user = await short_ttl_adapter.authenticate_user("testuser", "pass123")
        token_data = await short_ttl_adapter.issue_token(user)
        
        # Wait for token to expire
        import asyncio
        await asyncio.sleep(2)
        
        # Try to verify expired token
        result = await short_ttl_adapter.verify_token(token_data["access_token"])
        assert result is None


class TestLocalFSSecretProvider:
    """Test the LocalFS secret provider."""
    
    def test_ensure_default_secrets(self, temp_secrets_dir):
        """Test that default secrets are created."""
        provider = LocalFSSecretProvider(temp_secrets_dir)
        provider.ensure_default_secrets()
        
        # Check that files exist
        assert os.path.exists(os.path.join(temp_secrets_dir, "users.json"))
        assert os.path.exists(os.path.join(temp_secrets_dir, "tokens.json"))
        assert os.path.exists(os.path.join(temp_secrets_dir, "jwt_keys.json"))
        
        # Check that JWT keys are generated
        with open(os.path.join(temp_secrets_dir, "jwt_keys.json"), 'r') as f:
            jwt_keys = json.load(f)
            assert "private_key" in jwt_keys
            assert "public_key" in jwt_keys
            assert len(jwt_keys["private_key"]) > 100  # RSA key should be long
    
    @pytest.mark.asyncio
    async def test_get_secret_existing(self, secret_provider):
        """Test getting an existing secret."""
        # Store a secret first
        await secret_provider.store_secret("test_key", "test_value")
        
        # Retrieve it
        value = await secret_provider.get_secret("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_get_secret_nonexistent(self, secret_provider):
        """Test getting a non-existent secret."""
        value = await secret_provider.get_secret("nonexistent_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_store_secret(self, secret_provider):
        """Test storing a secret."""
        result = await secret_provider.store_secret("new_key", "new_value")
        assert result is True
        
        # Verify it can be retrieved
        value = await secret_provider.get_secret("new_key")
        assert value == "new_value"
    
    @pytest.mark.asyncio
    async def test_delete_secret(self, secret_provider):
        """Test deleting a secret."""
        # Store a secret first
        await secret_provider.store_secret("delete_me", "value")
        
        # Verify it exists
        value = await secret_provider.get_secret("delete_me")
        assert value == "value"
        
        # Delete it
        result = await secret_provider.delete_secret("delete_me")
        assert result is True
        
        # Verify it's gone
        value = await secret_provider.get_secret("delete_me")
        assert value is None


class TestRoleBasedAuth:
    """Test role-based authentication features."""
    
    @pytest.mark.asyncio
    async def test_require_role_success(self, auth_adapter):
        """Test successful role requirement check."""
        # Create users with different roles
        await auth_adapter.create_user("captain", "pass123", "captain")
        await auth_adapter.create_user("master", "pass123", "harbor-master")
        
        # Test captain can access captain-required resource
        captain_user = await auth_adapter.authenticate_user("captain", "pass123")
        assert await auth_adapter.require_role(captain_user, "captain") is True
        
        # Test harbor-master can access captain-required resource (higher privilege)
        master_user = await auth_adapter.authenticate_user("master", "pass123")
        assert await auth_adapter.require_role(master_user, "captain") is True
    
    @pytest.mark.asyncio
    async def test_require_role_failure(self, auth_adapter):
        """Test failed role requirement check."""
        # Create user with lower privilege
        await auth_adapter.create_user("captain", "pass123", "captain")
        captain_user = await auth_adapter.authenticate_user("captain", "pass123")
        
        # Captain should not be able to access harbor-master resources
        assert await auth_adapter.require_role(captain_user, "harbor-master") is False
    
    @pytest.mark.asyncio
    async def test_require_role_invalid_role(self, auth_adapter):
        """Test role requirement with invalid role."""
        await auth_adapter.create_user("user", "pass123", "captain")
        user = await auth_adapter.authenticate_user("user", "pass123")
        
        # Invalid role should return False
        assert await auth_adapter.require_role(user, "invalid-role") is False


class TestSecurityFeatures:
    """Test security-related features."""
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        from app.adapters.impl.simple_auth import hash_password, verify_password
        
        password = "test123"
        hashed = hash_password(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Should be bcrypt hash (starts with $2b$)
        assert hashed.startswith("$2b$")
        
        # Verification should work
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
    
    @pytest.mark.asyncio
    async def test_jwt_claims(self, auth_adapter):
        """Test JWT token claims."""
        # Create user and issue token
        await auth_adapter.create_user("testuser", "pass123", "captain")
        user = await auth_adapter.authenticate_user("testuser", "pass123")
        token_data = await auth_adapter.issue_token(user)
        
        # Decode token (without verification for testing)
        token = token_data["access_token"]
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Check required claims
        assert decoded["sub"] == "testuser"  # Subject
        assert decoded["role"] == "captain"
        assert decoded["iss"] == "l8e-harbor"  # Issuer
        assert "iat" in decoded  # Issued at
        assert "exp" in decoded  # Expiration
        assert "jti" in decoded  # JWT ID
        
        # Check expiration is in the future
        exp_time = datetime.fromtimestamp(decoded["exp"])
        assert exp_time > datetime.now()