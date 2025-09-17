#!/usr/bin/env python3
"""
Simple ML Models MCP server test script.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_ml_models_server():
    """Test the ML Models MCP server functionality."""
    print("🤖 Testing ML Models MCP Server...")
    
    try:
        # Import our ML Models MCP server
        from ai_agents.mcp_servers.ml_models import MLModelsMCPServer
        
        # Create and initialize server
        print("📦 Creating ML Models MCP server...")
        server = MLModelsMCPServer()
        
        print("🔧 Initializing server...")
        await server.initialize()
        print("✅ Server initialized successfully!")
        
        # Test text generation
        print("📝 Testing text generation...")
        text_result = await server._generate_text({
            "prompt": "Recommend a stylish outfit for a business meeting",
            "model": "gemini-pro"
        })
        print(f"✅ Text generation: {len(text_result['response'])} characters generated")
        
        # Test chat completion
        print("💬 Testing chat completion...")
        chat_result = await server._chat_completion({
            "messages": [
                {"role": "user", "content": "What colors go well with navy blue?"}
            ]
        })
        print(f"✅ Chat completion: {len(chat_result['response']['content'])} characters in response")
        
        # Test image analysis
        print("👁️ Testing image analysis...")
        image_result = await server._analyze_image({
            "prompt": "Analyze this fashion item",
            "analysis_type": "fashion"
        })
        print(f"✅ Image analysis: {image_result['confidence']:.2f} confidence score")
        
        # Test virtual try-on
        print("👗 Testing virtual try-on...")
        tryon_result = await server._virtual_try_on({
            "user_image": "mock_user_image",
            "product_image": "mock_product_image",
            "analysis_points": ["fit", "style", "color"]
        })
        print(f"✅ Virtual try-on: {tryon_result['overall_score']:.1f}/10 overall score")
        
        # Test recommendations
        print("🎯 Testing AI recommendations...")
        rec_result = await server._get_recommendations({
            "user_id": "test_user",
            "recommendation_type": "personalized",
            "limit": 5
        })
        print(f"✅ Recommendations: {len(rec_result['recommendations'])} items recommended")
        
        # Test style matching
        print("✨ Testing style matching...")
        style_result = await server._style_matching({
            "base_product_id": "PROD_123",
            "occasion": "casual"
        })
        print(f"✅ Style matching: {len(style_result['style_matches'])} matching items found")
        
        # Test sentiment analysis
        print("😊 Testing sentiment analysis...")
        sentiment_result = await server._analyze_sentiment({
            "text": "I love this dress! It's perfect for my style.",
            "context": "review"
        })
        print(f"✅ Sentiment analysis: {sentiment_result['sentiment']['sentiment']} sentiment detected")
        
        # Test trend detection
        print("📈 Testing trend detection...")
        trend_result = await server._detect_trends({
            "data_source": "sales",
            "time_range": "7d"
        })
        print(f"✅ Trend detection: {len(trend_result['trends'])} trends identified")
        
        # Test model info
        print("ℹ️ Testing model information...")
        model_info = await server._get_model_info({})
        print(f"✅ Model info: {model_info['total_models']} models available")
        
        # Test model health
        print("🏥 Testing model health check...")
        health_result = await server._model_health_check({})
        print(f"✅ Model health: {health_result['overall_status']} status")
        
        print("\n🎉 All ML Models MCP server tests passed!")
        print("🤖 The ML Models MCP Server is working correctly!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the ai-agents directory")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("🤖 AI-Powered Boutique Agents - ML Models MCP Server Test")
    print("=" * 65)
    
    # Run the test
    success = asyncio.run(test_ml_models_server())
    
    if success:
        print("\n✅ SUCCESS: ML Models MCP server is ready!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Check the errors above")
        sys.exit(1)