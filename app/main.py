"""
l8e-harbor main application.
"""

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import get_settings, load_merged_config
from app.core.dependencies import initialize_adapters
from app.core.proxy import RouteManager, ProxyHandler
from app.api.v1.auth import router as auth_router
from app.api.v1.routes import router as routes_router
from app.api.v1.admin import router as admin_router

# Import adapters
from app.adapters.impl.localfs_secrets import LocalFSSecretProvider
from app.adapters.impl.k8s_secrets import KubernetesSecretProvider
from app.adapters.impl.simple_auth import SimpleLocalAuthAdapter
from app.adapters.impl.k8s_auth import K8sServiceAccountAdapter
from app.adapters.impl.memory_routes import InMemoryRouteStore
from app.adapters.impl.sqlite_routes import SQLiteRouteStore

# Global instances
proxy_handler: ProxyHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global proxy_handler
    
    # Startup
    settings = load_merged_config()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize secret provider
    if settings.secret_provider == "localfs":
        secret_provider = LocalFSSecretProvider(settings.secret_path)
        secret_provider.ensure_default_secrets()
    elif settings.secret_provider == "kubernetes":
        secret_provider = KubernetesSecretProvider(settings.k8s_namespace)
    else:
        raise ValueError(f"Unsupported secret provider: {settings.secret_provider}")
    
    # Initialize auth adapter
    if settings.auth_adapter == "local":
        auth_adapter = SimpleLocalAuthAdapter(
            secret_provider=secret_provider,
            jwt_ttl_seconds=settings.jwt_ttl_seconds
        )
    elif settings.auth_adapter == "k8s_sa":
        auth_adapter = K8sServiceAccountAdapter()
    else:
        raise ValueError(f"Unsupported auth adapter: {settings.auth_adapter}")
    
    # Initialize route store
    if settings.route_store == "memory":
        route_store = InMemoryRouteStore(settings.route_store_path + ".snapshot.json")
    elif settings.route_store == "sqlite":
        route_store = SQLiteRouteStore(settings.route_store_path)
    else:
        raise ValueError(f"Unsupported route store: {settings.route_store}")
    
    # Initialize dependencies
    initialize_adapters(auth_adapter, secret_provider, route_store)
    
    # Initialize proxy handler
    route_manager = RouteManager(route_store)
    proxy_handler = ProxyHandler(route_manager, auth_adapter)
    
    logging.info(f"l8e-harbor started in {settings.mode} mode")
    logging.info(f"Using secret provider: {settings.secret_provider}")
    logging.info(f"Using auth adapter: {settings.auth_adapter}")
    logging.info(f"Using route store: {settings.route_store}")
    
    yield
    
    # Shutdown
    if proxy_handler:
        await proxy_handler.close()
    logging.info("l8e-harbor shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="l8e-harbor",
    description="Open, Pluggable, Deployment-Agnostic AI Gateway",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware.
# In a production environment, you should restrict this to your UI's domain.
# This can be made configurable via an environment variable, for example:
# L8E_CORS_ALLOW_ORIGINS="http://localhost:3000,https://your-ui-domain.com"
allowed_origins = [
    "http://localhost:3000",  # For local UI development and Docker
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Allow cookies and authorization headers
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def proxy_middleware(request: Request, call_next):
    """
    Main proxy middleware that handles routing and proxying.
    """
    start_time = time.time()
    
    # Management API paths bypass proxy logic
    if (request.url.path.startswith("/api/v1/") or
        request.url.path in ["/", "/health", "/healthz", "/readyz", "/metrics", "/docs", "/openapi.json"]):
        response = await call_next(request)
    else:
        # Proxy request
        try:
            response = await proxy_handler.handle_request(request)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logging.error(f"Proxy error: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    # Add processing time header
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Include API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(routes_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


# Health check endpoints
@app.get("/", tags=["Health"])
def read_root():
    """Root endpoint providing service info."""
    return {
        "service": "l8e-harbor",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health", tags=["Health"])
@app.get("/healthz", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/readyz", tags=["Health"])
def readiness_check():
    """Readiness check endpoint."""
    # TODO: Check that all adapters are ready
    return {"status": "ready"}


@app.get("/metrics", tags=["Observability"])
def metrics():
    """Prometheus metrics endpoint."""
    # TODO: Implement metrics collection
    return {"message": "Metrics not yet implemented"}


def main():
    """Main entry point for the application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="l8e-harbor AI Gateway")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8443, help="Port to bind to")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    # Override settings with CLI args
    settings = load_merged_config()
    if args.config:
        settings.config_file = args.config
    if args.host:
        settings.host = args.host
    if args.port:
        settings.port = args.port
    if args.log_level:
        settings.log_level = args.log_level
    
    # Run server
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=args.reload,
        ssl_keyfile=settings.tls_key_file,
        ssl_certfile=settings.tls_cert_file,
    )


if __name__ == "__main__":
    main()
