"""
Simple logging configuration for AI-Powered Boutique Agents.

This module provides basic logging with rich console output for development.
"""

import logging
import sys
from typing import Any, Dict

from rich.console import Console
from rich.logging import RichHandler

from ai_agents.core.config import settings


def configure_logging() -> None:
    """Configure logging for the application."""
    
    # Setup rich handler for development
    if settings.is_development():
        console = Console()
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(message)s",
            handlers=[rich_handler]
        )
    else:
        # Production: simple format
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout
        )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def setup_rich_logging() -> None:
    """Setup rich logging handler for development."""
    if not settings.is_development():
        return
        
    console = Console()
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(rich_handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))


class AgentLogger:
    """Specialized logger for AI agents with context management."""
    
    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.logger = get_logger(f"agent.{agent_id}")
        
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context."""
        context = f"[{self.agent_id}:{self.agent_name}]"
        if kwargs:
            context += f" {kwargs}"
        return f"{context} {message}"
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with agent context."""
        self.logger.info(self._format_message(message, **kwargs))
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with agent context."""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with agent context."""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with agent context."""
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with agent context."""
        self.logger.critical(self._format_message(message, **kwargs))


class MCPLogger:
    """Specialized logger for MCP servers."""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.logger = get_logger(f"mcp.{server_name}")
    
    def log_request(self, method: str, params: Dict[str, Any], request_id: str) -> None:
        """Log MCP request."""
        self.logger.info(f"[{self.server_name}] MCP request: {method} (ID: {request_id})")
    
    def log_response(self, request_id: str, success: bool, duration_ms: float) -> None:
        """Log MCP response."""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"[{self.server_name}] MCP response: {status} (ID: {request_id}, {duration_ms:.1f}ms)")
    
    def log_error(self, error: Exception, request_id: str = None) -> None:
        """Log MCP error."""
        self.logger.error(f"[{self.server_name}] MCP error: {error} (ID: {request_id})")


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self):
        self.logger = get_logger("performance")
    
    def log_request_duration(
        self, 
        endpoint: str, 
        method: str, 
        duration_ms: float,
        status_code: int = None
    ) -> None:
        """Log request duration."""
        slow = " (SLOW)" if duration_ms > 1000 else ""
        self.logger.info(f"Request: {method} {endpoint} - {duration_ms:.1f}ms{slow}")
    
    def log_agent_performance(
        self,
        agent_id: str,
        operation: str,
        duration_ms: float,
        success: bool
    ) -> None:
        """Log agent operation performance."""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"Agent {agent_id}: {operation} - {status} ({duration_ms:.1f}ms)")
    
    def log_resource_usage(
        self,
        component: str,
        cpu_percent: float,
        memory_mb: float,
        disk_usage_percent: float = None
    ) -> None:
        """Log resource usage metrics."""
        self.logger.info(f"Resources {component}: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB")


# Initialize logging on module import
configure_logging()
if settings.is_development():
    setup_rich_logging()

# Export commonly used loggers
performance_logger = PerformanceLogger()