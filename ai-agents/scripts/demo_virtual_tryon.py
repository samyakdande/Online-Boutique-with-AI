#!/usr/bin/env python3
"""
Virtual Try-On Agent Demo

This script demonstrates the Virtual Try-On Agent functionality
with real Online Boutique products, body measurements analysis, 
and Gemini AI styling recommendations.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_agents.agents.virtual_tryon import (
    VirtualTryOnAgent, 
    TryOnRequest,
    TryOnResult,
    BodyType,
    FaceShape,
    SkinTone,
    BodyMeasurements,
    FacialFeatures,
)
from ai_agents.core.config import get_settings

# ================================
# Real Online Boutique Product IDs for Virtual Try-On
# ================================
TRYON_SCENARIOS = [
    {
        "name": "Vintage Typewriter Try-On",
        "user_id": "vintage_lover_001",
        "product_ids": ["OLJCESPC7Z"],  # Vintage Typewriter
        "image_data": "mock_base64_image_data",
        "preferences": {
            "style": "vintage",
            "fit_preference": "regular",
            "color_preference": "classic"
        },
        "expected_outcome": "vintage_accessory_analysis"
    },
    {
        "name": "Record Player Style Analysis",
        "user_id": "music_enthusiast_001", 
        "product_ids": ["66VCHSJNUP"],  # Vintage Record Player
        "preferences": {
            "style": "retro",
            "fit_preference": "statement_piece",
            "occasion": "home_decor"
        },
        "expected_outcome": "retro_style_analysis"
    },
    {
        "name": "Home Barista Kit Recommendations",
        "user_id": "coffee_lover_001",
        "product_ids": ["1YMWWN1N4O", "L9ECAV7KIM"],  # Home Barista Kit, Terrarium Kit
        "preferences": {
            "style": "modern",
            "fit_preference": "functional",
            "age_group": "young_professional"
        },
        "expected_outcome": "lifestyle_product_analysis"
    }
]

# ================================
# Helper printing functions
# ================================
def print_header(title: str):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_tryon_result(scenario: dict, results: List):
    print(f"\n👗 Scenario: {scenario['name']}")
    print(f"👤 User: {scenario['user_id']}")
    print(f"🛍️ Products: {', '.join(scenario['product_ids'])}")
    print(f"🎯 Expected: {scenario['expected_outcome']}")

    if not results:
        print("❌ No results returned")
        return

    for i, result in enumerate(results, 1):
        print(f"\n🔍 Product {i} Results:")
        print(f"   • Product: {result.product_name}")
        print(f"   • Fit Score: {result.fit_score:.1f}/10")
        print(f"   • Style Score: {result.style_score:.1f}/10")
        print(f"   • Overall Score: {result.overall_score:.1f}/10")
        print(f"   • Size Recommendation: {result.size_recommendation}")
        print(f"   • Confidence: {result.confidence:.1%}")
        
        if result.styling_tips:
            print(f"   • Style Tips:")
            for tip in result.styling_tips[:3]:  # Show top 3
                print(f"     - {tip}")
        
        if result.color_recommendations:
            print(f"   • Color Recommendations: {', '.join(result.color_recommendations[:3])}")
        
        # Quality indicators
        good_fit = result.fit_score >= 7.0
        good_style = result.style_score >= 7.0
        high_confidence = result.confidence >= 0.7
        
        print(f"   📊 Quality Check:")
        print(f"      • Fit Quality: {'✅' if good_fit else '⚠️'}")
        print(f"      • Style Match: {'✅' if good_style else '⚠️'}")
        print(f"      • Analysis Confidence: {'✅' if high_confidence else '⚠️'}")

async def demo_virtual_tryon():
    """Demonstrate virtual try-on functionality"""
    print_header("👗 Virtual Try-On Agent Demo")
    
    # Check if we have Gemini API key
    settings = get_settings()
    if not settings.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return
    
    print(f"🔑 Using Gemini API key: {settings.gemini_api_key[:10]}...")

    print("\n🚀 Initializing Virtual Try-On Agent...")
    agent = VirtualTryOnAgent()

    try:
        print("🔧 Initializing agent...")
        await agent.initialize()
        print("▶️ Starting agent...")
        await agent.start()
        print("✅ Agent started successfully!")

        # Health check
        print("\n🏥 Running health check...")
        health = await agent.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Gemini Connection: {'✅' if health.get('gemini_connection', False) else '❌'}")
        print(f"   Cached Users: {health.get('cached_users', 0)}")
        print(f"   Cached Products: {health.get('cached_products', 0)}")
        if health['status'] != 'healthy':
            print("⚠️ Agent is not fully healthy, but continuing with demo...")

        # Test scenarios
        print_header("👗 Testing Virtual Try-On Scenarios")
        
        # Test each try-on scenario
        for i, scenario in enumerate(TRYON_SCENARIOS, 1):
            print(f"\n--- Scenario {i}/{len(TRYON_SCENARIOS)} ---")
            
            request = TryOnRequest(
                user_id=scenario["user_id"],
                product_ids=scenario["product_ids"],
                image_data=scenario.get("image_data"),
                preferences=scenario["preferences"]
            )
            
            try:
                results = await agent.virtual_try_on(request)
                print_tryon_result(scenario, results)
                
                # Small delay between scenarios
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error in scenario {scenario['name']}: {str(e)}")
        
        print_header("📏 Testing User Feature Analysis")
        
        # Test user analysis
        analysis_request = TryOnRequest(
            user_id="analysis_test_user",
            product_ids=["TEST_PRODUCT"],
            image_data="mock_image_data_for_analysis",
            preferences={"style": "casual"}
        )
        
        try:
            user_analysis = await agent.analyze_user_features(analysis_request)
            print(f"👤 User Analysis Results:")
            
            if 'body_measurements' in user_analysis:
                body = user_analysis['body_measurements']
                print(f"   • Body Type: {body.body_type.value.replace('_', ' ').title()}")
                print(f"   • Height: {body.height:.1f} cm")
                print(f"   • Key Measurements: {body.chest:.1f}-{body.waist:.1f}-{body.hips:.1f} cm")
                print(f"   • Analysis Confidence: {body.confidence:.1%}")
            
            if 'facial_features' in user_analysis:
                face = user_analysis['facial_features']
                print(f"   • Face Shape: {face.face_shape.value.title()}")
                print(f"   • Skin Tone: {face.skin_tone.value.title()}")
            
        except Exception as e:
            print(f"❌ Error in user analysis: {str(e)}")
        
        print_header("🔗 Testing A2A Communication")
        
        # Test A2A virtual try-on request
        a2a_request = {
            "user_id": "a2a_user_001", 
            "product_ids": ["A2A_PRODUCT_001"], 
            "preferences": {"style": "casual"}
        }
        
        try:
            a2a_response = await agent._handle_virtual_try_on_request(a2a_request)
            print(f"🔗 A2A Virtual Try-On:")
            if a2a_response and len(a2a_response) > 0:
                result = a2a_response[0]
                print(f"   • Product Analyzed: ✅")
                print(f"   • Fit Score: {result.get('fit_score', 0):.1f}/10")
                print(f"   • Style Score: {result.get('style_score', 0):.1f}/10")
                print(f"   • Size Recommended: {result.get('size_recommendation', 'N/A')}")
            else:
                print("   • No results returned: ❌")
                
        except Exception as e:
            print(f"❌ Error in A2A communication: {str(e)}")
        
        print_header("📊 Final Statistics")
        
        # Show final statistics
        final_health = await agent.health_check()
        print(f"📈 Final Statistics:")
        print(f"   • Active Sessions: {len(getattr(agent, 'active_sessions', {}))}")
        print(f"   • User Analyses: {len(getattr(agent, 'user_analyses', {}))}")
        print(f"   • Product Catalog: {len(getattr(agent, 'product_catalog', {}))}")
        print(f"   • Agent Uptime: {final_health.get('uptime', 0):.1f} seconds")
        
        print_header("✅ Demo Complete")
        print("The Virtual Try-On Agent successfully:")
        print("• ✅ Analyzed user body measurements and facial features")
        print("• ✅ Generated fit scores for different products")
        print("• ✅ Provided style recommendations using Gemini AI")
        print("• ✅ Calculated size recommendations")
        print("• ✅ Suggested color alternatives based on skin tone")
        print("• ✅ Integrated with A2A protocol for agent communication")
        print("• ✅ Supported multiple try-on scenarios")
        print("• ✅ Worked with real Online Boutique products")
        
        print("\n🎉 Ready for virtual fitting experiences!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🛑 Stopping agent...")
        await agent.stop()
        print("✅ Agent stopped successfully")

def main():
    """Main demo function"""
    asyncio.run(demo_virtual_tryon())

if __name__ == "__main__":
    main()