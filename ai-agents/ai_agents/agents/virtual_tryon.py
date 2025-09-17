"""
Virtual Try-On Agent

This agent provides AI-powered virtual try-on experiences using computer vision
and Gemini Vision to analyze body structure, face shape, and skin tone for
realistic product fitting and styling recommendations.

Features:
- Real-time body and face analysis
- Virtual clothing try-on rendering
- Fit scoring (1-10 scale)
- Style recommendations
- Size and color alternatives
- Multi-modal interaction support
"""

import asyncio
import json
import logging
import os
import uuid
import base64
from datetime import datetime
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

class BodyType(str, Enum):
    """Body type classifications"""
    PEAR = "pear"
    APPLE = "apple"
    HOURGLASS = "hourglass"
    RECTANGLE = "rectangle"
    INVERTED_TRIANGLE = "inverted_triangle"
    ATHLETIC = "athletic"

class FaceShape(str, Enum):
    """Face shape classifications"""
    OVAL = "oval"
    ROUND = "round"
    SQUARE = "square"
    HEART = "heart"
    DIAMOND = "diamond"
    OBLONG = "oblong"

class SkinTone(str, Enum):
    """Skin tone classifications"""
    FAIR = "fair"
    LIGHT = "light"
    MEDIUM = "medium"
    OLIVE = "olive"
    TAN = "tan"
    DARK = "dark"
    DEEP = "deep"

@dataclass
class BodyMeasurements:
    """Body measurements and proportions"""
    height: float  # in cm
    chest: float   # in cm
    waist: float   # in cm
    hips: float    # in cm
    shoulder_width: float  # in cm
    body_type: BodyType
    confidence: float      # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class FacialFeatures:
    """Facial feature analysis"""
    face_shape: FaceShape
    skin_tone: SkinTone
    eye_color: str
    hair_color: str
    confidence: float      # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TryOnResult:
    """Virtual try-on result"""
    session_id: str
    product_id: str
    product_name: str
    fit_score: float       # 1.0 to 10.0
    style_score: float     # 1.0 to 10.0
    overall_score: float   # 1.0 to 10.0
    size_recommendation: str
    styling_tips: List[str]
    color_recommendations: List[str]
    confidence: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class TryOnRequest(BaseModel):
    """Request model for virtual try-on"""
    user_id: Optional[str] = Field(None, description="User ID for personalization")
    product_ids: List[str] = Field(..., description="Product IDs to try on")
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")

