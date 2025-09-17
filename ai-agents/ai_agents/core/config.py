"""
Configuration management for AI-Powered Boutique Agents.

This module handles all configuration settings using Pydantic Settings,
supporting environment variables, .env files, and validation.
"""

import os
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GeminiConfig(BaseSettings):
    """Gemini AI configuration."""
    
    api_key: str = Field(..., description="Gemini API key")
    project_id: str = Field(..., description="Google Cloud project ID")
    model_pro: str = Field(default="gemini-pro", description="Gemini Pro model name")
    model_vision: str = Field(default="gemini-pro-vision", description="Gemini Vision model name")
    model_code: str = Field(default="gemini-pro", description="Gemini Code model name")
    
    # Request configuration
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.8, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1, le=100)
    max_output_tokens: int = Field(default=2048, ge=1, le=8192)
    timeout: int = Field(default=30, ge=1, le=300)

    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        protected_namespaces=('settings_',)
    )


class KubernetesConfig(BaseSettings):
    """Kubernetes and kubectl-ai configuration."""
    
    cluster_name: str = Field(default="ai-boutique-cluster")
    namespace: str = Field(default="ai-agents")
    region: str = Field(default="us-central1")
    kubectl_ai_enabled: bool = Field(default=True)
    
    # Resource defaults
    default_cpu: str = Field(default="100m")
    default_memory: str = Field(default="128Mi")
    max_cpu: str = Field(default="2")
    max_memory: str = Field(default="4Gi")

    model_config = SettingsConfigDict(env_prefix="K8S_")


class MCPConfig(BaseSettings):
    """Model Context Protocol configuration."""
    
    enabled: bool = Field(default=True)
    boutique_api_port: int = Field(default=8080, ge=1024, le=65535)
    analytics_port: int = Field(default=8081, ge=1024, le=65535)
    ml_models_port: int = Field(default=8082, ge=1024, le=65535)
    
    # Health check configuration
    health_check_path: str = Field(default="/health")
    health_check_interval: int = Field(default=30, ge=5, le=300)

    model_config = SettingsConfigDict(env_prefix="MCP_")


class A2AConfig(BaseSettings):
    """Agent-to-Agent protocol configuration."""
    
    enabled: bool = Field(default=True)
    protocol: str = Field(default="websocket", pattern="^(websocket|mqtt|grpc)$")
    port: int = Field(default=9090, ge=1024, le=65535)
    heartbeat_interval: int = Field(default=10, ge=1, le=60)
    timeout: int = Field(default=30, ge=5, le=120)
    discovery_enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="A2A_")


class DevelopmentConfig(BaseSettings):
    """Development and hot-reload configuration."""
    
    hot_reload_enabled: bool = Field(default=True)
    watch_paths: List[str] = Field(default_factory=lambda: [
        "ai_agents/agents",
        "ai_agents/mcp_servers", 
        "ai_agents/shared"
    ])
    exclude_patterns: List[str] = Field(default_factory=lambda: [
        "**/__pycache__/**",
        "**/*.pyc",
        "**/.pytest_cache/**",
        "**/test_*.py",
        "**/*_test.py"
    ])
    debounce_seconds: float = Field(default=1.0, ge=0.1, le=10.0)

    model_config = SettingsConfigDict(env_prefix="DEV_")


