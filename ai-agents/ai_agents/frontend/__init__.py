"""
Frontend Integration Layer for AI-Powered Boutique Agents

This module provides the integration layer between the AI agents and the
Online Boutique frontend, enabling real-time AI features in the web interface.
"""

from .agent_sdk import AgentSDK
from .websocket_handler import WebSocketHandler
from .api_gateway import APIGateway
from .real_time_features import RealTimeFeatures

__all__ = [
    'AgentSDK',
    'WebSocketHandler', 
    'APIGateway',
    'RealTimeFeatures'
]