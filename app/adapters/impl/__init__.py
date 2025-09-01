"""
Default adapter implementations for l8e-harbor.
"""

from .localfs_secrets import LocalFSSecretProvider
from .k8s_secrets import KubernetesSecretProvider
from .simple_auth import SimpleLocalAuthAdapter
from .k8s_auth import K8sServiceAccountAdapter
from .memory_routes import InMemoryRouteStore
from .sqlite_routes import SQLiteRouteStore

__all__ = [
    "LocalFSSecretProvider",
    "KubernetesSecretProvider", 
    "SimpleLocalAuthAdapter",
    "K8sServiceAccountAdapter",
    "InMemoryRouteStore",
    "SQLiteRouteStore",
]