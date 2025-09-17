"""
API Gateway for AI Agent Frontend Integration

This module provides a FastAPI-based gateway that exposes AI agent functionality
to the frontend through RESTful APIs and WebSocket connections.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .agent_sdk import get_agent_sdk, AgentSDK, FrontendRequest
from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Request/Response Models
class AgentCallRequest(BaseModel):
    agent_id: str = Field(..., description="ID of the agent to call")
    method: str = Field(..., description="Method to call on the agent")
    data: Dict[str, Any] = Field(default_factory=dict, description="Request data")
    session_id: Optional[str] = Field(None, description="Session ID for context")

class RecommendationRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    product_context: Dict[str, Any] = Field(default_factory=dict, description="Product context")
    session_id: str = Field(..., description="Session ID")

class VirtualTryOnRequest(BaseModel):
    user_image: str = Field(..., description="Base64 encoded user image")
    product_id: str = Field(..., description="Product ID to try on")
    session_id: str = Field(..., description="Session ID")

class DynamicPricingRequest(BaseModel):
    product_ids: List[str] = Field(..., description="List of product IDs")
    session_id: str = Field(..., description="Session ID")

class ChatRequest(BaseModel):
    message: str = Field(..., description="Chat message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class ReviewAnalysisRequest(BaseModel):
    product_id: str = Field(..., description="Product ID")
    session_id: str = Field(..., description="Session ID")

class StyleAnalysisRequest(BaseModel):
    user_image: str = Field(..., description="Base64 encoded user image")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="Style preferences")
    session_id: str = Field(..., description="Session ID")

class SessionCreateRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Optional user ID")

class SessionUpdateRequest(BaseModel):
    context_update: Dict[str, Any] = Field(..., description="Context updates")

# Create FastAPI app
app = FastAPI(
    title="AI Boutique Agent Gateway",
    description="API Gateway for AI-Powered Online Boutique Agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

# Dependency to get SDK
async def get_sdk() -> AgentSDK:
    return await get_agent_sdk()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Agent status endpoint
@app.get("/api/v1/agents/status")
async def get_agents_status(sdk: AgentSDK = Depends(get_sdk)):
    """Get status of all agents"""
    try:
        status = await sdk.get_agent_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Generic agent call endpoint
@app.post("/api/v1/agents/call")
async def call_agent(request: AgentCallRequest, sdk: AgentSDK = Depends(get_sdk)):
    """Generic endpoint to call any agent method"""
    try:
        response = await sdk.call_agent(
            request.agent_id,
            request.method,
            request.data,
            request.session_id
        )
        return JSONResponse(content=response.to_dict())
    except Exception as e:
        logger.error(f"Error calling agent {request.agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Specific agent endpoints
@app.post("/api/v1/recommendations")
async def get_recommendations(request: RecommendationRequest, sdk: AgentSDK = Depends(get_sdk)):
    """Get personalized product recommendations"""
    try:
        response = await sdk.get_product_recommendations(
            request.user_id,
            request.product_context,
            request.session_id
        )
        return JSONResponse(content=response.to_dict())
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/virtual-tryon")
async def virtual_tryon(request: VirtualTryOnRequest, sdk: AgentSDK = Depends(get_sdk)):
    """Analyze virtual try-on for a product"""
    try:
        response = await sdk.analyze_virtual_tryon(
            request.user_image,
            request.product_id,
            request.session_id
        )
        return JSONResponse(content=response.to_dict())
    except Exception as e:
        logger.error(f"Error in virtual try-on: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/pricing")
async def get_dynamic_pricing(request: DynamicPricingRequest, sdk: AgentSDK = Depends(get_sdk)):
    """Get dynamic pricing recommendations"""
    try:
        response = await sdk.get_dynamic_pricing(
            request.product_ids,
            request.session_id
        )
        return JSONResponse(content=response.to_dict())
    except Exception as e:
        logger.error(f"Error getting dynamic pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
async def chat_with_ai(request: ChatRequest, sdk: AgentSDK = Depends(get_sdk)):
    """Chat with AI assistant"""
    try:
        response = await sdk.chat_with_ai(
            request.message,
            request.session_id,
            request.context
        )
        
        # Send real-time update via WebSocket
        await manager.send_personal_message(
            json.dumps({
                "type": "chat_response",
                "data": response.to_dict()
            }),
            request.session_id
        )
        
        return JSONResponse(content=response.to_dict())
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/reviews/analysis")
async def analyze_reviews(request: ReviewAnalysisRequest, sdk: AgentSDK = Depends(get_sdk)):
    """Get review analysis for a product"""
    try:
        response = await sdk.analyze_reviews(
            request.product_id,
            request.session_id
        )
        return JSONResponse(content=response.to_dict())
    except Exception as e:
        logger.error(f"Error analyzing reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/style/analysis")
async def analyze_style(request: StyleAnalysisRequest, sdk: AgentSDK = Depends(get_sdk)):
    """Get personalized style analysis"""
    try:
        response = await sdk.get_style_recommendations(
            request.user_image,
            request.preferences,
            request.session_id
        )
        return JSONResponse(content=response.to_dict())
    except Exception as e:
        logger.error(f"Error in style analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session management endpoints
@app.post("/api/v1/sessions")
async def create_session(request: SessionCreateRequest, sdk: AgentSDK = Depends(get_sdk)):
    """Create a new session"""
    try:
        session_id = await sdk.create_session(request.user_id)
        return JSONResponse(content={"session_id": session_id})
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/sessions/{session_id}")
async def update_session(
    session_id: str, 
    request: SessionUpdateRequest, 
    sdk: AgentSDK = Depends(get_sdk)
):
    """Update session context"""
    try:
        await sdk.update_session_context(session_id, request.context_update)
        return JSONResponse(content={"status": "updated"})
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str, sdk: AgentSDK = Depends(get_sdk)):
    """Get session context"""
    try:
        context = await sdk.get_session_context(session_id)
        return JSONResponse(content={"session_id": session_id, "context": context})
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time features
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, sdk: AgentSDK = Depends(get_sdk)):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket, session_id)
    
    # Register with SDK for real-time updates
    await sdk.register_websocket(session_id, websocket)
    
    try:
        while True:
            # Receive messages from frontend
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
            elif message.get("type") == "chat":
                # Handle real-time chat
                response = await sdk.chat_with_ai(
                    message.get("message", ""),
                    session_id,
                    message.get("context")
                )
                
                await websocket.send_text(json.dumps({
                    "type": "chat_response",
                    "data": response.to_dict()
                }))
            
            elif message.get("type") == "virtual_tryon_stream":
                # Handle real-time virtual try-on updates
                # This would be implemented for streaming video analysis
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(session_id)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the API gateway"""
    logger.info("AI Boutique Agent Gateway starting up...")
    
    # Initialize SDK
    await get_agent_sdk()
    
    logger.info("AI Boutique Agent Gateway startup completed")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("AI Boutique Agent Gateway shutting down...")
    
    # Cleanup SDK
    sdk = await get_agent_sdk()
    await sdk.shutdown()
    
    logger.info("AI Boutique Agent Gateway shutdown completed")

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "ai_agents.frontend.api_gateway:app",
        host="0.0.0.0",
        port=settings.api_gateway_port,
        reload=True,
        log_level="info"
    )