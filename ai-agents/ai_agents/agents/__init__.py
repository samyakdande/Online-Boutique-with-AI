"""
AI Agents Package

This package contains all the AI agents for the Online Boutique enhancement.
Each agent is built using the ADK framework and integrates with MCP servers
and the A2A protocol for seamless communication.
"""

from .review_tracker import ReviewTrackerAgent
from .advanced_recommendation import AdvancedRecommendationAgent
from .ai_chatbot import AIChatbotAgent
from .dynamic_pricing import DynamicPricingAgent
# from .marketing_email import MarketingEmailAgent  # Temporarily disabled due to syntax errors
from .virtual_tryon import VirtualTryOnAgent

__all__ = [
    'ReviewTrackerAgent',
    'AdvancedRecommendationAgent',
    'AIChatbotAgent',
    'DynamicPricingAgent',
    # 'MarketingEmailAgent',  # Temporarily disabled
    'VirtualTryOnAgent',
]