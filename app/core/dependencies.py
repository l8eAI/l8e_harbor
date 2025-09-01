"""
FastAPI dependency injection for l8e-harbor.
"""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from app.adapters.auth import AuthAdapter, AuthContext
from app.adapters.secrets import SecretProvider
from app.adapters.routes import RouteStore
from app.core.config import Settings, get_settings

security = HTTPBearer()

# Global instances (will be initialized by the application)
_auth_adapter: AuthAdapter = None
_secret_provider: SecretProvider = None
_route_store: RouteStore = None


def initialize_adapters(
    auth_adapter: AuthAdapter,
    secret_provider: SecretProvider,
    route_store: RouteStore
) -> None:
    """
    Initialize the global adapter instances.
    
    This should be called during application startup.
    """
    global _auth_adapter, _secret_provider, _route_store
    _auth_adapter = auth_adapter
    _secret_provider = secret_provider
    _route_store = route_store


def get_auth_adapter() -> AuthAdapter:
    """Get the current authentication adapter."""
    if _auth_adapter is None:
        raise HTTPException(
            status_code=500,
            detail="Authentication adapter not initialized"
        )
    return _auth_adapter


def get_secret_provider() -> SecretProvider:
    """Get the current secret provider."""
    if _secret_provider is None:
        raise HTTPException(
            status_code=500,
            detail="Secret provider not initialized"
        )
    return _secret_provider


def get_route_store() -> RouteStore:
    """Get the current route store."""
    if _route_store is None:
        raise HTTPException(
            status_code=500,
            detail="Route store not initialized"
        )
    return _route_store


async def get_current_user(
    request: Request,
    auth_adapter: AuthAdapter = Depends(get_auth_adapter)
) -> AuthContext:
    """
    Get the current authenticated user.
    
    Args:
        request: FastAPI request object
        auth_adapter: Authentication adapter
        
    Returns:
        AuthContext for the authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    auth_context = await auth_adapter.authenticate(request)
    
    if not auth_context:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return auth_context


async def require_role(required_role: str):
    """
    Create a dependency that requires a specific role.
    
    Args:
        required_role: Required role name
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: AuthContext = Depends(get_current_user)
    ) -> AuthContext:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{required_role}' required"
            )
        return current_user
    
    return role_checker


# Common role dependencies
require_harbor_master = require_role("harbor-master")
require_captain = require_role("captain")


def get_auth_context(request: Request, auth_adapter: AuthAdapter) -> AuthContext:
    """
    Get auth context from request synchronously (for use in non-async contexts).
    
    Args:
        request: FastAPI request object
        auth_adapter: Authentication adapter
        
    Returns:
        AuthContext if authenticated, None otherwise
    """
    import asyncio
    try:
        # Run the async authenticate method
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we need to handle this differently
            # For now, we'll use a simple approach that works with the auth adapters
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None
            
            # Create a minimal request-like object for the auth adapter
            from app.adapters.impl.simple_auth import SimpleLocalAuthAdapter
            if isinstance(auth_adapter, SimpleLocalAuthAdapter):
                # Use the synchronous pattern from the adapter
                import time
                import jwt
                
                token = authorization[7:]  # Remove "Bearer " prefix
                try:
                    _, public_key = auth_adapter._load_keys()
                    payload = jwt.decode(token, public_key, algorithms=["RS256"])
                    
                    # Check expiration
                    exp = payload.get("exp")
                    if exp and exp < time.time():
                        return None
                    
                    # Extract claims
                    subject = payload.get("sub")
                    role = payload.get("role")
                    jti = payload.get("jti")
                    
                    if not subject or not role:
                        return None
                    
                    return AuthContext(
                        subject=subject,
                        role=role,
                        meta={"iat": payload.get("iat"), "iss": payload.get("iss")},
                        token_id=jti,
                        expires_at=exp
                    )
                except jwt.InvalidTokenError:
                    return None
                except Exception:
                    return None
        else:
            return loop.run_until_complete(auth_adapter.authenticate(request))
    except Exception:
        return None
    
    return None