"""
Base MCP Server implementation.

This module provides the base classes and utilities for implementing
Model Context Protocol servers.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

from ai_agents.core.config import settings
from ai_agents.core.logging import MCPLogger


class MCPRequest(BaseModel):
    """MCP request model."""
    method: str = Field(..., description="MCP method name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    id: str = Field(..., description="Request ID")


class MCPResponse(BaseModel):
    """MCP response model."""
    result: Optional[Any] = Field(None, description="Method result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information")
    id: str = Field(..., description="Request ID")


class MCPError(BaseModel):
    """MCP error model."""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")


@dataclass
class MCPMethod:
    """MCP method definition."""
    name: str
    description: str
    params_schema: Dict[str, Any]
    result_schema: Dict[str, Any]
    handler: callable


class BaseMCPServer(ABC):
    """Base class for MCP servers."""
    
    def __init__(self, name: str, port: int, description: str = ""):
        self.name = name
        self.port = port
        self.description = description
        self.logger = MCPLogger(name)
        
        # FastAPI app
        self.app = FastAPI(
            title=f"{name} MCP Server",
            description=description,
            version="1.0.0"
        )
        
        # Method registry
        self.methods: Dict[str, MCPMethod] = {}
        
        # Setup routes
        self._setup_routes()
        
        # Performance tracking
        self._request_count = 0
        self._error_count = 0
        self._total_duration = 0.0
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "server": self.name,
                "methods": list(self.methods.keys()),
                "stats": {
                    "requests": self._request_count,
                    "errors": self._error_count,
                    "avg_duration_ms": self._total_duration / max(self._request_count, 1) * 1000
                }
            }
        
        @self.app.get("/methods")
        async def list_methods():
            """List available MCP methods."""
            return {
                "methods": [
                    {
                        "name": method.name,
                        "description": method.description,
                        "params_schema": method.params_schema,
                        "result_schema": method.result_schema
                    }
                    for method in self.methods.values()
                ]
            }
        
        @self.app.post("/mcp")
        async def handle_mcp_request(request: MCPRequest):
            """Handle MCP requests."""
            start_time = time.time()
            self._request_count += 1
            
            try:
                self.logger.log_request(request.method, request.params, request.id)
                
                # Find method handler
                if request.method not in self.methods:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown method: {request.method}"
                    )
                
                method = self.methods[request.method]
                
                # Validate parameters (basic validation)
                # In a full implementation, you'd use JSON Schema validation
                
                # Call handler
                result = await method.handler(request.params)
                
                duration = time.time() - start_time
                self._total_duration += duration
                
                self.logger.log_response(request.id, True, duration * 1000)
                
                return MCPResponse(result=result, id=request.id)
                
            except Exception as e:
                duration = time.time() - start_time
                self._total_duration += duration
                self._error_count += 1
                
                self.logger.log_error(e, request.id)
                
                error = MCPError(
                    code=500,
                    message=str(e),
                    data={"type": type(e).__name__}
                )
                
                return MCPResponse(error=error.dict(), id=request.id)
    
    def register_method(
        self,
        name: str,
        handler: callable,
        description: str = "",
        params_schema: Dict[str, Any] = None,
        result_schema: Dict[str, Any] = None
    ):
        """Register an MCP method."""
        method = MCPMethod(
            name=name,
            description=description,
            params_schema=params_schema or {},
            result_schema=result_schema or {},
            handler=handler
        )
        
        self.methods[name] = method
        self.logger.logger.info(f"Registered MCP method: {name}")
    
    @abstractmethod
    async def initialize(self):
        """Initialize the MCP server."""
        pass
    
    async def start(self):
        """Start the MCP server."""
        self.logger.logger.info(f"Starting {self.name} MCP server on port {self.port}")
        
        # Initialize server
        await self.initialize()
        
        # Start FastAPI server
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level=settings.log_level.lower()
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Stop the MCP server."""
        self.logger.logger.info(f"Stopping {self.name} MCP server")


class MCPClient:
    """Client for making requests to MCP servers."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.logger = MCPLogger("mcp_client")
    
    async def call_method(
        self,
        method: str,
        params: Dict[str, Any] = None,
        request_id: str = None
    ) -> Any:
        """Call an MCP method."""
        import httpx
        
        if request_id is None:
            request_id = f"req_{int(time.time() * 1000)}"
        
        request = MCPRequest(
            method=method,
            params=params or {},
            id=request_id
        )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    json=request.dict(),
                    timeout=30.0
                )
                response.raise_for_status()
                
                mcp_response = MCPResponse(**response.json())
                
                if mcp_response.error:
                    raise Exception(f"MCP Error: {mcp_response.error}")
                
                return mcp_response.result
                
        except Exception as e:
            self.logger.log_error(e, request_id)
            raise
    
    async def get_methods(self) -> List[Dict[str, Any]]:
        """Get available methods from the MCP server."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/methods")
                response.raise_for_status()
                return response.json()["methods"]
        except Exception as e:
            self.logger.log_error(e)
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check server health."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            self.logger.log_error(e)
            raise