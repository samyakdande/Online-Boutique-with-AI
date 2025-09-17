"""
Agent Communication Framework

This module provides standardized agent interfaces, message serialization,
security, and authentication for the A2A protocol.
"""

import asyncio
import json
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from ai_agents.core.config import settings
from ai_agents.core.logging import get_logger
from ai_agents.a2a.protocol import A2AMessage, MessageType, MessagePriority, A2AProtocolHandler

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security levels for agent communication."""
    NONE = "none"
    BASIC = "basic"
    ENCRYPTED = "encrypted"
    AUTHENTICATED = "authenticated"


class MessageFormat(Enum):
    """Message serialization formats."""
    JSON = "json"
    MSGPACK = "msgpack"
    PROTOBUF = "protobuf"


@dataclass
class AgentCredentials:
    """Agent authentication credentials."""
    agent_id: str
    secret_key: str
    permissions: List[str]
    expires_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Check if credentials are valid."""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return bool(self.agent_id and self.secret_key)


@dataclass
class MessageEnvelope:
    """Secure message envelope with metadata."""
    message: A2AMessage
    signature: Optional[str] = None
    encryption_key: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.BASIC
    format: MessageFormat = MessageFormat.JSON
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message": self.message.to_dict(),
            "signature": self.signature,
            "encryption_key": self.encryption_key,
            "security_level": self.security_level.value,
            "format": self.format.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageEnvelope':
        """Create from dictionary."""
        return cls(
            message=A2AMessage.from_dict(data["message"]),
            signature=data.get("signature"),
            encryption_key=data.get("encryption_key"),
            security_level=SecurityLevel(data.get("security_level", "basic")),
            format=MessageFormat(data.get("format", "json"))
        )


class MessageSerializer:
    """Handles message serialization and deserialization."""
    
    @staticmethod
    def serialize(message: A2AMessage, format: MessageFormat = MessageFormat.JSON) -> bytes:
        """Serialize message to bytes."""
        data = message.to_dict()
        
        if format == MessageFormat.JSON:
            return json.dumps(data).encode('utf-8')
        elif format == MessageFormat.MSGPACK:
            try:
                import msgpack
                return msgpack.packb(data)
            except ImportError:
                logger.warning("msgpack not available, falling back to JSON")
                return json.dumps(data).encode('utf-8')
        else:
            # Default to JSON
            return json.dumps(data).encode('utf-8')
    
    @staticmethod
    def deserialize(data: bytes, format: MessageFormat = MessageFormat.JSON) -> A2AMessage:
        """Deserialize bytes to message."""
        if format == MessageFormat.JSON:
            message_dict = json.loads(data.decode('utf-8'))
        elif format == MessageFormat.MSGPACK:
            try:
                import msgpack
                message_dict = msgpack.unpackb(data, raw=False)
            except ImportError:
                logger.warning("msgpack not available, trying JSON")
                message_dict = json.loads(data.decode('utf-8'))
        else:
            message_dict = json.loads(data.decode('utf-8'))
        
        return A2AMessage.from_dict(message_dict)


