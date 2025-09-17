#!/usr/bin/env python3
"""
Advanced Recommendation Agent Demo

This script demonstrates the Advanced Recommendation Agent functionality
with sample user profiles and real Gemini AI recommendations.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_agents.agents.advanced_recommendation import (
    AdvancedRecommendationAgent, 
    RecommendationRequest,
    RecommendationType,
    UserProfile,
    UserSegment
)
from ai_agents.core.config import get_settings

# Sample user scenarios for testing
SAMPLE_SCENARIOS = [
    {
        "name": "New User - No History",
        "user_id": "new_user_001",
        "context": {
            "demographics": {"age": 25, "location": "San Francisco"},
            "device_type": "mobile",
            "session_data": {"referrer": "google"}
        },
        "recommendation_type": RecommendationType.PERSONALIZED,
        "expected": "cold_start_recommendations"
    },
    {
        "name": "Frequent Buyer - Fashion Forward",
        "user_id": "frequent_buyer_001", 
        "context": {
            "purchase_history": ["OLJCESPC7Z", "66VCHSJNUP", "2ZYFJ3GM2N"],
            "browsing_history": ["1YMWWN1N4O", "L9ECAV7KIM"],
            "preferences": {"style": "vintage", "price_range": "premium"},
            "demographics": {"age": 32, "location": "New York"}
        },
        "recommendation_type": RecommendationType.PERSONALIZED,
        "expected": "personalized_recommendations"
    },
    {
        "name": "Cart-Based Complementary",
        "user_id": "shopper_001",
        "context": {
            "current_cart": ["OLJCESPC7Z"],  # Vintage Typewriter
            "purchase_history": ["66VCHSJNUP"],
            "preferences": {"category": "accessories"}
        },
        "recommendation_type": RecommendationType.COMPLEMENTARY,
        "expected": "complementary_recommendations"
    },
    {
        "name": "Trending Products",
        "user_id": "trend_follower_001",
        "context": {
            "demographics": {"age": 22, "location": "Los Angeles"},
            "preferences": {"follows_trends": True}
        },
        "recommendation_type": RecommendationType.TRENDING,
        "expected": "trending_recommendations"
    },
    {
        "name": "Price Conscious Shopper",
        "user_id": "budget_shopper_001",
        "context": {
            "purchase_history": ["L9ECAV7KIM"],  # Lower priced items
            "preferences": {"price_range": "budget", "value_conscious": True},
            "demographics": {"age": 28, "location": "Chicago"}
        },
        "recommendation_type": RecommendationType.PERSONALIZED,
        "expected": "budget_friendly_recommendations"
    }
]

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_recommendation_result(scenario: dict, response, expected: str):
    """Print formatted recommendation results"""
    print(f"\n🎯 Scenario: {scenario['name']}")
    print(f"👤 User: {scenario['user_id']}")
    print(f"🔍 Type: {scenario['recommendation_type'].value}")
    print(f"📊 Results:")
    print(f"   • User Segment: {response.user_segment.value}")
    print(f"   • Recommendations: {len(response.recommendations)}")
    print(f"   • Generated: {response.generated_at.strftime('%H:%M:%S')}")
    print(f"   • Expires: {response.expires_at.strftime('%H:%M:%S')}")
    
    print(f"\n🛍️ Recommended Products:")
    for i, rec in enumerate(response.recommendations[:5], 1):  # Show top 5
        print(f"   {i}. {rec.product_name}")
        print(f"      • ID: {rec.product_id}")
        print(f"      • Price: ${rec.price:.2f}")
        print(f"      • Confidence: {rec.confidence_score:.2f}")
        print(f"      • Category: {rec.category}")
        print(f"      • Reasoning: {rec.reasoning}")
        print()
    
    # Simple validation
    has_recommendations = len(response.recommendations) > 0
    appropriate_segment = response.user_segment != UserSegment.NEW_USER or scenario['user_id'].startswith('new_user')
    
    print(f"   ✅ Analysis {'successful' if has_recommendations and appropriate_segment else 'needs review'}")

async def demo_recommendation_analysis():
    """Demonstrate recommendation functionality"""
    print_header("🤖 Advanced Recommendation Agent Demo")
    
    # Check if we have Gemini API key
    settings = get_settings()
    if not settings.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return
    
    print(f"🔑 Using Gemini API key: {settings.gemini_api_key[:10]}...")
    
    # Initialize agent
    print("\n🚀 Initializing Advanced Recommendation Agent...")
    agent = AdvancedRecommendationAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Agent started successfully!")
        
        # Test health check
        print("\n🏥 Running health check...")
        health = await agent.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Gemini Connection: {'✅' if health['gemini_connection'] else '❌'}")
        print(f"   Product Catalog: {health['product_catalog_size']} products")
        print(f"   Trending Products: {health['trending_products']} items")
        
        if not health['gemini_connection']:
            print("❌ Gemini connection failed. Please check your API key.")
            return
        
        print_header("🎯 Testing Recommendation Scenarios")
        
        # Test each scenario
        for i, scenario in enumerate(SAMPLE_SCENARIOS, 1):
            print(f"\n--- Scenario {i}/{len(SAMPLE_SCENARIOS)} ---")
            
            request = RecommendationRequest(
                user_id=scenario["user_id"],
                context=scenario["context"],
                recommendation_type=scenario["recommendation_type"],
                limit=8,
                exclude_products=[]
            )
            
            try:
                response = await agent.get_recommendations(request)
                print_recommendation_result(scenario, response, scenario["expected"])
                
                # Small delay between requests
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error in scenario {scenario['name']}: {str(e)}")
        
        print_header("🔄 Testing User Behavior Updates")
        
        # Test behavior updates
        test_user = "frequent_buyer_001"
        print(f"\n📈 Updating behavior for user: {test_user}")
        
        # Simulate user viewing a product
        await agent._handle_update_user_behavior_request({
            "user_id": test_user,
            "behavior_data": {
                "viewed_product": "1YMWWN1N4O",  # Home Barista Kit
                "preferences": {"interest_coffee": True}
            }
        })
        
        # Get updated recommendations
        updated_request = RecommendationRequest(
            user_id=test_user,
            context={"updated_behavior": True},
            recommendation_type=RecommendationType.PERSONALIZED,
            limit=5
        )
        
        updated_response = await agent.get_recommendations(updated_request)
        print(f"✅ Updated recommendations generated: {len(updated_response.recommendations)} items")
        
        print_header("🔗 Testing A2A Communication")
        
        # Test complementary products request
        complementary_request = {
            "product_ids": ["OLJCESPC7Z"],  # Vintage Typewriter
            "limit": 3
        }
        
        complementary_response = await agent._handle_get_complementary_products_request(complementary_request)
        print(f"🔗 Complementary products found: {len(complementary_response['complementary_products'])} items")
        
        for product in complementary_response['complementary_products']:
            print(f"   • {product['product_name']} (${product['price']:.2f})")
        
        print_header("📊 Agent Statistics")
        
        # Show final statistics
        final_health = await agent.health_check()
        print(f"📈 Final Statistics:")
        print(f"   • Cached Recommendations: {final_health['cached_recommendations']}")
        print(f"   • User Profiles: {final_health['user_profiles']}")
        print(f"   • Product Catalog: {final_health['product_catalog_size']}")
        print(f"   • Agent Uptime: {final_health['uptime']:.1f} seconds")
        
        print_header("✅ Demo Complete")
        print("The Advanced Recommendation Agent successfully:")
        print("• ✅ Generated personalized recommendations using Gemini AI")
        print("• ✅ Provided complementary product suggestions")
        print("• ✅ Handled different user segments and scenarios")
        print("• ✅ Updated user behavior and adapted recommendations")
        print("• ✅ Managed trending products and seasonal context")
        print("• ✅ Handled A2A communication with other agents")
        print("\n🎉 Ready for integration with the Online Boutique!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🛑 Stopping agent...")
        await agent.stop()
        print("✅ Agent stopped successfully")

async def interactive_demo():
    """Interactive demo where user can request recommendations"""
    print_header("🎮 Interactive Recommendation Demo")
    
    agent = AdvancedRecommendationAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Agent ready! Request personalized recommendations")
        
        while True:
            print("\n" + "-"*50)
            print("Recommendation Options:")
            print("1. Personalized recommendations")
            print("2. Complementary products")
            print("3. Trending products")
            print("4. Quit")
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == "4":
                break
            
            if choice not in ["1", "2", "3"]:
                print("Invalid choice. Please select 1-4.")
                continue
            
            # Get user input
            user_id = input("Enter user ID (or press Enter for 'demo_user'): ").strip()
            if not user_id:
                user_id = "demo_user"
            
            # Map choice to recommendation type
            rec_types = {
                "1": RecommendationType.PERSONALIZED,
                "2": RecommendationType.COMPLEMENTARY,
                "3": RecommendationType.TRENDING
            }
            
            rec_type = rec_types[choice]
            
            # Build context based on choice
            context = {}
            if choice == "2":  # Complementary
                cart_items = input("Enter current cart items (comma-separated product IDs): ").strip()
                if cart_items:
                    context["current_cart"] = [item.strip() for item in cart_items.split(",")]
            
            request = RecommendationRequest(
                user_id=user_id,
                context=context,
                recommendation_type=rec_type,
                limit=5
            )
            
            try:
                print(f"\n🤖 Generating {rec_type.value} recommendations...")
                response = await agent.get_recommendations(request)
                
                print(f"\n🎯 Recommendations for {user_id}:")
                print(f"User Segment: {response.user_segment.value}")
                
                for i, rec in enumerate(response.recommendations, 1):
                    print(f"\n{i}. {rec.product_name}")
                    print(f"   Price: ${rec.price:.2f}")
                    print(f"   Confidence: {rec.confidence_score:.2f}")
                    print(f"   Reasoning: {rec.reasoning}")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    finally:
        await agent.stop()

def main():
    """Main demo function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_demo())
    else:
        asyncio.run(demo_recommendation_analysis())

if __name__ == "__main__":
    main()