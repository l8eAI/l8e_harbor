"""
SQLite route store implementation.
"""

import json
import sqlite3
import asyncio
import aiosqlite
from datetime import datetime
from typing import List, Optional, AsyncIterator
from app.adapters.routes import RouteStore, ChangeEvent, ChangeEventType
from app.models.schemas import RouteSpec


class SQLiteRouteStore(RouteStore):
    """SQLite-based route store."""
    
    def __init__(self, db_path: str = "/var/lib/l8e-harbor/routes.db"):
        """
        Initialize the SQLite route store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialized = False
        self._change_listeners: List[asyncio.Queue] = []
    
    async def _init_db(self) -> None:
        """Initialize database schema."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS routes (
                    id TEXT PRIMARY KEY,
                    spec TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_routes_path 
                ON routes(json_extract(spec, '$.path'))
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_routes_priority
                ON routes(json_extract(spec, '$.priority'))
            """)
            await db.commit()
        
        self._initialized = True
    
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
        await self._init_db()
        
        routes = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT spec FROM routes ORDER BY id") as cursor:
                async for row in cursor:
                    spec_data = json.loads(row[0])
                    routes.append(RouteSpec(**spec_data))
        
        return routes
    
    async def get_route(self, route_id: str) -> Optional[RouteSpec]:
        """Get a route by ID."""
        await self._init_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT spec FROM routes WHERE id = ?", 
                (route_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    spec_data = json.loads(row[0])
                    return RouteSpec(**spec_data)
        
        return None
    
    async def put_route(self, route: RouteSpec) -> None:
        """Store or update a route."""
        await self._init_db()
        
        is_new = await self.get_route(route.id) is None
        route.updated_at = datetime.utcnow()
        
        spec_json = route.json()
        
        async with aiosqlite.connect(self.db_path) as db:
            if is_new:
                await db.execute(
                    "INSERT INTO routes (id, spec, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (route.id, spec_json, route.created_at, route.updated_at)
                )
            else:
                await db.execute(
                    "UPDATE routes SET spec = ?, updated_at = ? WHERE id = ?",
                    (spec_json, route.updated_at, route.id)
                )
            await db.commit()
        
        # Notify listeners
        event_type = ChangeEventType.CREATED if is_new else ChangeEventType.UPDATED
        await self._notify_change(ChangeEvent(
            event_type=event_type,
            route_id=route.id,
            route=route
        ))
    
    async def delete_route(self, route_id: str) -> bool:
        """Delete a route by ID."""
        await self._init_db()
        
        # Get route before deletion for notification
        route = await self.get_route(route_id)
        if not route:
            return False
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM routes WHERE id = ?", (route_id,))
            await db.commit()
            
            if cursor.rowcount == 0:
                return False
        
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
    
    async def get_routes_by_path_prefix(self, path_prefix: str) -> List[RouteSpec]:
        """Get routes matching a path prefix (helper method for routing)."""
        await self._init_db()
        
        routes = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT spec FROM routes 
                WHERE json_extract(spec, '$.path') <= ? 
                AND ? LIKE json_extract(spec, '$.path') || '%'
                ORDER BY 
                    json_extract(spec, '$.priority') DESC,
                    length(json_extract(spec, '$.path')) DESC,
                    created_at ASC
            """, (path_prefix, path_prefix)) as cursor:
                async for row in cursor:
                    spec_data = json.loads(row[0])
                    routes.append(RouteSpec(**spec_data))
        
        return routes
    
    async def clear_all_routes(self) -> None:
        """Clear all routes (for testing)."""
        await self._init_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM routes")
            await db.commit()