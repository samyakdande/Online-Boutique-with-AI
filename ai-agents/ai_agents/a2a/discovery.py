"""
A2A Service Discovery

This module provides service discovery capabilities for the A2A protocol,
allowing agents to find and connect to each other dynamically.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict

from ai_agents.core.config import settings
from ai_agents.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceEndpoint:
    """Service endpoint information."""
    agent_id: str
    name: str
    capabilities: List[str]
    endpoint: str
    health_check_url: str
    last_seen: datetime
    status: str = "healthy"
    metadata: Dict[str, str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["last_seen"] = self.last_seen.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ServiceEndpoint':
        """Create from dictionary."""
        data["last_seen"] = datetime.fromisoformat(data["last_seen"])
        return cls(**data)


class ServiceRegistry:
    """Service registry for A2A protocol."""
    
    def __init__(self):
        self.services: Dict[str, ServiceEndpoint] = {}
        self.capability_index: Dict[str, Set[str]] = {}
        self.health_check_interval = 30  # seconds
        self.service_timeout = 90  # seconds
    
    def register_service(self, service: ServiceEndpoint) -> bool:
        """Register a service."""
        try:
            # Update service registry
            self.services[service.agent_id] = service
            
            # Update capability index
            for capability in service.capabilities:
                if capability not in self.capability_index:
                    self.capability_index[capability] = set()
                self.capability_index[capability].add(service.agent_id)
            
            logger.info(f"Registered service: {service.agent_id} ({service.name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service.agent_id}: {e}")
            return False
    
    def unregister_service(self, agent_id: str) -> bool:
        """Unregister a service."""
        try:
            if agent_id in self.services:
                service = self.services[agent_id]
                
                # Remove from capability index
                for capability in service.capabilities:
                    if capability in self.capability_index:
                        self.capability_index[capability].discard(agent_id)
                        if not self.capability_index[capability]:
                            del self.capability_index[capability]
                
                # Remove from services
                del self.services[agent_id]
                
                logger.info(f"Unregistered service: {agent_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister service {agent_id}: {e}")
            return False
    
    def get_service(self, agent_id: str) -> Optional[ServiceEndpoint]:
        """Get service by agent ID."""
        return self.services.get(agent_id)
    
    def get_services_by_capability(self, capability: str) -> List[ServiceEndpoint]:
        """Get services that provide a specific capability."""
        if capability not in self.capability_index:
            return []
        
        services = []
        for agent_id in self.capability_index[capability]:
            if agent_id in self.services:
                service = self.services[agent_id]
                if service.status == "healthy":
                    services.append(service)
        
        return services
    
    def get_all_services(self) -> List[ServiceEndpoint]:
        """Get all registered services."""
        return list(self.services.values())
    
    def update_service_health(self, agent_id: str, status: str):
        """Update service health status."""
        if agent_id in self.services:
            self.services[agent_id].status = status
            self.services[agent_id].last_seen = datetime.now()
    
    def cleanup_stale_services(self):
        """Remove stale services."""
        current_time = datetime.now()
        stale_services = []
        
        for agent_id, service in self.services.items():
            time_since_seen = current_time - service.last_seen
            if time_since_seen.total_seconds() > self.service_timeout:
                stale_services.append(agent_id)
        
        for agent_id in stale_services:
            self.unregister_service(agent_id)
            logger.warning(f"Removed stale service: {agent_id}")
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        healthy_services = sum(1 for s in self.services.values() if s.status == "healthy")
        
        return {
            "total_services": len(self.services),
            "healthy_services": healthy_services,
            "unhealthy_services": len(self.services) - healthy_services,
            "capabilities": list(self.capability_index.keys()),
            "capability_count": len(self.capability_index)
        }


class ServiceDiscovery:
    """Service discovery manager."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.registry = ServiceRegistry()
        self.running = False
        self.health_check_task = None
    
    async def start(self):
        """Start service discovery."""
        logger.info("Starting service discovery")
        self.running = True
        
        # Start health check loop
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Service discovery started")
    
    async def stop(self):
        """Stop service discovery."""
        logger.info("Stopping service discovery")
        self.running = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Service discovery stopped")
    
    async def register_agent(
        self,
        agent_id: str,
        name: str,
        capabilities: List[str],
        endpoint: str,
        health_check_url: str = None,
        metadata: Dict[str, str] = None
    ) -> bool:
        """Register an agent as a service."""
        if not health_check_url:
            health_check_url = f"{endpoint}/health"
        
        service = ServiceEndpoint(
            agent_id=agent_id,
            name=name,
            capabilities=capabilities,
            endpoint=endpoint,
            health_check_url=health_check_url,
            last_seen=datetime.now(),
            metadata=metadata or {}
        )
        
        return self.registry.register_service(service)
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        return self.registry.unregister_service(agent_id)
    
    async def discover_agents(self, capability: str = None) -> List[ServiceEndpoint]:
        """Discover agents by capability."""
        if capability:
            return self.registry.get_services_by_capability(capability)
        else:
            return self.registry.get_all_services()
    
    async def find_agent(self, agent_id: str) -> Optional[ServiceEndpoint]:
        """Find a specific agent."""
        return self.registry.get_service(agent_id)
    
    async def find_best_agent(self, capability: str) -> Optional[ServiceEndpoint]:
        """Find the best agent for a capability (load balancing)."""
        agents = self.registry.get_services_by_capability(capability)
        
        if not agents:
            return None
        
        # Simple round-robin for now
        # In a real implementation, you might consider load, response time, etc.
        return min(agents, key=lambda a: a.last_seen)
    
    async def _health_check_loop(self):
        """Periodic health check of registered services."""
        import httpx
        
        while self.running:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    for service in self.registry.get_all_services():
                        try:
                            # Perform health check
                            response = await client.get(service.health_check_url)
                            
                            if response.status_code == 200:
                                self.registry.update_service_health(service.agent_id, "healthy")
                            else:
                                self.registry.update_service_health(service.agent_id, "unhealthy")
                                logger.warning(f"Service {service.agent_id} health check failed: {response.status_code}")
                        
                        except Exception as e:
                            self.registry.update_service_health(service.agent_id, "unhealthy")
                            logger.warning(f"Service {service.agent_id} health check error: {e}")
                
                # Clean up stale services
                self.registry.cleanup_stale_services()
                
                await asyncio.sleep(self.registry.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(30)
    
    def get_registry_stats(self) -> Dict:
        """Get service registry statistics."""
        return self.registry.get_stats()


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflows."""
    
    def __init__(self, discovery: ServiceDiscovery):
        self.discovery = discovery
        self.active_workflows: Dict[str, Dict] = {}
    
    async def start_workflow(
        self,
        workflow_id: str,
        workflow_definition: Dict,
        context: Dict = None
    ) -> bool:
        """Start a multi-agent workflow."""
        try:
            workflow = {
                "id": workflow_id,
                "definition": workflow_definition,
                "context": context or {},
                "status": "running",
                "current_step": 0,
                "start_time": datetime.now(),
                "steps_completed": [],
                "errors": []
            }
            
            self.active_workflows[workflow_id] = workflow
            
            # Start first step
            await self._execute_workflow_step(workflow_id, 0)
            
            logger.info(f"Started workflow: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_id}: {e}")
            return False
    
    async def _execute_workflow_step(self, workflow_id: str, step_index: int):
        """Execute a workflow step."""
        if workflow_id not in self.active_workflows:
            return
        
        workflow = self.active_workflows[workflow_id]
        steps = workflow["definition"].get("steps", [])
        
        if step_index >= len(steps):
            # Workflow complete
            workflow["status"] = "completed"
            workflow["end_time"] = datetime.now()
            logger.info(f"Workflow {workflow_id} completed")
            return
        
        step = steps[step_index]
        
        try:
            # Find agent for this step
            required_capability = step.get("capability")
            agent = await self.discovery.find_best_agent(required_capability)
            
            if not agent:
                raise Exception(f"No agent found for capability: {required_capability}")
            
            # Execute step (this would integrate with A2A protocol)
            logger.info(f"Executing workflow {workflow_id} step {step_index} on agent {agent.agent_id}")
            
            # Mark step as completed
            workflow["steps_completed"].append({
                "step_index": step_index,
                "agent_id": agent.agent_id,
                "completed_at": datetime.now().isoformat()
            })
            
            # Move to next step
            workflow["current_step"] = step_index + 1
            await self._execute_workflow_step(workflow_id, step_index + 1)
            
        except Exception as e:
            workflow["errors"].append({
                "step_index": step_index,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            workflow["status"] = "failed"
            logger.error(f"Workflow {workflow_id} step {step_index} failed: {e}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get workflow status."""
        return self.active_workflows.get(workflow_id)
    
    def get_active_workflows(self) -> List[Dict]:
        """Get all active workflows."""
        return list(self.active_workflows.values())