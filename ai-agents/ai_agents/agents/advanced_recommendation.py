"""
Advanced Recommendation Agent

This agent provides personalized product recommendations using Gemini AI,
analyzing user behavior, preferences, and context to suggest relevant products.

Features:
- Real-time personalized recommendations
- Complementary product suggestions
- Adaptive learning from user behavior
- Seasonal trend integration
- Cold-start recommendations for new users
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
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

class RecommendationType(str, Enum):
    """Types of recommendations"""
    PERSONALIZED = "personalized"
    COMPLEMENTARY = "complementary"
    TRENDING = "trending"
    SIMILAR = "similar"
    SEASONAL = "seasonal"
    COLD_START = "cold_start"

class UserSegment(str, Enum):
    """User segments for recommendations"""
    NEW_USER = "new_user"
    FREQUENT_BUYER = "frequent_buyer"
    PRICE_CONSCIOUS = "price_conscious"
    FASHION_FORWARD = "fashion_forward"
    CASUAL_SHOPPER = "casual_shopper"

@dataclass
class UserProfile:
    """User profile for personalization"""
    user_id: str
    segment: UserSegment
    preferences: Dict[str, Any]
    purchase_history: List[str]
    browsing_history: List[str]
    demographics: Dict[str, Any]
    last_activity: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['last_activity'] = self.last_activity.isoformat()
        return result

@dataclass
class RecommendationContext:
    """Context for generating recommendations"""
    user_profile: Optional[UserProfile]
    current_cart: List[str]
    current_product: Optional[str]
    session_data: Dict[str, Any]
    time_of_day: str
    season: str
    device_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.user_profile:
            result['user_profile'] = self.user_profile.to_dict()
        return result

@dataclass
class ProductRecommendation:
    """Individual product recommendation"""
    product_id: str
    product_name: str
    confidence_score: float  # 0.0 to 1.0
    recommendation_type: RecommendationType
    reasoning: str
    price: float
    category: str
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class RecommendationResponse:
    """Complete recommendation response"""
    recommendations: List[ProductRecommendation]
    user_segment: UserSegment
    context_used: Dict[str, Any]
    generated_at: datetime
    expires_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['recommendations'] = [rec.to_dict() for rec in self.recommendations]
        result['generated_at'] = self.generated_at.isoformat()
        result['expires_at'] = self.expires_at.isoformat()
        return result

class RecommendationRequest(BaseModel):
    """Request model for recommendations"""
    user_id: Optional[str] = Field(None, description="User ID for personalization")
    context: Dict[str, Any] = Field(default_factory=dict, description="Recommendation context")
    recommendation_type: RecommendationType = Field(RecommendationType.PERSONALIZED, description="Type of recommendation")
    limit: int = Field(10, ge=1, le=50, description="Number of recommendations")
    exclude_products: List[str] = Field(default_factory=list, description="Products to exclude")

class AdvancedRecommendationAgent(BaseAgent):
    """
    AI Agent for advanced product recommendations
    
    This agent provides intelligent product recommendations using:
    - Gemini AI for understanding user preferences
    - Behavioral analysis and pattern recognition
    - Real-time adaptation to user actions
    - Seasonal and trending product integration
    """
    
    def __init__(self):
        super().__init__(
            agent_id="advanced-recommendation",
            name="Advanced Recommendation Agent",
            version="1.0.0",
            capabilities=[
                "personalized_recommendations",
                "behavioral_analysis",
                "trend_analysis",
                "real_time_adaptation"
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
        self.a2a_handler.port = int(os.getenv('RECOMMENDATION_AGENT_A2A_PORT', '9092'))
        
        # User profiles and recommendation cache
        self.user_profiles: Dict[str, UserProfile] = {}
        self.recommendation_cache: Dict[str, RecommendationResponse] = {}
        self.product_catalog: Dict[str, Dict[str, Any]] = {}
        
        # ML models and patterns (simplified for demo)
        self.user_patterns: Dict[str, Dict[str, Any]] = {}
        self.trending_products: List[str] = []
        
        logger.info(f"Initialized {self.name} with ID: {self.agent_id}")

    async def _initialize(self) -> None:
        """Custom initialization for Advanced Recommendation Agent"""
        # Initialize Gemini AI
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Load initial product catalog (mock data)
        await self._load_product_catalog()
        
        # Initialize trending products
        await self._update_trending_products()
        
        logger.info("Advanced Recommendation Agent custom initialization completed")

    async def _start(self) -> None:
        """Custom start logic for Advanced Recommendation Agent"""
        await self.a2a_handler.start()
        
        # Register message handlers
        self.a2a_handler.register_handler(
            "get_recommendations", 
            self._handle_get_recommendations_request
        )
        self.a2a_handler.register_handler(
            "update_user_behavior", 
            self._handle_update_user_behavior_request
        )
        self.a2a_handler.register_handler(
            "get_complementary_products", 
            self._handle_get_complementary_products_request
        )
        
        # Start background tasks
        asyncio.create_task(self._trending_update_loop())
        asyncio.create_task(self._cache_cleanup_loop())
        
        logger.info("Advanced Recommendation Agent started successfully")

    async def _stop(self) -> None:
        """Custom stop logic for Advanced Recommendation Agent"""
        await self.a2a_handler.stop()
        logger.info("Advanced Recommendation Agent stopped")

    async def _handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming ADK messages"""
        try:
            if message.message_type == ADKMessageType.REQUEST:
                request_type = message.payload.get('type')
                
                if request_type == 'get_recommendations':
                    result = await self._handle_get_recommendations_request(message.payload.get('data', {}))
                    return AgentMessage(
                        id=f"response_{message.id}",
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type=ADKMessageType.RESPONSE,
                        payload={'result': result}
                    )
                elif request_type == 'update_user_behavior':
                    result = await self._handle_update_user_behavior_request(message.payload.get('data', {}))
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

    async def get_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        """
        Get personalized product recommendations
        
        Args:
            request: Recommendation request with user context
            
        Returns:
            RecommendationResponse: Personalized recommendations
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            if cache_key in self.recommendation_cache:
                cached = self.recommendation_cache[cache_key]
                if datetime.now() < cached.expires_at:
                    logger.debug(f"Returning cached recommendations for {request.user_id}")
                    return cached
            
            # Get or create user profile
            user_profile = await self._get_or_create_user_profile(request.user_id, request.context)
            
            # Build recommendation context
            context = RecommendationContext(
                user_profile=user_profile,
                current_cart=request.context.get('current_cart', []),
                current_product=request.context.get('current_product'),
                session_data=request.context.get('session_data', {}),
                time_of_day=self._get_time_of_day(),
                season=self._get_current_season(),
                device_type=request.context.get('device_type', 'desktop')
            )
            
            # Generate recommendations based on type
            if request.recommendation_type == RecommendationType.PERSONALIZED:
                recommendations = await self._generate_personalized_recommendations(context, request.limit, request.exclude_products)
            elif request.recommendation_type == RecommendationType.COMPLEMENTARY:
                recommendations = await self._generate_complementary_recommendations(context, request.limit, request.exclude_products)
            elif request.recommendation_type == RecommendationType.TRENDING:
                recommendations = await self._generate_trending_recommendations(context, request.limit, request.exclude_products)
            else:
                recommendations = await self._generate_personalized_recommendations(context, request.limit, request.exclude_products)
            
            # Create response
            response = RecommendationResponse(
                recommendations=recommendations,
                user_segment=user_profile.segment if user_profile else UserSegment.NEW_USER,
                context_used=context.to_dict(),
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=30)
            )
            
            # Cache the response
            self.recommendation_cache[cache_key] = response
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {request.user_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            # Return empty recommendations on error
            return RecommendationResponse(
                recommendations=[],
                user_segment=UserSegment.NEW_USER,
                context_used={},
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=5)
            )

    async def _generate_personalized_recommendations(
        self, 
        context: RecommendationContext, 
        limit: int, 
        exclude_products: List[str]
    ) -> List[ProductRecommendation]:
        """Generate personalized recommendations using Gemini AI"""
        
        # Create prompt for Gemini
        prompt = self._create_recommendation_prompt(context, "personalized")
        
        try:
            # Get AI recommendations
            response = await self._get_gemini_recommendations(prompt)
            
            # Parse and validate recommendations
            recommendations = self._parse_gemini_recommendations(response, RecommendationType.PERSONALIZED)
            
            # Filter out excluded products
            recommendations = [rec for rec in recommendations if rec.product_id not in exclude_products]
            
            # Limit results
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error generating personalized recommendations: {str(e)}")
            return await self._fallback_recommendations(context, limit, exclude_products)

    async def _generate_complementary_recommendations(
        self, 
        context: RecommendationContext, 
        limit: int, 
        exclude_products: List[str]
    ) -> List[ProductRecommendation]:
        """Generate complementary product recommendations"""
        
        if not context.current_cart and not context.current_product:
            return await self._generate_personalized_recommendations(context, limit, exclude_products)
        
        # Create prompt for complementary products
        prompt = self._create_recommendation_prompt(context, "complementary")
        
        try:
            response = await self._get_gemini_recommendations(prompt)
            recommendations = self._parse_gemini_recommendations(response, RecommendationType.COMPLEMENTARY)
            
            # Filter and limit
            recommendations = [rec for rec in recommendations if rec.product_id not in exclude_products]
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error generating complementary recommendations: {str(e)}")
            return await self._fallback_recommendations(context, limit, exclude_products)

    async def _generate_trending_recommendations(
        self, 
        context: RecommendationContext, 
        limit: int, 
        exclude_products: List[str]
    ) -> List[ProductRecommendation]:
        """Generate trending product recommendations"""
        
        recommendations = []
        
        for product_id in self.trending_products:
            if product_id in exclude_products:
                continue
                
            if product_id in self.product_catalog:
                product = self.product_catalog[product_id]
                
                rec = ProductRecommendation(
                    product_id=product_id,
                    product_name=product.get('name', 'Unknown Product'),
                    confidence_score=0.8,  # High confidence for trending
                    recommendation_type=RecommendationType.TRENDING,
                    reasoning="Currently trending product",
                    price=product.get('price', 0.0),
                    category=product.get('category', 'Unknown'),
                    image_url=product.get('image_url')
                )
                
                recommendations.append(rec)
                
                if len(recommendations) >= limit:
                    break
        
        return recommendations

    def _create_recommendation_prompt(self, context: RecommendationContext, rec_type: str) -> str:
        """Create a prompt for Gemini AI recommendation generation"""
        
        base_prompt = f"""
