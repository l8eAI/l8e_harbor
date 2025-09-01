"""
Structured logging setup for l8e-harbor.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None
) -> None:
    """
    Setup application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_type: Format type (json, text)
        log_file: Optional log file path
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create formatter
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn.access").disabled = True  # Disable uvicorn access logs
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce httpx verbosity


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


class RequestLogger:
    """Context-aware request logger."""
    
    def __init__(self, logger_name: str = "l8e.request"):
        self.logger = get_logger(logger_name)
    
    def log_request_start(
        self,
        request_id: str,
        method: str,
        path: str,
        client_ip: str,
        user_agent: Optional[str] = None,
        route_id: Optional[str] = None
    ):
        """Log request start."""
        self.logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "route_id": route_id,
                "event": "request_start"
            }
        )
    
    def log_request_end(
        self,
        request_id: str,
        status_code: int,
        duration_ms: float,
        route_id: Optional[str] = None,
        backend: Optional[str] = None,
        user: Optional[str] = None
    ):
        """Log request completion."""
        self.logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "route_id": route_id,
                "backend": backend,
                "user": user,
                "event": "request_end"
            }
        )
    
    def log_auth_attempt(
        self,
        request_id: str,
        adapter_type: str,
        success: bool,
        user: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """Log authentication attempt."""
        level = logging.INFO if success else logging.WARNING
        message = "Authentication successful" if success else "Authentication failed"
        
        self.logger.log(
            level,
            message,
            extra={
                "request_id": request_id,
                "adapter_type": adapter_type,
                "success": success,
                "user": user,
                "reason": reason,
                "event": "auth_attempt"
            }
        )
    
    def log_route_match(
        self,
        request_id: str,
        route_id: str,
        path: str,
        matched_path: str,
        priority: int
    ):
        """Log route matching."""
        self.logger.debug(
            "Route matched",
            extra={
                "request_id": request_id,
                "route_id": route_id,
                "path": path,
                "matched_path": matched_path,
                "priority": priority,
                "event": "route_match"
            }
        )
    
    def log_backend_call(
        self,
        request_id: str,
        backend_url: str,
        method: str,
        status_code: int,
        duration_ms: float,
        attempt: int = 1
    ):
        """Log backend call."""
        self.logger.info(
            "Backend call",
            extra={
                "request_id": request_id,
                "backend_url": backend_url,
                "method": method,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "attempt": attempt,
                "event": "backend_call"
            }
        )
    
    def log_circuit_breaker(
        self,
        request_id: str,
        backend_url: str,
        state: str,
        reason: str
    ):
        """Log circuit breaker events."""
        self.logger.warning(
            "Circuit breaker event",
            extra={
                "request_id": request_id,
                "backend_url": backend_url,
                "state": state,
                "reason": reason,
                "event": "circuit_breaker"
            }
        )


class AuditLogger:
    """Security audit logging."""
    
    def __init__(self, logger_name: str = "l8e.audit"):
        self.logger = get_logger(logger_name)
    
    def log_management_action(
        self,
        user: str,
        action: str,
        resource_type: str,
        resource_id: str,
        success: bool,
        client_ip: str,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log management API actions."""
        level = logging.INFO if success else logging.WARNING
        message = f"Management action: {action} {resource_type} {resource_id}"
        
        self.logger.log(
            level,
            message,
            extra={
                "user": user,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "success": success,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "details": details or {},
                "event": "management_action"
            }
        )
    
    def log_login_attempt(
        self,
        username: str,
        success: bool,
        client_ip: str,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """Log login attempts."""
        level = logging.INFO if success else logging.WARNING
        message = f"Login {'successful' if success else 'failed'} for user {username}"
        
        self.logger.log(
            level,
            message,
            extra={
                "username": username,
                "success": success,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "reason": reason,
                "event": "login_attempt"
            }
        )