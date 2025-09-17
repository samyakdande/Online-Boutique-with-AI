"""
AI Chatbot Agent

This agent provides intelligent conversational AI for customer support,
product assistance, and shopping guidance using Gemini models with
multi-modal capabilities (text, voice, and video).

Features:
- Natural language conversations
- Product information and recommendations
- Shopping assistance and guidance
- Voice interaction capabilities
- Context-aware responses
- Escalation to human support
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
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

class ConversationState(str, Enum):
    """Conversation states"""
    GREETING = "greeting"
    PRODUCT_INQUIRY = "product_inquiry"
    SHOPPING_ASSISTANCE = "shopping_assistance"
    TECHNICAL_SUPPORT = "technical_support"
    ESCALATION = "escalation"
    CLOSING = "closing"

class MessageType(str, Enum):
    """Message types for chatbot"""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    VIDEO = "video"

class IntentType(str, Enum):
    """Intent classification"""
    GREETING = "greeting"
    PRODUCT_QUESTION = "product_question"
    RECOMMENDATION_REQUEST = "recommendation_request"
    ORDER_INQUIRY = "order_inquiry"
    SIZING_HELP = "sizing_help"
    PRICE_QUESTION = "price_question"
    AVAILABILITY_CHECK = "availability_check"
    COMPLAINT = "complaint"
    COMPLIMENT = "compliment"
    GOODBYE = "goodbye"
    ESCALATION_REQUEST = "escalation_request"
    UNKNOWN = "unknown"

@dataclass
class ConversationContext:
    """Context for maintaining conversation state"""
    session_id: str
    user_id: Optional[str]
    state: ConversationState
    intent_history: List[IntentType]
    mentioned_products: List[str]
    user_preferences: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    created_at: datetime
    last_activity: datetime
    escalation_requested: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        result['last_activity'] = self.last_activity.isoformat()
        return result

@dataclass
class ChatMessage:
    """Individual chat message"""
    message_id: str
    session_id: str
    sender: str  # 'user' or 'bot'
    content: str
    message_type: MessageType
    intent: Optional[IntentType]
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class ChatResponse:
    """Chatbot response"""
    message_id: str
    session_id: str
    content: str
    suggestions: List[str]
    actions: List[Dict[str, Any]]
    context_updated: bool
    escalation_needed: bool
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ChatRequest(BaseModel):
    """Request model for chat interactions"""
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_id: Optional[str] = Field(None, description="User ID for personalization")
    message: str = Field(..., description="User message")
    message_type: MessageType = Field(MessageType.TEXT, description="Type of message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class AIChatbotAgent(BaseAgent):
    """
    AI Chatbot Agent for customer interactions
    
    This agent provides intelligent conversational AI using:
    - Gemini Pro for natural language understanding
    - Context-aware conversation management
    - Multi-modal interaction support
    - Product knowledge integration
    - Escalation handling
    """
    
    def __init__(self):
        super().__init__(
            agent_id="ai-chatbot",
            name="AI Chatbot Agent",
            version="1.0.0",
            capabilities=[
                "natural_language_processing",
                "conversation_management",
                "product_assistance",
                "voice_interaction",
                "context_awareness"
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
        self.a2a_handler.port = int(os.getenv('CHATBOT_AGENT_A2A_PORT', '9093'))
        
        # Conversation management
        self.active_sessions: Dict[str, ConversationContext] = {}
        self.message_history: Dict[str, List[ChatMessage]] = {}
        
        # Knowledge base (simplified for demo)
        self.product_knowledge: Dict[str, Dict[str, Any]] = {}
        self.faq_knowledge: Dict[str, str] = {}
        
        # Intent classification patterns
        self.intent_patterns = self._initialize_intent_patterns()
        
        logger.info(f"Initialized {self.name} with ID: {self.agent_id}")

    async def _initialize(self) -> None:
        """Custom initialization for AI Chatbot Agent"""
        # Initialize Gemini AI
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Load knowledge bases
        await self._load_product_knowledge()
        await self._load_faq_knowledge()
        
        logger.info("AI Chatbot Agent custom initialization completed")

    async def _start(self) -> None:
        """Custom start logic for AI Chatbot Agent"""
        await self.a2a_handler.start()
        
        # Register message handlers
        self.a2a_handler.register_handler(
            "chat_message", 
            self._handle_chat_message_request
        )
        self.a2a_handler.register_handler(
            "get_conversation_context", 
            self._handle_get_conversation_context_request
        )
        self.a2a_handler.register_handler(
            "escalate_conversation", 
            self._handle_escalate_conversation_request
        )
        
        # Start background tasks
        asyncio.create_task(self._session_cleanup_loop())
        
        logger.info("AI Chatbot Agent started successfully")

    async def _stop(self) -> None:
        """Custom stop logic for AI Chatbot Agent"""
        await self.a2a_handler.stop()
        logger.info("AI Chatbot Agent stopped")

    async def _handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming ADK messages"""
        try:
            if message.message_type == ADKMessageType.REQUEST:
                request_type = message.payload.get('type')
                
                if request_type == 'chat_message':
                    result = await self._handle_chat_message_request(message.payload.get('data', {}))
                    return AgentMessage(
                        id=f"response_{message.id}",
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type=ADKMessageType.RESPONSE,
                        payload={'result': result}
                    )
                elif request_type == 'get_conversation_context':
                    result = await self._handle_get_conversation_context_request(message.payload.get('data', {}))
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

    async def process_chat_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message and generate response
        
        Args:
            request: Chat request with user message
            
        Returns:
            ChatResponse: Bot response with suggestions and actions
        """
        try:
            # Get or create session
            session_id = request.session_id or str(uuid.uuid4())
            context = await self._get_or_create_session(session_id, request.user_id)
            
            # Create user message
            user_message = ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                sender="user",
                content=request.message,
                message_type=request.message_type,
                intent=None,
                confidence=1.0,
                timestamp=datetime.now(),
                metadata=request.context
            )
            
            # Classify intent
            intent, confidence = await self._classify_intent(request.message, context)
            user_message.intent = intent
            user_message.confidence = confidence
            
            # Store message
            if session_id not in self.message_history:
                self.message_history[session_id] = []
            self.message_history[session_id].append(user_message)
            
            # Update context
            context.intent_history.append(intent)
            context.last_activity = datetime.now()
            context.conversation_history.append(user_message.to_dict())
            
            # Generate response
            response_content, suggestions, actions = await self._generate_response(
                user_message, context
            )
            
            # Create bot message
            bot_message = ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                sender="bot",
                content=response_content,
                message_type=MessageType.TEXT,
                intent=intent,
                confidence=confidence,
                timestamp=datetime.now()
            )
            
            # Store bot message
            self.message_history[session_id].append(bot_message)
            context.conversation_history.append(bot_message.to_dict())
            
            # Update conversation state
            await self._update_conversation_state(context, intent)
            
            # Check for escalation
            escalation_needed = await self._check_escalation_needed(context, intent)
            
            response = ChatResponse(
                message_id=bot_message.message_id,
                session_id=session_id,
                content=response_content,
                suggestions=suggestions,
                actions=actions,
                context_updated=True,
                escalation_needed=escalation_needed,
                confidence=confidence
            )
            
            logger.info(f"Processed chat message for session {session_id}: intent={intent.value}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            # Return error response
            return ChatResponse(
                message_id=str(uuid.uuid4()),
                session_id=request.session_id or "error",
                content="I'm sorry, I'm having trouble understanding right now. Please try again.",
                suggestions=["Can you rephrase that?", "Contact support"],
                actions=[],
                context_updated=False,
                escalation_needed=True,
                confidence=0.0
            )

    async def _classify_intent(self, message: str, context: ConversationContext) -> tuple[IntentType, float]:
        """Classify user intent using Gemini AI"""
        
        # Create intent classification prompt
        prompt = self._create_intent_classification_prompt(message, context)
        
        try:
            response = await self._get_gemini_response(prompt)
            intent, confidence = self._parse_intent_response(response)
            return intent, confidence
            
        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            return IntentType.UNKNOWN, 0.5

    async def _generate_response(
        self, 
        user_message: ChatMessage, 
        context: ConversationContext
    ) -> tuple[str, List[str], List[Dict[str, Any]]]:
        """Generate chatbot response using Gemini AI"""
        
        # Create response generation prompt
        prompt = self._create_response_prompt(user_message, context)
        
        try:
            response = await self._get_gemini_response(prompt)
            content, suggestions, actions = self._parse_response(response, user_message.intent)
            
            # Enhance with product information if needed
            if user_message.intent in [IntentType.PRODUCT_QUESTION, IntentType.RECOMMENDATION_REQUEST]:
                content, actions = await self._enhance_with_product_info(content, actions, user_message.content)
            
            return content, suggestions, actions
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._get_fallback_response(user_message.intent)

    def _create_intent_classification_prompt(self, message: str, context: ConversationContext) -> str:
        """Create prompt for intent classification"""
        
        prompt = f"""
