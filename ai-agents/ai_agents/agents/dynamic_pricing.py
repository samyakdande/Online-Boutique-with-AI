"""
Dynamic Pricing Agent

This agent provides intelligent price optimization that adjusts product prices
based on demand patterns, inventory levels, competitor analysis, and market conditions
to maximize revenue and maintain competitiveness.

Features:
- Real-time price optimization
- Demand-based pricing adjustments
- Inventory-driven pricing strategies
- Competitor price monitoring
- Revenue optimization algorithms
- Stakeholder notifications
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import math

import google.generativeai as genai
from pydantic import BaseModel, Field

from ..core.adk import BaseAgent, AgentMessage, MessageType as ADKMessageType
from ..core.config import get_settings
from ..a2a.protocol import A2AProtocolHandler, MessageType
from ..mcp_servers.boutique_api import BoutiqueAPIMCPServer

# Configure logging
logger = logging.getLogger(__name__)

class PricingStrategy(str, Enum):
    """Pricing strategy types"""
    DEMAND_BASED = "demand_based"
    INVENTORY_BASED = "inventory_based"
    COMPETITOR_BASED = "competitor_based"
    REVENUE_OPTIMIZATION = "revenue_optimization"
    CLEARANCE = "clearance"
    PREMIUM = "premium"

class PriceChangeReason(str, Enum):
    """Reasons for price changes"""
    HIGH_DEMAND = "high_demand"
    LOW_DEMAND = "low_demand"
    LOW_INVENTORY = "low_inventory"
    HIGH_INVENTORY = "high_inventory"
    COMPETITOR_ADJUSTMENT = "competitor_adjustment"
    SEASONAL_ADJUSTMENT = "seasonal_adjustment"
    PROMOTION_END = "promotion_end"
    MANUAL_OVERRIDE = "manual_override"

class MarketCondition(str, Enum):
    """Market condition indicators"""
    BULLISH = "bullish"  # High demand, rising prices
    BEARISH = "bearish"  # Low demand, falling prices
    STABLE = "stable"    # Normal conditions
    VOLATILE = "volatile" # Rapidly changing conditions

@dataclass
class PricingRule:
    """Pricing rule configuration"""
    rule_id: str
    product_id: Optional[str]  # None for global rules
    category: Optional[str]
    strategy: PricingStrategy
    min_price: float
    max_price: float
    base_price: float
    demand_multiplier: float = 1.0
    inventory_multiplier: float = 1.0
    competitor_weight: float = 0.3
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MarketData:
    """Market data for pricing decisions"""
    product_id: str
    current_price: float
    demand_score: float  # 0.0 to 1.0
    inventory_level: int
    inventory_turnover: float
    competitor_prices: List[float]
    sales_velocity: float
    profit_margin: float
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['last_updated'] = self.last_updated.isoformat()
        return result

@dataclass
class PriceRecommendation:
    """Price change recommendation"""
    product_id: str
    current_price: float
    recommended_price: float
    price_change: float
    price_change_percent: float
    strategy: PricingStrategy
    reason: PriceChangeReason
    confidence: float
    expected_impact: Dict[str, float]  # demand, revenue, profit
    valid_until: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['valid_until'] = self.valid_until.isoformat()
        return result

@dataclass
class PriceChangeEvent:
    """Price change event record"""
    event_id: str
    product_id: str
    old_price: float
    new_price: float
    change_reason: PriceChangeReason
    strategy_used: PricingStrategy
    timestamp: datetime
    applied_by: str
    stakeholders_notified: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

class PricingRequest(BaseModel):
    """Request model for pricing analysis"""
    product_ids: List[str] = Field(..., description="Product IDs to analyze")
    strategy: Optional[PricingStrategy] = Field(None, description="Preferred pricing strategy")
    force_update: bool = Field(False, description="Force price recalculation")
    apply_changes: bool = Field(False, description="Apply recommended changes automatically")

class DynamicPricingAgent(BaseAgent):
    """
    Dynamic Pricing Agent for intelligent price optimization
    
    This agent provides:
    - Real-time price optimization using AI
    - Demand and inventory-based pricing
    - Competitor price monitoring
    - Revenue optimization strategies
    - Automated price adjustments
    """
    
    def __init__(self):
        super().__init__(
            agent_id="dynamic-pricing",
            name="Dynamic Pricing Agent",
            version="1.0.0",
            capabilities=[
                "price_optimization",
                "demand_analysis",
                "inventory_management",
                "competitor_monitoring",
                "revenue_optimization"
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
        self.a2a_handler.port = int(os.getenv('DYNAMIC_PRICING_A2A_PORT', '9094'))
        
        # Pricing data and rules
        self.pricing_rules: Dict[str, PricingRule] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.price_history: Dict[str, List[PriceChangeEvent]] = {}
        self.competitor_data: Dict[str, Dict[str, float]] = {}
        
        # Configuration
        self.max_price_change_percent = 0.25  # Max 25% price change
        self.min_profit_margin = 0.10  # Minimum 10% profit margin
        self.price_update_interval = 300  # 5 minutes
        
        logger.info(f"Initialized {self.name} with ID: {self.agent_id}")

    async def _initialize(self) -> None:
        """Custom initialization for Dynamic Pricing Agent"""
        # Initialize Gemini AI
        genai.configure(api_key=self.settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Load pricing rules and market data
        await self._load_pricing_rules()
        await self._load_market_data()
        await self._load_competitor_data()
        
        logger.info("Dynamic Pricing Agent custom initialization completed")

    async def _start(self) -> None:
        """Custom start logic for Dynamic Pricing Agent"""
        await self.a2a_handler.start()
        
        # Register message handlers
        self.a2a_handler.register_handler(
            "get_price_recommendations", 
            self._handle_get_price_recommendations_request
        )
        self.a2a_handler.register_handler(
            "update_market_data", 
            self._handle_update_market_data_request
        )
        self.a2a_handler.register_handler(
            "apply_price_changes", 
            self._handle_apply_price_changes_request
        )
        
        # Start background tasks
        asyncio.create_task(self._price_monitoring_loop())
        asyncio.create_task(self._competitor_monitoring_loop())
        asyncio.create_task(self._market_analysis_loop())
        
        logger.info("Dynamic Pricing Agent started successfully")

    async def _stop(self) -> None:
        """Custom stop logic for Dynamic Pricing Agent"""
        await self.a2a_handler.stop()
        logger.info("Dynamic Pricing Agent stopped")

    async def _handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming ADK messages"""
        try:
            if message.message_type == ADKMessageType.REQUEST:
                request_type = message.payload.get('type')
                
                if request_type == 'get_price_recommendations':
                    result = await self._handle_get_price_recommendations_request(message.payload.get('data', {}))
                    return AgentMessage(
                        id=f"response_{message.id}",
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type=ADKMessageType.RESPONSE,
                        payload={'result': result}
                    )
                elif request_type == 'update_market_data':
                    result = await self._handle_update_market_data_request(message.payload.get('data', {}))
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

    async def get_price_recommendations(self, request: PricingRequest) -> List[PriceRecommendation]:
        """
        Get price recommendations for products
        
        Args:
            request: Pricing request with product IDs and strategy
            
        Returns:
            List[PriceRecommendation]: Price recommendations
        """
        try:
            recommendations = []
            
            for product_id in request.product_ids:
                # Get current market data
                market_data = await self._get_market_data(product_id)
                if not market_data:
                    logger.warning(f"No market data available for product {product_id}")
                    continue
                
                # Get pricing rule
                pricing_rule = await self._get_pricing_rule(product_id)
                if not pricing_rule:
                    logger.warning(f"No pricing rule found for product {product_id}")
                    continue
                
                # Generate recommendation
                recommendation = await self._generate_price_recommendation(
                    market_data, pricing_rule, request.strategy
                )
                
                if recommendation:
                    recommendations.append(recommendation)
            
            logger.info(f"Generated {len(recommendations)} price recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating price recommendations: {str(e)}")
            return []

    async def _generate_price_recommendation(
        self, 
        market_data: MarketData, 
        pricing_rule: PricingRule,
        preferred_strategy: Optional[PricingStrategy] = None
    ) -> Optional[PriceRecommendation]:
        """Generate price recommendation using AI and market data"""
        
        try:
            # Determine optimal strategy
            strategy = preferred_strategy or await self._determine_optimal_strategy(market_data, pricing_rule)
            
            # Calculate base price adjustment
            price_adjustment = await self._calculate_price_adjustment(market_data, pricing_rule, strategy)
            
            # Apply constraints
            new_price = self._apply_pricing_constraints(
                market_data.current_price + price_adjustment,
                pricing_rule,
                market_data
            )
            
            # Determine reason for change
            reason = self._determine_price_change_reason(market_data, strategy)
            
            # Calculate expected impact using AI
            expected_impact = await self._calculate_expected_impact(
                market_data, new_price, strategy
            )
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(market_data, pricing_rule, strategy)
            
            recommendation = PriceRecommendation(
                product_id=market_data.product_id,
                current_price=market_data.current_price,
                recommended_price=new_price,
                price_change=new_price - market_data.current_price,
                price_change_percent=(new_price - market_data.current_price) / market_data.current_price * 100,
                strategy=strategy,
                reason=reason,
                confidence=confidence,
                expected_impact=expected_impact,
                valid_until=datetime.now() + timedelta(hours=1)
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating price recommendation for {market_data.product_id}: {str(e)}")
            return None

    async def _determine_optimal_strategy(
        self, 
        market_data: MarketData, 
        pricing_rule: PricingRule
    ) -> PricingStrategy:
        """Determine optimal pricing strategy using AI"""
        
        # Create strategy selection prompt
        prompt = f"""
You are an expert pricing strategist. Determine the optimal pricing strategy based on market conditions.

Product Data:
- Current Price: ${market_data.current_price:.2f}
- Demand Score: {market_data.demand_score:.2f} (0.0 = low, 1.0 = high)
- Inventory Level: {market_data.inventory_level} units
- Inventory Turnover: {market_data.inventory_turnover:.2f}
- Sales Velocity: {market_data.sales_velocity:.2f}
- Profit Margin: {market_data.profit_margin:.2f}
- Competitor Prices: {market_data.competitor_prices}

Available Strategies:
- demand_based: Adjust based on demand patterns
- inventory_based: Adjust based on inventory levels
- competitor_based: Adjust based on competitor prices
- revenue_optimization: Maximize total revenue
- clearance: Clear excess inventory
- premium: Position as premium product

Consider:
- High demand + low inventory = increase prices
- Low demand + high inventory = decrease prices
- Competitor prices significantly lower = consider matching
- High profit margins = room for strategic pricing

Respond with JSON:
{{
    "strategy": "strategy_name",
    "reasoning": "Brief explanation",
    "confidence": 0.85
}}
"""
        
        try:
            response = await self._get_gemini_response(prompt)
            data = self._parse_json_response(response)
            
            strategy_str = data.get('strategy', 'demand_based')
            try:
                return PricingStrategy(strategy_str)
            except ValueError:
                return PricingStrategy.DEMAND_BASED
                
        except Exception as e:
            logger.error(f"Error determining optimal strategy: {str(e)}")
            return PricingStrategy.DEMAND_BASED

    async def _calculate_price_adjustment(
        self, 
        market_data: MarketData, 
        pricing_rule: PricingRule,
        strategy: PricingStrategy
    ) -> float:
        """Calculate price adjustment based on strategy"""
        
        base_price = pricing_rule.base_price
        current_price = market_data.current_price
        
        if strategy == PricingStrategy.DEMAND_BASED:
            # Adjust based on demand score
            demand_factor = (market_data.demand_score - 0.5) * 2  # -1 to 1
            adjustment = base_price * 0.1 * demand_factor * pricing_rule.demand_multiplier
            
        elif strategy == PricingStrategy.INVENTORY_BASED:
            # Adjust based on inventory levels
            # Low inventory (< 10) = increase price, High inventory (> 100) = decrease price
            if market_data.inventory_level < 10:
                inventory_factor = 0.2  # Increase by up to 20%
            elif market_data.inventory_level > 100:
                inventory_factor = -0.15  # Decrease by up to 15%
            else:
                inventory_factor = 0.0
            
            adjustment = base_price * inventory_factor * pricing_rule.inventory_multiplier
            
        elif strategy == PricingStrategy.COMPETITOR_BASED:
            # Adjust based on competitor prices
            if market_data.competitor_prices:
                avg_competitor_price = sum(market_data.competitor_prices) / len(market_data.competitor_prices)
                price_gap = avg_competitor_price - current_price
                adjustment = price_gap * pricing_rule.competitor_weight
            else:
                adjustment = 0.0
                
        elif strategy == PricingStrategy.REVENUE_OPTIMIZATION:
            # Use AI to optimize for revenue
            adjustment = await self._ai_revenue_optimization(market_data, pricing_rule)
            
        elif strategy == PricingStrategy.CLEARANCE:
            # Aggressive price reduction for clearance
            adjustment = -base_price * 0.3  # 30% reduction
            
        elif strategy == PricingStrategy.PREMIUM:
            # Premium pricing strategy
            adjustment = base_price * 0.15  # 15% increase
            
        else:
            adjustment = 0.0
        
        return adjustment

    async def _ai_revenue_optimization(
        self, 
        market_data: MarketData, 
        pricing_rule: PricingRule
    ) -> float:
        """Use AI to optimize price for maximum revenue"""
        
        prompt = f"""
You are a revenue optimization expert. Calculate the optimal price adjustment to maximize revenue.

Current Situation:
- Current Price: ${market_data.current_price:.2f}
- Base Price: ${pricing_rule.base_price:.2f}
- Demand Score: {market_data.demand_score:.2f}
- Sales Velocity: {market_data.sales_velocity:.2f}
- Profit Margin: {market_data.profit_margin:.2f}
- Inventory: {market_data.inventory_level} units

Price Constraints:
- Min Price: ${pricing_rule.min_price:.2f}
- Max Price: ${pricing_rule.max_price:.2f}
- Max Change: ±25%

Calculate the price adjustment that maximizes: Price × Expected Demand × Profit Margin

Consider:
- Price elasticity of demand
- Inventory turnover optimization
- Profit margin preservation

Respond with JSON:
{{
    "price_adjustment": 5.50,
    "expected_revenue_increase": 0.12,
    "reasoning": "Brief explanation"
}}
"""
        
        try:
            response = await self._get_gemini_response(prompt)
            data = self._parse_json_response(response)
            return float(data.get('price_adjustment', 0.0))
            
        except Exception as e:
            logger.error(f"Error in AI revenue optimization: {str(e)}")
            return 0.0

    def _apply_pricing_constraints(
        self, 
        proposed_price: float, 
        pricing_rule: PricingRule,
        market_data: MarketData
    ) -> float:
        """Apply pricing constraints and limits"""
        
        # Apply min/max price constraints
        constrained_price = max(pricing_rule.min_price, min(pricing_rule.max_price, proposed_price))
        
        # Apply maximum change percentage
        max_change = market_data.current_price * self.max_price_change_percent
        min_allowed = market_data.current_price - max_change
        max_allowed = market_data.current_price + max_change
        
        constrained_price = max(min_allowed, min(max_allowed, constrained_price))
        
        # Ensure minimum profit margin
        min_price_for_margin = pricing_rule.base_price * (1 + self.min_profit_margin)
        constrained_price = max(min_price_for_margin, constrained_price)
        
        return round(constrained_price, 2)

    def _determine_price_change_reason(
        self, 
        market_data: MarketData, 
        strategy: PricingStrategy
    ) -> PriceChangeReason:
        """Determine the reason for price change"""
        
        if strategy == PricingStrategy.DEMAND_BASED:
            return PriceChangeReason.HIGH_DEMAND if market_data.demand_score > 0.7 else PriceChangeReason.LOW_DEMAND
        elif strategy == PricingStrategy.INVENTORY_BASED:
            return PriceChangeReason.LOW_INVENTORY if market_data.inventory_level < 20 else PriceChangeReason.HIGH_INVENTORY
        elif strategy == PricingStrategy.COMPETITOR_BASED:
            return PriceChangeReason.COMPETITOR_ADJUSTMENT
        elif strategy == PricingStrategy.CLEARANCE:
            return PriceChangeReason.HIGH_INVENTORY
        else:
            return PriceChangeReason.HIGH_DEMAND

    async def _calculate_expected_impact(
        self, 
        market_data: MarketData, 
        new_price: float,
        strategy: PricingStrategy
    ) -> Dict[str, float]:
        """Calculate expected impact of price change using AI"""
        
        price_change_percent = (new_price - market_data.current_price) / market_data.current_price * 100
        
        # Simple impact model (in production, use more sophisticated ML models)
        demand_elasticity = -1.2  # Typical elasticity for retail products
        expected_demand_change = demand_elasticity * (price_change_percent / 100)
        
        expected_revenue_change = (price_change_percent / 100) + expected_demand_change
        expected_profit_change = expected_revenue_change * 1.2  # Profit typically more sensitive
        
        return {
            "demand_change": expected_demand_change,
            "revenue_change": expected_revenue_change,
            "profit_change": expected_profit_change
        }

    def _calculate_confidence_score(
        self, 
        market_data: MarketData, 
        pricing_rule: PricingRule,
        strategy: PricingStrategy
    ) -> float:
        """Calculate confidence score for the recommendation"""
        
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on data quality
        if market_data.demand_score > 0:
            confidence += 0.2
        if market_data.inventory_level > 0:
            confidence += 0.1
        if market_data.competitor_prices:
            confidence += 0.1
        if market_data.sales_velocity > 0:
            confidence += 0.1
        
        # Adjust based on market volatility
        if len(market_data.competitor_prices) > 1:
            price_variance = max(market_data.competitor_prices) - min(market_data.competitor_prices)
            if price_variance / market_data.current_price > 0.2:  # High variance
                confidence -= 0.1
        
        return min(1.0, max(0.1, confidence))

    async def _get_market_data(self, product_id: str) -> Optional[MarketData]:
        """Get market data for a product"""
        
        if product_id in self.market_data:
            return self.market_data[product_id]
        
        # Generate mock market data for demo
        return await self._generate_mock_market_data(product_id)

    async def _generate_mock_market_data(self, product_id: str) -> MarketData:
        """Generate mock market data for demo purposes"""
        
        import random
        
        # Mock product prices
        product_prices = {
            "OLJCESPC7Z": 67.99,  # Vintage Typewriter
            "66VCHSJNUP": 65.50,  # Vintage Record Player
            "1YMWWN1N4O": 124.99, # Home Barista Kit
            "L9ECAV7KIM": 36.45,  # Terrarium Kit
            "2ZYFJ3GM2N": 2275.00 # Film Camera
        }
        
        base_price = product_prices.get(product_id, 50.00)
        
        market_data = MarketData(
            product_id=product_id,
            current_price=base_price,
            demand_score=random.uniform(0.2, 0.9),
            inventory_level=random.randint(5, 150),
            inventory_turnover=random.uniform(0.5, 3.0),
            competitor_prices=[
                base_price * random.uniform(0.85, 1.15) for _ in range(3)
            ],
            sales_velocity=random.uniform(0.1, 2.0),
            profit_margin=random.uniform(0.15, 0.45),
            last_updated=datetime.now()
        )
        
        self.market_data[product_id] = market_data
        return market_data

    async def _get_pricing_rule(self, product_id: str) -> Optional[PricingRule]:
        """Get pricing rule for a product"""
        
        if product_id in self.pricing_rules:
            return self.pricing_rules[product_id]
        
        # Create default pricing rule
        market_data = await self._get_market_data(product_id)
        if not market_data:
            return None
        
        rule = PricingRule(
            rule_id=f"rule_{product_id}",
            product_id=product_id,
            category=None,
            strategy=PricingStrategy.DEMAND_BASED,
            min_price=market_data.current_price * 0.7,
            max_price=market_data.current_price * 1.5,
            base_price=market_data.current_price,
            demand_multiplier=1.0,
            inventory_multiplier=1.0,
            competitor_weight=0.3
        )
        
        self.pricing_rules[product_id] = rule
        return rule

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

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from Gemini"""
        try:
            # Clean response
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            return json.loads(clean_response.strip())
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            return {}

    async def _load_pricing_rules(self):
        """Load pricing rules configuration"""
        # Mock pricing rules for demo
        logger.info("Loaded pricing rules configuration")

    async def _load_market_data(self):
        """Load market data from external sources"""
        # Mock market data loading
        logger.info("Loaded market data")

    async def _load_competitor_data(self):
        """Load competitor pricing data"""
        # Mock competitor data
        logger.info("Loaded competitor pricing data")

    async def _price_monitoring_loop(self):
        """Background task for continuous price monitoring"""
        while True:
            try:
                await asyncio.sleep(self.price_update_interval)
                
                # Monitor all products with pricing rules
                for product_id in self.pricing_rules.keys():
                    await self._monitor_product_price(product_id)
                    
            except Exception as e:
                logger.error(f"Error in price monitoring loop: {str(e)}")
                await asyncio.sleep(60)

    async def _monitor_product_price(self, product_id: str):
        """Monitor individual product price"""
        try:
            # Get current recommendations
            request = PricingRequest(product_ids=[product_id])
            recommendations = await self.get_price_recommendations(request)
            
            if recommendations:
                rec = recommendations[0]
                
                # Apply automatic price changes if confidence is high
                if rec.confidence > 0.8 and abs(rec.price_change_percent) > 5:
                    await self._apply_price_change(rec)
                    
        except Exception as e:
            logger.error(f"Error monitoring price for {product_id}: {str(e)}")

    async def _apply_price_change(self, recommendation: PriceRecommendation):
        """Apply price change and notify stakeholders"""
        try:
            # Create price change event
            event = PriceChangeEvent(
                event_id=f"price_change_{datetime.now().timestamp()}",
                product_id=recommendation.product_id,
                old_price=recommendation.current_price,
                new_price=recommendation.recommended_price,
                change_reason=recommendation.reason,
                strategy_used=recommendation.strategy,
                timestamp=datetime.now(),
                applied_by=self.agent_id,
                stakeholders_notified=[]
            )
            
            # Store event
            if recommendation.product_id not in self.price_history:
                self.price_history[recommendation.product_id] = []
            self.price_history[recommendation.product_id].append(event)
            
            # Update market data
            if recommendation.product_id in self.market_data:
                self.market_data[recommendation.product_id].current_price = recommendation.recommended_price
            
            # Notify stakeholders
            await self._notify_price_change(event)
            
            logger.info(f"Applied price change for {recommendation.product_id}: "
                       f"${recommendation.current_price:.2f} → ${recommendation.recommended_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error applying price change: {str(e)}")

    async def _notify_price_change(self, event: PriceChangeEvent):
        """Notify stakeholders about price changes"""
        try:
            notification_data = {
                "event_type": "price_change",
                "product_id": event.product_id,
                "old_price": event.old_price,
                "new_price": event.new_price,
                "change_percent": ((event.new_price - event.old_price) / event.old_price) * 100,
                "reason": event.change_reason.value,
                "timestamp": event.timestamp.isoformat()
            }
            
            # Notify other agents
            await self.a2a_handler.broadcast_notification(
                "price_change_notification",
                notification_data
            )
            
            logger.info(f"Notified stakeholders about price change for {event.product_id}")
            
        except Exception as e:
            logger.error(f"Error notifying price change: {str(e)}")

    async def _competitor_monitoring_loop(self):
        """Background task for competitor price monitoring"""
        while True:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes
                await self._update_competitor_prices()
                
            except Exception as e:
                logger.error(f"Error in competitor monitoring: {str(e)}")
                await asyncio.sleep(300)

    async def _update_competitor_prices(self):
        """Update competitor pricing data"""
        # Mock competitor price updates
        import random
        
        for product_id, market_data in self.market_data.items():
            # Simulate competitor price changes
            for i, price in enumerate(market_data.competitor_prices):
                change = random.uniform(-0.05, 0.05)  # ±5% change
                market_data.competitor_prices[i] = max(0.01, price * (1 + change))
        
        logger.info("Updated competitor pricing data")

    async def _market_analysis_loop(self):
        """Background task for market analysis"""
        while True:
            try:
                await asyncio.sleep(3600)  # Analyze every hour
                await self._analyze_market_conditions()
                
            except Exception as e:
                logger.error(f"Error in market analysis: {str(e)}")
                await asyncio.sleep(600)

    async def _analyze_market_conditions(self):
        """Analyze overall market conditions"""
        # Mock market analysis
        logger.info("Analyzed market conditions")

    # A2A Protocol handlers
    async def _handle_get_price_recommendations_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle price recommendations requests from other agents"""
        try:
            request = PricingRequest(**payload)
            recommendations = await self.get_price_recommendations(request)
            return {
                "recommendations": [rec.to_dict() for rec in recommendations]
            }
        except Exception as e:
            logger.error(f"Error handling get price recommendations request: {str(e)}")
            raise

    async def _handle_update_market_data_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle market data update requests from other agents"""
        try:
            product_id = payload.get('product_id')
            updates = payload.get('updates', {})
            
            if product_id and product_id in self.market_data:
                market_data = self.market_data[product_id]
                
                # Update market data fields
                for field, value in updates.items():
                    if hasattr(market_data, field):
                        setattr(market_data, field, value)
                
                market_data.last_updated = datetime.now()
                
                logger.info(f"Updated market data for {product_id}")
                return {"status": "success", "updated_fields": list(updates.keys())}
            
            return {"status": "error", "message": "Product not found"}
            
        except Exception as e:
            logger.error(f"Error handling update market data request: {str(e)}")
            raise

    async def _handle_apply_price_changes_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle apply price changes requests from other agents"""
        try:
            product_ids = payload.get('product_ids', [])
            force_apply = payload.get('force_apply', False)
            
            applied_changes = []
            
            for product_id in product_ids:
                request = PricingRequest(product_ids=[product_id], apply_changes=True)
                recommendations = await self.get_price_recommendations(request)
                
                if recommendations:
                    rec = recommendations[0]
                    if force_apply or rec.confidence > 0.7:
                        await self._apply_price_change(rec)
                        applied_changes.append({
                            "product_id": product_id,
                            "old_price": rec.current_price,
                            "new_price": rec.recommended_price,
                            "change_percent": rec.price_change_percent
                        })
            
            return {
                "status": "success",
                "applied_changes": applied_changes,
                "total_changes": len(applied_changes)
            }
            
        except Exception as e:
            logger.error(f"Error handling apply price changes request: {str(e)}")
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
            'pricing_rules': len(self.pricing_rules),
            'monitored_products': len(self.market_data),
            'price_changes_today': sum(
                len([event for event in events if event.timestamp.date() == datetime.now().date()])
                for events in self.price_history.values()
            ),
            'uptime': (datetime.now() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
        }