You are an expert e-commerce recommendation system. Generate {rec_type} product recommendations.

Context:
- Time: {context.time_of_day}
- Season: {context.season}
- Device: {context.device_type}
"""
        
        if context.user_profile:
            base_prompt += f"""
User Profile:
- Segment: {context.user_profile.segment.value}
- Purchase History: {context.user_profile.purchase_history[-5:] if context.user_profile.purchase_history else 'None'}
- Preferences: {context.user_profile.preferences}
"""
        
        if context.current_cart:
            base_prompt += f"""
Current Cart: {context.current_cart}
"""
        
        if context.current_product:
            base_prompt += f"""
Current Product: {context.current_product}
"""
        
        base_prompt += f"""
Available Products (sample): {list(self.product_catalog.keys())[:20]}

Please recommend products and respond with a JSON array of objects with this structure:
[
  {{
    "product_id": "PRODUCT_ID",
    "product_name": "Product Name",
    "confidence_score": 0.85,
    "reasoning": "Why this product is recommended",
    "category": "Category"
  }}
]

Focus on {rec_type} recommendations. Provide 5-10 recommendations.
"""
        
        return base_prompt

    async def _get_gemini_recommendations(self, prompt: str) -> str:
        """Get recommendations from Gemini AI"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise

    def _parse_gemini_recommendations(self, response: str, rec_type: RecommendationType) -> List[ProductRecommendation]:
        """Parse Gemini response into ProductRecommendation objects"""
        try:
            # Clean the response
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            data = json.loads(clean_response.strip())
            
            recommendations = []
            for item in data:
                if isinstance(item, dict):
                    product_id = item.get('product_id', 'unknown')
                    
                    # Get product details from catalog
                    product_info = self.product_catalog.get(product_id, {})
                    
                    rec = ProductRecommendation(
                        product_id=product_id,
                        product_name=item.get('product_name', product_info.get('name', 'Unknown Product')),
                        confidence_score=float(item.get('confidence_score', 0.5)),
                        recommendation_type=rec_type,
                        reasoning=item.get('reasoning', 'AI recommended'),
                        price=product_info.get('price', 0.0),
                        category=item.get('category', product_info.get('category', 'Unknown')),
                        image_url=product_info.get('image_url')
                    )
                    
                    recommendations.append(rec)
            
            return recommendations
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing Gemini recommendations: {str(e)}")
            logger.debug(f"Raw response: {response}")
            return []

    async def _fallback_recommendations(
        self, 
        context: RecommendationContext, 
        limit: int, 
        exclude_products: List[str]
    ) -> List[ProductRecommendation]:
        """Fallback recommendations when AI fails"""
        
        recommendations = []
        
        # Use trending products as fallback
        for product_id in self.trending_products:
            if product_id in exclude_products:
                continue
                
            if product_id in self.product_catalog:
                product = self.product_catalog[product_id]
                
                rec = ProductRecommendation(
                    product_id=product_id,
                    product_name=product.get('name', 'Unknown Product'),
                    confidence_score=0.6,
                    recommendation_type=RecommendationType.TRENDING,
                    reasoning="Fallback recommendation",
                    price=product.get('price', 0.0),
                    category=product.get('category', 'Unknown'),
                    image_url=product.get('image_url')
                )
                
                recommendations.append(rec)
                
                if len(recommendations) >= limit:
                    break
        
        return recommendations

    async def _get_or_create_user_profile(self, user_id: Optional[str], context: Dict[str, Any]) -> Optional[UserProfile]:
        """Get existing user profile or create new one"""
        
        if not user_id:
            return None
            
        if user_id in self.user_profiles:
            # Update last activity
            self.user_profiles[user_id].last_activity = datetime.now()
            return self.user_profiles[user_id]
        
        # Create new user profile
        profile = UserProfile(
            user_id=user_id,
            segment=self._determine_user_segment(context),
            preferences=context.get('preferences', {}),
            purchase_history=context.get('purchase_history', []),
            browsing_history=context.get('browsing_history', []),
            demographics=context.get('demographics', {}),
            last_activity=datetime.now()
        )
        
        self.user_profiles[user_id] = profile
        logger.info(f"Created new user profile for {user_id}")
        
        return profile

    def _determine_user_segment(self, context: Dict[str, Any]) -> UserSegment:
        """Determine user segment based on context"""
        
        purchase_history = context.get('purchase_history', [])
        
        if not purchase_history:
            return UserSegment.NEW_USER
        elif len(purchase_history) > 10:
            return UserSegment.FREQUENT_BUYER
        else:
            return UserSegment.CASUAL_SHOPPER

    async def _load_product_catalog(self):
        """Load product catalog (mock data for demo)"""
        
        # Mock product catalog
        self.product_catalog = {
            "OLJCESPC7Z": {
                "name": "Vintage Typewriter",
                "price": 67.99,
                "category": "Accessories",
                "image_url": "/static/img/products/typewriter.jpg"
            },
            "66VCHSJNUP": {
                "name": "Vintage Record Player",
                "price": 65.50,
                "category": "Electronics",
                "image_url": "/static/img/products/record-player.jpg"
            },
            "1YMWWN1N4O": {
                "name": "Home Barista Kit",
                "price": 124.99,
                "category": "Kitchen",
                "image_url": "/static/img/products/barista-kit.jpg"
            },
            "L9ECAV7KIM": {
                "name": "Terrarium Kit",
                "price": 36.45,
                "category": "Garden",
                "image_url": "/static/img/products/terrarium.jpg"
            },
            "2ZYFJ3GM2N": {
                "name": "Film Camera",
                "price": 2275.00,
                "category": "Electronics",
                "image_url": "/static/img/products/film-camera.jpg"
            }
        }
        
        logger.info(f"Loaded {len(self.product_catalog)} products into catalog")

    async def _update_trending_products(self):
        """Update trending products list"""
        
        # Mock trending products (in production, this would come from analytics)
        self.trending_products = [
            "OLJCESPC7Z",  # Vintage Typewriter
            "66VCHSJNUP",  # Vintage Record Player
            "1YMWWN1N4O",  # Home Barista Kit
            "L9ECAV7KIM",  # Terrarium Kit
        ]
        
        logger.info(f"Updated trending products: {len(self.trending_products)} items")

    def _generate_cache_key(self, request: RecommendationRequest) -> str:
        """Generate cache key for recommendation request"""
        
        key_parts = [
            request.user_id or "anonymous",
            request.recommendation_type.value,
            str(request.limit),
            str(sorted(request.exclude_products)),
            str(hash(str(sorted(request.context.items()))))
        ]
        
        return "|".join(key_parts)

    def _get_time_of_day(self) -> str:
        """Get current time of day"""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def _get_current_season(self) -> str:
        """Get current season"""
        month = datetime.now().month
        
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"

    async def _trending_update_loop(self):
        """Background task to update trending products"""
        while True:
            try:
                await asyncio.sleep(3600)  # Update every hour
                await self._update_trending_products()
            except Exception as e:
                logger.error(f"Error updating trending products: {str(e)}")
                await asyncio.sleep(300)  # Retry in 5 minutes

    async def _cache_cleanup_loop(self):
        """Background task to clean up expired cache entries"""
        while True:
            try:
                await asyncio.sleep(600)  # Clean up every 10 minutes
                
                current_time = datetime.now()
                expired_keys = [
                    key for key, response in self.recommendation_cache.items()
                    if current_time > response.expires_at
                ]
                
                for key in expired_keys:
                    del self.recommendation_cache[key]
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except Exception as e:
                logger.error(f"Error in cache cleanup: {str(e)}")
                await asyncio.sleep(300)

    # A2A Protocol handlers
    async def _handle_get_recommendations_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get recommendations requests from other agents"""
        try:
            request = RecommendationRequest(**payload)
            response = await self.get_recommendations(request)
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error handling get recommendations request: {str(e)}")
            raise

    async def _handle_update_user_behavior_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user behavior update requests from other agents"""
        try:
            user_id = payload.get('user_id')
            behavior_data = payload.get('behavior_data', {})
            
            if user_id and user_id in self.user_profiles:
                profile = self.user_profiles[user_id]
                
                # Update browsing history
                if 'viewed_product' in behavior_data:
                    profile.browsing_history.append(behavior_data['viewed_product'])
                    profile.browsing_history = profile.browsing_history[-50:]  # Keep last 50
                
                # Update purchase history
                if 'purchased_product' in behavior_data:
                    profile.purchase_history.append(behavior_data['purchased_product'])
                
                # Update preferences
                if 'preferences' in behavior_data:
                    profile.preferences.update(behavior_data['preferences'])
                
                profile.last_activity = datetime.now()
                
                logger.info(f"Updated behavior for user {user_id}")
                
            return {"status": "success", "updated": user_id is not None}
            
        except Exception as e:
            logger.error(f"Error handling update user behavior request: {str(e)}")
            raise

    async def _handle_get_complementary_products_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle complementary products requests from other agents"""
        try:
            product_ids = payload.get('product_ids', [])
            limit = payload.get('limit', 5)
            
            # Create context for complementary recommendations
            context = RecommendationContext(
                user_profile=None,
                current_cart=product_ids,
                current_product=product_ids[0] if product_ids else None,
                session_data={},
                time_of_day=self._get_time_of_day(),
                season=self._get_current_season(),
                device_type="web"
            )
            
            recommendations = await self._generate_complementary_recommendations(context, limit, product_ids)
            
            return {
                "complementary_products": [rec.to_dict() for rec in recommendations]
            }
            
        except Exception as e:
            logger.error(f"Error handling get complementary products request: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the agent"""
        try:
            # Test Gemini connection
            test_response = await self._get_gemini_recommendations("Test prompt for health check")
            gemini_healthy = bool(test_response)
        except:
            gemini_healthy = False
        
        return {
            'agent_id': self.agent_id,
            'status': 'healthy' if gemini_healthy else 'degraded',
            'gemini_connection': gemini_healthy,
            'cached_recommendations': len(self.recommendation_cache),
            'user_profiles': len(self.user_profiles),
            'product_catalog_size': len(self.product_catalog),
            'trending_products': len(self.trending_products),
            'uptime': (datetime.now() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
        }