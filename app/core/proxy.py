"""
Core proxy logic and route matching for l8e-harbor.
"""

import time
import uuid
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
import httpx
from fastapi import Request, Response, HTTPException
from starlette.responses import StreamingResponse
from app.models.schemas import RouteSpec, BackendSpec, MatcherSpec
from app.adapters.routes import RouteStore
from app.adapters.auth import AuthAdapter, AuthContext


class CircuitBreaker:
    """Simple circuit breaker implementation."""
    
    def __init__(self, failure_threshold: int, minimum_requests: int, timeout_ms: int):
        self.failure_threshold = failure_threshold
        self.minimum_requests = minimum_requests
        self.timeout_ms = timeout_ms
        self.failures = 0
        self.requests = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        now = time.time() * 1000
        
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if now - self.last_failure_time > self.timeout_ms:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful execution."""
        self.failures = 0
        self.requests += 1
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed execution."""
        self.failures += 1
        self.requests += 1
        self.last_failure_time = time.time() * 1000
        
        if (self.requests >= self.minimum_requests and 
            (self.failures / self.requests) * 100 >= self.failure_threshold):
            self.state = "OPEN"


class RouteManager:
    """Route matching and management."""
    
    def __init__(self, route_store: RouteStore):
        self.route_store = route_store
        self._route_cache: List[RouteSpec] = []
        self._cache_updated = 0
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    async def _update_route_cache(self) -> None:
        """Update the route cache from store."""
        try:
            routes = await self.route_store.list_routes()
            self._route_cache = sorted(
                routes,
                key=lambda r: (-r.priority, -len(r.path), r.created_at)
            )
            self._cache_updated = time.time()
        except Exception as e:
            print(f"Failed to update route cache: {e}")
    
    async def find_matching_route(self, request: Request) -> Optional[RouteSpec]:
        """
        Find the best matching route for a request.
        
        Args:
            request: The incoming request
            
        Returns:
            Matching RouteSpec or None
        """
        # Update cache if needed (simple time-based cache)
        if time.time() - self._cache_updated > 30:  # 30 seconds
            await self._update_route_cache()
        
        path = request.url.path
        method = request.method
        
        # Find candidate routes
        candidates = []
        for route in self._route_cache:
            if (path.startswith(route.path) and 
                method in route.methods):
                candidates.append(route)
        
        # Evaluate matchers
        for route in candidates:
            if await self._evaluate_matchers(request, route.matchers):
                return route
        
        return None
    
    async def _evaluate_matchers(
        self, 
        request: Request, 
        matchers: Optional[List[MatcherSpec]]
    ) -> bool:
        """
        Evaluate request matchers.
        
        Args:
            request: The request to evaluate
            matchers: List of matchers to check
            
        Returns:
            True if all matchers pass, False otherwise
        """
        if not matchers:
            return True
        
        for matcher in matchers:
            if not await self._evaluate_single_matcher(request, matcher):
                return False
        
        return True
    
    async def _evaluate_single_matcher(
        self,
        request: Request,
        matcher: MatcherSpec
    ) -> bool:
        """Evaluate a single matcher."""
        import re
        
        if matcher.name == "header":
            header_value = request.headers.get(matcher.value, "")
            if matcher.op == "exists":
                return bool(header_value)
            elif matcher.op == "equals":
                return header_value == matcher.value
            elif matcher.op == "contains":
                return matcher.value in header_value
            elif matcher.op == "regex":
                return bool(re.match(matcher.value, header_value))
        
        elif matcher.name == "query":
            query_params = dict(request.query_params)
            if matcher.op == "exists":
                return matcher.value in query_params
            elif matcher.op == "equals":
                return query_params.get(matcher.value) == matcher.value
            elif matcher.op == "contains":
                param_value = query_params.get(matcher.value, "")
                return matcher.value in param_value
        
        elif matcher.name == "cookie":
            cookie_value = request.cookies.get(matcher.value, "")
            if matcher.op == "exists":
                return bool(cookie_value)
            elif matcher.op == "equals":
                return cookie_value == matcher.value
            elif matcher.op == "contains":
                return matcher.value in cookie_value
        
        return False
    
    def get_circuit_breaker(self, backend_url: str, route: RouteSpec) -> CircuitBreaker:
        """Get or create circuit breaker for backend."""
        if backend_url not in self._circuit_breakers:
            cb_config = route.circuit_breaker
            self._circuit_breakers[backend_url] = CircuitBreaker(
                failure_threshold=cb_config.failure_threshold,
                minimum_requests=cb_config.minimum_requests,
                timeout_ms=cb_config.timeout_ms
            )
        return self._circuit_breakers[backend_url]


