"""
Development server with hot reload capabilities.

This module provides a development server that watches for file changes
and automatically reloads agents and MCP servers.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ai_agents.core.adk import agent_manager
from ai_agents.core.config import settings
from ai_agents.core.logging import get_logger

logger = get_logger(__name__)


class HotReloadHandler(FileSystemEventHandler):
    """File system event handler for hot reload."""
    
    def __init__(self, reload_callback):
        super().__init__()
        self.reload_callback = reload_callback
        self.debounce_timer = None
        self.changed_files: Set[str] = set()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Check if file should be ignored
        if self._should_ignore_file(file_path):
            return
        
        self.changed_files.add(file_path)
        
        # Debounce rapid file changes
        if self.debounce_timer:
            self.debounce_timer.cancel()
        
        self.debounce_timer = asyncio.get_event_loop().call_later(
            settings.development.debounce_seconds,
            self._trigger_reload
        )
    
    def _should_ignore_file(self, file_path: str) -> bool:
        """Check if file should be ignored based on patterns."""
        for pattern in settings.development.exclude_patterns:
            if Path(file_path).match(pattern):
                return True
        return False
    
    def _trigger_reload(self):
        """Trigger the reload callback."""
        if self.changed_files:
            logger.info(
                "Files changed, triggering reload",
                changed_files=list(self.changed_files)
            )
            asyncio.create_task(self.reload_callback(self.changed_files.copy()))
            self.changed_files.clear()


class DevelopmentServer:
    """Development server with hot reload capabilities."""
    
    def __init__(self):
        self.observer = Observer()
        self.reload_handler = HotReloadHandler(self._handle_reload)
        self.running = False
    
    async def start(self):
        """Start the development server."""
        logger.info("Starting development server with hot reload")
        
        # Setup file watching
        if settings.development.hot_reload_enabled:
            self._setup_file_watching()
        
        # Start agents
        await self._start_agents()
        
        # Start MCP servers
        await self._start_mcp_servers()
        
        self.running = True
        logger.info("Development server started successfully")
        
        # Keep the server running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the development server."""
        logger.info("Stopping development server")
        
        self.running = False
        
        # Stop file watching
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        
        # Stop agents
        await agent_manager.stop_all_agents()
        
        logger.info("Development server stopped")
    
    def _setup_file_watching(self):
        """Setup file system watching for hot reload."""
        project_root = Path(__file__).parent.parent.parent
        
        for watch_path in settings.development.watch_paths:
            full_path = project_root / watch_path
            if full_path.exists():
                self.observer.schedule(
                    self.reload_handler,
                    str(full_path),
                    recursive=True
                )
                logger.info(f"Watching for changes: {full_path}")
        
        self.observer.start()
    
    async def _start_agents(self):
        """Start all agents."""
        logger.info("Starting agents")
        
        # Import and register agents
        try:
            from ai_agents.agents.personal_stylist import PersonalStylistAgent
            from ai_agents.agents.inventory_optimizer import InventoryOptimizerAgent
            from ai_agents.agents.customer_insights import CustomerInsightsAgent
            
            # Register agents
            agent_manager.register_agent(PersonalStylistAgent())
            agent_manager.register_agent(InventoryOptimizerAgent())
            agent_manager.register_agent(CustomerInsightsAgent())
            
            # Start all agents
            await agent_manager.start_all_agents()
            
        except ImportError as e:
            logger.warning(f"Some agents not available yet: {e}")
        except Exception as e:
            logger.error(f"Error starting agents: {e}")
    
    async def _start_mcp_servers(self):
        """Start MCP servers."""
        logger.info("Starting MCP servers")
        
        try:
            from ai_agents.mcp_servers.boutique_api import start_boutique_api_server
            from ai_agents.mcp_servers.analytics import start_analytics_server
            from ai_agents.mcp_servers.ml_models import start_ml_models_server
            
            # Start MCP servers in background
            asyncio.create_task(start_boutique_api_server())
            asyncio.create_task(start_analytics_server())
            asyncio.create_task(start_ml_models_server())
            
        except ImportError as e:
            logger.warning(f"Some MCP servers not available yet: {e}")
        except Exception as e:
            logger.error(f"Error starting MCP servers: {e}")
    
    async def _handle_reload(self, changed_files: Set[str]):
        """Handle hot reload when files change."""
        logger.info("Hot reload triggered", changed_files=list(changed_files))
        
        try:
            # Stop current agents
            await agent_manager.stop_all_agents()
            
            # Clear module cache for changed files
            self._clear_module_cache(changed_files)
            
            # Restart agents
            await self._start_agents()
            
            logger.info("Hot reload completed successfully")
            
        except Exception as e:
            logger.error(f"Hot reload failed: {e}")
    
    def _clear_module_cache(self, changed_files: Set[str]):
        """Clear Python module cache for changed files."""
        project_root = Path(__file__).parent.parent.parent
        
        for file_path in changed_files:
            if not file_path.endswith('.py'):
                continue
            
            # Convert file path to module name
            rel_path = Path(file_path).relative_to(project_root)
            if rel_path.parts[0] == 'ai_agents':
                module_name = '.'.join(rel_path.with_suffix('').parts)
                
                if module_name in sys.modules:
                    logger.debug(f"Clearing module cache: {module_name}")
                    del sys.modules[module_name]


async def start_dev_server():
    """Start the development server."""
    server = DevelopmentServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(start_dev_server())