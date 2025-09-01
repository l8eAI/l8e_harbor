"""
Admin API endpoints for user management and system bootstrap.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from app.models.schemas import (
    UserCreateRequest, UserDTO, BootstrapRequest, BootstrapResponse,
    LoginResponse
)
from app.adapters.auth import AuthAdapter, AuthContext
from app.adapters.impl.simple_auth import SimpleLocalAuthAdapter
from app.core.dependencies import get_auth_adapter

router = APIRouter(tags=["Admin"])


async def require_admin_or_init(
    request: Request,
    auth_adapter: AuthAdapter = Depends(get_auth_adapter),
    x_admin_init: str = Header(None)
) -> AuthContext:
    """
    Require admin authentication or allow initialization header for bootstrap.
    """
    if not isinstance(auth_adapter, SimpleLocalAuthAdapter):
        raise HTTPException(
            status_code=400,
            detail="Admin operations not supported with current authentication adapter"
        )
    
    # Allow init operations if system is not bootstrapped and has init header
    if x_admin_init == "true" and not auth_adapter.is_bootstrapped():
        # Return a special init context
        return AuthContext(
            subject="system-init",
            role="harbor-master",
            meta={"init": True}
        )
    
    # Otherwise require normal authentication
    auth_context = await auth_adapter.authenticate(request)
    
    if not auth_context:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if auth_context.role != "harbor-master":
        raise HTTPException(status_code=403, detail="Admin role required")
    
    return auth_context


@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap_system(
    request: BootstrapRequest,
    auth_adapter: SimpleLocalAuthAdapter = Depends(get_auth_adapter)
):
    """
    Bootstrap the system with initial admin user and JWT keys.
    This endpoint is only available when no users exist.
    """
    if not isinstance(auth_adapter, SimpleLocalAuthAdapter):
        raise HTTPException(
            status_code=400,
            detail="Bootstrap not supported with current authentication adapter"
        )
    
    if auth_adapter.is_bootstrapped():
        raise HTTPException(
            status_code=400,
            detail="System is already bootstrapped"
        )
    
    try:
        # Configure JWT keys if provided
        jwt_keys_configured = False
        if request.jwt_private_key and request.jwt_public_key:
            auth_adapter.configure_jwt_keys(request.jwt_private_key, request.jwt_public_key)
            jwt_keys_configured = True
        
        # Create admin user
        user_data = auth_adapter.create_user(
            username=request.admin_username,
            password=request.admin_password,
            role="harbor-master",
            meta={
                "created_by": "bootstrap",
                "is_admin": True
            }
        )
        
        return BootstrapResponse(
            admin_user_created=True,
            jwt_keys_configured=jwt_keys_configured,
            message=f"System bootstrapped successfully. Admin user '{request.admin_username}' created."
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bootstrap failed: {e}")


@router.post("/admin/users", response_model=UserDTO)
async def create_user(
    request: UserCreateRequest,
    auth_context: AuthContext = Depends(require_admin_or_init),
    auth_adapter: SimpleLocalAuthAdapter = Depends(get_auth_adapter)
):
    """
    Create a new user. Requires admin role or init context.
    """
    try:
        user_data = auth_adapter.create_user(
            username=request.username,
            password=request.password,
            role=request.role,
            meta=request.meta
        )
        
        # Convert to DTO (exclude password_hash)
        return UserDTO(
            username=user_data["username"],
            role=user_data["role"],
            meta=user_data["meta"],
            created_at=user_data["created_at"],
            updated_at=user_data["updated_at"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User creation failed: {e}")


@router.get("/admin/users", response_model=List[UserDTO])
async def list_users(
    auth_context: AuthContext = Depends(require_admin_or_init),
    auth_adapter: SimpleLocalAuthAdapter = Depends(get_auth_adapter)
):
    """
    List all users. Requires admin role.
    """
    try:
        users = auth_adapter.list_users()
        
        # Convert to DTOs (exclude password_hash)
        return [
            UserDTO(
                username=user["username"],
                role=user["role"],
                meta=user["meta"],
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )
            for user in users
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list users: {e}")


@router.get("/admin/users/{username}", response_model=UserDTO)
async def get_user(
    username: str,
    auth_context: AuthContext = Depends(require_admin_or_init),
    auth_adapter: SimpleLocalAuthAdapter = Depends(get_auth_adapter)
):
    """
    Get a specific user by username. Requires admin role.
    """
    try:
        user_data = auth_adapter.get_user(username)
        
        if not user_data:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
        return UserDTO(
            username=user_data["username"],
            role=user_data["role"],
            meta=user_data["meta"],
            created_at=user_data["created_at"],
            updated_at=user_data["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {e}")


@router.put("/admin/users/{username}", response_model=UserDTO)
async def update_user(
    username: str,
    request: UserCreateRequest,
    auth_context: AuthContext = Depends(require_admin_or_init),
    auth_adapter: SimpleLocalAuthAdapter = Depends(get_auth_adapter)
):
    """
    Update an existing user. Requires admin role.
    """
    try:
        user_data = auth_adapter.update_user(
            username=username,
            password=request.password,
            role=request.role,
            meta=request.meta
        )
        
        return UserDTO(
            username=user_data["username"],
            role=user_data["role"],
            meta=user_data["meta"],
            created_at=user_data["created_at"],
            updated_at=user_data["updated_at"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User update failed: {e}")


@router.delete("/admin/users/{username}")
async def delete_user(
    username: str,
    auth_context: AuthContext = Depends(require_admin_or_init),
    auth_adapter: SimpleLocalAuthAdapter = Depends(get_auth_adapter)
):
    """
    Delete a user. Requires admin role.
    """
    try:
        deleted = auth_adapter.delete_user(username)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        
        return {"message": f"User '{username}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User deletion failed: {e}")


@router.get("/admin/status")
async def get_admin_status(
    auth_context: AuthContext = Depends(require_admin_or_init),
    auth_adapter: SimpleLocalAuthAdapter = Depends(get_auth_adapter)
):
    """
    Get system admin status and configuration.
    """
    try:
        users = auth_adapter.list_users()
        
        return {
            "bootstrapped": auth_adapter.is_bootstrapped(),
            "user_count": len(users),
            "admin_users": [u["username"] for u in users if u["role"] == "harbor-master"],
            "auth_adapter": "simple_local"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")