"""
Simple local authentication adapter implementation.
"""

import time
import jwt
import bcrypt
import base64
import yaml
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException
from app.adapters.auth import AuthAdapter, AuthContext
from app.adapters.secrets import SecretProvider


class SimpleLocalAuthAdapter(AuthAdapter):
    """Simple local authentication using JWT tokens."""
    
    def __init__(self, secret_provider: SecretProvider, jwt_ttl_seconds: int = 900):
        """
        Initialize the simple local auth adapter.
        
        Args:
            secret_provider: Secret provider for keys and user data
            jwt_ttl_seconds: JWT token TTL in seconds
        """
        self.secret_provider = secret_provider
        self.jwt_ttl_seconds = jwt_ttl_seconds
        self._private_key: Optional[str] = None
        self._public_key: Optional[str] = None
        self._revoked_tokens: set = set()
    
    def _load_keys(self) -> tuple[str, str]:
        """Load JWT signing keys."""
        if self._private_key and self._public_key:
            return self._private_key, self._public_key
        
        try:
            # First try to load raw keys (stored directly in secret provider)
            try:
                jwt_keys_raw = self.secret_provider.get_secret("jwt_keys_raw")
                self._private_key = jwt_keys_raw["private_key"]
                self._public_key = jwt_keys_raw["public_key"]
                return self._private_key, self._public_key
            except KeyError:
                pass
            
            # Fallback to file-based keys
            jwt_keys = self.secret_provider.get_secret("jwt_keys")
            
            with open(jwt_keys["private_key_path"], 'r') as f:
                self._private_key = f.read()
            
            with open(jwt_keys["public_key_path"], 'r') as f:
                self._public_key = f.read()
                
            return self._private_key, self._public_key
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load JWT keys: {e}")
    
    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        """Load user data from secret provider."""
        try:
            users_data = self.secret_provider.get_secret("users")
            return users_data
        except KeyError:
            return {}
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against bcrypt hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        """
        Authenticate request using Bearer token.
        
        Args:
            request: FastAPI request object
            
        Returns:
            AuthContext if authenticated, None otherwise
        """
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        try:
            _, public_key = self._load_keys()
            payload = jwt.decode(token, public_key, algorithms=["RS256"])
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and jti in self._revoked_tokens:
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and exp < time.time():
                return None
            
            # Extract claims
            subject = payload.get("sub")
            role = payload.get("role")
            
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
    
    async def issue_token(self, subject: str, role: str, ttl_seconds: int) -> str:
        """
        Issue a new JWT token.
        
        Args:
            subject: Subject identifier
            role: Role to assign
            ttl_seconds: Token TTL in seconds
            
        Returns:
            JWT token string
        """
        private_key, _ = self._load_keys()
        
        now = int(time.time())
        jti = f"{subject}_{now}"
        
        payload = {
            "sub": subject,
            "role": role,
            "iat": now,
            "exp": now + ttl_seconds,
            "iss": "l8e-harbor",
            "jti": jti
        }
        
        token = jwt.encode(payload, private_key, algorithm="RS256")
        return token
    
    async def revoke_token(self, token_id: str) -> bool:
        """
        Revoke a token by adding its JTI to the revoked set.
        
        Args:
            token_id: Token ID (JTI) to revoke
            
        Returns:
            True if revoked successfully
        """
        self._revoked_tokens.add(token_id)
        
        # Persist revoked tokens
        try:
            revoked_data = {"revoked_tokens": list(self._revoked_tokens)}
            self.secret_provider.put_secret("revoked_tokens", revoked_data)
            return True
        except Exception:
            return False
    
    async def verify_credentials(self, username: str, password: str) -> Optional[AuthContext]:
        """
        Verify username/password credentials.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            AuthContext if valid credentials, None otherwise
        """
        users = self._load_users()
        user_data = users.get(username)
        
        if not user_data:
            return None
        
        password_hash = user_data.get("password_hash")
        if not password_hash or not self._verify_password(password, password_hash):
            return None
        
        role = user_data.get("role", "captain")
        
        return AuthContext(
            subject=username,
            role=role,
            meta={"login_time": int(time.time())},
        )
    
    def get_public_key(self) -> str:
        """Get the public key for JWT verification."""
        _, public_key = self._load_keys()
        return public_key
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JWKS (JSON Web Key Set) for public key distribution."""
        public_key = self.get_public_key()
        
        # Convert PEM to JWK format (simplified)
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": "l8e-harbor-key-1",
                    "n": "example_modulus",  # In real implementation, extract from key
                    "e": "AQAB"
                }
            ]
        }
    
    # User management methods
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8')
    
    def create_user(self, username: str, password: str, role: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            username: Username
            password: Plain text password
            role: User role
            meta: Additional metadata
            
        Returns:
            User data dictionary
            
        Raises:
            ValueError: If user already exists
        """
        users = self._load_users()
        
        if username in users:
            raise ValueError(f"User '{username}' already exists")
        
        password_hash = self._hash_password(password)
        now = datetime.utcnow()
        
        user_data = {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "meta": meta or {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Add user to users dict
        users[username] = user_data
        
        # Save users back to secret provider
        self._save_users(users)
        
        return user_data
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username.
        
        Args:
            username: Username to look up
            
        Returns:
            User data dictionary or None if not found
        """
        users = self._load_users()
        return users.get(username)
    
    def list_users(self) -> List[Dict[str, Any]]:
        """
        List all users.
        
        Returns:
            List of user data dictionaries
        """
        users = self._load_users()
        return list(users.values())
    
    def update_user(self, username: str, password: Optional[str] = None, role: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update an existing user.
        
        Args:
            username: Username to update
            password: New password (optional)
            role: New role (optional) 
            meta: New metadata (optional)
            
        Returns:
            Updated user data dictionary
            
        Raises:
            ValueError: If user doesn't exist
        """
        users = self._load_users()
        
        if username not in users:
            raise ValueError(f"User '{username}' not found")
        
        user_data = users[username].copy()
        
        if password:
            user_data["password_hash"] = self._hash_password(password)
        if role:
            user_data["role"] = role
        if meta is not None:
            user_data["meta"] = meta
        
        user_data["updated_at"] = datetime.utcnow().isoformat()
        
        users[username] = user_data
        self._save_users(users)
        
        return user_data
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user.
        
        Args:
            username: Username to delete
            
        Returns:
            True if deleted, False if user didn't exist
        """
        users = self._load_users()
        
        if username in users:
            del users[username]
            self._save_users(users)
            return True
        
        return False
    
    def _save_users(self, users: Dict[str, Dict[str, Any]]):
        """Save users data to secret provider."""
        try:
            self.secret_provider.put_secret("users", users)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save users: {e}")
    
    def configure_jwt_keys(self, private_key_b64: str, public_key_b64: str):
        """
        Configure JWT keys from base64 encoded strings.
        
        Args:
            private_key_b64: Base64 encoded private key
            public_key_b64: Base64 encoded public key
        """
        try:
            private_key = base64.b64decode(private_key_b64).decode('utf-8')
            public_key = base64.b64decode(public_key_b64).decode('utf-8')
            
            # Validate keys by trying to load them
            jwt.decode("test", public_key, algorithms=["RS256"], options={"verify_signature": False})
            
            # Store keys in secret provider
            jwt_keys_data = {
                "private_key": private_key,
                "public_key": public_key,
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.secret_provider.put_secret("jwt_keys_raw", jwt_keys_data)
            
            # Update cached keys
            self._private_key = private_key
            self._public_key = public_key
            
        except Exception as e:
            raise ValueError(f"Invalid JWT keys: {e}")
    
    def is_bootstrapped(self) -> bool:
        """Check if the system has been bootstrapped with initial admin user."""
        users = self._load_users()
        return len(users) > 0