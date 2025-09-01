"""
Kubernetes ServiceAccount authentication adapter.
"""

import json
import base64
from typing import Optional, Dict, Any
from fastapi import Request
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from app.adapters.auth import AuthAdapter, AuthContext


class K8sServiceAccountAdapter(AuthAdapter):
    """Kubernetes ServiceAccount token authentication."""
    
    def __init__(self, roles_map: Optional[Dict[str, str]] = None):
        """
        Initialize the K8s ServiceAccount auth adapter.
        
        Args:
            roles_map: Mapping of "namespace:serviceaccount" to roles
        """
        self.roles_map = roles_map or {}
        
        try:
            # Try in-cluster config first
            config.load_incluster_config()
        except:
            try:
                # Fallback to kubeconfig
                config.load_kube_config()
            except Exception as e:
                raise Exception(f"Failed to load Kubernetes configuration: {e}")
        
        self.auth_v1 = client.AuthenticationV1Api()
    
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        """
        Authenticate request using Kubernetes ServiceAccount token.
        
        Args:
            request: FastAPI request object
            
        Returns:
            AuthContext if authenticated, None otherwise
        """
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        try:
            # Create TokenReview request
            token_review = client.V1TokenReview(
                metadata=client.V1ObjectMeta(),
                spec=client.V1TokenReviewSpec(token=token)
            )
            
            # Submit for validation
            result = self.auth_v1.create_token_review(body=token_review)
            
            if not result.status.authenticated:
                return None
            
            # Extract user info
            user_info = result.status.user
            if not user_info:
                return None
            
            username = user_info.username  # e.g., "system:serviceaccount:namespace:name"
            groups = user_info.groups or []
            
            # Parse ServiceAccount info
            if not username.startswith("system:serviceaccount:"):
                return None
            
            parts = username.split(":")
            if len(parts) != 4:
                return None
            
            namespace = parts[2]
            service_account = parts[3]
            sa_key = f"{namespace}:{service_account}"
            
            # Map to internal role
            role = self.roles_map.get(sa_key)
            if not role:
                # Default role mapping based on ServiceAccount name
                if service_account == "l8e-harbor-admin":
                    role = "harbor-master"
                elif service_account.startswith("l8e-harbor"):
                    role = "captain"
                else:
                    role = "captain"  # Default role
            
            return AuthContext(
                subject=username,
                role=role,
                meta={
                    "namespace": namespace,
                    "service_account": service_account,
                    "groups": groups,
                    "token_type": "k8s_sa"
                }
            )
            
        except ApiException as e:
            print(f"Token validation failed: {e}")
            return None
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def set_roles_map(self, roles_map: Dict[str, str]) -> None:
        """
        Update the roles mapping.
        
        Args:
            roles_map: New mapping of "namespace:serviceaccount" to roles
        """
        self.roles_map = roles_map
    
    @classmethod
    def from_config_map(cls, config_map_data: Dict[str, Any]) -> 'K8sServiceAccountAdapter':
        """
        Create adapter from ConfigMap data.
        
        Args:
            config_map_data: ConfigMap containing roles mapping
            
        Returns:
            Configured K8sServiceAccountAdapter
        """
        roles_map = config_map_data.get("roles_map", {})
        return cls(roles_map=roles_map)