class ProxyHandler:
    """HTTP proxy handler."""
    
    def __init__(self, route_manager: RouteManager, auth_adapter: AuthAdapter):
        self.route_manager = route_manager
        self.auth_adapter = auth_adapter
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    
    async def handle_request(self, request: Request) -> Response:
        """
        Handle incoming proxy request.
        
        Args:
            request: The incoming request
            
        Returns:
            Response from backend or error response
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID for tracing
        request.state.request_id = request_id
        
        try:
            # Find matching route
            route = await self.route_manager.find_matching_route(request)
            if not route:
                raise HTTPException(status_code=404, detail="No matching route found")
            
            # Store route in request state
            request.state.route = route
            
            # Apply middleware
            await self._apply_middleware(request, route)
            
            # Select backend
            backend = self._select_backend(route)
            if not backend:
                raise HTTPException(status_code=503, detail="No available backends")
            
            # Check circuit breaker
            circuit_breaker = self.route_manager.get_circuit_breaker(str(backend.url), route)
            if not circuit_breaker.can_execute():
                raise HTTPException(status_code=503, detail="Circuit breaker open")
            
            # Proxy request
            try:
                response = await self._proxy_request(request, route, backend)
                circuit_breaker.record_success()
                return response
            except Exception as e:
                circuit_breaker.record_failure()
                raise e
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Proxy error: {e}")
        finally:
            # Log request
            duration_ms = (time.time() - start_time) * 1000
            print(f"Request {request_id} to {request.url.path} took {duration_ms:.2f}ms")
    
    async def _apply_middleware(self, request: Request, route: RouteSpec) -> None:
        """Apply middleware to request."""
        for middleware in route.middleware:
            await self._apply_single_middleware(request, middleware.name, middleware.config)
    
    async def _apply_single_middleware(
        self,
        request: Request,
        middleware_name: str,
        config: Dict[str, Any]
    ) -> None:
        """Apply single middleware."""
        if middleware_name == "auth":
            # Enforce authentication
            auth_context = await self.auth_adapter.authenticate(request)
            if not auth_context:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Check role requirements
            required_roles = config.get("require_role", [])
            if required_roles and auth_context.role not in required_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Required role: {required_roles}"
                )
            
            request.state.auth_context = auth_context
        
        elif middleware_name == "logging":
            # Enhanced logging (implementation would add structured logging)
            level = config.get("level", "info")
            print(f"[{level.upper()}] Processing request {request.state.request_id}")
        
        elif middleware_name == "header-rewrite":
            # Header manipulation
            headers_to_set = config.get("set", {})
            headers_to_remove = config.get("remove", [])
            
            # Store header modifications in request state
            if not hasattr(request.state, 'header_modifications'):
                request.state.header_modifications = {"set": {}, "remove": []}
            
            request.state.header_modifications["set"].update(headers_to_set)
            request.state.header_modifications["remove"].extend(headers_to_remove)
    
    def _select_backend(self, route: RouteSpec) -> Optional[BackendSpec]:
        """Select a backend from the route (simple round-robin for now)."""
        if not route.backends:
            return None
        
        # For now, just return the first backend
        # TODO: Implement proper load balancing
        return route.backends[0]
    
    async def _proxy_request(
        self,
        request: Request,
        route: RouteSpec,
        backend: BackendSpec
    ) -> Response:
        """Proxy request to backend."""
        # Build target URL
        target_path = request.url.path
        if route.strip_prefix:
            target_path = target_path[len(route.path):] or "/"
        
        target_url = str(backend.url).rstrip('/') + target_path
        if request.url.query:
            target_url += "?" + request.url.query
        
        # Prepare headers
        headers = dict(request.headers)
        
        # Remove hop-by-hop headers
        hop_by_hop_headers = {
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade'
        }
        for header in hop_by_hop_headers:
            headers.pop(header, None)
        
        # Add forwarding headers
        headers['x-forwarded-for'] = request.client.host
        headers['x-forwarded-proto'] = request.url.scheme
        headers['x-forwarded-host'] = request.headers.get('host', '')
        headers['x-request-id'] = request.state.request_id
        
        # Apply header modifications
        if hasattr(request.state, 'header_modifications'):
            mods = request.state.header_modifications
            headers.update(mods["set"])
            for header_to_remove in mods["remove"]:
                headers.pop(header_to_remove.lower(), None)
        
        # Read request body
        body = await request.body()
        
        # Make request with retry logic
        retry_policy = route.retry_policy
        last_exception = None
        
        for attempt in range(retry_policy.max_retries + 1):
            try:
                response = await self.client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    timeout=route.timeout_ms / 1000.0
                )
                
                # Return streaming response
                return StreamingResponse(
                    content=self._stream_response(response),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.headers.get('content-type')
                )
                
            except Exception as e:
                last_exception = e
                if attempt < retry_policy.max_retries:
                    # Should retry based on policy
                    if self._should_retry(e, retry_policy.retry_on):
                        await asyncio.sleep(retry_policy.backoff_ms / 1000.0)
                        continue
                break
        
        # All retries failed
        raise HTTPException(
            status_code=502,
            detail=f"Backend request failed: {last_exception}"
        )
    
    async def _stream_response(self, response: httpx.Response):
        """Stream response content."""
        async for chunk in response.aiter_bytes():
            yield chunk
    
    def _should_retry(self, exception: Exception, retry_on: List[str]) -> bool:
        """Check if request should be retried based on error."""
        if "5xx" in retry_on and isinstance(exception, httpx.HTTPStatusError):
            return 500 <= exception.response.status_code < 600
        
        if "gateway-error" in retry_on and isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code in [502, 503, 504]
        
        if "timeout" in retry_on and isinstance(exception, httpx.TimeoutException):
            return True
        
        return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()