class SecurityManager:
    """Manages security for agent communication."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.credentials: Dict[str, AgentCredentials] = {}
        self.jwt_secret = settings.security_jwt_secret
        self.default_security_level = SecurityLevel.BASIC
        
        if not JWT_AVAILABLE:
            logger.warning("PyJWT not available, JWT functionality disabled")
    
    def register_agent_credentials(self, credentials: AgentCredentials):
        """Register agent credentials."""
        self.credentials[credentials.agent_id] = credentials
        logger.info(f"Registered credentials for agent: {credentials.agent_id}")
    
    def generate_token(self, agent_id: str, permissions: List[str] = None) -> str:
        """Generate JWT token for agent."""
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT not available, cannot generate tokens")
            
        payload = {
            "agent_id": agent_id,
            "permissions": permissions or [],
            "iat": datetime.now(),
            "exp": datetime.now() + timedelta(hours=24)
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        if not JWT_AVAILABLE:
            logger.warning("PyJWT not available, cannot verify tokens")
            return None
            
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    def sign_message(self, message: A2AMessage, secret_key: str) -> str:
        """Sign message with HMAC."""
        message_data = json.dumps(message.to_dict(), sort_keys=True)
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, message: A2AMessage, signature: str, secret_key: str) -> bool:
        """Verify message signature."""
        expected_signature = self.sign_message(message, secret_key)
        return hmac.compare_digest(signature, expected_signature)
    
    def encrypt_message(self, message: A2AMessage, key: str) -> bytes:
        """Encrypt message (simple XOR for demo - use proper encryption in production)."""
        message_data = json.dumps(message.to_dict()).encode('utf-8')
        key_bytes = key.encode('utf-8')
        
        encrypted = bytearray()
        for i, byte in enumerate(message_data):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return bytes(encrypted)
    
    def decrypt_message(self, encrypted_data: bytes, key: str) -> A2AMessage:
        """Decrypt message."""
        key_bytes = key.encode('utf-8')
        
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_data):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        message_dict = json.loads(decrypted.decode('utf-8'))
        return A2AMessage.from_dict(message_dict)
    
    def check_permissions(self, agent_id: str, required_permission: str) -> bool:
        """Check if agent has required permission."""
        if agent_id not in self.credentials:
            return False
        
        credentials = self.credentials[agent_id]
        return required_permission in credentials.permissions or "admin" in credentials.permissions


class AgentInterface:
    """Standardized interface for agent communication."""
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        capabilities: List[str],
        security_level: SecurityLevel = SecurityLevel.BASIC
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.security_level = security_level
        
        # Communication components
        self.a2a_handler = A2AProtocolHandler(agent_id, agent_name, capabilities)
        self.security_manager = SecurityManager(agent_id)
        self.serializer = MessageSerializer()
        
        # Message routing
        self.request_handlers: Dict[str, Callable] = {}
        self.notification_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            "requests_sent": 0,
            "requests_received": 0,
            "notifications_sent": 0,
            "notifications_received": 0,
            "errors": 0
        }
    
    async def start(self):
        """Start the agent interface."""
        logger.info(f"Starting agent interface for {self.agent_id}")
        
        # Start A2A protocol handler
        await self.a2a_handler.start()
        
        # Register message handlers
        self.a2a_handler.register_handler("agent_request", self._handle_agent_request)
        self.a2a_handler.register_handler("agent_notification", self._handle_agent_notification)
        
        logger.info(f"Agent interface started for {self.agent_id}")
    
    async def stop(self):
        """Stop the agent interface."""
        logger.info(f"Stopping agent interface for {self.agent_id}")
        await self.a2a_handler.stop()
        logger.info(f"Agent interface stopped for {self.agent_id}")
    
    def register_request_handler(self, request_type: str, handler: Callable):
        """Register a request handler."""
        self.request_handlers[request_type] = handler
        logger.info(f"Registered request handler: {request_type}")
    
    def register_notification_handler(self, notification_type: str, handler: Callable):
        """Register a notification handler."""
        self.notification_handlers[notification_type] = handler
        logger.info(f"Registered notification handler: {notification_type}")
    
    async def send_request(
        self,
        to_agent: str,
        request_type: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.MEDIUM
    ) -> Dict[str, Any]:
        """Send a request to another agent."""
        self.stats["requests_sent"] += 1
        
        try:
            # Create secure message envelope
            message = A2AMessage(
                message_type=MessageType.REQUEST,
                from_agent=self.agent_id,
                to_agent=to_agent,
                payload={
                    "type": "agent_request",
                    "request_type": request_type,
                    "data": payload
                },
                priority=priority
            )
            
            # Send via A2A protocol
            response = await self.a2a_handler.send_request(
                to_agent, "agent_request", message.payload, timeout
            )
            
            return response.payload.get("result", {})
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to send request to {to_agent}: {e}")
            raise
    
    async def send_notification(
        self,
        to_agent: str,
        notification_type: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.LOW
    ):
        """Send a notification to another agent."""
        self.stats["notifications_sent"] += 1
        
        try:
            await self.a2a_handler.send_notification(
                to_agent,
                "agent_notification",
                {
                    "notification_type": notification_type,
                    "data": payload
                }
            )
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to send notification to {to_agent}: {e}")
            raise
    
    async def broadcast_notification(
        self,
        notification_type: str,
        payload: Dict[str, Any]
    ):
        """Broadcast a notification to all agents."""
        try:
            await self.a2a_handler.broadcast_notification(
                "agent_notification",
                {
                    "notification_type": notification_type,
                    "data": payload
                }
            )
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to broadcast notification: {e}")
            raise
    
    async def _handle_agent_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming agent request."""
        self.stats["requests_received"] += 1
        
        request_type = payload.get("request_type")
        data = payload.get("data", {})
        
        if request_type in self.request_handlers:
            try:
                result = await self.request_handlers[request_type](data)
                return {"status": "success", "result": result}
            except Exception as e:
                logger.error(f"Request handler error for {request_type}: {e}")
                return {"status": "error", "error": str(e)}
        else:
            return {"status": "error", "error": f"No handler for request type: {request_type}"}
    
    async def _handle_agent_notification(self, payload: Dict[str, Any]):
        """Handle incoming agent notification."""
        self.stats["notifications_received"] += 1
        
        notification_type = payload.get("notification_type")
        data = payload.get("data", {})
        
        if notification_type in self.notification_handlers:
            try:
                await self.notification_handlers[notification_type](data)
            except Exception as e:
                logger.error(f"Notification handler error for {notification_type}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get communication statistics."""
        return {
            **self.stats,
            "a2a_stats": self.a2a_handler.get_stats(),
            "registered_handlers": {
                "requests": list(self.request_handlers.keys()),
                "notifications": list(self.notification_handlers.keys())
            }
        }


class MultiAgentCoordinator:
    """Coordinates communication between multiple agents."""
    
    def __init__(self):
        self.agents: Dict[str, AgentInterface] = {}
        self.coordination_patterns: Dict[str, Callable] = {}
    
    def register_agent(self, agent: AgentInterface):
        """Register an agent for coordination."""
        self.agents[agent.agent_id] = agent
        logger.info(f"Registered agent for coordination: {agent.agent_id}")
    
    def register_coordination_pattern(self, pattern_name: str, handler: Callable):
        """Register a coordination pattern."""
        self.coordination_patterns[pattern_name] = handler
        logger.info(f"Registered coordination pattern: {pattern_name}")
    
    async def execute_coordination_pattern(
        self,
        pattern_name: str,
        participants: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a coordination pattern."""
        if pattern_name not in self.coordination_patterns:
            raise ValueError(f"Unknown coordination pattern: {pattern_name}")
        
        # Verify all participants are available
        for agent_id in participants:
            if agent_id not in self.agents:
                raise ValueError(f"Agent not registered: {agent_id}")
        
        # Execute pattern
        handler = self.coordination_patterns[pattern_name]
        return await handler(participants, context, self.agents)
    
    async def broadcast_to_agents(
        self,
        agent_ids: List[str],
        notification_type: str,
        payload: Dict[str, Any]
    ):
        """Broadcast notification to specific agents."""
        tasks = []
        for agent_id in agent_ids:
            if agent_id in self.agents:
                task = self.agents[agent_id].broadcast_notification(notification_type, payload)
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def collect_responses(
        self,
        agent_ids: List[str],
        request_type: str,
        payload: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Collect responses from multiple agents."""
        tasks = {}
        
        for agent_id in agent_ids:
            if agent_id in self.agents:
                # Find an agent that can send to this target
                sender = next(iter(self.agents.values()))
                task = sender.send_request(agent_id, request_type, payload, timeout)
                tasks[agent_id] = task
        
        results = {}
        if tasks:
            responses = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for agent_id, response in zip(tasks.keys(), responses):
                if isinstance(response, Exception):
                    results[agent_id] = {"error": str(response)}
                else:
                    results[agent_id] = response
        
        return results


# Predefined coordination patterns
async def request_response_pattern(
    participants: List[str],
    context: Dict[str, Any],
    agents: Dict[str, AgentInterface]
) -> Dict[str, Any]:
    """Simple request-response coordination pattern."""
    requester = participants[0]
    responder = participants[1]
    
    request_type = context.get("request_type", "generic_request")
    payload = context.get("payload", {})
    
    if requester in agents:
        agent = agents[requester]
        response = await agent.send_request(responder, request_type, payload)
        return {"status": "success", "response": response}
    
    return {"status": "error", "error": "Requester agent not found"}


async def pipeline_pattern(
    participants: List[str],
    context: Dict[str, Any],
    agents: Dict[str, AgentInterface]
) -> Dict[str, Any]:
    """Pipeline coordination pattern - data flows through agents sequentially."""
    if len(participants) < 2:
        return {"status": "error", "error": "Pipeline requires at least 2 agents"}
    
    current_data = context.get("initial_data", {})
    request_type = context.get("request_type", "process_data")
    
    results = []
    
    for i in range(len(participants) - 1):
        current_agent = participants[i]
        next_agent = participants[i + 1]
        
        if current_agent in agents:
            agent = agents[current_agent]
            try:
                response = await agent.send_request(next_agent, request_type, current_data)
                current_data = response.get("result", current_data)
                results.append({
                    "agent": next_agent,
                    "response": response
                })
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Pipeline failed at {next_agent}: {str(e)}",
                    "completed_steps": results
                }
    
    return {
        "status": "success",
        "final_result": current_data,
        "pipeline_results": results
    }


async def consensus_pattern(
    participants: List[str],
    context: Dict[str, Any],
    agents: Dict[str, AgentInterface]
) -> Dict[str, Any]:
    """Consensus coordination pattern - collect votes/opinions from agents."""
    request_type = context.get("request_type", "vote")
    payload = context.get("payload", {})
    
    # Collect responses from all participants
    coordinator = MultiAgentCoordinator()
    for agent_id, agent in agents.items():
        coordinator.register_agent(agent)
    
    responses = await coordinator.collect_responses(participants, request_type, payload)
    
    # Simple majority consensus
    votes = {}
    for agent_id, response in responses.items():
        if "error" not in response:
            vote = response.get("vote", "abstain")
            votes[vote] = votes.get(vote, 0) + 1
    
    if votes:
        consensus = max(votes, key=votes.get)
        return {
            "status": "success",
            "consensus": consensus,
            "votes": votes,
            "responses": responses
        }
    
    return {"status": "error", "error": "No valid votes received"}