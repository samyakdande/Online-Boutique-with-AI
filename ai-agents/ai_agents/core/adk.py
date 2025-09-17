"""
Agent Development Kit (ADK) for Python.

This module provides the core ADK functionality for building, managing,
and orchestrating AI agents in the Online Boutique enhancement project.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union

import google.generativeai as genai
from pydantic import BaseModel

from ai_agents.core.config import settings
from ai_agents.core.logging import AgentLogger, get_logger

logger = get_logger(__name__)


class AgentState(Enum):
    """Agent lifecycle states."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


class MessageType(Enum):
    """Agent message types for A2A communication."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class AgentMessage:
    """Message structure for agent-to-agent communication."""
    id: str
    from_agent: str
    to_agent: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    priority: str = "medium"  # low, medium, high, critical


@dataclass
class AgentCapability:
    """Represents an agent capability."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    version: str = "1.0.0"


class AgentProtocol(Protocol):
    """Protocol defining the agent interface."""
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        ...
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process an incoming message."""
        ...
    
    async def shutdown(self) -> None:
        """Shutdown the agent gracefully."""
        ...


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        version: str = "1.0.0",
        capabilities: List[str] = None,
        dependencies: List[str] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.version = version
        self.capabilities = capabilities or []
        self.dependencies = dependencies or []
        
        self.state = AgentState.INITIALIZING
        self.logger = AgentLogger(agent_id, name)
        self.gemini_client = None
        self._message_handlers: Dict[str, callable] = {}
        self._startup_time = None
        
        # A2A Protocol integration
        self.a2a_handler = None
        self.agent_interface = None
        
        # Performance tracking
        self._request_count = 0
        self._error_count = 0
        self._last_heartbeat = time.time()
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        self.logger.info("Initializing agent", version=self.version)
        
        try:
            # Initialize Gemini client
            if settings.gemini_api_key and settings.gemini_api_key != "your-gemini-api-key-here":
                genai.configure(api_key=settings.gemini_api_key)
                self.gemini_client = genai.GenerativeModel(settings.gemini_model_pro)
                self.logger.info("Gemini client initialized")
            
            # Initialize A2A communication (optional for now)
            if settings.a2a_enabled:
                try:
                    from ai_agents.a2a.communication import AgentInterface, SecurityLevel
                    self.agent_interface = AgentInterface(
                        agent_id=self.agent_id,
                        agent_name=self.name,
                        capabilities=self.capabilities,
                        security_level=SecurityLevel.BASIC
                    )
                    self.logger.info("A2A communication interface initialized")
                except ImportError:
                    self.logger.warning("A2A communication not available")
            
            # Custom initialization
            await self._initialize()
            
            self.state = AgentState.READY
            self._startup_time = time.time()
            self.logger.info("Agent initialized successfully")
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.logger.error("Agent initialization failed", error=str(e))
            raise
    
    @abstractmethod
    async def _initialize(self) -> None:
        """Custom initialization logic for the agent."""
        pass
    
    async def start(self) -> None:
        """Start the agent."""
        if self.state != AgentState.READY:
            raise RuntimeError(f"Agent not ready to start. Current state: {self.state}")
        
        self.state = AgentState.RUNNING
        self.logger.info("Agent started")
        
        # Start A2A communication interface
        if self.agent_interface:
            try:
                await self.agent_interface.start()
                self.logger.info("A2A communication interface started")
            except Exception as e:
                self.logger.warning(f"Failed to start A2A interface: {e}")
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_loop())
        await self._start()
    
    @abstractmethod
    async def _start(self) -> None:
        """Custom start logic for the agent."""
        pass
    
    async def stop(self) -> None:
        """Stop the agent gracefully."""
        self.state = AgentState.STOPPING
        self.logger.info("Stopping agent")
        
        try:
            await self._stop()
            self.state = AgentState.STOPPED
            self.logger.info("Agent stopped successfully")
        except Exception as e:
            self.state = AgentState.ERROR
            self.logger.error("Error stopping agent", error=str(e))
            raise
    
    @abstractmethod
    async def _stop(self) -> None:
        """Custom stop logic for the agent."""
        pass
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process an incoming message."""
        self._request_count += 1
        start_time = time.time()
        
        try:
            self.logger.info(
                "Processing message",
                message_id=message.id,
                from_agent=message.from_agent,
                message_type=message.message_type.value
            )
            
            # Route to appropriate handler
            handler = self._message_handlers.get(message.message_type.value)
            if handler:
                response = await handler(message)
            else:
                response = await self._handle_message(message)
            
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Message processed",
                message_id=message.id,
                duration_ms=duration_ms
            )
            
            return response
            
        except Exception as e:
            self._error_count += 1
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Error processing message",
                message_id=message.id,
                error=str(e),
                duration_ms=duration_ms
            )
            
            # Return error response
            return AgentMessage(
                id=f"error_{message.id}",
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                message_type=MessageType.ERROR,
                payload={"error": str(e), "original_message_id": message.id}
            )
    
    @abstractmethod
    async def _handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming messages. Override in subclasses."""
        pass
    
    def register_message_handler(self, message_type: str, handler: callable) -> None:
        """Register a message handler for a specific message type."""
        self._message_handlers[message_type] = handler
    
    async def send_message(self, message: AgentMessage) -> None:
        """Send a message to another agent."""
        # This would integrate with the A2A protocol implementation
        self.logger.info(
            "Sending message",
            message_id=message.id,
            to_agent=message.to_agent,
            message_type=message.message_type.value
        )
        # TODO: Implement actual message sending via A2A protocol
    
    async def call_gemini(
        self,
        prompt: str,
        model: str = None,
        **kwargs
    ) -> str:
        """Call Gemini API with the given prompt."""
        if not self.gemini_client:
            raise RuntimeError("Gemini client not initialized")
        
        model_name = model or settings.gemini.model_pro
        start_time = time.time()
        
        try:
            # Configure generation parameters
            generation_config = {
                "temperature": kwargs.get("temperature", settings.gemini.temperature),
                "top_p": kwargs.get("top_p", settings.gemini.top_p),
                "top_k": kwargs.get("top_k", settings.gemini.top_k),
                "max_output_tokens": kwargs.get("max_output_tokens", settings.gemini.max_output_tokens),
            }
            
            # Generate response
            response = await self.gemini_client.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Gemini API call completed",
                model=model_name,
                duration_ms=duration_ms,
                prompt_length=len(prompt),
                response_length=len(response.text) if response.text else 0
            )
            
            return response.text
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Gemini API call failed",
                model=model_name,
                error=str(e),
                duration_ms=duration_ms
            )
            raise
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while self.state == AgentState.RUNNING:
            try:
                self._last_heartbeat = time.time()
                
                # Send heartbeat message
                heartbeat = AgentMessage(
                    id=f"heartbeat_{int(time.time())}",
                    from_agent=self.agent_id,
                    to_agent="system",
                    message_type=MessageType.HEARTBEAT,
                    payload={
                        "state": self.state.value,
                        "uptime": time.time() - self._startup_time if self._startup_time else 0,
                        "request_count": self._request_count,
                        "error_count": self._error_count
                    }
                )
                
                await self.send_message(heartbeat)
                await asyncio.sleep(settings.a2a.heartbeat_interval)
                
            except Exception as e:
                self.logger.error("Heartbeat failed", error=str(e))
                await asyncio.sleep(5)  # Retry after 5 seconds
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "state": self.state.value,
            "uptime": time.time() - self._startup_time if self._startup_time else 0,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
            "last_heartbeat": self._last_heartbeat,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies
        }


class AgentManager:
    """Manages multiple agents and their lifecycle."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.logger = get_logger("agent_manager")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the manager."""
        self.agents[agent.agent_id] = agent
        self.logger.info("Agent registered", agent_id=agent.agent_id, name=agent.name)
    
    async def start_agent(self, agent_id: str) -> None:
        """Start a specific agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.agents[agent_id]
        await agent.initialize()
        await agent.start()
        self.logger.info("Agent started", agent_id=agent_id)
    
    async def stop_agent(self, agent_id: str) -> None:
        """Stop a specific agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.agents[agent_id]
        await agent.stop()
        self.logger.info("Agent stopped", agent_id=agent_id)
    
    async def start_all_agents(self) -> None:
        """Start all registered agents."""
        for agent_id in self.agents:
            try:
                await self.start_agent(agent_id)
            except Exception as e:
                self.logger.error("Failed to start agent", agent_id=agent_id, error=str(e))
    
    async def stop_all_agents(self) -> None:
        """Stop all running agents."""
        for agent_id in self.agents:
            try:
                await self.stop_agent(agent_id)
            except Exception as e:
                self.logger.error("Failed to stop agent", agent_id=agent_id, error=str(e))
    
    def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents."""
        return {
            agent_id: agent.get_health_status()
            for agent_id, agent in self.agents.items()
        }
    
    async def route_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Route a message to the appropriate agent."""
        target_agent = self.agents.get(message.to_agent)
        if not target_agent:
            self.logger.error("Target agent not found", agent_id=message.to_agent)
            return None
        
        return await target_agent.process_message(message)


# Global agent manager instance
agent_manager = AgentManager()