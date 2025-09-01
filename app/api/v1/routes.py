"""
Route management API endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import HTTPBearer
from app.models.schemas import (
    RouteDTO, RouteCreateRequest, RouteListResponse, RouteSpec
)
from app.adapters.auth import AuthContext
from app.adapters.routes import RouteStore
from app.core.dependencies import get_route_store, get_current_user
from datetime import datetime

router = APIRouter(tags=["Route Management"])
security = HTTPBearer()


@router.get("/routes", response_model=RouteListResponse)
async def list_routes(
    path: Optional[str] = Query(None, description="Filter by path prefix"),
    backend: Optional[str] = Query(None, description="Filter by backend URL"),
    route_store: RouteStore = Depends(get_route_store),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    List all routes with optional filtering.
    """
    try:
        routes = await route_store.list_routes()
        
        # Apply filters
        if path:
            routes = [r for r in routes if r.path.startswith(path)]
        
        if backend:
            routes = [
                r for r in routes 
                if any(str(b.url).startswith(backend) for b in r.backends)
            ]
        
        # Convert to DTOs
        route_dtos = [RouteDTO.from_orm(route) for route in routes]
        
        return RouteListResponse(routes=route_dtos)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list routes: {e}"
        )


@router.get("/routes/{route_id}", response_model=RouteDTO)
async def get_route(
    route_id: str = Path(..., description="Route ID"),
    route_store: RouteStore = Depends(get_route_store),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Get a specific route by ID.
    """
    try:
        route = await route_store.get_route(route_id)
        if not route:
            raise HTTPException(
                status_code=404,
                detail=f"Route '{route_id}' not found"
            )
        
        return RouteDTO.from_orm(route)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get route: {e}"
        )


@router.put("/routes/{route_id}", response_model=RouteDTO)
async def create_or_update_route(
    route_id: str = Path(..., description="Route ID"),
    request: RouteCreateRequest = ...,
    route_store: RouteStore = Depends(get_route_store),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Create or update a route.
    """
    # Check if user has permission (harbor-master required)
    if current_user.role != "harbor-master":
        raise HTTPException(
            status_code=403,
            detail="harbor-master role required for route management"
        )
    
    try:
        # Check if route exists
        existing_route = await route_store.get_route(route_id)
        is_new = existing_route is None
        
        # Create route spec
        now = datetime.utcnow()
        route_data = request.dict()
        route_data['id'] = route_id
        
        if is_new:
            route_data['created_at'] = now
        else:
            route_data['created_at'] = existing_route.created_at
        
        route_data['updated_at'] = now
        
        route = RouteSpec(**route_data)
        
        # Validate route
        if not route.backends:
            raise HTTPException(
                status_code=400,
                detail="At least one backend is required"
            )
        
        # Store route
        await route_store.put_route(route)
        
        return RouteDTO.from_orm(route)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save route: {e}"
        )


@router.delete("/routes/{route_id}")
async def delete_route(
    route_id: str = Path(..., description="Route ID"),
    route_store: RouteStore = Depends(get_route_store),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Delete a route by ID.
    """
    # Check if user has permission (harbor-master required)
    if current_user.role != "harbor-master":
        raise HTTPException(
            status_code=403,
            detail="harbor-master role required for route management"
        )
    
    try:
        deleted = await route_store.delete_route(route_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Route '{route_id}' not found"
            )
        
        return {"message": f"Route '{route_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete route: {e}"
        )


@router.post("/routes:bulk-apply")
async def bulk_apply_routes(
    routes: list[RouteCreateRequest],
    route_store: RouteStore = Depends(get_route_store),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Apply multiple routes in bulk.
    """
    # Check if user has permission (harbor-master required)
    if current_user.role != "harbor-master":
        raise HTTPException(
            status_code=403,
            detail="harbor-master role required for route management"
        )
    
    try:
        results = []
        for route_request in routes:
            # Generate ID from path if not provided
            route_id = route_request.path.replace('/', '_').strip('_') or 'root'
            
            # Check if route exists
            existing_route = await route_store.get_route(route_id)
            is_new = existing_route is None
            
            # Create route spec
            now = datetime.utcnow()
            route_data = route_request.dict()
            route_data['id'] = route_id
            
            if is_new:
                route_data['created_at'] = now
            else:
                route_data['created_at'] = existing_route.created_at
            
            route_data['updated_at'] = now
            
            route = RouteSpec(**route_data)
            await route_store.put_route(route)
            
            results.append({
                "id": route_id,
                "status": "created" if is_new else "updated"
            })
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to bulk apply routes: {e}"
        )


@router.get("/routes:export")
async def export_routes(
    route_store: RouteStore = Depends(get_route_store),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Export all routes as YAML.
    """
    try:
        routes = await route_store.list_routes()
        
        # Convert to exportable format
        export_data = {
            "apiVersion": "harbor.l8e/v1",
            "kind": "RouteList",
            "metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "exported_by": current_user.subject
            },
            "items": [route.dict() for route in routes]
        }
        
        return export_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export routes: {e}"
        )