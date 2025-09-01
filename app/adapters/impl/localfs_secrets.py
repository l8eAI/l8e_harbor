"""
LocalFS secret provider implementation.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
from app.adapters.secrets import SecretProvider


class LocalFSSecretProvider(SecretProvider):
    """Local filesystem secret provider."""
    
    def __init__(self, secret_path: str = "/etc/l8e-harbor/secrets"):
        """
        Initialize the LocalFS secret provider.
        
        Args:
            secret_path: Directory path where secrets are stored
        """
        self.secret_path = Path(secret_path)
        self.secret_path.mkdir(parents=True, exist_ok=True)
    
    def get_secret(self, path: str) -> Dict[str, Any]:
        """
        Get secret from filesystem.
        
        Args:
            path: Secret filename (without extension)
            
        Returns:
            Dictionary containing secret data
            
        Raises:
            KeyError: If secret file doesn't exist
        """
        secret_file = self.secret_path / f"{path}.json"
        
        if not secret_file.exists():
            # Try YAML format as fallback
            yaml_file = self.secret_path / f"{path}.yaml"
            if yaml_file.exists():
                import yaml
                try:
                    with open(yaml_file, 'r') as f:
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    raise KeyError(f"Failed to read secret '{path}': {e}")
            
            # Try plain text files for certain secrets
            txt_file = self.secret_path / path
            if txt_file.exists():
                try:
                    with open(txt_file, 'r') as f:
                        content = f.read().strip()
                        return {"value": content}
                except Exception as e:
                    raise KeyError(f"Failed to read secret '{path}': {e}")
            
            raise KeyError(f"Secret '{path}' not found")
        
        try:
            with open(secret_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise KeyError(f"Failed to read secret '{path}': {e}")
    
    def put_secret(self, path: str, payload: Dict[str, Any]) -> None:
        """
        Store secret to filesystem.
        
        Args:
            path: Secret filename (without extension)
            payload: Secret data to store
        """
        secret_file = self.secret_path / f"{path}.json"
        
        try:
            with open(secret_file, 'w') as f:
                json.dump(payload, f, indent=2)
            
            # Set secure permissions
            os.chmod(secret_file, 0o600)
        except Exception as e:
            raise Exception(f"Failed to write secret '{path}': {e}")
    
    def delete_secret(self, path: str) -> bool:
        """
        Delete secret from filesystem.
        
        Args:
            path: Secret filename
            
        Returns:
            True if deleted, False if not found
        """
        secret_file = self.secret_path / f"{path}.json"
        
        if secret_file.exists():
            try:
                secret_file.unlink()
                return True
            except Exception:
                return False
        
        return False
    
    def list_secrets(self, prefix: str = "") -> List[str]:
        """
        List secret files in the directory.
        
        Args:
            prefix: Filter secrets by prefix
            
        Returns:
            List of secret names (without extensions)
        """
        secrets = []
        
        for file_path in self.secret_path.iterdir():
            if file_path.is_file():
                name = file_path.stem  # Get filename without extension
                if name.startswith(prefix):
                    secrets.append(name)
        
        return sorted(secrets)
    
    def ensure_default_secrets(self) -> None:
        """
        Create default secret files if they don't exist.
        Only creates JWT keys structure and empty tokens, NOT default users.
        """
        defaults = {
            "jwt_keys": {
                "private_key_path": str(self.secret_path / "jwt_private.pem"),
                "public_key_path": str(self.secret_path / "jwt_public.pem")
            },
            "tokens": {}
        }
        
        for name, data in defaults.items():
            try:
                self.get_secret(name)
            except KeyError:
                self.put_secret(name, data)
        
        # Initialize empty users file if it doesn't exist
        try:
            self.get_secret("users")
        except KeyError:
            self.put_secret("users", {})