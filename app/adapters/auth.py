"""
Authentication adapter interfaces and base implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from fastapi import Request


@dataclass
class AuthContext:
    """Authentication context passed through the request lifecycle."""
    subject: str
    role: str
    meta: Dict[str, Any]
    token_id: Optional[str] = None
    expires_at: Optional[int] = None


class AuthAdapter(ABC):
    """Abstract base class for authentication adapters."""
    
    @abstractmethod
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        """
        Authenticate an incoming request.
        
        Args:
            request: The FastAPI request object
            
        Returns:
            AuthContext if authenticated, None otherwise
        """
        pass
    
    async def issue_token(self, subject: str, role: str, ttl_seconds: int) -> str:
        """
        Issue a token for the given subject and role.
        
        Args:
            subject: The subject identifier
            role: The role to assign
            ttl_seconds: Time to live in seconds
            
        Returns:
            Token string (JWT or opaque)
            
        Raises:
            NotImplementedError: If the adapter doesn't support token issuance
        """
        raise NotImplementedError("Token issuance not supported by this adapter")
    
    async def revoke_token(self, token_id: str) -> bool:
        """
        Revoke a token by its ID.
        
        Args:
            token_id: The token ID to revoke
            
        Returns:
            True if revoked successfully, False otherwise
            
        Raises:
            NotImplementedError: If the adapter doesn't support token revocation
        """
        raise NotImplementedError("Token revocation not supported by this adapter")