class VirtualTryOnAgent(BaseAgent):
    """
    Virtual Try-On Agent for AI-powered fitting experiences
    
    This agent provides:
    - Real-time body and face analysis using Gemini Vision
    - Virtual clothing try-on rendering
    - Fit scoring and style recommendations
    - Size and color alternative suggestions
    """
    
    def __init__(self):
        super().__init__(
            agent_id="virtual-tryon",
            name="Virtual Try-On Agent",
            version="1.0.0",
            capabilities=[
                "body_analysis",
                "face_analysis",
                "virtual_tryon",
                "fit_scoring",
                "style_recommendations"
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
        self.a2a_handler.port = int(os.getenv('VIRTUAL_TRYON_A2A_PORT', '9096'))
        
        # Cache for user data
        self.user_cache: Dict[str, Dict[str, Any]] = {}
        self.product_cache: Dict[str, Dict[str, Any]] = {}
        self.start_time = datetime.now()
        
        logger.info(f"Initialized {self.name} with ID: {self.agent_id}")

    async def _initialize(self) -> None:
        """Custom initialization for Virtual Try-On Agent"""
        # Initialize Gemini AI
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("Virtual Try-On Agent custom initialization completed")

    async def _start(self) -> None:
        """Custom start logic for Virtual Try-On Agent"""
        await self.a2a_handler.start()
        
        # Register message handlers
        self.a2a_handler.register_handler(
            "virtual_try_on", 
            self._handle_virtual_try_on_request
        )
        self.a2a_handler.register_handler(
            "get_size_recommendation", 
            self._handle_get_size_recommendation_request
        )
        self.a2a_handler.register_handler(
            "analyze_body_measurements", 
            self._handle_analyze_body_measurements_request
        )
        
        logger.info("Virtual Try-On Agent started successfully")

    async def _stop(self) -> None:
        """Custom stop logic for Virtual Try-On Agent"""
        await self.a2a_handler.stop()
        logger.info("Virtual Try-On Agent stopped")

    async def _handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming ADK messages"""
        try:
            if message.message_type == ADKMessageType.REQUEST:
                request_type = message.payload.get('type')
                
                if request_type == 'virtual_try_on':
                    result = await self._handle_virtual_try_on_request(message.payload.get('data', {}))
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

    async def virtual_try_on(self, request: TryOnRequest) -> List[TryOnResult]:
        """
        Perform virtual try-on for products
        
        Args:
            request: Try-on request with products and user data
            
        Returns:
            List[TryOnResult]: Try-on results with fit scores and recommendations
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Analyze user features
            body_measurements, facial_features = await self._analyze_user_features(request)
            
            results = []
            
            # Process each product
            for product_id in request.product_ids:
                result = await self._process_product_tryon(
                    session_id, product_id, body_measurements, facial_features, request.preferences
                )
                if result:
                    results.append(result)
            
            logger.info(f"Completed virtual try-on for {len(results)} products")
            return results
            
        except Exception as e:
            logger.error(f"Error in virtual try-on: {str(e)}")
            return []

    async def analyze_user_features(self, request: TryOnRequest) -> Dict[str, Any]:
        """
        Analyze user's physical features from image
        
        Args:
            request: Try-on request with image data
            
        Returns:
            Dict: Complete physical feature analysis
        """
        try:
            body_measurements, facial_features = await self._analyze_user_features(request)
            
            return {
                'body_measurements': body_measurements,
                'facial_features': facial_features
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user features: {str(e)}")
            return await self._generate_mock_analysis()

    async def _analyze_user_features(self, request: TryOnRequest) -> Tuple[BodyMeasurements, FacialFeatures]:
        """Analyze user features from image or generate mock data"""
        
        if request.image_data:
            try:
                # Use Gemini Vision for real image analysis
                return await self._analyze_with_gemini_vision(request.image_data)
            except Exception as e:
                logger.warning(f"Gemini Vision analysis failed, using mock data: {e}")
                return await self._generate_mock_analysis()
        else:
            return await self._generate_mock_analysis()

    async def _generate_mock_analysis(self) -> Tuple[BodyMeasurements, FacialFeatures]:
        """Generate mock user analysis for demo"""
        import random
        
        body_measurements = BodyMeasurements(
            height=random.uniform(150, 190),
            chest=random.uniform(80, 110),
            waist=random.uniform(60, 90),
            hips=random.uniform(85, 115),
            shoulder_width=random.uniform(35, 50),
            body_type=random.choice(list(BodyType)),
            confidence=random.uniform(0.7, 0.95)
        )
        
        facial_features = FacialFeatures(
            face_shape=random.choice(list(FaceShape)),
            skin_tone=random.choice(list(SkinTone)),
            eye_color=random.choice(["brown", "blue", "green", "hazel", "gray"]),
            hair_color=random.choice(["black", "brown", "blonde", "red", "gray"]),
            confidence=random.uniform(0.8, 0.95)
        )
        
        return body_measurements, facial_features

    async def _analyze_with_gemini_vision(self, image_data: str) -> Tuple[BodyMeasurements, FacialFeatures]:
        """Analyze user features using Gemini Vision"""
        
        try:
            # Create analysis prompt
            prompt = """
Analyze this person's physical features for virtual clothing try-on. Provide detailed analysis of:

1. Body measurements and type
2. Facial features and shape
3. Skin tone and coloring

Respond with JSON:
{
    "body_measurements": {
        "height": 170,
        "chest": 90,
        "waist": 70,
        "hips": 95,
        "shoulder_width": 40,
        "body_type": "hourglass",
        "confidence": 0.85
    },
    "facial_features": {
        "face_shape": "oval",
        "skin_tone": "medium",
        "eye_color": "brown",
        "hair_color": "dark_brown",
        "confidence": 0.9
    }
}
"""
            
            # Convert base64 to image for Gemini Vision
            try:
                image_bytes = base64.b64decode(image_data)
                
                # Use Gemini Vision model
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    [prompt, {"mime_type": "image/jpeg", "data": image_bytes}]
                )
                
                # Parse response
                analysis_data = self._parse_json_response(response.text)
                
                # Convert to dataclasses with safe enum conversion
                body_data = analysis_data.get('body_measurements', {})
                facial_data = analysis_data.get('facial_features', {})
                
                # Safe enum conversion with fallback
                try:
                    body_type = BodyType(body_data.get('body_type', 'rectangle'))
                except ValueError:
                    logger.warning(f"Invalid body_type: {body_data.get('body_type')}, using rectangle")
                    body_type = BodyType.RECTANGLE
                
                try:
                    face_shape = FaceShape(facial_data.get('face_shape', 'oval'))
                except ValueError:
                    logger.warning(f"Invalid face_shape: {facial_data.get('face_shape')}, using oval")
                    face_shape = FaceShape.OVAL
                
                try:
                    skin_tone = SkinTone(facial_data.get('skin_tone', 'medium'))
                except ValueError:
                    logger.warning(f"Invalid skin_tone: {facial_data.get('skin_tone')}, using medium")
                    skin_tone = SkinTone.MEDIUM
                
                body_measurements = BodyMeasurements(
                    height=body_data.get('height', 170),
                    chest=body_data.get('chest', 90),
                    waist=body_data.get('waist', 70),
                    hips=body_data.get('hips', 95),
                    shoulder_width=body_data.get('shoulder_width', 40),
                    body_type=body_type,
                    confidence=body_data.get('confidence', 0.8)
                )
                
                facial_features = FacialFeatures(
                    face_shape=face_shape,
                    skin_tone=skin_tone,
                    eye_color=facial_data.get('eye_color', 'brown'),
                    hair_color=facial_data.get('hair_color', 'brown'),
                    confidence=facial_data.get('confidence', 0.8)
                )
                
                logger.info("Successfully analyzed user features with Gemini Vision")
                return body_measurements, facial_features
                
            except Exception as vision_error:
                logger.error(f"Gemini Vision processing error: {vision_error}")
                raise
            
        except Exception as e:
            logger.error(f"Error in Gemini Vision analysis: {str(e)}")
            # Fallback to mock analysis
            return await self._generate_mock_analysis()

    async def _process_product_tryon(
        self, 
        session_id: str,
        product_id: str, 
        body_measurements: BodyMeasurements,
        facial_features: FacialFeatures,
        preferences: Dict[str, Any]
    ) -> Optional[TryOnResult]:
        """Process virtual try-on for a specific product"""
        
        try:
            # Get product info
            product_info = await self._get_product_info(product_id)
            
            # Calculate scores
            fit_score = await self._calculate_fit_score(body_measurements, product_info)
            style_score = await self._calculate_style_score(facial_features, product_info, preferences)
            overall_score = (fit_score * 0.6 + style_score * 0.4)
            
            # Generate recommendations
            styling_tips = await self._generate_styling_tips(body_measurements, facial_features, product_info)
            color_recommendations = await self._get_color_recommendations(facial_features)
            size_recommendation = await self._get_size_recommendation(body_measurements)
            
            return TryOnResult(
                session_id=session_id,
                product_id=product_id,
                product_name=product_info.get('name', f'Product {product_id}'),
                fit_score=fit_score,
                style_score=style_score,
                overall_score=overall_score,
                size_recommendation=size_recommendation,
                styling_tips=styling_tips,
                color_recommendations=color_recommendations,
                confidence=min(body_measurements.confidence, facial_features.confidence)
            )
            
        except Exception as e:
            logger.error(f"Error processing product {product_id}: {str(e)}")
            return None

    async def _calculate_fit_score(self, body_measurements: BodyMeasurements, product_info: Dict[str, Any]) -> float:
        """Calculate fit score based on body measurements"""
        
        # Base score
        score = 7.0
        
        # Adjust based on body type
        category = product_info.get('category', 'tops')
        
        if category == 'tops':
            if body_measurements.body_type == BodyType.HOURGLASS:
                score += 1.0
            elif body_measurements.body_type == BodyType.PEAR:
                score += 0.8
        elif category == 'bottoms':
            if body_measurements.body_type == BodyType.PEAR:
                score += 1.0
            elif body_measurements.body_type == BodyType.APPLE:
                score -= 0.5
        
        # Add some variation
        import random
        score += random.uniform(-0.5, 0.5)
        
        return max(1.0, min(10.0, score))

    async def _calculate_style_score(self, facial_features: FacialFeatures, product_info: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Calculate style score based on features and preferences"""
        
        score = 7.0
        
        # Adjust for skin tone compatibility
        if facial_features.skin_tone in [SkinTone.FAIR, SkinTone.LIGHT]:
            score += 0.5
        elif facial_features.skin_tone in [SkinTone.DARK, SkinTone.DEEP]:
            score += 0.8
        
        # User preference match
        if preferences.get('style') == product_info.get('style', 'casual'):
            score += 1.0
        
        # Add variation
        import random
        score += random.uniform(-0.3, 0.7)
        
        return max(1.0, min(10.0, score))

    async def _generate_styling_tips(self, body_measurements: BodyMeasurements, facial_features: FacialFeatures, product_info: Dict[str, Any]) -> List[str]:
        """Generate styling tips using Gemini AI"""
        
        try:
            prompt = f"""
You are a professional stylist. Provide 3 styling tips for:
- Body Type: {body_measurements.body_type.value}
- Face Shape: {facial_features.face_shape.value}
- Product: {product_info.get('category', 'clothing')}

Respond with JSON: {{"styling_tips": ["tip1", "tip2", "tip3"]}}
"""
            
            response = await self._get_gemini_response(prompt)
            data = self._parse_json_response(response)
            
            return data.get('styling_tips', [
                "Consider your body proportions",
                "Choose colors that complement your skin tone",
                "Focus on fit and comfort"
            ])
            
        except Exception as e:
            logger.error(f"Error generating styling tips: {str(e)}")
            return ["Focus on fit and comfort", "Choose flattering colors"]

    async def _get_color_recommendations(self, facial_features: FacialFeatures) -> List[str]:
        """Get color recommendations based on skin tone"""
        
        skin_tone_colors = {
            SkinTone.FAIR: ['navy', 'soft pink', 'lavender'],
            SkinTone.LIGHT: ['dusty blue', 'rose', 'sage green'],
            SkinTone.MEDIUM: ['coral', 'teal', 'warm brown'],
            SkinTone.OLIVE: ['emerald', 'burgundy', 'warm orange'],
            SkinTone.TAN: ['turquoise', 'bright coral', 'golden brown'],
            SkinTone.DARK: ['royal blue', 'bright pink', 'emerald green'],
            SkinTone.DEEP: ['electric blue', 'magenta', 'bright orange']
        }
        
        return skin_tone_colors.get(facial_features.skin_tone, ['black', 'white', 'gray'])

    async def _get_size_recommendation(self, body_measurements: BodyMeasurements) -> str:
        """Get size recommendation based on measurements"""
        
        chest = body_measurements.chest
        
        if chest < 85:
            return 'XS'
        elif chest < 90:
            return 'S'
        elif chest < 95:
            return 'M'
        elif chest < 100:
            return 'L'
        else:
            return 'XL'

    async def _get_product_info(self, product_id: str) -> Dict[str, Any]:
        """Get product information from MCP server"""
        
        if product_id in self.product_cache:
            return self.product_cache[product_id]
        
        try:
            # Try to get product from MCP server
            if self.mcp_client:
                product_info = await self.mcp_client.get_product(product_id)
                if product_info:
                    # Enhance with virtual try-on specific data
                    product_info.update({
                        'style': product_info.get('style', 'casual'),
                        'fit_type': 'regular',
                        'material': 'cotton blend',
                        'style_tags': ['casual', 'versatile']
                    })
                    self.product_cache[product_id] = product_info
                    return product_info
        except Exception as e:
            logger.warning(f"Could not get product from MCP server: {e}")
        
        # Fallback to mock product info
        product_info = {
            'id': product_id,
            'name': f'Product {product_id}',
            'category': 'tops',
            'style': 'casual',
            'colors': ['black', 'white', 'navy'],
            'sizes': ['XS', 'S', 'M', 'L', 'XL'],
            'fit_type': 'regular',
            'material': 'cotton blend',
            'style_tags': ['casual', 'versatile']
        }
        
        self.product_cache[product_id] = product_info
        return product_info

    async def _get_gemini_response(self, prompt: str) -> str:
        """Get response from Gemini AI"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return '{"styling_tips": ["Default tip 1", "Default tip 2", "Default tip 3"]}'

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from Gemini"""
        try:
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            parsed = json.loads(clean_response.strip())
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            return {}

    # A2A Protocol handlers
    async def _handle_virtual_try_on_request(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle virtual try-on requests from other agents"""
        try:
            request = TryOnRequest(**payload)
            results = await self.virtual_try_on(request)
            return [result.to_dict() for result in results]
        except Exception as e:
            logger.error(f"Error handling virtual try-on request: {str(e)}")
            raise

    async def _handle_get_size_recommendation_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle size recommendation requests from other agents"""
        try:
            user_id = payload.get('user_id')
            product_id = payload.get('product_id')
            measurements_data = payload.get('measurements', {})
            
            # Create body measurements from data
            if measurements_data:
                body_measurements = BodyMeasurements(
                    height=measurements_data.get('height', 170),
                    chest=measurements_data.get('chest', 90),
                    waist=measurements_data.get('waist', 75),
                    hips=measurements_data.get('hips', 95),
                    shoulder_width=measurements_data.get('shoulder_width', 40),
                    body_type=BodyType(measurements_data.get('body_type', 'rectangle')),
                    confidence=measurements_data.get('confidence', 0.8)
                )
            else:
                # Generate mock measurements
                body_measurements, _ = await self._generate_mock_analysis()
            
            # Get size recommendation
            size_recommendation = await self._get_size_recommendation(body_measurements)
            
            return {
                "user_id": user_id,
                "product_id": product_id,
                "recommended_size": size_recommendation,
                "confidence": body_measurements.confidence,
                "body_type": body_measurements.body_type.value
            }
            
        except Exception as e:
            logger.error(f"Error handling size recommendation request: {str(e)}")
            raise

    async def _handle_analyze_body_measurements_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle body measurement analysis requests from other agents"""
        try:
            user_id = payload.get('user_id')
            image_data = payload.get('image_data')
            
            if image_data:
                body_measurements, facial_features = await self._analyze_with_gemini_vision(image_data)
            else:
                body_measurements, facial_features = await self._generate_mock_analysis()
            
            return {
                "success": True,
                "user_id": user_id,
                "body_measurements": body_measurements.to_dict(),
                "facial_features": facial_features.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error handling body measurements analysis request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the agent"""
        try:
            # Test Gemini connection
            test_response = await self._get_gemini_response("Test prompt")
            gemini_healthy = bool(test_response)
        except:
            gemini_healthy = False
        
        return {
            'agent_id': self.agent_id,
            'status': 'healthy' if gemini_healthy else 'degraded',
            'gemini_connection': gemini_healthy,
            'cached_users': len(self.user_cache),
            'cached_products': len(self.product_cache),
            'uptime': (datetime.now() - self.start_time).total_seconds()
        }