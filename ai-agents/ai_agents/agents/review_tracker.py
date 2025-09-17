"""
Review Tracker Agent

This agent analyzes product reviews for sentiment, authenticity, and key themes.
It uses Gemini AI for intelligent analysis and integrates with the MCP servers
for data access and the A2A protocol for agent communication.

Features:
- Real-time sentiment analysis
- Fake review detection
- Key theme extraction
- Review quality scoring
- Integration with product recommendations
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import google.generativeai as genai
from pydantic import BaseModel, Field

from ..core.adk import BaseAgent, AgentMessage, MessageType as ADKMessageType
from ..core.config import get_settings
from ..a2a.protocol import A2AProtocolHandler, MessageType
from ..mcp_servers.boutique_api import BoutiqueAPIMCPServer

# Configure logging
logger = logging.getLogger(__name__)

class SentimentType(str, Enum):
    """Sentiment classification types"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"

class ReviewTheme(str, Enum):
    """Common review themes"""
    QUALITY = "quality"
    SIZING = "sizing"
    COMFORT = "comfort"
    STYLE = "style"
    VALUE = "value"
    SHIPPING = "shipping"
    CUSTOMER_SERVICE = "customer_service"
    DURABILITY = "durability"
    COLOR = "color"
    FIT = "fit"

@dataclass
class ReviewAnalysis:
    """Analysis results for a single review"""
    review_id: str
    product_id: str
    sentiment_score: float  # -1.0 to 1.0
    sentiment_type: SentimentType
    authenticity_score: float  # 0.0 to 1.0 (1.0 = authentic)
    key_themes: List[ReviewTheme]
    confidence: float  # 0.0 to 1.0
    reasoning: str
    flagged_for_moderation: bool
    analyzed_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['analyzed_at'] = self.analyzed_at.isoformat()
        return result

@dataclass
class ProductReviewSummary:
    """Aggregated review analysis for a product"""
    product_id: str
    total_reviews: int
    average_sentiment: float
    sentiment_distribution: Dict[SentimentType, int]
    top_themes: List[ReviewTheme]
    authenticity_rate: float
    recommendation_impact: float  # How much reviews should impact recommendations
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['last_updated'] = self.last_updated.isoformat()
        return result

class ReviewRequest(BaseModel):
    """Request model for review analysis"""
    review_text: str = Field(..., description="The review text to analyze")
    product_id: str = Field(..., description="Product ID the review is for")
    reviewer_id: Optional[str] = Field(None, description="ID of the reviewer")
    review_id: Optional[str] = Field(None, description="Unique review ID")

