"""
Route store interfaces and base implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, AsyncIterator
from app.models.schemas import RouteSpec


class ChangeEventType(Enum):
    """Types of route change events."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


@dataclass
class ChangeEvent:
    """Route change event."""
    event_type: ChangeEventType
    route_id: str
    route: Optional[RouteSpec] = None


class RouteStore(ABC):
    """Abstract base class for route storage backends."""
    
    @abstractmethod
    async def list_routes(self) -> List[RouteSpec]:
        """
        List all routes in the store.
        
        Returns:
            List of RouteSpec objects
        """
        pass
    
    @abstractmethod
    async def get_route(self, route_id: str) -> Optional[RouteSpec]:
        """
        Get a specific route by ID.
        
        Args:
            route_id: The route identifier
            
        Returns:
            RouteSpec if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def put_route(self, route: RouteSpec) -> None:
        """
        Store or update a route.
        
        Args:
            route: The RouteSpec to store
            
        Raises:
            Exception: For store-specific errors
        """
        pass
    
    @abstractmethod
    async def delete_route(self, route_id: str) -> bool:
        """
        Delete a route by ID.
        
        Args:
            route_id: The route identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        pass
    
    async def watch_changes(self) -> AsyncIterator[ChangeEvent]:
        """
        Watch for route changes.
        
        Yields:
            ChangeEvent objects for route modifications
        """
        # Default implementation - no watching capability
        # Subclasses should override if they support watching
        # This makes it an async generator that yields nothing
        if False:  # pragma: no cover
            yield ChangeEvent(ChangeEventType.CREATED, "", None)