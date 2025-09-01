"""
Configuration management for l8e-harbor.
"""

import os
from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from app.models.schemas import AppConfig


class Settings(BaseSettings):
    """Application settings loaded from environment and config files."""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8443
    workers: int = 1
    
    # Application mode
    mode: str = "vm"  # k8s, vm, hybrid
    
    # TLS settings
    tls_cert_file: Optional[str] = None
    tls_key_file: Optional[str] = None
    tls_ca_file: Optional[str] = None
    
    # Adapter settings
    secret_provider: str = "localfs"
    secret_path: str = "/etc/l8e-harbor/secrets"
    route_store: str = "memory"
    route_store_path: str = "/var/lib/l8e-harbor/routes.db"
    auth_adapter: str = "local"
    
    # JWT settings
    jwt_ttl_seconds: int = 900  # 15 minutes
    
    # Logging
    log_level: str = "INFO"
    
    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = False
    
    # Kubernetes specific
    k8s_namespace: Optional[str] = None
    k8s_config_map: Optional[str] = None
    
    # Config file path
    config_file: Optional[str] = None
    
    class Config:
        env_prefix = "HARBOR_"
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def create_app_config(settings: Settings) -> AppConfig:
    """
    Create AppConfig from Settings.
    
    Args:
        settings: Application settings
        
    Returns:
        AppConfig instance
    """
    return AppConfig(
        mode=settings.mode,
        server={
            "host": settings.host,
            "port": settings.port,
            "workers": settings.workers
        },
        tls={
            "cert_file": settings.tls_cert_file,
            "key_file": settings.tls_key_file,
            "ca_file": settings.tls_ca_file
        } if settings.tls_cert_file else None,
        secret_provider=settings.secret_provider,
        secret_path=settings.secret_path,
        route_store=settings.route_store,
        route_store_path=settings.route_store_path,
        auth_adapter=settings.auth_adapter,
        jwt_ttl_seconds=settings.jwt_ttl_seconds,
        log_level=settings.log_level,
        enable_metrics=settings.enable_metrics,
        enable_tracing=settings.enable_tracing
    )


def load_config_from_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    import yaml
    
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"WARNING: Failed to load config file {config_path}: {e}")
        return {}


def get_config_file_paths() -> list[str]:
    """Get list of potential config file paths in order of preference."""
    return [
        os.environ.get("HARBOR_CONFIG_FILE", ""),
        "/etc/l8e-harbor/config.yaml",
        os.path.expanduser("~/.config/l8e-harbor/config.yaml"),
        "./config.yaml"
    ]


def load_merged_config() -> Settings:
    """
    Load configuration from multiple sources with precedence:
    1. CLI flags (handled by caller)
    2. Environment variables
    3. Configuration files
    4. Defaults
    """
    # Start with base settings (env vars + defaults)
    settings = Settings()
    
    # Load from config files
    config_data = {}
    for config_path in get_config_file_paths():
        if config_path and os.path.exists(config_path):
            file_config = load_config_from_file(config_path)
            config_data.update(file_config)
            break
    
    # Override with file config
    if config_data:
        # Convert nested config to flat env-style keys
        flat_config = {}
        
        # Server config
        server_config = config_data.get("server", {})
        if "host" in server_config:
            flat_config["host"] = server_config["host"]
        if "port" in server_config:
            flat_config["port"] = server_config["port"]
        if "workers" in server_config:
            flat_config["workers"] = server_config["workers"]
        
        # TLS config
        tls_config = config_data.get("tls", {})
        if "cert_file" in tls_config:
            flat_config["tls_cert_file"] = tls_config["cert_file"]
        if "key_file" in tls_config:
            flat_config["tls_key_file"] = tls_config["key_file"]
        if "ca_file" in tls_config:
            flat_config["tls_ca_file"] = tls_config["ca_file"]
        
        # Direct mappings
        for key in ["mode", "secret_provider", "secret_path", "route_store", 
                   "route_store_path", "auth_adapter", "jwt_ttl_seconds",
                   "log_level", "enable_metrics", "enable_tracing",
                   "k8s_namespace", "k8s_config_map"]:
            if key in config_data:
                flat_config[key] = config_data[key]
        
        # Create settings with overrides
        settings = Settings(**flat_config)
    
    return settings