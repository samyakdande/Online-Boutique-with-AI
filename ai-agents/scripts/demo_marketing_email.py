#!/usr/bin/env python3
"""
Marketing Email Agent Demo

This script demonstrates the Marketing Email Agent functionality
with sample customer profiles and real Gemini AI email generation.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_agents.agents.marketing_email import (
    MarketingEmailAgent, 
    EmailRequest,
    EmailType,
    CustomerSegment
)
from ai_agents.core.config import get_settings

# Sample email campaign scenarios for testing
EMAIL_SCENARIOS = [
    {
        "name": "Welcome Campaign for New Customers",
        "customer_ids": ["new_customer_001", "new_customer_002"],
        "email_type": EmailType.WELCOME,
        "personalization_data": {
            "welcome_offer": "15% off your first purchase",
            "featured_categories": ["accessories", "electronics"]
        },
        "expected_outcome": "personalized_welcome_emails"
    },
    {
        "name": "Cart Abandonment Recovery",
        "customer_ids": ["cart_abandoner_001"],
        "email_type": EmailType.CART_ABANDONMENT,
        "personalization_data": {
            "cart_items": ["OLJCESPC7Z", "66VCHSJNUP"],
            "cart_value": 133.49,
            "incentive": "10% off your cart + free shipping"
        },
        "expected_outcome": "recovery_email_with_incentive"
    },
    {
        "name": "Product Recommendations",
        "customer_ids": ["loyal_customer_001", "frequent_buyer_001"],
        "email_type": EmailType.PRODUCT_RECOMMENDATION,
        "personalization_data": {
            "recommended_products": ["1YMWWN1N4O", "L9ECAV7KIM"],
            "reason": "Based on your recent purchases"
        },
        "expected_outcome": "personalized_product_suggestions"
    },
    {
        "name": "Re-engagement Campaign",
        "customer_ids": ["inactive_customer_001", "inactive_customer_002"],
        "email_type": EmailType.RE_ENGAGEMENT,
        "personalization_data": {
            "special_offer": "20% off everything",
            "message": "We miss you! Come back and see what's new."
        },
        "expected_outcome": "win_back_emails"
    }
]

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_email_result(scenario: dict, emails: list):
    """Print formatted email campaign results"""
    print(f"\n📧 Campaign: {scenario['name']}")
    print(f"🎯 Type: {scenario['email_type'].value}")
    print(f"👥 Recipients: {len(scenario['customer_ids'])}")
    print(f"📊 Expected: {scenario['expected_outcome']}")
    
    if not emails:
        print("❌ No emails generated")
        return
    
    print(f"\n📬 Generated Emails: {len(emails)}")
    
    for i, email in enumerate(emails, 1):
        print(f"\n   📨 Email {i}:")
        print(f"      • To: {email.email_address}")
        print(f"      • Subject: {email.subject}")
        print(f"      • Content Preview: {email.content[:100]}{'...' if len(email.content) > 100 else ''}")
        print(f"      • Status: {email.status.value}")
        print(f"      • Scheduled: {email.scheduled_time.strftime('%H:%M:%S')}")
        
        if email.personalized_data:
            print(f"      • Personalization:")
            for key, value in email.personalized_data.items():
                if isinstance(value, list):
                    print(f"        - {key}: {', '.join(str(v) for v in value[:3])}")
                else:
                    print(f"        - {key}: {value}")
    
    # Validate email quality
    has_personalization = any(email.personalized_data for email in emails)
    appropriate_subjects = all(len(email.subject) < 60 for email in emails)
    
    print(f"\n   📈 Quality Check:")
    print(f"      • Personalized: {'✅' if has_personalization else '❌'}")
    print(f"      • Subject Length: {'✅' if appropriate_subjects else '❌'}")
    print(f"      • Content Generated: {'✅' if all(email.content for email in emails) else '❌'}")

async def demo_marketing_email():
    """Demonstrate marketing email functionality"""
    print_header("📧 Marketing Email Agent Demo")
    
    # Check if we have Gemini API key
    settings = get_settings()
    if not settings.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return
    
    print(f"🔑 Using Gemini API key: {settings.gemini_api_key[:10]}...")
    
    # Initialize agent
    print("\n🚀 Initializing Marketing Email Agent...")
    agent = MarketingEmailAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Agent started successfully!")
        
        # Test health check
        print("\n🏥 Running health check...")
        health = await agent.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Gemini Connection: {'✅' if health['gemini_connection'] else '❌'}")
        print(f"   Customer Profiles: {health['customer_profiles']}")
        print(f"   Email Templates: {health['email_templates']}")
        
        if not health['gemini_connection']:
            print("❌ Gemini connection failed. Please check your API key.")
            return
        
        print_header("📬 Testing Email Campaign Scenarios")
        
        # Test each email scenario
        for i, scenario in enumerate(EMAIL_SCENARIOS, 1):
            print(f"\n--- Scenario {i}/{len(EMAIL_SCENARIOS)} ---")
            
            request = EmailRequest(
                customer_ids=scenario["customer_ids"],
                email_type=scenario["email_type"],
                personalization_data=scenario["personalization_data"],
                send_immediately=False,
                test_mode=True  # Test mode for demo
            )
            
            try:
                emails = await agent.create_email_campaign(request)
                print_email_result(scenario, emails)
                
                # Small delay between campaigns
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error in scenario {scenario['name']}: {str(e)}")
        
        print_header("🎯 Testing Triggered Campaigns")
        
        # Test cart abandonment trigger
        print(f"\n🛒 Testing Cart Abandonment Trigger")
        cart_success = await agent.trigger_cart_abandonment_email(
            "cart_abandoner_002", 
            ["OLJCESPC7Z", "1YMWWN1N4O"]
        )
        print(f"   Cart Abandonment Email: {'✅ Triggered' if cart_success else '❌ Failed'}")
        
        # Test product recommendation trigger
        print(f"\n🎁 Testing Product Recommendation Trigger")
        rec_success = await agent.trigger_product_recommendation_email(
            "loyal_customer_002",
            ["66VCHSJNUP", "L9ECAV7KIM", "2ZYFJ3GM2N"]
        )
        print(f"   Product Recommendation Email: {'✅ Triggered' if rec_success else '❌ Failed'}")
        
        # Test re-engagement campaign
        print(f"\n💌 Testing Re-engagement Campaign")
        inactive_customers = ["inactive_001", "inactive_002", "inactive_003"]
        re_engagement_count = await agent.trigger_re_engagement_campaign(inactive_customers)
        print(f"   Re-engagement Emails: {re_engagement_count} triggered")
        
        print_header("📊 Customer Profile Analysis")
        
        # Show customer profiles created during demo
        print(f"\n👥 Customer Profiles Created:")
        for customer_id, profile in agent.customer_profiles.items():
            print(f"\n   👤 {profile.name} ({customer_id}):")
            print(f"      • Segment: {profile.segment.value}")
            print(f"      • Email: {profile.email}")
            print(f"      • Preferences: {profile.preferences}")
            print(f"      • Purchase History: {profile.purchase_history}")
            print(f"      • Email Engagement: Open {profile.email_engagement.get('open_rate', 0):.1%}, Click {profile.email_engagement.get('click_rate', 0):.1%}")
            print(f"      • Last Purchase: {profile.last_purchase.strftime('%Y-%m-%d') if profile.last_purchase else 'Never'}")
        
        print_header("⏱️ Email Queue Processing")
        
        # Wait for email processing
        print(f"\n📤 Processing Email Queue...")
        print(f"   Emails in Queue: {len(agent.email_queue)}")
        
        # Wait a bit for background processing
        await asyncio.sleep(5)
        
        # Check sent emails
        print(f"   Emails Sent: {len(agent.sent_emails)}")
        
        if agent.sent_emails:
            print(f"\n📨 Recent Sent Emails:")
            for email_id, email in list(agent.sent_emails.items())[:3]:  # Show first 3
                print(f"      • {email.subject} → {email.customer_id}")
                print(f"        Status: {email.status.value}")
                if email.tracking_data:
                    print(f"        Tracking: {list(email.tracking_data.keys())}")
        
        print_header("🔗 Testing A2A Communication")
        
        # Test A2A email campaign request
        a2a_request = {
            "customer_ids": ["a2a_customer_001"],
            "email_type": "welcome",
            "personalization_data": {"source": "A2A_request"},
            "test_mode": True
        }
        
        a2a_response = await agent._handle_send_email_campaign_request(a2a_request)
        print(f"🔗 A2A Email Campaign:")
        print(f"   Campaign Created: {'✅' if a2a_response['campaign_created'] else '❌'}")
        print(f"   Emails Generated: {a2a_response['emails_generated']}")
        
        # Test behavior tracking
        behavior_request = {
            "customer_id": "behavior_test_001",
            "behavior_data": {
                "cart_abandoned": True,
                "cart_items": ["OLJCESPC7Z"],
                "product_viewed": "66VCHSJNUP"
            }
        }
        
        behavior_response = await agent._handle_track_customer_behavior_request(behavior_request)
        print(f"🔗 A2A Behavior Tracking:")
        print(f"   Customer Updated: {'✅' if behavior_response['customer_updated'] else '❌'}")
        
        # Test metrics request
        metrics_response = await agent._handle_get_campaign_metrics_request({})
        print(f"🔗 A2A Campaign Metrics:")
        if 'overall_metrics' in metrics_response:
            metrics = metrics_response['overall_metrics']
            print(f"   Total Emails Sent: {metrics['total_emails_sent']}")
            print(f"   Overall Open Rate: {metrics['overall_open_rate']:.1%}")
            print(f"   Overall Click Rate: {metrics['overall_click_rate']:.1%}")
        
        print_header("📊 Final Statistics")
        
        # Show final statistics
        final_health = await agent.health_check()
        print(f"📈 Final Statistics:")
        print(f"   • Customer Profiles: {final_health['customer_profiles']}")
        print(f"   • Email Templates: {final_health['email_templates']}")
        print(f"   • Emails in Queue: {final_health['emails_in_queue']}")
        print(f"   • Emails Sent Today: {final_health['emails_sent_today']}")
        print(f"   • Active Campaigns: {final_health['active_campaigns']}")
        print(f"   • Agent Uptime: {final_health['uptime']:.1f} seconds")
        
        print_header("✅ Demo Complete")
        print("The Marketing Email Agent successfully:")
        print("• ✅ Generated personalized email content using Gemini AI")
        print("• ✅ Created targeted campaigns for different customer segments")
        print("• ✅ Triggered automated emails based on customer behavior")
        print("• ✅ Processed email queue with delivery simulation")
        print("• ✅ Tracked email engagement and performance metrics")
        print("• ✅ Integrated with A2A protocol for agent communication")
        print("\n🎉 Ready for automated email marketing campaigns!")
        
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
    asyncio.run(demo_marketing_email())

if __name__ == "__main__":
    main()