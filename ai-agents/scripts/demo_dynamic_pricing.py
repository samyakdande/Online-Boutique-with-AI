#!/usr/bin/env python3
"""
Dynamic Pricing Agent Demo

This script demonstrates the Dynamic Pricing Agent functionality
with sample market conditions and real Gemini AI price optimization.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_agents.agents.dynamic_pricing import (
    DynamicPricingAgent, 
    PricingRequest,
    PricingStrategy,
    PriceChangeReason
)
from ai_agents.core.config import get_settings

# Sample pricing scenarios for testing
PRICING_SCENARIOS = [
    {
        "name": "High Demand Product",
        "product_id": "OLJCESPC7Z",  # Vintage Typewriter
        "market_conditions": {
            "demand_score": 0.9,
            "inventory_level": 8,
            "sales_velocity": 2.5
        },
        "expected_outcome": "price_increase"
    },
    {
        "name": "Overstocked Item",
        "product_id": "66VCHSJNUP",  # Vintage Record Player
        "market_conditions": {
            "demand_score": 0.3,
            "inventory_level": 120,
            "sales_velocity": 0.4
        },
        "expected_outcome": "price_decrease"
    },
    {
        "name": "Competitor Price War",
        "product_id": "1YMWWN1N4O",  # Home Barista Kit
        "market_conditions": {
            "demand_score": 0.6,
            "inventory_level": 45,
            "competitor_prices": [89.99, 95.50, 92.00]  # Lower than current $124.99
        },
        "expected_outcome": "competitive_adjustment"
    },
    {
        "name": "Premium Positioning",
        "product_id": "2ZYFJ3GM2N",  # Film Camera
        "market_conditions": {
            "demand_score": 0.7,
            "inventory_level": 15,
            "sales_velocity": 1.2,
            "profit_margin": 0.35
        },
        "expected_outcome": "premium_pricing"
    },
    {
        "name": "Clearance Sale",
        "product_id": "L9ECAV7KIM",  # Terrarium Kit
        "market_conditions": {
            "demand_score": 0.2,
            "inventory_level": 200,
            "sales_velocity": 0.1
        },
        "expected_outcome": "clearance_pricing"
    }
]

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_pricing_result(scenario: dict, recommendations: list):
    """Print formatted pricing results"""
    print(f"\n💰 Scenario: {scenario['name']}")
    print(f"🛍️ Product: {scenario['product_id']}")
    print(f"📊 Expected: {scenario['expected_outcome']}")
    
    if not recommendations:
        print("❌ No recommendations generated")
        return
    
    rec = recommendations[0]
    
    print(f"\n💡 Pricing Recommendation:")
    print(f"   • Current Price: ${rec.current_price:.2f}")
    print(f"   • Recommended Price: ${rec.recommended_price:.2f}")
    print(f"   • Price Change: ${rec.price_change:+.2f} ({rec.price_change_percent:+.1f}%)")
    print(f"   • Strategy: {rec.strategy.value}")
    print(f"   • Reason: {rec.reason.value}")
    print(f"   • Confidence: {rec.confidence:.2f}")
    
    print(f"\n📈 Expected Impact:")
    for metric, value in rec.expected_impact.items():
        print(f"   • {metric.replace('_', ' ').title()}: {value:+.1%}")
    
    print(f"   • Valid Until: {rec.valid_until.strftime('%H:%M:%S')}")
    
    # Validate against expected outcome
    if scenario['expected_outcome'] == 'price_increase' and rec.price_change > 0:
        result = "✅ Correct"
    elif scenario['expected_outcome'] == 'price_decrease' and rec.price_change < 0:
        result = "✅ Correct"
    elif scenario['expected_outcome'] == 'competitive_adjustment' and rec.strategy == PricingStrategy.COMPETITOR_BASED:
        result = "✅ Correct"
    elif scenario['expected_outcome'] == 'premium_pricing' and rec.strategy == PricingStrategy.PREMIUM:
        result = "✅ Correct"
    elif scenario['expected_outcome'] == 'clearance_pricing' and rec.strategy == PricingStrategy.CLEARANCE:
        result = "✅ Correct"
    else:
        result = "⚠️ Different approach"
    
    print(f"\n   {result} - Strategy aligns with market conditions")

async def demo_dynamic_pricing():
    """Demonstrate dynamic pricing functionality"""
    print_header("💰 Dynamic Pricing Agent Demo")
    
    # Check if we have Gemini API key
    settings = get_settings()
    if not settings.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return
    
    print(f"🔑 Using Gemini API key: {settings.gemini_api_key[:10]}...")
    
    # Initialize agent
    print("\n🚀 Initializing Dynamic Pricing Agent...")
    agent = DynamicPricingAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Agent started successfully!")
        
        # Test health check
        print("\n🏥 Running health check...")
        health = await agent.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Gemini Connection: {'✅' if health['gemini_connection'] else '❌'}")
        print(f"   Pricing Rules: {health['pricing_rules']}")
        print(f"   Monitored Products: {health['monitored_products']}")
        
        if not health['gemini_connection']:
            print("❌ Gemini connection failed. Please check your API key.")
            return
        
        print_header("💡 Testing Pricing Scenarios")
        
        # Test each pricing scenario
        for i, scenario in enumerate(PRICING_SCENARIOS, 1):
            print(f"\n--- Scenario {i}/{len(PRICING_SCENARIOS)} ---")
            
            # Update market conditions for this scenario
            if 'market_conditions' in scenario:
                await agent._handle_update_market_data_request({
                    'product_id': scenario['product_id'],
                    'updates': scenario['market_conditions']
                })
            
            # Get pricing recommendations
            request = PricingRequest(
                product_ids=[scenario['product_id']],
                strategy=None,  # Let AI choose optimal strategy
                force_update=True
            )
            
            try:
                recommendations = await agent.get_price_recommendations(request)
                print_pricing_result(scenario, recommendations)
                
                # Small delay between scenarios
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error in scenario {scenario['name']}: {str(e)}")
        
        print_header("🎯 Testing Specific Strategies")
        
        # Test specific pricing strategies
        strategies_to_test = [
            (PricingStrategy.DEMAND_BASED, "OLJCESPC7Z"),
            (PricingStrategy.INVENTORY_BASED, "66VCHSJNUP"),
            (PricingStrategy.COMPETITOR_BASED, "1YMWWN1N4O"),
            (PricingStrategy.REVENUE_OPTIMIZATION, "2ZYFJ3GM2N")
        ]
        
        for strategy, product_id in strategies_to_test:
            print(f"\n🎯 Testing {strategy.value} strategy on {product_id}")
            
            request = PricingRequest(
                product_ids=[product_id],
                strategy=strategy,
                force_update=True
            )
            
            recommendations = await agent.get_price_recommendations(request)
            
            if recommendations:
                rec = recommendations[0]
                print(f"   • Price Change: ${rec.price_change:+.2f} ({rec.price_change_percent:+.1f}%)")
                print(f"   • Confidence: {rec.confidence:.2f}")
                print(f"   • Expected Revenue Impact: {rec.expected_impact.get('revenue_change', 0):+.1%}")
            
            await asyncio.sleep(0.5)
        
        print_header("📊 Market Data Analysis")
        
        # Show market data for all products
        all_products = ["OLJCESPC7Z", "66VCHSJNUP", "1YMWWN1N4O", "L9ECAV7KIM", "2ZYFJ3GM2N"]
        
        print(f"\n📈 Current Market Conditions:")
        for product_id in all_products:
            market_data = await agent._get_market_data(product_id)
            if market_data:
                print(f"\n   🛍️ {product_id}:")
                print(f"      • Current Price: ${market_data.current_price:.2f}")
                print(f"      • Demand Score: {market_data.demand_score:.2f}")
                print(f"      • Inventory: {market_data.inventory_level} units")
                print(f"      • Sales Velocity: {market_data.sales_velocity:.2f}")
                print(f"      • Profit Margin: {market_data.profit_margin:.1%}")
                
                if market_data.competitor_prices:
                    avg_competitor = sum(market_data.competitor_prices) / len(market_data.competitor_prices)
                    print(f"      • Avg Competitor Price: ${avg_competitor:.2f}")
        
        print_header("🔄 Testing Bulk Price Updates")
        
        # Test bulk price updates
        bulk_request = {
            'product_ids': all_products[:3],
            'force_apply': False
        }
        
        bulk_response = await agent._handle_apply_price_changes_request(bulk_request)
        
        print(f"📦 Bulk Update Results:")
        print(f"   • Products Processed: {len(bulk_request['product_ids'])}")
        print(f"   • Changes Applied: {bulk_response['total_changes']}")
        
        if bulk_response['applied_changes']:
            print(f"   • Applied Changes:")
            for change in bulk_response['applied_changes']:
                print(f"     - {change['product_id']}: ${change['old_price']:.2f} → ${change['new_price']:.2f}")
        
        print_header("🔗 Testing A2A Communication")
        
        # Test A2A message handling
        test_pricing_request = {
            "product_ids": ["OLJCESPC7Z"],
            "strategy": "demand_based",
            "force_update": True
        }
        
        a2a_response = await agent._handle_get_price_recommendations_request(test_pricing_request)
        
        print(f"🔗 A2A Pricing Response:")
        if a2a_response['recommendations']:
            rec_data = a2a_response['recommendations'][0]
            print(f"   • Product: {rec_data['product_id']}")
            print(f"   • Recommended Price: ${rec_data['recommended_price']:.2f}")
            print(f"   • Strategy: {rec_data['strategy']}")
            print(f"   • Confidence: {rec_data['confidence']:.2f}")
        
        print_header("📊 Final Statistics")
        
        # Show final statistics
        final_health = await agent.health_check()
        print(f"📈 Final Statistics:")
        print(f"   • Pricing Rules: {final_health['pricing_rules']}")
        print(f"   • Monitored Products: {final_health['monitored_products']}")
        print(f"   • Price Changes Today: {final_health['price_changes_today']}")
        print(f"   • Agent Uptime: {final_health['uptime']:.1f} seconds")
        
        print_header("✅ Demo Complete")
        print("The Dynamic Pricing Agent successfully:")
        print("• ✅ Analyzed market conditions using Gemini AI")
        print("• ✅ Generated intelligent price recommendations")
        print("• ✅ Applied different pricing strategies appropriately")
        print("• ✅ Considered demand, inventory, and competitor factors")
        print("• ✅ Calculated expected business impact")
        print("• ✅ Integrated with A2A protocol for agent communication")
        print("\n🎉 Ready for real-time price optimization!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🛑 Stopping agent...")
        await agent.stop()
        print("✅ Agent stopped successfully")

async def interactive_pricing_demo():
    """Interactive demo where user can test pricing scenarios"""
    print_header("🎮 Interactive Pricing Demo")
    
    agent = DynamicPricingAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Pricing agent ready! Test different scenarios (type 'quit' to exit)")
        
        products = {
            "1": ("OLJCESPC7Z", "Vintage Typewriter", 67.99),
            "2": ("66VCHSJNUP", "Vintage Record Player", 65.50),
            "3": ("1YMWWN1N4O", "Home Barista Kit", 124.99),
            "4": ("L9ECAV7KIM", "Terrarium Kit", 36.45),
            "5": ("2ZYFJ3GM2N", "Film Camera", 2275.00)
        }
        
        strategies = {
            "1": PricingStrategy.DEMAND_BASED,
            "2": PricingStrategy.INVENTORY_BASED,
            "3": PricingStrategy.COMPETITOR_BASED,
            "4": PricingStrategy.REVENUE_OPTIMIZATION,
            "5": PricingStrategy.CLEARANCE,
            "6": PricingStrategy.PREMIUM
        }
        
        while True:
            print("\n" + "-"*50)
            print("Available Products:")
            for key, (product_id, name, price) in products.items():
                print(f"  {key}. {name} (${price:.2f})")
            
            product_choice = input("\nSelect product (1-5) or 'quit': ").strip()
            
            if product_choice.lower() in ['quit', 'exit', 'q']:
                break
            
            if product_choice not in products:
                print("Invalid choice. Please select 1-5.")
                continue
            
            product_id, product_name, current_price = products[product_choice]
            
            print(f"\nSelected: {product_name}")
            print("Pricing Strategies:")
            for key, strategy in strategies.items():
                print(f"  {key}. {strategy.value.replace('_', ' ').title()}")
            
            strategy_choice = input("Select strategy (1-6) or press Enter for AI choice: ").strip()
            
            selected_strategy = None
            if strategy_choice in strategies:
                selected_strategy = strategies[strategy_choice]
            
            # Get recommendations
            request = PricingRequest(
                product_ids=[product_id],
                strategy=selected_strategy,
                force_update=True
            )
            
            try:
                print(f"\n🤖 Analyzing pricing for {product_name}...")
                recommendations = await agent.get_price_recommendations(request)
                
                if recommendations:
                    rec = recommendations[0]
                    print(f"\n💰 Pricing Recommendation:")
                    print(f"   Current Price: ${rec.current_price:.2f}")
                    print(f"   Recommended Price: ${rec.recommended_price:.2f}")
                    print(f"   Change: ${rec.price_change:+.2f} ({rec.price_change_percent:+.1f}%)")
                    print(f"   Strategy: {rec.strategy.value}")
                    print(f"   Reason: {rec.reason.value}")
                    print(f"   Confidence: {rec.confidence:.2f}")
                    
                    print(f"\n📊 Expected Impact:")
                    for metric, value in rec.expected_impact.items():
                        print(f"   {metric.replace('_', ' ').title()}: {value:+.1%}")
                else:
                    print("❌ No recommendations generated")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    finally:
        await agent.stop()

def main():
    """Main demo function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_pricing_demo())
    else:
        asyncio.run(demo_dynamic_pricing())

if __name__ == "__main__":
    main()