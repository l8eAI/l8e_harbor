"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from app.models.schemas import LoginRequest, LoginResponse, JWKSResponse
from app.adapters.auth import AuthAdapter
from app.adapters.impl.simple_auth import SimpleLocalAuthAdapter
from app.core.dependencies import get_auth_adapter

router = APIRouter(tags=["Authentication"])
security = HTTPBearer()


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_adapter: AuthAdapter = Depends(get_auth_adapter)
):
    """
    Authenticate user and return access token.
    """
    if not isinstance(auth_adapter, SimpleLocalAuthAdapter):
        raise HTTPException(
            status_code=400,
            detail="Login not supported with current authentication adapter"
        )
    
    # Verify credentials
    auth_context = await auth_adapter.verify_credentials(
        request.username, 
        request.password
    )
    
    if not auth_context:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    # Issue token
    try:
        access_token = await auth_adapter.issue_token(
            subject=auth_context.subject,
            role=auth_context.role,
            ttl_seconds=900  # 15 minutes
        )
        
        return LoginResponse(
            access_token=access_token,
            expires_in=900,
            token_type="bearer"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to issue token: {e}"
        )


@router.get("/.well-known/jwks.json", response_model=JWKSResponse)
async def get_jwks(auth_adapter: AuthAdapter = Depends(get_auth_adapter)):
    """
    Get JSON Web Key Set for JWT verification.
    """
    if not isinstance(auth_adapter, SimpleLocalAuthAdapter):
        raise HTTPException(
            status_code=404,
            detail="JWKS not available with current authentication adapter"
        )
    
    try:
        jwks = auth_adapter.get_jwks()
        return JWKSResponse(**jwks)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get JWKS: {e}"
        )