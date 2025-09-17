#!/usr/bin/env python3
"""
Review Tracker Agent Demo

This script demonstrates the Review Tracker Agent functionality
with sample reviews and real Gemini AI analysis.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_agents.agents.review_tracker import ReviewTrackerAgent, ReviewRequest
from ai_agents.core.config import get_settings

# Sample reviews for testing
SAMPLE_REVIEWS = [
    {
        "text": "This jacket is absolutely amazing! The quality is outstanding, fits perfectly, and the color is exactly as shown. Fast shipping too. Highly recommend!",
        "product_id": "OLJCESPC7Z",
        "review_id": "review_001",
        "expected": "positive_authentic"
    },
    {
        "text": "Product is okay I guess. Nothing special. It's fine.",
        "product_id": "OLJCESPC7Z", 
        "review_id": "review_002",
        "expected": "neutral_authentic"
    },
    {
        "text": "AMAZING PRODUCT! BEST EVER! FIVE STARS! HIGHLY RECOMMEND! GREAT QUALITY!",
        "product_id": "OLJCESPC7Z",
        "review_id": "review_003", 
        "expected": "positive_fake"
    },
    {
        "text": "The sizing runs really small. I ordered a medium but it fits like a small. The material feels cheap and started pilling after one wash. Very disappointed.",
        "product_id": "OLJCESPC7Z",
        "review_id": "review_004",
        "expected": "negative_authentic"
    },
    {
        "text": "Great product! Love it! Amazing quality! Fast shipping! Perfect fit! Highly recommend! Five stars!",
        "product_id": "66VCHSJNUP",
        "review_id": "review_005",
        "expected": "positive_fake"
    },
    {
        "text": "I bought this for my daughter and she loves it. The fabric is soft and comfortable, true to size, and the color hasn't faded after multiple washes. Good value for money.",
        "product_id": "66VCHSJNUP",
        "review_id": "review_006",
        "expected": "positive_authentic"
    }
]

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_analysis_result(review_text: str, analysis, expected: str):
    """Print formatted analysis results"""
    print(f"\n📝 Review: \"{review_text[:80]}{'...' if len(review_text) > 80 else ''}\"")
    print(f"🎯 Expected: {expected}")
    print(f"📊 Results:")
    print(f"   • Sentiment: {analysis.sentiment_type.value} (score: {analysis.sentiment_score:.2f})")
    print(f"   • Authenticity: {analysis.authenticity_score:.2f}")
    print(f"   • Confidence: {analysis.confidence:.2f}")
    print(f"   • Themes: {[theme.value for theme in analysis.key_themes]}")
    print(f"   • Flagged: {'Yes' if analysis.flagged_for_moderation else 'No'}")
    print(f"   • Reasoning: {analysis.reasoning}")
    
    # Simple validation
    if expected == "positive_authentic":
        correct = analysis.sentiment_score > 0.3 and analysis.authenticity_score > 0.6
    elif expected == "positive_fake":
        correct = analysis.sentiment_score > 0.3 and analysis.authenticity_score < 0.5
    elif expected == "negative_authentic":
        correct = analysis.sentiment_score < -0.1 and analysis.authenticity_score > 0.6
    elif expected == "neutral_authentic":
        correct = -0.3 < analysis.sentiment_score < 0.3 and analysis.authenticity_score > 0.6
    else:
        correct = True
    
    print(f"   ✅ Analysis {'matches' if correct else 'differs from'} expectation")

async def demo_review_analysis():
    """Demonstrate review analysis functionality"""
    print_header("🤖 Review Tracker Agent Demo")
    
    # Check if we have Gemini API key
    settings = get_settings()
    if not settings.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return
    
    print(f"🔑 Using Gemini API key: {settings.gemini_api_key[:10]}...")
    
    # Initialize agent
    print("\n🚀 Initializing Review Tracker Agent...")
    agent = ReviewTrackerAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Agent started successfully!")
        
        # Test health check
        print("\n🏥 Running health check...")
        health = await agent.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Gemini Connection: {'✅' if health['gemini_connection'] else '❌'}")
        
        if not health['gemini_connection']:
            print("❌ Gemini connection failed. Please check your API key.")
            return
        
        print_header("📊 Analyzing Sample Reviews")
        
        # Analyze each sample review
        for i, sample in enumerate(SAMPLE_REVIEWS, 1):
            print(f"\n--- Review {i}/{len(SAMPLE_REVIEWS)} ---")
            
            request = ReviewRequest(
                review_text=sample["text"],
                product_id=sample["product_id"],
                review_id=sample["review_id"]
            )
            
            try:
                analysis = await agent.analyze_review(request)
                print_analysis_result(sample["text"], analysis, sample["expected"])
                
            except Exception as e:
                print(f"❌ Error analyzing review: {str(e)}")
        
        print_header("📈 Product Summaries")
        
        # Show product summaries
        unique_products = list(set(sample["product_id"] for sample in SAMPLE_REVIEWS))
        
        for product_id in unique_products:
            summary = await agent.get_product_review_summary(product_id)
            if summary:
                print(f"\n🛍️ Product: {product_id}")
                print(f"   • Total Reviews: {summary.total_reviews}")
                print(f"   • Average Sentiment: {summary.average_sentiment:.2f}")
                print(f"   • Authenticity Rate: {summary.authenticity_rate:.2f}")
                print(f"   • Top Themes: {[theme.value for theme in summary.top_themes[:3]]}")
                print(f"   • Recommendation Impact: {summary.recommendation_impact:.2f}")
                
                # Show sentiment distribution
                print(f"   • Sentiment Distribution:")
                for sentiment, count in summary.sentiment_distribution.items():
                    if count > 0:
                        print(f"     - {sentiment.value}: {count}")
        
        print_header("📊 Sentiment Trends")
        
        # Show sentiment trends
        for product_id in unique_products:
            trends = await agent.get_sentiment_trends(product_id, 30)
            print(f"\n📈 Trends for {product_id}:")
            print(f"   • Trend: {trends['trend']}")
            print(f"   • Sentiment Change: {trends['sentiment_change']:+.2f}")
            print(f"   • Volume Change: {trends['review_volume_change']:+.2f}")
            print(f"   • Authenticity Trend: {trends['authenticity_trend']}")
        
        print_header("🔗 A2A Communication Test")
        
        # Test A2A communication
        test_message = {
            'request_type': 'get_product_sentiment',
            'data': {'product_id': unique_products[0]}
        }
        
        response = await agent._handle_a2a_request(test_message)
        print(f"A2A Request: {test_message['request_type']}")
        print(f"Response Success: {'✅' if response['success'] else '❌'}")
        if response['success'] and response['data']:
            print(f"Data: Product has {response['data']['total_reviews']} reviews")
        
        print_header("✅ Demo Complete")
        print("The Review Tracker Agent successfully:")
        print("• ✅ Analyzed review sentiment using Gemini AI")
        print("• ✅ Detected potentially fake reviews")
        print("• ✅ Extracted key themes from reviews")
        print("• ✅ Generated product summaries")
        print("• ✅ Provided sentiment trends")
        print("• ✅ Handled A2A communication")
        print("\n🎉 Ready for integration with other agents!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🛑 Stopping agent...")
        await agent.stop()
        print("✅ Agent stopped successfully")

async def interactive_demo():
    """Interactive demo where user can input their own reviews"""
    print_header("🎮 Interactive Review Analysis")
    
    agent = ReviewTrackerAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Agent ready! Enter reviews to analyze (type 'quit' to exit)")
        
        while True:
            print("\n" + "-"*50)
            review_text = input("📝 Enter a review to analyze: ").strip()
            
            if review_text.lower() in ['quit', 'exit', 'q']:
                break
            
            if not review_text:
                continue
            
            product_id = input("🛍️ Enter product ID (or press Enter for 'TEST123'): ").strip()
            if not product_id:
                product_id = "TEST123"
            
            request = ReviewRequest(
                review_text=review_text,
                product_id=product_id,
                review_id=f"interactive_{datetime.now().timestamp()}"
            )
            
            try:
                print("\n🤖 Analyzing...")
                analysis = await agent.analyze_review(request)
                print_analysis_result(review_text, analysis, "user_input")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    finally:
        await agent.stop()

def main():
    """Main demo function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_demo())
    else:
        asyncio.run(demo_review_analysis())

if __name__ == "__main__":
    main()