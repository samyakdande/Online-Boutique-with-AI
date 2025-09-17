"""
A2A Protocol WebSocket Gateway

This service provides a WebSocket gateway for frontend clients to communicate
with AI agents through the A2A protocol.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Set, Optional, Any
import websockets
from websockets.server import WebSocketServerProtocol
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class A2AWebSocketGateway:
    """WebSocket gateway for A2A protocol communication"""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.agent_endpoints = {
            'virtual-tryon': 'http://virtual-tryon-agent:8000',
            'dynamic-pricing': 'http://dynamic-pricing-agent:8000',
            'ai-chatbot': 'http://ai-chatbot-agent:8000',
            'recommendation': 'http://recommendation-agent:8000',
            'marketing-email': 'http://marketing-email-agent:8000',
            'review-tracker': 'http://review-tracker-agent:8000',
            'personal-stylist': 'http://personal-stylist-agent:8000'
        }
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def start(self):
        """Start the WebSocket gateway server"""
        logger.info(f"Starting A2A WebSocket Gateway on port {self.port}")
        
        async with websockets.serve(
            self.handle_client,
            "0.0.0.0",
            self.port,
            ping_interval=20,
            ping_timeout=10
        ):
            logger.info(f"A2A Gateway listening on ws://0.0.0.0:{self.port}")
            await asyncio.Future()  # Run forever
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket client connection"""
        self.clients.add(websocket)
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_id}")
        
        try:
            await self.send_message(websocket, {
                'type': 'connection_established',
                'data': {
                    'client_id': client_id,
                    'timestamp': datetime.now().isoformat(),
                    'available_agents': list(self.agent_endpoints.keys())
                }
            })
            
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            self.clients.discard(websocket)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            request_id = data.get('requestId')
            message_type = data.get('type')
            payload = data.get('data', {})
            
            logger.info(f"Received message: {message_type} (ID: {request_id})")
            
            # Route message to appropriate handler
            response = await self.route_message(message_type, payload)
            
            # Send response back to client
            await self.send_message(websocket, {
                'requestId': request_id,
                'type': f"{message_type}_response",
                'data': response,
                'timestamp': datetime.now().isoformat()
            })
            
        except json.JSONDecodeError:
            await self.send_error(websocket, "Invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(websocket, str(e))
    
    async def route_message(self, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Route message to appropriate AI agent"""
        
        # Virtual Try-On messages
        if message_type == 'virtual_tryon_start':
            return await self.call_agent('virtual-tryon', 'start_tryon', payload)
        elif message_type == 'virtual_tryon_analyze':
            return await self.call_agent('virtual-tryon', 'analyze', payload)
        
        # Dynamic Pricing messages
        elif message_type == 'subscribe_price_updates':
            return await self.call_agent('dynamic-pricing', 'subscribe', payload)
        elif message_type == 'get_price_recommendations':
            return await self.call_agent('dynamic-pricing', 'recommendations', payload)
        
        # Chatbot messages
        elif message_type == 'chat_message':
            return await self.call_agent('ai-chatbot', 'chat', payload)
        elif message_type == 'voice_chat_start':
            return await self.call_agent('ai-chatbot', 'voice_start', payload)
        
        # Recommendation messages
        elif message_type == 'get_recommendations':
            return await self.call_agent('recommendation', 'get_recommendations', payload)
        
        # Style analysis messages
        elif message_type == 'analyze_style':
            return await self.call_agent('personal-stylist', 'analyze', payload)
        
        # Health check
        elif message_type == 'health_check':
            return await self.health_check()
        
        else:
            raise ValueError(f"Unknown message type: {message_type}")
    
    async def call_agent(self, agent_name: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call an AI agent via HTTP"""
        if agent_name not in self.agent_endpoints:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        agent_url = self.agent_endpoints[agent_name]
        url = f"{agent_url}/api/{endpoint}"
        
        try:
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Request to {agent_name} failed: {e}")
            return {
                'error': f"Agent {agent_name} is unavailable",
                'details': str(e)
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {agent_name}: {e}")
            return {
                'error': f"Agent {agent_name} returned error {e.response.status_code}",
                'details': e.response.text
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all agents"""
        health_status = {}
        
        for agent_name, agent_url in self.agent_endpoints.items():
            try:
                response = await self.http_client.get(f"{agent_url}/health", timeout=5.0)
                health_status[agent_name] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_time': response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                health_status[agent_name] = {
                    'status': 'unavailable',
                    'error': str(e)
                }
        
        return {
            'gateway_status': 'healthy',
            'connected_clients': len(self.clients),
            'agents': health_status,
            'timestamp': datetime.now().isoformat()
        }
    
    async def send_message(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Attempted to send message to closed connection")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def send_error(self, websocket: WebSocketServerProtocol, error_message: str):
        """Send error message to WebSocket client"""
        await self.send_message(websocket, {
            'type': 'error',
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        })
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
        
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await self.send_message(client, message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected_clients
    
    async def shutdown(self):
        """Shutdown the gateway"""
        logger.info("Shutting down A2A Gateway")
        await self.http_client.aclose()

# Health check endpoint for Docker
async def health_endpoint(request):
    """Simple health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'a2a-gateway',
        'timestamp': datetime.now().isoformat()
    }

async def main():
    """Main entry point"""
    port = int(os.getenv('WEBSOCKET_PORT', 9090))
    gateway = A2AWebSocketGateway(port)
    
    try:
        await gateway.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await gateway.shutdown()

if __name__ == "__main__":
    asyncio.run(main())