You are an expert intent classifier for an e-commerce chatbot. Classify the user's intent.

User Message: "{message}"

Conversation Context:
- Current State: {context.state.value}
- Recent Intents: {[intent.value for intent in context.intent_history[-3:]]}
- Mentioned Products: {context.mentioned_products}

Available Intent Types:
- greeting: User is greeting or starting conversation
- product_question: User asking about specific products
- recommendation_request: User wants product recommendations
- order_inquiry: User asking about orders or purchases
- sizing_help: User needs help with sizing
- price_question: User asking about prices
- availability_check: User checking product availability
- complaint: User has a complaint or issue
- compliment: User giving positive feedback
- goodbye: User ending conversation
- escalation_request: User wants to speak to human
- unknown: Intent unclear

Respond with JSON:
{{
    "intent": "intent_name",
    "confidence": 0.85,
    "reasoning": "Brief explanation"
}}
"""
        return prompt

    def _create_response_prompt(self, user_message: ChatMessage, context: ConversationContext) -> str:
        """Create prompt for response generation"""
        
        prompt = f"""
You are a helpful, friendly AI shopping assistant for an online boutique. Generate a natural response.

User Message: "{user_message.content}"
Intent: {user_message.intent.value if user_message.intent else 'unknown'}
Confidence: {user_message.confidence}