class ReviewTrackerAgent(BaseAgent):
    """
    AI Agent for tracking and analyzing product reviews
    
    This agent provides intelligent review analysis including:
    - Sentiment analysis using Gemini AI
    - Fake review detection
    - Key theme extraction
    - Product review summaries
    - Integration with recommendation systems
    """
    
    def __init__(self):
        super().__init__(
            agent_id="review-tracker",
            name="Review Tracker Agent",
            version="1.0.0",
            capabilities=[
                "text_analysis",
                "sentiment_analysis", 
                "data_aggregation",
                "real_time_processing"
            ]
        )
        
        self.settings = get_settings()
        self.mcp_client = BoutiqueAPIMCPServer()
        self.a2a_handler = A2AProtocolHandler(
            agent_id=self.agent_id,
            agent_name=self.name,
            capabilities=self.capabilities
        )
        # Use specific port for this agent
        self.a2a_handler.port = int(os.getenv('REVIEW_TRACKER_A2A_PORT', '9091'))
        
        # Initialize Gemini AI
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # In-memory cache for review analyses (in production, use Redis)
        self.review_cache: Dict[str, ReviewAnalysis] = {}
        self.product_summaries: Dict[str, ProductReviewSummary] = {}
        
        logger.info(f"Initialized {self.name} with ID: {self.agent_id}")

    async def _initialize(self) -> None:
        """Custom initialization for Review Tracker Agent"""
        # Initialize Gemini AI
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # In-memory cache for review analyses (in production, use Redis)
        self.review_cache: Dict[str, ReviewAnalysis] = {}
        self.product_summaries: Dict[str, ProductReviewSummary] = {}
        
        logger.info("Review Tracker Agent custom initialization completed")

    async def _start(self) -> None:
        """Custom start logic for Review Tracker Agent"""
        await self.a2a_handler.start()
        
        # Register message handlers
        self.a2a_handler.register_handler(
            "analyze_review", 
            self._handle_analyze_review_request
        )
        self.a2a_handler.register_handler(
            "get_product_sentiment", 
            self._handle_get_product_sentiment_request
        )
        self.a2a_handler.register_handler(
            "get_sentiment_trends", 
            self._handle_get_sentiment_trends_request
        )
        
        logger.info("Review Tracker Agent started successfully")

    async def _stop(self) -> None:
        """Custom stop logic for Review Tracker Agent"""
        await self.a2a_handler.stop()
        logger.info("Review Tracker Agent stopped")

    async def _handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming ADK messages"""
        try:
            # Route based on message type and payload
            if message.message_type == ADKMessageType.REQUEST:
                request_type = message.payload.get('type')
                
                if request_type == 'analyze_review':
                    result = await self._handle_analyze_review_request(message.payload.get('data', {}))
                    return AgentMessage(
                        id=f"response_{message.id}",
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type=ADKMessageType.RESPONSE,
                        payload={'result': result}
                    )
                elif request_type == 'get_product_sentiment':
                    result = await self._handle_get_product_sentiment_request(message.payload.get('data', {}))
                    return AgentMessage(
                        id=f"response_{message.id}",
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type=ADKMessageType.RESPONSE,
                        payload={'result': result}
                    )
                elif request_type == 'get_sentiment_trends':
                    result = await self._handle_get_sentiment_trends_request(message.payload.get('data', {}))
                    return AgentMessage(
                        id=f"response_{message.id}",
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type=ADKMessageType.RESPONSE,
                        payload={'result': result}
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            return AgentMessage(
                id=f"error_{message.id}",
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                message_type=ADKMessageType.ERROR,
                payload={'error': str(e)}
            )



    async def analyze_review(self, request: ReviewRequest) -> ReviewAnalysis:
        """
        Analyze a single review for sentiment, authenticity, and themes
        
        Args:
            request: Review analysis request
            
        Returns:
            ReviewAnalysis: Complete analysis results
        """
        try:
            # Check cache first
            cache_key = f"{request.product_id}:{hash(request.review_text)}"
            if cache_key in self.review_cache:
                logger.debug(f"Returning cached analysis for review")
                return self.review_cache[cache_key]
            
            # Prepare prompt for Gemini
            analysis_prompt = self._create_analysis_prompt(request.review_text)
            
            # Get AI analysis
            response = await self._get_gemini_analysis(analysis_prompt)
            
            # Parse and structure the response
            analysis = self._parse_gemini_response(
                response, 
                request.review_id or f"review_{datetime.now().timestamp()}",
                request.product_id
            )
            
            # Cache the result
            self.review_cache[cache_key] = analysis
            
            # Update product summary
            await self._update_product_summary(analysis)
            
            # Notify other agents if needed
            if analysis.flagged_for_moderation or analysis.authenticity_score < 0.3:
                await self._notify_moderation_needed(analysis)
            
            logger.info(f"Analyzed review for product {request.product_id}: "
                       f"sentiment={analysis.sentiment_type}, "
                       f"authenticity={analysis.authenticity_score:.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing review: {str(e)}")
            # Return a default analysis in case of error
            return ReviewAnalysis(
                review_id=request.review_id or "error",
                product_id=request.product_id,
                sentiment_score=0.0,
                sentiment_type=SentimentType.NEUTRAL,
                authenticity_score=0.5,
                key_themes=[],
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                flagged_for_moderation=True,
                analyzed_at=datetime.now()
            )

    async def get_product_review_summary(self, product_id: str) -> Optional[ProductReviewSummary]:
        """
        Get aggregated review analysis for a product
        
        Args:
            product_id: Product ID to get summary for
            
        Returns:
            ProductReviewSummary or None if no reviews analyzed
        """
        return self.product_summaries.get(product_id)

    async def get_sentiment_trends(self, product_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get sentiment trends for a product over time
        
        Args:
            product_id: Product ID
            days: Number of days to analyze
            
        Returns:
            Dictionary with trend data
        """
        # In a real implementation, this would query a time-series database
        # For now, return mock trend data
        return {
            "product_id": product_id,
            "period_days": days,
            "trend": "improving",  # improving, declining, stable
            "sentiment_change": 0.15,  # Change in average sentiment
            "review_volume_change": 0.25,  # Change in review volume
            "authenticity_trend": "stable"
        }

    def _create_analysis_prompt(self, review_text: str) -> str:
        """Create a structured prompt for Gemini analysis"""
        return f"""
Analyze this product review and provide a structured analysis:

Review Text: "{review_text}"

Please analyze and respond with a JSON object containing:
1. sentiment_score: A number from -1.0 (very negative) to 1.0 (very positive)
2. sentiment_type: One of "very_positive", "positive", "neutral", "negative", "very_negative"
3. authenticity_score: A number from 0.0 to 1.0 indicating how authentic the review seems
4. key_themes: Array of themes mentioned (quality, sizing, comfort, style, value, shipping, customer_service, durability, color, fit)
5. confidence: How confident you are in this analysis (0.0 to 1.0)
6. reasoning: Brief explanation of your analysis
7. flagged_for_moderation: Boolean indicating if this review needs human review

Consider these factors for authenticity:
- Generic language vs specific details
- Emotional authenticity
- Review length and depth
- Unusual patterns or repetitive phrases
- Balance of positive/negative aspects

Respond only with valid JSON.
"""

    async def _get_gemini_analysis(self, prompt: str) -> str:
        """Get analysis from Gemini AI model"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise

    def _parse_gemini_response(self, response: str, review_id: str, product_id: str) -> ReviewAnalysis:
        """Parse Gemini response into ReviewAnalysis object"""
        try:
            # Clean the response (remove markdown formatting if present)
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            data = json.loads(clean_response.strip())
            
            return ReviewAnalysis(
                review_id=review_id,
                product_id=product_id,
                sentiment_score=float(data.get('sentiment_score', 0.0)),
                sentiment_type=SentimentType(data.get('sentiment_type', 'neutral')),
                authenticity_score=float(data.get('authenticity_score', 0.5)),
                key_themes=[ReviewTheme(theme) for theme in data.get('key_themes', []) 
                           if theme in [t.value for t in ReviewTheme]],
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', 'No reasoning provided'),
                flagged_for_moderation=bool(data.get('flagged_for_moderation', False)),
                analyzed_at=datetime.now()
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            
            # Return a fallback analysis
            return ReviewAnalysis(
                review_id=review_id,
                product_id=product_id,
                sentiment_score=0.0,
                sentiment_type=SentimentType.NEUTRAL,
                authenticity_score=0.5,
                key_themes=[],
                confidence=0.1,
                reasoning="Failed to parse AI analysis",
                flagged_for_moderation=True,
                analyzed_at=datetime.now()
            )

    async def _update_product_summary(self, analysis: ReviewAnalysis) -> None:
        """Update the aggregated product summary with new analysis"""
        product_id = analysis.product_id
        
        if product_id not in self.product_summaries:
            self.product_summaries[product_id] = ProductReviewSummary(
                product_id=product_id,
                total_reviews=0,
                average_sentiment=0.0,
                sentiment_distribution={sentiment: 0 for sentiment in SentimentType},
                top_themes=[],
                authenticity_rate=0.0,
                recommendation_impact=0.0,
                last_updated=datetime.now()
            )
        
        summary = self.product_summaries[product_id]
        
        # Update counts and averages
        old_total = summary.total_reviews
        new_total = old_total + 1
        
        # Update average sentiment
        summary.average_sentiment = (
            (summary.average_sentiment * old_total + analysis.sentiment_score) / new_total
        )
        
        # Update sentiment distribution
        summary.sentiment_distribution[analysis.sentiment_type] += 1
        
        # Update authenticity rate
        old_auth_sum = summary.authenticity_rate * old_total
        summary.authenticity_rate = (old_auth_sum + analysis.authenticity_score) / new_total
        
        # Update theme tracking (simplified - in production, use proper frequency tracking)
        all_themes = list(summary.top_themes) + analysis.key_themes
        theme_counts = {}
        for theme in all_themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        summary.top_themes = sorted(theme_counts.keys(), 
                                  key=lambda x: theme_counts[x], 
                                  reverse=True)[:5]
        
        # Calculate recommendation impact
        summary.recommendation_impact = self._calculate_recommendation_impact(summary)
        
        summary.total_reviews = new_total
        summary.last_updated = datetime.now()

    def _calculate_recommendation_impact(self, summary: ProductReviewSummary) -> float:
        """Calculate how much reviews should impact product recommendations"""
        # Factors: sentiment, authenticity, review volume
        sentiment_factor = (summary.average_sentiment + 1) / 2  # Convert -1,1 to 0,1
        authenticity_factor = summary.authenticity_rate
        volume_factor = min(summary.total_reviews / 50, 1.0)  # Cap at 50 reviews
        
        return (sentiment_factor * 0.5 + authenticity_factor * 0.3 + volume_factor * 0.2)

    async def _notify_moderation_needed(self, analysis: ReviewAnalysis) -> None:
        """Notify other agents/systems when a review needs moderation"""
        try:
            message_data = {
                "review_id": analysis.review_id,
                "product_id": analysis.product_id,
                "reason": "low_authenticity" if analysis.authenticity_score < 0.3 else "flagged_content",
                "authenticity_score": analysis.authenticity_score,
                "flagged_for_moderation": analysis.flagged_for_moderation
            }
            
            await self.a2a_handler.send_notification(
                to_agent="moderation-system",
                notification_type="review_moderation_needed",
                payload=message_data
            )
            
            logger.info(f"Notified moderation system about review {analysis.review_id}")
            
        except Exception as e:
            logger.error(f"Failed to notify moderation system: {str(e)}")

    async def _handle_analyze_review_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analyze review requests from other agents"""
        try:
            request = ReviewRequest(**payload)
            analysis = await self.analyze_review(request)
            return analysis.to_dict()
        except Exception as e:
            logger.error(f"Error handling analyze review request: {str(e)}")
            raise

    async def _handle_get_product_sentiment_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get product sentiment requests from other agents"""
        try:
            product_id = payload.get('product_id')
            summary = await self.get_product_review_summary(product_id)
            return summary.to_dict() if summary else None
        except Exception as e:
            logger.error(f"Error handling get product sentiment request: {str(e)}")
            raise

    async def _handle_get_sentiment_trends_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get sentiment trends requests from other agents"""
        try:
            product_id = payload.get('product_id')
            days = payload.get('days', 30)
            trends = await self.get_sentiment_trends(product_id, days)
            return trends
        except Exception as e:
            logger.error(f"Error handling get sentiment trends request: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the agent"""
        try:
            # Test Gemini connection
            test_response = await self._get_gemini_analysis("Test prompt")
            gemini_healthy = bool(test_response)
        except:
            gemini_healthy = False
        
        return {
            'agent_id': self.agent_id,
            'status': 'healthy' if gemini_healthy else 'degraded',
            'gemini_connection': gemini_healthy,
            'cached_reviews': len(self.review_cache),
            'tracked_products': len(self.product_summaries),
            'uptime': (datetime.now() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
        }