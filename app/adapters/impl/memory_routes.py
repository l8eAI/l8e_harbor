"""
In-memory route store with snapshot persistence.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, AsyncIterator
from app.adapters.routes import RouteStore, ChangeEvent, ChangeEventType
from app.models.schemas import RouteSpec


class InMemoryRouteStore(RouteStore):
    """In-memory route store with file-based snapshots."""
    
    def __init__(self, snapshot_path: str = "/var/lib/l8e-harbor/routes.snapshot.json"):
        """
        Initialize the in-memory route store.
        
        Args:
            snapshot_path: Path for snapshot persistence
        """
        self.routes: Dict[str, RouteSpec] = {}
        self.snapshot_path = Path(snapshot_path)
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_snapshot()
        self._change_listeners: List[asyncio.Queue] = []
    
    def _load_snapshot(self) -> None:
        """Load routes from snapshot file."""
        if not self.snapshot_path.exists():
            return
        
        try:
            with open(self.snapshot_path, 'r') as f:
                data = json.load(f)
            
            for route_data in data.get("routes", []):
                route = RouteSpec(**route_data)
                self.routes[route.id] = route
        except Exception as e:
            print(f"WARNING: Failed to load route snapshot: {e}")
    
    def _save_snapshot(self) -> None:
        """Save current routes to snapshot file."""
        try:
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "routes": [route.dict() for route in self.routes.values()]
            }
            
            with open(self.snapshot_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"WARNING: Failed to save route snapshot: {e}")
    
    async def _notify_change(self, event: ChangeEvent) -> None:
        """Notify all listeners of a change event."""
        for queue in self._change_listeners[:]:  # Copy to avoid modification during iteration
            try:
                await queue.put(event)
            except Exception:
                # Remove broken listeners
                self._change_listeners.remove(queue)
    
    async def list_routes(self) -> List[RouteSpec]:
        """List all routes."""
        return list(self.routes.values())
    
    async def get_route(self, route_id: str) -> Optional[RouteSpec]:
        """Get a route by ID."""
        return self.routes.get(route_id)
    
    async def put_route(self, route: RouteSpec) -> None:
        """Store or update a route."""
        is_new = route.id not in self.routes
        route.updated_at = datetime.utcnow()
        
        self.routes[route.id] = route
        self._save_snapshot()
        
        # Notify listeners
        event_type = ChangeEventType.CREATED if is_new else ChangeEventType.UPDATED
        await self._notify_change(ChangeEvent(
            event_type=event_type,
            route_id=route.id,
            route=route
        ))
    
    async def delete_route(self, route_id: str) -> bool:
        """Delete a route by ID."""
        if route_id not in self.routes:
            return False
        
        route = self.routes.pop(route_id)
        self._save_snapshot()
        
        # Notify listeners
        await self._notify_change(ChangeEvent(
            event_type=ChangeEventType.DELETED,
            route_id=route_id,
            route=route
        ))
        
        return True
    
    async def watch_changes(self) -> AsyncIterator[ChangeEvent]:
        """Watch for route changes."""
        queue: asyncio.Queue = asyncio.Queue()
        self._change_listeners.append(queue)
        
        try:
            while True:
                event = await queue.get()
                yield event
        except GeneratorExit:
            # Clean up when generator is closed
            if queue in self._change_listeners:
                self._change_listeners.remove(queue)
    
    def get_routes_by_path_prefix(self, path_prefix: str) -> List[RouteSpec]:
        """Get routes matching a path prefix (helper method for routing)."""
        matching_routes = []
        
        for route in self.routes.values():
            if path_prefix.startswith(route.path):
                matching_routes.append(route)
        
        # Sort by priority (descending) then path length (descending)
        matching_routes.sort(
            key=lambda r: (-r.priority, -len(r.path), r.created_at)
        )
        
        return matching_routes
    
    def clear_all_routes(self) -> None:
        """Clear all routes (for testing)."""
        self.routes.clear()
        self._save_snapshot()