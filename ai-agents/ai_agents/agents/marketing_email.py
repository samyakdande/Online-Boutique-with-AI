"""
Marketing Email Agent

This agent provides personalized email marketing campaigns based on customer
behavior, preferences, and shopping patterns using Gemini AI for content
generation and targeting optimization.

Features:
- Personalized email campaigns
- Cart abandonment recovery
- Product recommendation emails
- Re-engagement campaigns
- Email performance tracking
- A/B testing for optimization
"""

import asyncio
import json
import logging
import os
import uuid
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

class EmailType(str, Enum):
    """Email campaign types"""
    WELCOME = "welcome"
    CART_ABANDONMENT = "cart_abandonment"
    PRODUCT_RECOMMENDATION = "product_recommendation"
    NEW_PRODUCT_ALERT = "new_product_alert"
    RE_ENGAGEMENT = "re_engagement"
    PROMOTIONAL = "promotional"
    SEASONAL = "seasonal"
    BIRTHDAY = "birthday"
    REVIEW_REQUEST = "review_request"

class EmailStatus(str, Enum):
    """Email delivery status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


class CustomerSegment(str, Enum):
    """Customer segmentation for targeting"""
    NEW_CUSTOMER = "new_customer"
    LOYAL_CUSTOMER = "loyal_customer"
    VIP_CUSTOMER = "vip_customer"
    AT_RISK = "at_risk"
    INACTIVE = "inactive"
    PRICE_SENSITIVE = "price_sensitive"
    FREQUENT_BUYER = "frequent_buyer"

@dataclass
class CustomerProfile:
    """Customer profile for email personalization"""
    customer_id: str
    email: str
    name: str
    segment: CustomerSegment
    preferences: Dict[str, Any]
    purchase_history: List[str]
    browsing_history: List[str]
    email_engagement: Dict[str, float]
    last_purchase: Optional[datetime]
    last_email_sent: Optional[datetime]
    unsubscribed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.last_purchase:
            result['last_purchase'] = self.last_purchase.isoformat()
        if self.last_email_sent:
            result['last_email_sent'] = self.last_email_sent.isoformat()
        return result

@dataclass
class EmailMessage:
    """Individual email message"""
    message_id: str
    campaign_id: str
    customer_id: str
    email_address: str
    subject: str
    content: str
    personalized_data: Dict[str, Any]
    scheduled_time: datetime
    sent_time: Optional[datetime]
    status: EmailStatus
    tracking_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['scheduled_time'] = self.scheduled_time.isoformat()
        if self.sent_time:
            result['sent_time'] = self.sent_time.isoformat()
        return result

class EmailRequest(BaseModel):
    """Request model for email operations"""
    customer_ids: List[str] = Field(..., description="Customer IDs to target")
    email_type: EmailType = Field(..., description="Type of email campaign")
    personalization_data: Dict[str, Any] = Field(default_factory=dict, description="Personalization data")
    send_immediately: bool = Field(False, description="Send immediately or schedule")
    test_mode: bool = Field(True, description="Test mode for demo")

class MarketingEmailAgent(BaseAgent):
    """
    Marketing Email Agent for personalized email campaigns
    
    This agent provides:
    - Personalized email content generation using Gemini AI
    - Customer behavior-based targeting
    - Cart abandonment recovery emails
    - Product recommendation campaigns
    - Re-engagement campaigns
    - Email performance tracking and optimization
    """
    
    def __init__(self):
        super().__init__(
            agent_id="marketing-email",
            name="Marketing Email Agent",
            version="1.0.0",
            capabilities=[
                "email_personalization",
                "customer_segmentation",
                "campaign_automation",
                "content_generation",
                "performance_tracking"
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
        self.a2a_handler.port = int(os.getenv('MARKETING_EMAIL_A2A_PORT', '9095'))
        
        # Email data and templates
        self.customer_profiles: Dict[str, CustomerProfile] = {}
        self.email_queue: List[EmailMessage] = []
        self.sent_emails: Dict[str, EmailMessage] = {}
        
        logger.info(f"Initialized {self.name} with ID: {self.agent_id}")

    async def _initialize(self) -> None:
        """Custom initialization for Marketing Email Agent"""
        # Initialize Gemini AI
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("Marketing Email Agent custom initialization completed")

    async def _start(self) -> None:
        """Custom start logic for Marketing Email Agent"""
        await self.a2a_handler.start()
        
        # Register message handlers
        self.a2a_handler.register_handler(
            "send_email_campaign", 
            self._handle_send_email_campaign_request
        )
        
        # Start background tasks
        asyncio.create_task(self._email_processing_loop())
        
        logger.info("Marketing Email Agent started successfully")

    async def _stop(self) -> None:
        """Custom stop logic for Marketing Email Agent"""
        await self.a2a_handler.stop()
        logger.info("Marketing Email Agent stopped")

    async def _handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming ADK messages"""
        try:
            if message.message_type == ADKMessageType.REQUEST:
                request_type = message.payload.get('type')
                
                if request_type == 'send_email_campaign':
                    result = await self._handle_send_email_campaign_request(message.payload.get('data', {}))
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

    async def create_email_campaign(self, request: EmailRequest) -> List[EmailMessage]:
        """
        Create personalized email campaign
        
        Args:
            request: Email campaign request
            
        Returns:
            List[EmailMessage]: Generated email messages
        """
        try:
            emails = []
            
            # Generate emails for each customer
            for customer_id in request.customer_ids:
                customer = await self._get_customer_profile(customer_id)
                if not customer or customer.unsubscribed:
                    continue
                
                # Generate personalized content
                email_content = await self._generate_personalized_email(
                    customer, request.email_type, request.personalization_data
                )
                
                if email_content:
                    email = EmailMessage(
                        message_id=str(uuid.uuid4()),
                        campaign_id=f"campaign_{datetime.now().timestamp()}",
                        customer_id=customer_id,
                        email_address=customer.email,
                        subject=email_content['subject'],
                        content=email_content['content'],
                        personalized_data=email_content['personalization'],
                        scheduled_time=datetime.now() if request.send_immediately else datetime.now() + timedelta(minutes=5),
                        sent_time=None,
                        status=EmailStatus.DRAFT,
                        tracking_data={}
                    )
                    
                    emails.append(email)
                    
                    # Add to queue if not test mode
                    if not request.test_mode:
                        self.email_queue.append(email)
            
            logger.info(f"Created {len(emails)} personalized emails for campaign")
            return emails
            
        except Exception as e:
            logger.error(f"Error creating email campaign: {str(e)}")
            return []

    async def _generate_personalized_email(
        self, 
        customer: CustomerProfile, 
        email_type: EmailType,
        personalization_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate personalized email content using Gemini AI"""
        
        try:
            # Create personalization prompt
            prompt = self._create_email_generation_prompt(customer, email_type, personalization_data)
            
            # Get AI-generated content
            response = await self._get_gemini_response(prompt)
            
            # Parse response
            email_content = self._parse_email_response(response)
            
            return email_content
            
        except Exception as e:
            logger.error(f"Error generating personalized email for {customer.customer_id}: {str(e)}")
            return None

    def _create_email_generation_prompt(
        self, 
        customer: CustomerProfile, 
        email_type: EmailType,
        personalization_data: Dict[str, Any]
    ) -> str:
        """Create prompt for email content generation"""
        
        # Get recent purchase info
        recent_purchases = customer.purchase_history[-3:] if customer.purchase_history else []
        
        # Get browsing behavior
        recent_browsing = customer.browsing_history[-5:] if customer.browsing_history else []
        
        prompt = f"""
You are an expert email marketing copywriter. Create a personalized email for a customer.

Customer Profile:
- Name: {customer.name}
- Segment: {customer.segment.value}
- Recent Purchases: {recent_purchases}
- Recent Browsing: {recent_browsing}
- Email Engagement: Open Rate {customer.email_engagement.get('open_rate', 0.5):.1%}, Click Rate {customer.email_engagement.get('click_rate', 0.2):.1%}
- Preferences: {customer.preferences}

Email Type: {email_type.value}
Personalization Data: {personalization_data}

Guidelines:
- Use the customer's name naturally
- Reference their purchase/browsing history when relevant
- Match their segment (new customer vs loyal customer tone)
- Keep subject line under 50 characters
- Make content engaging and actionable
- Include clear call-to-action
- Maintain brand voice: friendly, helpful, not pushy

Respond with JSON:
{{
    "subject": "Personalized subject line",
    "content": "Full email content with HTML formatting",
    "personalization": {{
        "customer_name": "{customer.name}",
        "recommended_products": ["PROD1", "PROD2"],
        "special_offer": "10% off your next purchase"
    }}
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

    def _parse_email_response(self, response: str) -> Dict[str, Any]:
        """Parse Gemini email response"""
        try:
            # Clean response
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            data = json.loads(clean_response.strip())
            
            return {
                'subject': data.get('subject', 'Special Offer Just for You!'),
                'content': data.get('content', 'Thank you for being a valued customer!'),
                'personalization': data.get('personalization', {})
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing email response: {str(e)}")
            return {
                'subject': 'Special Offer Just for You!',
                'content': 'Thank you for being a valued customer! Check out our latest products.',
                'personalization': {}
            }

    async def _get_customer_profile(self, customer_id: str) -> Optional[CustomerProfile]:
        """Get customer profile for personalization"""
        
        if customer_id in self.customer_profiles:
            return self.customer_profiles[customer_id]
        
        # Create mock customer profile for demo
        return await self._create_mock_customer_profile(customer_id)

    async def _create_mock_customer_profile(self, customer_id: str) -> CustomerProfile:
        """Create mock customer profile for demo"""
        
        import random
        
        # Mock customer data
        names = ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Emma Brown"]
        segments = list(CustomerSegment)
        
        profile = CustomerProfile(
            customer_id=customer_id,
            email=f"{customer_id}@example.com",
            name=random.choice(names),
            segment=random.choice(segments),
            preferences={
                "categories": random.sample(["accessories", "electronics", "home", "fashion"], 2),
                "price_range": random.choice(["budget", "mid-range", "premium"]),
                "communication_frequency": random.choice(["weekly", "bi-weekly", "monthly"])
            },
            purchase_history=random.sample(["OLJCESPC7Z", "66VCHSJNUP", "1YMWWN1N4O", "L9ECAV7KIM"], 2),
            browsing_history=random.sample(["OLJCESPC7Z", "66VCHSJNUP", "1YMWWN1N4O", "L9ECAV7KIM", "2ZYFJ3GM2N"], 3),
            email_engagement={
                "open_rate": random.uniform(0.2, 0.8),
                "click_rate": random.uniform(0.05, 0.3),
                "conversion_rate": random.uniform(0.01, 0.1)
            },
            last_purchase=datetime.now() - timedelta(days=random.randint(1, 90)),
            last_email_sent=datetime.now() - timedelta(days=random.randint(1, 30)) if random.choice([True, False]) else None,
            unsubscribed=False
        )
        
        self.customer_profiles[customer_id] = profile
        return profile

    async def _email_processing_loop(self):
        """Background task for processing email queue"""
        while True:
            try:
                await asyncio.sleep(30)  # Process every 30 seconds
                
                if self.email_queue:
                    emails_to_send = []
                    current_time = datetime.now()
                    
                    # Find emails ready to send
                    for email in self.email_queue[:]:
                        if email.scheduled_time <= current_time:
                            emails_to_send.append(email)
                            self.email_queue.remove(email)
                    
                    # "Send" emails (mock for demo)
                    for email in emails_to_send:
                        await self._send_email(email)
                        
            except Exception as e:
                logger.error(f"Error in email processing loop: {str(e)}")
                await asyncio.sleep(60)

    async def _send_email(self, email: EmailMessage):
        """Send email (mock implementation for demo)"""
        try:
            # Mock email sending
            email.sent_time = datetime.now()
            email.status = EmailStatus.SENT
            
            # Store sent email
            self.sent_emails[email.message_id] = email
            
            # Update customer profile
            if email.customer_id in self.customer_profiles:
                self.customer_profiles[email.customer_id].last_email_sent = email.sent_time
            
            # Mock delivery and engagement
            await asyncio.sleep(0.1)  # Simulate sending delay
            
            # Simulate delivery
            email.status = EmailStatus.DELIVERED
            
            # Simulate engagement (random for demo)
            import random
            if random.random() < 0.6:  # 60% open rate
                email.status = EmailStatus.OPENED
                email.tracking_data['opened_at'] = datetime.now().isoformat()
                
                if random.random() < 0.3:  # 30% click rate of opens
                    email.status = EmailStatus.CLICKED
                    email.tracking_data['clicked_at'] = datetime.now().isoformat()
            
            logger.info(f"Sent email {email.message_id} to {email.customer_id}: {email.subject}")
            
        except Exception as e:
            logger.error(f"Error sending email {email.message_id}: {str(e)}")
            email.status = EmailStatus.BOUNCED 
   # A2A Protocol handlers
    async def _handle_send_email_campaign_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email campaign requests from other agents"""
        try:
            request = EmailRequest(**payload)
            emails = await self.create_email_campaign(request)
            
            return {
                "campaign_created": True,
                "emails_generated": len(emails),
                "emails": [email.to_dict() for email in emails[:3]]  # Return first 3 for demo
            }
        except Exception as e:
            logger.error(f"Error handling send email campaign request: {str(e)}")
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
            'customer_profiles': len(self.customer_profiles),
            'emails_in_queue': len(self.email_queue),
            'emails_sent_today': len([email for email in self.sent_emails.values() 
                                    if email.sent_time and email.sent_time.date() == datetime.now().date()]),
            'uptime': (datetime.now() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
        }