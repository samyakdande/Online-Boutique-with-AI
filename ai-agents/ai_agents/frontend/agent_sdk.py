"""
Agent SDK for Frontend Integration

This module provides a Python SDK for integrating AI agents with the frontend,
handling communication, state management, and real-time features.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import httpx
import websockets
from websockets.server import WebSocketServerProtocol

from ..core.config import get_settings
from ..a2a.protocol import A2AProtocolHandler

logger = logging.getLogger(__name__)

@dataclass
class AgentResponse:
    """Standard response format from agents"""
    agent_id: str
    response_type: str
    data: Dict[str, Any]
    confidence: float
    timestamp: datetime
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class FrontendRequest:
    """Standard request format from frontend"""
    request_id: str
    request_type: str
    data: Dict[str, Any]
    session_id: str
    user_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class AgentSDK:
    """
    Python SDK for AI Agent Frontend Integration
    
    Provides a unified interface for the frontend to communicate with
    all AI agents, handling routing, state management, and real-time features.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.agents: Dict[str, str] = {}  # agent_id -> endpoint
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: Dict[str, WebSocketServerProtocol] = {}
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Agent endpoints configuration
        self.agent_endpoints = {
            'virtual-tryon': f"http://localhost:{self.settings.virtual_tryon_port}",
            'dynamic-pricing': f"http://localhost:{self.settings.dynamic_pricing_port}",
            'marketing-email': f"http://localhost:{self.settings.marketing_email_port}",
            'ai-chatbot': f"http://localhost:{self.settings.ai_chatbot_port}",
            'recommendation': f"http://localhost:{self.settings.recommendation_port}",
            'review-tracker': f"http://localhost:{self.settings.review_tracker_port}",
            'personal-stylist': f"http://localhost:{self.settings.personal_stylist_port}"
        }
        
        logger.info("Agent SDK initialized")
    
    async def initialize(self):
        """Initialize the SDK and establish connections"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Test agent connectivity
        await self._test_agent_connectivity()
        
        logger.info("Agent SDK initialization completed")
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.http_client:
            await self.http_client.aclose()
        
        # Close websocket connections
        for ws in self.websocket_connections.values():
            await ws.close()
        
        logger.info("Agent SDK shutdown completed")
    
    async def _test_agent_connectivity(self):
        """Test connectivity to all agents"""
        for agent_id, endpoint in self.agent_endpoints.items():
            try:
                response = await self.http_client.get(f"{endpoint}/health")
                if response.status_code == 200:
                    self.agents[agent_id] = endpoint
                    logger.info(f"Agent {agent_id} is available at {endpoint}")
                else:
                    logger.warning(f"Agent {agent_id} health check failed: {response.status_code}")
            except Exception as e:
                logger.warning(f"Agent {agent_id} is not available: {e}")
    
    async def call_agent(
        self, 
        agent_id: str, 
        method: str, 
        data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Call a specific agent method
        
        Args:
            agent_id: ID of the agent to call
            method: Method name to call
            data: Request data
            session_id: Optional session ID for context
            
        Returns:
            AgentResponse: Response from the agent
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} is not available")
        
        endpoint = self.agents[agent_id]
        
        try:
            # Prepare request
            request_data = {
                'method': method,
                'data': data,
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # Make HTTP request to agent
            response = await self.http_client.post(
                f"{endpoint}/api/v1/call",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                return AgentResponse(
                    agent_id=agent_id,
                    response_type=result.get('response_type', 'success'),
                    data=result.get('data', {}),
                    confidence=result.get('confidence', 1.0),
                    timestamp=datetime.now(),
                    session_id=session_id
                )
            else:
                logger.error(f"Agent {agent_id} call failed: {response.status_code}")
                return AgentResponse(
                    agent_id=agent_id,
                    response_type='error',
                    data={'error': f"HTTP {response.status_code}"},
                    confidence=0.0,
                    timestamp=datetime.now(),
                    session_id=session_id
                )
                
        except Exception as e:
            logger.error(f"Error calling agent {agent_id}: {e}")
            return AgentResponse(
                agent_id=agent_id,
                response_type='error',
                data={'error': str(e)},
                confidence=0.0,
                timestamp=datetime.now(),
                session_id=session_id
            )
    
    async def get_product_recommendations(
        self, 
        user_id: str, 
        product_context: Dict[str, Any],
        session_id: str
    ) -> AgentResponse:
        """Get personalized product recommendations"""
        return await self.call_agent(
            'recommendation',
            'get_recommendations',
            {
                'user_id': user_id,
                'context': product_context,
                'limit': 5
            },
            session_id
        )
    
    async def analyze_virtual_tryon(
        self,
        user_image: str,
        product_id: str,
        session_id: str
    ) -> AgentResponse:
        """Analyze virtual try-on for a product"""
        return await self.call_agent(
            'virtual-tryon',
            'analyze_virtual_tryon',
            {
                'user_image_data': user_image,
                'product_id': product_id,
                'analysis_type': 'full_analysis'
            },
            session_id
        )
    
    async def get_dynamic_pricing(
        self,
        product_ids: List[str],
        session_id: str
    ) -> AgentResponse:
        """Get dynamic pricing recommendations"""
        return await self.call_agent(
            'dynamic-pricing',
            'get_price_recommendations',
            {
                'product_ids': product_ids,
                'apply_changes': False
            },
            session_id
        )
    
    async def chat_with_ai(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Chat with AI assistant"""
        return await self.call_agent(
            'ai-chatbot',
            'process_message',
            {
                'message': message,
                'context': context or {},
                'session_id': session_id
            },
            session_id
        )
    
    async def analyze_reviews(
        self,
        product_id: str,
        session_id: str
    ) -> AgentResponse:
        """Get review analysis for a product"""
        return await self.call_agent(
            'review-tracker',
            'get_review_analysis',
            {
                'product_id': product_id,
                'include_sentiment': True,
                'include_themes': True
            },
            session_id
        )
    
    async def get_style_recommendations(
        self,
        user_image: str,
        preferences: Dict[str, Any],
        session_id: str
    ) -> AgentResponse:
        """Get personalized style recommendations"""
        return await self.call_agent(
            'personal-stylist',
            'analyze_style',
            {
                'user_image': user_image,
                'preferences': preferences,
                'analysis_type': 'comprehensive'
            },
            session_id
        )
    
    async def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new session for tracking user interactions"""
        session_id = f"session_{datetime.now().timestamp()}"
        
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'interactions': [],
            'context': {}
        }
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    async def update_session_context(
        self,
        session_id: str,
        context_update: Dict[str, Any]
    ):
        """Update session context with new information"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['context'].update(context_update)
            logger.debug(f"Updated context for session {session_id}")
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get current session context"""
        return self.active_sessions.get(session_id, {}).get('context', {})
    
    async def register_websocket(self, session_id: str, websocket: WebSocketServerProtocol):
        """Register a websocket connection for real-time updates"""
        self.websocket_connections[session_id] = websocket
        logger.info(f"Registered websocket for session {session_id}")
    
    async def send_realtime_update(
        self,
        session_id: str,
        update_type: str,
        data: Dict[str, Any]
    ):
        """Send real-time update to frontend via websocket"""
        if session_id in self.websocket_connections:
            try:
                message = {
                    'type': update_type,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                }
                
                await self.websocket_connections[session_id].send(
                    json.dumps(message)
                )
                
                logger.debug(f"Sent real-time update to session {session_id}")
                
            except Exception as e:
                logger.error(f"Error sending real-time update: {e}")
                # Remove broken connection
                del self.websocket_connections[session_id]
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {
            'available_agents': list(self.agents.keys()),
            'total_agents': len(self.agent_endpoints),
            'active_sessions': len(self.active_sessions),
            'websocket_connections': len(self.websocket_connections),
            'agent_health': {}
        }
        
        # Check agent health
        for agent_id, endpoint in self.agents.items():
            try:
                response = await self.http_client.get(f"{endpoint}/health")
                status['agent_health'][agent_id] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                status['agent_health'][agent_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return status

# Global SDK instance
_sdk_instance: Optional[AgentSDK] = None

async def get_agent_sdk() -> AgentSDK:
    """Get the global Agent SDK instance"""
    global _sdk_instance
    if _sdk_instance is None:
        _sdk_instance = AgentSDK()
        await _sdk_instance.initialize()
    return _sdk_instance