"""
Secret provider interfaces and base implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class SecretProvider(ABC):
    """Abstract base class for secret providers."""
    
    @abstractmethod
    def get_secret(self, path: str) -> Dict[str, Any]:
        """
        Fetch secret data from the provider.
        
        Args:
            path: The secret path/key
            
        Returns:
            Dictionary containing secret data
            
        Raises:
            KeyError: If the secret doesn't exist
            Exception: For other provider-specific errors
        """
        pass
    
    @abstractmethod 
    def put_secret(self, path: str, payload: Dict[str, Any]) -> None:
        """
        Store secret data in the provider.
        
        Args:
            path: The secret path/key
            payload: Dictionary containing secret data
            
        Raises:
            Exception: For provider-specific errors
        """
        pass
    
    def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from the provider.
        
        Args:
            path: The secret path/key
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            # Default implementation - subclasses may override
            self.get_secret(path)  # Check if exists
            # If we reach here, secret exists but deletion not implemented
            raise NotImplementedError("Secret deletion not supported by this provider")
        except KeyError:
            return False
    
    def list_secrets(self, prefix: str = "") -> list[str]:
        """
        List all secret paths with the given prefix.
        
        Args:
            prefix: Optional prefix to filter secrets
            
        Returns:
            List of secret paths
        """
        raise NotImplementedError("Secret listing not supported by this provider")