"""
A2A Protocol Handler

This module implements the Agent-to-Agent protocol for inter-agent communication,
service discovery, and message routing in the AI-Powered Online Boutique system.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol

from ai_agents.core.config import settings
from ai_agents.core.logging import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """A2A message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    DISCOVERY = "discovery"
    ERROR = "error"
    WORKFLOW = "workflow"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentStatus(Enum):
    """Agent status in the A2A network."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class A2AMessage:
    """A2A protocol message structure."""
    
    def __init__(
        self,
        message_type: MessageType,
        from_agent: str,
        to_agent: str = None,
        payload: Dict[str, Any] = None,
        priority: MessagePriority = MessagePriority.MEDIUM,
        correlation_id: str = None,
        workflow_id: str = None
    ):
        self.id = str(uuid.uuid4())
        self.message_type = message_type
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.payload = payload or {}
        self.priority = priority
        self.correlation_id = correlation_id
        self.workflow_id = workflow_id
        self.timestamp = datetime.now().isoformat()
        self.ttl = 300  # 5 minutes default TTL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "type": self.message_type.value,
            "from": self.from_agent,
            "to": self.to_agent,
            "payload": self.payload,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp,
            "ttl": self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """Create message from dictionary."""
        msg = cls(
            message_type=MessageType(data["type"]),
            from_agent=data["from"],
            to_agent=data.get("to"),
            payload=data.get("payload", {}),
            priority=MessagePriority(data.get("priority", "medium")),
            correlation_id=data.get("correlation_id"),
            workflow_id=data.get("workflow_id")
        )
        msg.id = data["id"]
        msg.timestamp = data["timestamp"]
        msg.ttl = data.get("ttl", 300)
        return msg


class AgentInfo:
    """Information about an agent in the A2A network."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        capabilities: List[str],
        endpoint: str,
        status: AgentStatus = AgentStatus.ONLINE
    ):
        self.agent_id = agent_id
        self.name = name
        self.capabilities = capabilities
        self.endpoint = endpoint
        self.status = status
        self.last_heartbeat = datetime.now()
        self.message_count = 0
        self.error_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent info to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": self.capabilities,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "message_count": self.message_count,
            "error_count": self.error_count
        }