Conversation Context:
- Session Duration: {(datetime.now() - context.created_at).total_seconds() / 60:.1f} minutes
- Previous Messages: {len(context.conversation_history)}
- User Preferences: {context.user_preferences}
- Mentioned Products: {context.mentioned_products}

Guidelines:
- Be helpful, friendly, and conversational
- Keep responses concise but informative
- Offer specific suggestions when appropriate
- If you don't know something, be honest
- For product questions, provide detailed information
- For recommendations, ask clarifying questions if needed

Respond with JSON:
{{
    "content": "Your response text here",
    "suggestions": ["Suggestion 1", "Suggestion 2", "Suggestion 3"],
    "actions": [
        {{"type": "show_products", "product_ids": ["PROD1", "PROD2"]}},
        {{"type": "open_category", "category": "accessories"}}
    ]
}}
"""
        return prompt

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
            raise

    def _parse_intent_response(self, response: str) -> tuple[IntentType, float]:
        """Parse Gemini intent classification response"""
        try:
            # Clean response
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            data = json.loads(clean_response.strip())
            
            intent_str = data.get('intent', 'unknown')
            confidence = float(data.get('confidence', 0.5))
            
            # Map to enum
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.UNKNOWN
            
            return intent, confidence
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing intent response: {str(e)}")
            return IntentType.UNKNOWN, 0.5

    def _parse_response(self, response: str, intent: Optional[IntentType]) -> tuple[str, List[str], List[Dict[str, Any]]]:
        """Parse Gemini response generation"""
        try:
            # Clean response
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            data = json.loads(clean_response.strip())
            
            content = data.get('content', 'I understand. How can I help you?')
            suggestions = data.get('suggestions', [])
            actions = data.get('actions', [])
            
            return content, suggestions, actions
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing response: {str(e)}")
            return self._get_fallback_response(intent)

    def _get_fallback_response(self, intent: Optional[IntentType]) -> tuple[str, List[str], List[Dict[str, Any]]]:
        """Get fallback response when AI fails"""
        
        fallback_responses = {
            IntentType.GREETING: (
                "Hello! Welcome to our boutique. How can I help you today?",
                ["Browse products", "Get recommendations", "Ask a question"],
                []
            ),
            IntentType.PRODUCT_QUESTION: (
                "I'd be happy to help you with product information. Which product are you interested in?",
                ["Show me popular items", "Browse categories", "Search products"],
                []
            ),
            IntentType.RECOMMENDATION_REQUEST: (
                "I can help you find the perfect products! What are you looking for?",
                ["Accessories", "Electronics", "Home & Garden"],
                []
            ),
            IntentType.GOODBYE: (
                "Thank you for visiting! Have a great day!",
                [],
                []
            )
        }
        
        return fallback_responses.get(intent, (
            "I'm here to help! What can I do for you?",
            ["Browse products", "Get help", "Contact support"],
            []
        ))

    async def _enhance_with_product_info(
        self, 
        content: str, 
        actions: List[Dict[str, Any]], 
        user_message: str
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Enhance response with actual product information"""
        
        # Extract product mentions from user message
        mentioned_products = []
        for product_id, product_info in self.product_knowledge.items():
            if product_info['name'].lower() in user_message.lower():
                mentioned_products.append(product_id)
        
        if mentioned_products:
            # Add product information to response
            product_info = self.product_knowledge[mentioned_products[0]]
            enhanced_content = f"{content}\n\nHere's information about {product_info['name']}:\n"
            enhanced_content += f"Price: ${product_info['price']:.2f}\n"
            enhanced_content += f"Category: {product_info['category']}\n"
            enhanced_content += f"Description: {product_info.get('description', 'A great product!')}"
            
            # Add show product action
            actions.append({
                "type": "show_product",
                "product_id": mentioned_products[0]
            })
            
            return enhanced_content, actions
        
        return content, actions

    async def _get_or_create_session(self, session_id: str, user_id: Optional[str]) -> ConversationContext:
        """Get existing session or create new one"""
        
        if session_id in self.active_sessions:
            context = self.active_sessions[session_id]
            context.last_activity = datetime.now()
            return context
        
        # Create new session
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            state=ConversationState.GREETING,
            intent_history=[],
            mentioned_products=[],
            user_preferences={},
            conversation_history=[],
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.active_sessions[session_id] = context
        logger.info(f"Created new conversation session: {session_id}")
        
        return context

    async def _update_conversation_state(self, context: ConversationContext, intent: IntentType):
        """Update conversation state based on intent"""
        
        state_transitions = {
            IntentType.GREETING: ConversationState.GREETING,
            IntentType.PRODUCT_QUESTION: ConversationState.PRODUCT_INQUIRY,
            IntentType.RECOMMENDATION_REQUEST: ConversationState.SHOPPING_ASSISTANCE,
            IntentType.ORDER_INQUIRY: ConversationState.TECHNICAL_SUPPORT,
            IntentType.COMPLAINT: ConversationState.TECHNICAL_SUPPORT,
            IntentType.ESCALATION_REQUEST: ConversationState.ESCALATION,
            IntentType.GOODBYE: ConversationState.CLOSING
        }
        
        if intent in state_transitions:
            context.state = state_transitions[intent]

    async def _check_escalation_needed(self, context: ConversationContext, intent: IntentType) -> bool:
        """Check if conversation needs escalation to human"""
        
        # Escalation triggers
        if intent == IntentType.ESCALATION_REQUEST:
            return True
        
        if intent == IntentType.COMPLAINT and len(context.intent_history) > 2:
            return True
        
        if len(context.conversation_history) > 20:  # Long conversation
            return True
        
        if context.intent_history.count(IntentType.UNKNOWN) > 3:  # Too many unknowns
            return True
        
        return False

    async def _load_product_knowledge(self):
        """Load product knowledge base"""
        
        # Mock product knowledge (in production, load from database)
        self.product_knowledge = {
            "OLJCESPC7Z": {
                "name": "Vintage Typewriter",
                "price": 67.99,
                "category": "Accessories",
                "description": "A beautiful vintage typewriter perfect for writers and collectors.",
                "features": ["Manual operation", "Classic design", "Durable construction"],
                "sizes": ["One size"],
                "colors": ["Black", "Green"]
            },
            "66VCHSJNUP": {
                "name": "Vintage Record Player",
                "price": 65.50,
                "category": "Electronics",
                "description": "High-quality vintage record player for music enthusiasts.",
                "features": ["Belt drive", "Built-in speakers", "USB connectivity"],
                "sizes": ["Standard"],
                "colors": ["Wood finish", "Black"]
            },
            "1YMWWN1N4O": {
                "name": "Home Barista Kit",
                "price": 124.99,
                "category": "Kitchen",
                "description": "Complete kit for making professional coffee at home.",
                "features": ["Manual grinder", "French press", "Measuring tools"],
                "sizes": ["Complete kit"],
                "colors": ["Stainless steel"]
            }
        }
        
        logger.info(f"Loaded {len(self.product_knowledge)} products into knowledge base")

    async def _load_faq_knowledge(self):
        """Load FAQ knowledge base"""
        
        self.faq_knowledge = {
            "shipping": "We offer free shipping on orders over $50. Standard shipping takes 3-5 business days.",
            "returns": "You can return items within 30 days for a full refund. Items must be in original condition.",
            "sizing": "Please check our size guide for accurate measurements. We offer exchanges for sizing issues.",
            "payment": "We accept all major credit cards, PayPal, and Apple Pay.",
            "support": "Our customer support team is available Monday-Friday 9AM-6PM EST."
        }
        
        logger.info(f"Loaded {len(self.faq_knowledge)} FAQ entries")

    def _initialize_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """Initialize intent classification patterns"""
        
        return {
            IntentType.GREETING: ["hello", "hi", "hey", "good morning", "good afternoon"],
            IntentType.PRODUCT_QUESTION: ["tell me about", "what is", "describe", "details", "specs"],
            IntentType.RECOMMENDATION_REQUEST: ["recommend", "suggest", "what should", "help me find"],
            IntentType.PRICE_QUESTION: ["how much", "price", "cost", "expensive", "cheap"],
            IntentType.AVAILABILITY_CHECK: ["in stock", "available", "can I buy", "do you have"],
            IntentType.SIZING_HELP: ["size", "fit", "measurements", "dimensions"],
            IntentType.COMPLAINT: ["problem", "issue", "wrong", "broken", "disappointed"],
            IntentType.GOODBYE: ["bye", "goodbye", "thanks", "thank you", "see you"]
        }

    async def _session_cleanup_loop(self):
        """Background task to clean up inactive sessions"""
        while True:
            try:
                await asyncio.sleep(1800)  # Clean up every 30 minutes
                
                current_time = datetime.now()
                inactive_sessions = []
                
                for session_id, context in self.active_sessions.items():
                    if current_time - context.last_activity > timedelta(hours=2):
                        inactive_sessions.append(session_id)
                
                for session_id in inactive_sessions:
                    del self.active_sessions[session_id]
                    if session_id in self.message_history:
                        del self.message_history[session_id]
                
                if inactive_sessions:
                    logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
                    
            except Exception as e:
                logger.error(f"Error in session cleanup: {str(e)}")
                await asyncio.sleep(300)

    # A2A Protocol handlers
    async def _handle_chat_message_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat message requests from other agents"""
        try:
            request = ChatRequest(**payload)
            response = await self.process_chat_message(request)
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error handling chat message request: {str(e)}")
            raise

    async def _handle_get_conversation_context_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conversation context requests from other agents"""
        try:
            session_id = payload.get('session_id')
            
            if session_id and session_id in self.active_sessions:
                context = self.active_sessions[session_id]
                return {
                    "context": context.to_dict(),
                    "message_count": len(self.message_history.get(session_id, [])),
                    "found": True
                }
            
            return {"found": False}
            
        except Exception as e:
            logger.error(f"Error handling get conversation context request: {str(e)}")
            raise

    async def _handle_escalate_conversation_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conversation escalation requests from other agents"""
        try:
            session_id = payload.get('session_id')
            reason = payload.get('reason', 'User request')
            
            if session_id and session_id in self.active_sessions:
                context = self.active_sessions[session_id]
                context.escalation_requested = True
                context.state = ConversationState.ESCALATION
                
                logger.info(f"Escalated conversation {session_id}: {reason}")
                
                return {
                    "escalated": True,
                    "session_id": session_id,
                    "reason": reason,
                    "context": context.to_dict()
                }
            
            return {"escalated": False, "error": "Session not found"}
            
        except Exception as e:
            logger.error(f"Error handling escalate conversation request: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the agent"""
        try:
            # Test Gemini connection
            test_response = await self._get_gemini_response("Test prompt for health check")
            gemini_healthy = bool(test_response)
        except:
            gemini_healthy = False
        
        return {
            'agent_id': self.agent_id,
            'status': 'healthy' if gemini_healthy else 'degraded',
            'gemini_connection': gemini_healthy,
            'active_sessions': len(self.active_sessions),
            'total_messages': sum(len(msgs) for msgs in self.message_history.values()),
            'product_knowledge_size': len(self.product_knowledge),
            'faq_knowledge_size': len(self.faq_knowledge),
            'uptime': (datetime.now() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
        }