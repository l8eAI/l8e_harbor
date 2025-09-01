"""
Pydantic models for l8e-harbor.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl, validator
import re


class BackendSpec(BaseModel):
    """Backend configuration for a route."""
    url: HttpUrl
    weight: Optional[int] = Field(default=100, ge=1, le=1000)
    health_check_path: Optional[str] = "/healthz"
    tls: Optional["TLSConfig"] = None


class TLSConfig(BaseModel):
    """TLS configuration for backends."""
    insecure_skip_verify: Optional[bool] = False
    ca_cert_secret: Optional[str] = None
    cert_secret: Optional[str] = None


class RetryPolicy(BaseModel):
    """Retry policy configuration."""
    max_retries: int = Field(default=0, ge=0, le=10)
    backoff_ms: int = Field(default=100, ge=0)
    retry_on: List[Literal['5xx', 'gateway-error', 'timeout']] = Field(default_factory=list)


class CircuitBreakerSpec(BaseModel):
    """Circuit breaker configuration."""
    enabled: bool = False
    failure_threshold: int = Field(default=50, ge=1, le=100)  # percentage
    minimum_requests: int = Field(default=20, ge=1)
    interval_ms: int = Field(default=60000, ge=1000)
    timeout_ms: int = Field(default=30000, ge=1000)


class MiddlewareSpec(BaseModel):
    """Middleware configuration."""
    name: str = Field(..., min_length=1)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MatcherSpec(BaseModel):
    """Request matcher configuration."""
    name: str  # header, query, cookie
    value: Optional[str] = None
    op: Literal['equals', 'contains', 'regex', 'exists'] = 'equals'
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Matcher name must start with letter and contain only alphanumeric, underscore, or dash')
        return v


class RouteSpec(BaseModel):
    """Complete route specification."""
    id: str = Field(..., pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = None
    path: str = Field(..., pattern=r'^/.*')
    methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    backends: List[BackendSpec] = Field(..., min_items=1)
    priority: Optional[int] = Field(default=0, ge=0)
    strip_prefix: Optional[bool] = True
    sticky_session: Optional[bool] = False
    timeout_ms: Optional[int] = Field(default=5000, ge=100, le=300000)
    retry_policy: Optional[RetryPolicy] = Field(default_factory=RetryPolicy)
    circuit_breaker: Optional[CircuitBreakerSpec] = Field(default_factory=CircuitBreakerSpec)
    middleware: List[MiddlewareSpec] = Field(default_factory=list)
    matchers: Optional[List[MatcherSpec]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('methods')
    def validate_methods(cls, v):
        allowed_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD", "TRACE"}
        invalid = set(v) - allowed_methods
        if invalid:
            raise ValueError(f'Invalid HTTP methods: {invalid}')
        return v
    
    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


# DTOs for API responses
class RouteDTO(BaseModel):
    """Route data transfer object for API responses."""
    id: str
    description: Optional[str]
    path: str
    methods: List[str]
    backends: List[BackendSpec]
    priority: int
    strip_prefix: bool
    sticky_session: bool
    timeout_ms: int
    retry_policy: RetryPolicy
    circuit_breaker: CircuitBreakerSpec
    middleware: List[MiddlewareSpec]
    matchers: Optional[List[MatcherSpec]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RouteCreateRequest(BaseModel):
    """Request model for creating/updating routes."""
    description: Optional[str] = None
    path: str = Field(..., pattern=r'^/.*')
    methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    backends: List[BackendSpec] = Field(..., min_items=1)
    priority: Optional[int] = Field(default=0, ge=0)
    strip_prefix: Optional[bool] = True
    sticky_session: Optional[bool] = False
    timeout_ms: Optional[int] = Field(default=5000, ge=100, le=300000)
    retry_policy: Optional[RetryPolicy] = Field(default_factory=RetryPolicy)
    circuit_breaker: Optional[CircuitBreakerSpec] = Field(default_factory=CircuitBreakerSpec)
    middleware: List[MiddlewareSpec] = Field(default_factory=list)
    matchers: Optional[List[MatcherSpec]] = None


class RouteListResponse(BaseModel):
    """Response model for listing routes."""
    routes: List[RouteDTO]


class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    expires_in: int
    token_type: str = "bearer"


class TokenCreateRequest(BaseModel):
    """Token creation request model."""
    role: str = Field(..., min_length=1)
    ttl: int = Field(default=3600, ge=60, le=86400)  # 1 minute to 1 day


class JWKSResponse(BaseModel):
    """JWKS response model."""
    keys: List[Dict[str, Any]]


# Admin/User management schemas
class UserSpec(BaseModel):
    """User specification model."""
    username: str = Field(..., min_length=1, max_length=64)
    password_hash: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreateRequest(BaseModel):
    """Request model for creating users."""
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8)
    role: str = Field(..., min_length=1)
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UserDTO(BaseModel):
    """User data transfer object for API responses."""
    username: str
    role: str
    meta: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BootstrapRequest(BaseModel):
    """Bootstrap request model for initial admin setup."""
    admin_username: str = Field(..., min_length=1, max_length=64)
    admin_password: str = Field(..., min_length=8)
    jwt_private_key: Optional[str] = None  # Base64 encoded
    jwt_public_key: Optional[str] = None   # Base64 encoded


class BootstrapResponse(BaseModel):
    """Bootstrap response model."""
    admin_user_created: bool
    jwt_keys_configured: bool
    message: str


# Configuration models
class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = Field(default=8443, ge=1, le=65535)
    workers: int = Field(default=1, ge=1)


class TLSServerConfig(BaseModel):
    """TLS server configuration."""
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ca_file: Optional[str] = None


class AppConfig(BaseModel):
    """Main application configuration."""
    mode: Literal["k8s", "vm", "hybrid"] = "vm"
    server: ServerConfig = Field(default_factory=ServerConfig)
    tls: Optional[TLSServerConfig] = None
    secret_provider: Literal["localfs", "kubernetes", "vault", "aws", "gcp"] = "localfs"
    secret_path: str = "/etc/l8e-harbor/secrets"
    route_store: Literal["memory", "sqlite", "configmap", "crd"] = "memory"
    route_store_path: Optional[str] = "/var/lib/l8e-harbor/routes.db"
    auth_adapter: Literal["local", "k8s_sa", "oidc", "opaque"] = "local"
    jwt_ttl_seconds: int = Field(default=900, ge=60, le=86400)  # 15 minutes default
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    enable_metrics: bool = True
    enable_tracing: bool = False


# Update forward references
BackendSpec.model_rebuild()
RouteSpec.model_rebuild()