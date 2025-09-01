"""
Kubernetes Secret provider implementation.
"""

import base64
import json
import os
from typing import Dict, Any, List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from app.adapters.secrets import SecretProvider


class KubernetesSecretProvider(SecretProvider):
    """Kubernetes Secret provider using the Kubernetes API."""
    
    def __init__(self, namespace: Optional[str] = None):
        """
        Initialize the Kubernetes secret provider.
        
        Args:
            namespace: Kubernetes namespace (defaults to current namespace)
        """
        self.namespace = namespace or self._get_current_namespace()
        
        try:
            # Try in-cluster config first
            config.load_incluster_config()
        except:
            try:
                # Fallback to kubeconfig
                config.load_kube_config()
            except Exception as e:
                raise Exception(f"Failed to load Kubernetes configuration: {e}")
        
        self.v1 = client.CoreV1Api()
    
    def _get_current_namespace(self) -> str:
        """Get the current namespace from service account."""
        namespace_file = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        
        if os.path.exists(namespace_file):
            with open(namespace_file, 'r') as f:
                return f.read().strip()
        
        return "default"
    
    def _secret_name(self, path: str) -> str:
        """Convert path to Kubernetes secret name."""
        # Replace invalid characters with dashes
        name = path.replace("_", "-").replace("/", "-").lower()
        return f"l8e-harbor-{name}"
    
    def get_secret(self, path: str) -> Dict[str, Any]:
        """
        Get secret from Kubernetes Secret.
        
        Args:
            path: Secret path/key
            
        Returns:
            Dictionary containing secret data
            
        Raises:
            KeyError: If secret doesn't exist
        """
        secret_name = self._secret_name(path)
        
        try:
            secret = self.v1.read_namespaced_secret(
                name=secret_name,
                namespace=self.namespace
            )
            
            if not secret.data:
                return {}
            
            # Decode base64 values and parse JSON if possible
            result = {}
            for key, value in secret.data.items():
                decoded_value = base64.b64decode(value).decode('utf-8')
                
                # Try to parse as JSON
                try:
                    result[key] = json.loads(decoded_value)
                except json.JSONDecodeError:
                    result[key] = decoded_value
            
            # If there's a single 'data' key, return its contents
            if len(result) == 1 and 'data' in result:
                return result['data']
            
            return result
            
        except ApiException as e:
            if e.status == 404:
                raise KeyError(f"Secret '{path}' not found")
            raise Exception(f"Failed to get secret '{path}': {e}")
    
    def put_secret(self, path: str, payload: Dict[str, Any]) -> None:
        """
        Store secret in Kubernetes Secret.
        
        Args:
            path: Secret path/key
            payload: Secret data to store
        """
        secret_name = self._secret_name(path)
        
        # Encode data to base64
        data = {}
        if isinstance(payload, dict) and len(payload) == 1:
            # If single key, check if it's already structured data
            key, value = next(iter(payload.items()))
            if isinstance(value, (dict, list)):
                data['data'] = base64.b64encode(
                    json.dumps(value, default=str).encode('utf-8')
                ).decode('utf-8')
            else:
                data[key] = base64.b64encode(str(value).encode('utf-8')).decode('utf-8')
        else:
            data['data'] = base64.b64encode(
                json.dumps(payload, default=str).encode('utf-8')
            ).decode('utf-8')
        
        secret_body = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=secret_name,
                labels={"app": "l8e-harbor", "component": "secret"}
            ),
            data=data
        )
        
        try:
            # Try to update first
            self.v1.patch_namespaced_secret(
                name=secret_name,
                namespace=self.namespace,
                body=secret_body
            )
        except ApiException as e:
            if e.status == 404:
                # Create if doesn't exist
                try:
                    self.v1.create_namespaced_secret(
                        namespace=self.namespace,
                        body=secret_body
                    )
                except ApiException as create_e:
                    raise Exception(f"Failed to create secret '{path}': {create_e}")
            else:
                raise Exception(f"Failed to update secret '{path}': {e}")
    
    def delete_secret(self, path: str) -> bool:
        """
        Delete secret from Kubernetes.
        
        Args:
            path: Secret path/key
            
        Returns:
            True if deleted, False if not found
        """
        secret_name = self._secret_name(path)
        
        try:
            self.v1.delete_namespaced_secret(
                name=secret_name,
                namespace=self.namespace
            )
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise Exception(f"Failed to delete secret '{path}': {e}")
    
    def list_secrets(self, prefix: str = "") -> List[str]:
        """
        List secrets in the namespace.
        
        Args:
            prefix: Filter secrets by prefix
            
        Returns:
            List of secret paths
        """
        try:
            secrets = self.v1.list_namespaced_secret(
                namespace=self.namespace,
                label_selector="app=l8e-harbor,component=secret"
            )
            
            result = []
            secret_prefix = "l8e-harbor-"
            
            for secret in secrets.items:
                if secret.metadata.name.startswith(secret_prefix):
                    # Extract original path from secret name
                    path = secret.metadata.name[len(secret_prefix):].replace("-", "_")
                    if path.startswith(prefix):
                        result.append(path)
            
            return sorted(result)
            
        except ApiException as e:
            raise Exception(f"Failed to list secrets: {e}")