class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    jwt_secret: str = Field(..., min_length=32, description="JWT secret key")
    jwt_expires_in: str = Field(default="1h")
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, ge=1, le=10000)
    rate_limit_window_minutes: int = Field(default=15, ge=1, le=60)

    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class PerformanceConfig(BaseSettings):
    """Performance and caching configuration."""
    
    # Caching
    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=300, ge=1, le=3600)
    cache_max_size: str = Field(default="100MB")
    
    # Connection pooling
    max_concurrent_requests: int = Field(default=100, ge=1, le=1000)
    connection_timeout: int = Field(default=30, ge=1, le=300)
    idle_timeout: int = Field(default=30, ge=1, le=300)

    model_config = SettingsConfigDict(env_prefix="PERF_")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    environment: str = Field(default="development", pattern="^(development|test|staging|production)$")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    # Google Cloud
    google_cloud_project: str = Field(..., description="Google Cloud project ID")
    google_cloud_region: str = Field(default="us-central1")
    
    # Online Boutique integration
    boutique_frontend_url: str = Field(default="http://frontend:80")
    boutique_api_gateway: str = Field(default="http://api-gateway:8080")
    
    # Gemini configuration (flattened)
    gemini_api_key: str = Field(..., description="Gemini API key")
    gemini_project_id: str = Field(..., description="Google Cloud project ID for Gemini")
    gemini_model_pro: str = Field(default="gemini-pro")
    gemini_model_vision: str = Field(default="gemini-pro-vision")
    gemini_model_code: str = Field(default="gemini-pro")
    gemini_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    gemini_top_p: float = Field(default=0.8, ge=0.0, le=1.0)
    gemini_top_k: int = Field(default=40, ge=1, le=100)
    gemini_max_output_tokens: int = Field(default=2048, ge=1, le=8192)
    gemini_timeout: int = Field(default=30, ge=1, le=300)
    
    # Kubernetes configuration (flattened)
    k8s_cluster_name: str = Field(default="ai-boutique-cluster")
    k8s_namespace: str = Field(default="ai-agents")
    k8s_region: str = Field(default="us-central1")
    k8s_kubectl_ai_enabled: bool = Field(default=True)
    
    # MCP configuration (flattened)
    mcp_enabled: bool = Field(default=True)
    mcp_boutique_api_port: int = Field(default=8080, ge=1024, le=65535)
    mcp_analytics_port: int = Field(default=8081, ge=1024, le=65535)
    mcp_ml_models_port: int = Field(default=8082, ge=1024, le=65535)
    
    # A2A configuration (flattened)
    a2a_enabled: bool = Field(default=True)
    a2a_protocol: str = Field(default="websocket", pattern="^(websocket|mqtt|grpc)$")
    a2a_protocol_port: int = Field(default=9090, ge=1024, le=65535)
    a2a_heartbeat_interval: int = Field(default=10, ge=1, le=60)
    a2a_timeout: int = Field(default=30, ge=5, le=120)
    a2a_discovery_enabled: bool = Field(default=True)
    
    # Development configuration (flattened)
    dev_hot_reload_enabled: bool = Field(default=True)
    dev_debounce_seconds: float = Field(default=1.0, ge=0.1, le=10.0)
    
    # Security configuration (flattened)
    security_jwt_secret: str = Field(..., min_length=32, description="JWT secret key")
    security_jwt_expires_in: str = Field(default="1h")
    security_cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    
    # Performance configuration (flattened)
    perf_cache_enabled: bool = Field(default=True)
    perf_cache_ttl_seconds: int = Field(default=300, ge=1, le=3600)
    perf_max_concurrent_requests: int = Field(default=100, ge=1, le=1000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be development, staging, or production")
        return v

    @validator("debug")
    def set_debug_from_environment(cls, v, values):
        """Set debug mode based on environment."""
        if values.get("environment") == "development":
            return True
        return v

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings

# Agent-specific configurations
AGENT_CONFIGS = {
    "personal_stylist": {
        "id": "personal-stylist",
        "name": "Personal Stylist Agent",
        "version": "1.0.0",
        "capabilities": ["style-analysis", "outfit-recommendation", "trend-prediction"],
        "dependencies": ["boutique-api", "analytics"],
        "resources": {
            "cpu": "200m",
            "memory": "256Mi",
            "storage": "1Gi"
        },
        "hot_reload": True
    },
    "inventory_optimizer": {
        "id": "inventory-optimizer", 
        "name": "Inventory Optimizer Agent",
        "version": "1.0.0",
        "capabilities": ["demand-forecasting", "stock-optimization", "supplier-management"],
        "dependencies": ["boutique-api", "analytics", "ml-models"],
        "resources": {
            "cpu": "500m",
            "memory": "512Mi", 
            "storage": "2Gi"
        },
        "hot_reload": True
    },
    "customer_insights": {
        "id": "customer-insights",
        "name": "Customer Insights Agent", 
        "version": "1.0.0",
        "capabilities": ["behavior-analysis", "segmentation", "churn-prediction"],
        "dependencies": ["boutique-api", "analytics"],
        "resources": {
            "cpu": "300m",
            "memory": "384Mi",
            "storage": "1Gi"
        },
        "hot_reload": True
    }
}