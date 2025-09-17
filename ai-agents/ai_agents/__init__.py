"""
AI-Powered Online Boutique Enhancement

This package provides intelligent AI agents for the Google Cloud Online Boutique
microservices demo, built for the GKE Turns 10 Hackathon.
"""

__version__ = "1.0.0"
__author__ = "GKE Turns 10 Hackathon Team"
__email__ = "team@example.com"

from ai_agents.core.config import settings
from ai_agents.core.logging import get_logger

logger = get_logger(__name__)

logger.info(
    f"AI-Powered Boutique Agents v{__version__} initialized",
    extra={"version": __version__, "environment": settings.environment}
)