class A2AProtocolHandler:
    """A2A Protocol Handler for inter-agent communication."""
    
    def __init__(self, agent_id: str, agent_name: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.capabilities = capabilities
        
        # Network configuration
        self.host = "0.0.0.0"
        self.port = settings.a2a_protocol_port
        
        # Agent registry
        self.agents: Dict[str, AgentInfo] = {}
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        
        # Message handling
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Workflow management
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Server and client
        self.server = None
        self.client_connections: Dict[str, WebSocketClientProtocol] = {}
        
        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "uptime_start": datetime.now()
        }
    
    async def start(self):
        """Start the A2A protocol handler."""
        logger.info(f"Starting A2A protocol handler for {self.agent_id}")
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port
        )
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._message_processor())
        asyncio.create_task(self._cleanup_loop())
        
        # Register self in the network
        await self._register_agent()
        
        logger.info(f"A2A protocol handler started on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the A2A protocol handler."""
        logger.info("Stopping A2A protocol handler")
        
        # Close all client connections
        for connection in self.client_connections.values():
            await connection.close()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("A2A protocol handler stopped")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connections."""
        client_id = f"client_{id(websocket)}"
        logger.info(f"New A2A connection: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    a2a_message = A2AMessage.from_dict(data)
                    
                    # Update connection mapping
                    if a2a_message.from_agent not in self.connections:
                        self.connections[a2a_message.from_agent] = websocket
                    
                    # Process message
                    await self._process_incoming_message(a2a_message)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in A2A message: {e}")
                    await self._send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Error processing A2A message: {e}")
                    await self._send_error(websocket, str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"A2A connection closed: {client_id}")
        except Exception as e:
            logger.error(f"A2A connection error: {e}")
        finally:
            # Clean up connection
            for agent_id, conn in list(self.connections.items()):
                if conn == websocket:
                    del self.connections[agent_id]
                    break
    
    async def _process_incoming_message(self, message: A2AMessage):
        """Process incoming A2A message."""
        self.stats["messages_received"] += 1
        
        logger.debug(f"Processing A2A message: {message.message_type.value} from {message.from_agent}")
        
        try:
            if message.message_type == MessageType.DISCOVERY:
                await self._handle_discovery(message)
            elif message.message_type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(message)
            elif message.message_type == MessageType.REQUEST:
                await self._handle_request(message)
            elif message.message_type == MessageType.RESPONSE:
                await self._handle_response(message)
            elif message.message_type == MessageType.NOTIFICATION:
                await self._handle_notification(message)
            elif message.message_type == MessageType.WORKFLOW:
                await self._handle_workflow(message)
            else:
                logger.warning(f"Unknown message type: {message.message_type}")
        
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            self.stats["errors"] += 1
    
    async def _handle_discovery(self, message: A2AMessage):
        """Handle agent discovery messages."""
        if message.payload.get("action") == "register":
            # Register new agent
            agent_info = AgentInfo(
                agent_id=message.from_agent,
                name=message.payload.get("name", message.from_agent),
                capabilities=message.payload.get("capabilities", []),
                endpoint=message.payload.get("endpoint", "")
            )
            self.agents[message.from_agent] = agent_info
            logger.info(f"Registered agent: {message.from_agent}")
            
            # Send acknowledgment
            response = A2AMessage(
                message_type=MessageType.RESPONSE,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                payload={"status": "registered", "agents": list(self.agents.keys())},
                correlation_id=message.id
            )
            await self._send_message(response)
        
        elif message.payload.get("action") == "query":
            # Send agent list
            agents_info = {
                agent_id: info.to_dict() 
                for agent_id, info in self.agents.items()
            }
            response = A2AMessage(
                message_type=MessageType.RESPONSE,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                payload={"agents": agents_info},
                correlation_id=message.id
            )
            await self._send_message(response)
    
    async def _handle_heartbeat(self, message: A2AMessage):
        """Handle heartbeat messages."""
        if message.from_agent in self.agents:
            self.agents[message.from_agent].last_heartbeat = datetime.now()
            self.agents[message.from_agent].status = AgentStatus.ONLINE
    
    async def _handle_request(self, message: A2AMessage):
        """Handle request messages."""
        # Check if we have a handler for this request
        request_type = message.payload.get("type")
        if request_type in self.message_handlers:
            try:
                # Call the handler
                result = await self.message_handlers[request_type](message.payload)
                
                # Send response
                response = A2AMessage(
                    message_type=MessageType.RESPONSE,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    payload={"result": result, "status": "success"},
                    correlation_id=message.id
                )
                await self._send_message(response)
                
            except Exception as e:
                # Send error response
                error_response = A2AMessage(
                    message_type=MessageType.ERROR,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    payload={"error": str(e), "status": "error"},
                    correlation_id=message.id
                )
                await self._send_message(error_response)
        else:
            # No handler found
            error_response = A2AMessage(
                message_type=MessageType.ERROR,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                payload={"error": f"No handler for request type: {request_type}"},
                correlation_id=message.id
            )
            await self._send_message(error_response)
    
    async def _handle_response(self, message: A2AMessage):
        """Handle response messages."""
        if message.correlation_id in self.pending_requests:
            future = self.pending_requests.pop(message.correlation_id)
            if not future.done():
                future.set_result(message)
    
    async def _handle_notification(self, message: A2AMessage):
        """Handle notification messages."""
        # Notifications are fire-and-forget
        notification_type = message.payload.get("type")
        if notification_type in self.message_handlers:
            try:
                await self.message_handlers[notification_type](message.payload)
            except Exception as e:
                logger.error(f"Error handling notification {notification_type}: {e}")
    
    async def _handle_workflow(self, message: A2AMessage):
        """Handle workflow orchestration messages."""
        workflow_id = message.workflow_id
        action = message.payload.get("action")
        
        if action == "start":
            # Start new workflow
            self.active_workflows[workflow_id] = {
                "id": workflow_id,
                "initiator": message.from_agent,
                "steps": message.payload.get("steps", []),
                "current_step": 0,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "context": message.payload.get("context", {})
            }
            logger.info(f"Started workflow: {workflow_id}")
            
        elif action == "step_complete":
            # Mark workflow step as complete
            if workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
                workflow["current_step"] += 1
                
                if workflow["current_step"] >= len(workflow["steps"]):
                    workflow["status"] = "completed"
                    workflow["end_time"] = datetime.now().isoformat()
                    logger.info(f"Completed workflow: {workflow_id}")
    
    async def send_request(
        self, 
        to_agent: str, 
        request_type: str, 
        payload: Dict[str, Any],
        timeout: float = 30.0
    ) -> A2AMessage:
        """Send a request to another agent and wait for response."""
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent=self.agent_id,
            to_agent=to_agent,
            payload={"type": request_type, **payload},
            priority=MessagePriority.MEDIUM
        )
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[message.id] = future
        
        try:
            # Send message
            await self._send_message(message)
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            # Clean up pending request
            self.pending_requests.pop(message.id, None)
            raise
    
    async def send_notification(
        self, 
        to_agent: str, 
        notification_type: str, 
        payload: Dict[str, Any]
    ):
        """Send a notification to another agent."""
        message = A2AMessage(
            message_type=MessageType.NOTIFICATION,
            from_agent=self.agent_id,
            to_agent=to_agent,
            payload={"type": notification_type, **payload},
            priority=MessagePriority.LOW
        )
        
        await self._send_message(message)
    
    async def broadcast_notification(
        self, 
        notification_type: str, 
        payload: Dict[str, Any]
    ):
        """Broadcast a notification to all agents."""
        for agent_id in self.agents:
            if agent_id != self.agent_id:
                await self.send_notification(agent_id, notification_type, payload)
    
    async def start_workflow(
        self, 
        workflow_id: str, 
        steps: List[Dict[str, Any]], 
        context: Dict[str, Any] = None
    ):
        """Start a multi-agent workflow."""
        message = A2AMessage(
            message_type=MessageType.WORKFLOW,
            from_agent=self.agent_id,
            payload={
                "action": "start",
                "steps": steps,
                "context": context or {}
            },
            workflow_id=workflow_id
        )
        
        # Broadcast to all agents
        for agent_id in self.agents:
            if agent_id != self.agent_id:
                message.to_agent = agent_id
                await self._send_message(message)
    
    async def _send_message(self, message: A2AMessage):
        """Send A2A message to target agent."""
        self.stats["messages_sent"] += 1
        
        try:
            if message.to_agent in self.connections:
                # Direct connection available
                websocket = self.connections[message.to_agent]
                await websocket.send(json.dumps(message.to_dict()))
            else:
                # Queue message for later delivery
                await self.message_queue.put(message)
                
        except Exception as e:
            logger.error(f"Failed to send message to {message.to_agent}: {e}")
            self.stats["errors"] += 1
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_message: str):
        """Send error message through WebSocket."""
        error_msg = A2AMessage(
            message_type=MessageType.ERROR,
            from_agent=self.agent_id,
            payload={"error": error_message}
        )
        
        try:
            await websocket.send(json.dumps(error_msg.to_dict()))
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    async def _register_agent(self):
        """Register this agent in the A2A network."""
        registration_message = A2AMessage(
            message_type=MessageType.DISCOVERY,
            from_agent=self.agent_id,
            payload={
                "action": "register",
                "name": self.agent_name,
                "capabilities": self.capabilities,
                "endpoint": f"ws://localhost:{self.port}"
            }
        )
        
        # Add self to registry
        self.agents[self.agent_id] = AgentInfo(
            agent_id=self.agent_id,
            name=self.agent_name,
            capabilities=self.capabilities,
            endpoint=f"ws://localhost:{self.port}"
        )
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while True:
            try:
                heartbeat = A2AMessage(
                    message_type=MessageType.HEARTBEAT,
                    from_agent=self.agent_id,
                    payload={
                        "status": "online",
                        "timestamp": datetime.now().isoformat(),
                        "stats": self.stats
                    }
                )
                
                # Broadcast heartbeat
                for agent_id in self.agents:
                    if agent_id != self.agent_id:
                        heartbeat.to_agent = agent_id
                        await self._send_message(heartbeat)
                
                await asyncio.sleep(settings.a2a_heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def _message_processor(self):
        """Process queued messages."""
        while True:
            try:
                message = await self.message_queue.get()
                
                # Try to deliver queued message
                if message.to_agent in self.connections:
                    websocket = self.connections[message.to_agent]
                    await websocket.send(json.dumps(message.to_dict()))
                else:
                    # Check if message has expired
                    message_time = datetime.fromisoformat(message.timestamp)
                    if datetime.now() - message_time > timedelta(seconds=message.ttl):
                        logger.warning(f"Message {message.id} expired")
                    else:
                        # Re-queue for later
                        await asyncio.sleep(1)
                        await self.message_queue.put(message)
                
            except Exception as e:
                logger.error(f"Message processor error: {e}")
                await asyncio.sleep(1)
    
    async def _cleanup_loop(self):
        """Clean up expired data."""
        while True:
            try:
                current_time = datetime.now()
                
                # Clean up offline agents
                offline_agents = []
                for agent_id, agent_info in self.agents.items():
                    if agent_id != self.agent_id:
                        time_since_heartbeat = current_time - agent_info.last_heartbeat
                        if time_since_heartbeat > timedelta(seconds=settings.a2a_timeout):
                            agent_info.status = AgentStatus.OFFLINE
                            offline_agents.append(agent_id)
                
                # Remove offline agents after extended period
                for agent_id in offline_agents:
                    time_since_heartbeat = current_time - self.agents[agent_id].last_heartbeat
                    if time_since_heartbeat > timedelta(seconds=settings.a2a_timeout * 3):
                        del self.agents[agent_id]
                        self.connections.pop(agent_id, None)
                        logger.info(f"Removed offline agent: {agent_id}")
                
                # Clean up expired pending requests
                expired_requests = []
                for request_id, future in self.pending_requests.items():
                    if future.done():
                        expired_requests.append(request_id)
                
                for request_id in expired_requests:
                    del self.pending_requests[request_id]
                
                await asyncio.sleep(60)  # Run cleanup every minute
                
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(60)
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler."""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered A2A handler: {message_type}")
    
    def get_agents(self) -> Dict[str, AgentInfo]:
        """Get all registered agents."""
        return self.agents.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get A2A protocol statistics."""
        uptime = datetime.now() - self.stats["uptime_start"]
        return {
            **self.stats,
            "uptime_seconds": uptime.total_seconds(),
            "connected_agents": len(self.connections),
            "registered_agents": len(self.agents),
            "pending_requests": len(self.pending_requests),
            "active_workflows": len(self.active_workflows)
        }