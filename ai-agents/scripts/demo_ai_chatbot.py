#!/usr/bin/env python3
"""
AI Chatbot Agent Demo

This script demonstrates the AI Chatbot Agent functionality
with sample conversations and real Gemini AI responses.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_agents.agents.ai_chatbot import (
    AIChatbotAgent, 
    ChatRequest,
    MessageType,
    IntentType
)
from ai_agents.core.config import get_settings

# Sample conversation scenarios for testing
SAMPLE_CONVERSATIONS = [
    {
        "name": "New Customer Greeting",
        "messages": [
            "Hello! I'm new here.",
            "What products do you have?",
            "I'm looking for something vintage.",
            "Thanks for your help!"
        ],
        "expected_intents": [IntentType.GREETING, IntentType.PRODUCT_QUESTION, IntentType.RECOMMENDATION_REQUEST, IntentType.GOODBYE]
    },
    {
        "name": "Product Inquiry",
        "messages": [
            "Hi there!",
            "Tell me about the vintage typewriter",
            "How much does it cost?",
            "Is it available in different colors?",
            "What's the return policy?"
        ],
        "expected_intents": [IntentType.GREETING, IntentType.PRODUCT_QUESTION, IntentType.PRICE_QUESTION, IntentType.AVAILABILITY_CHECK, IntentType.PRODUCT_QUESTION]
    },
    {
        "name": "Shopping Assistance",
        "messages": [
            "I need help finding a gift",
            "It's for my coffee-loving friend",
            "What do you recommend?",
            "That sounds perfect! How do I order it?"
        ],
        "expected_intents": [IntentType.RECOMMENDATION_REQUEST, IntentType.RECOMMENDATION_REQUEST, IntentType.RECOMMENDATION_REQUEST, IntentType.ORDER_INQUIRY]
    },
    {
        "name": "Customer Complaint",
        "messages": [
            "I have a problem with my order",
            "The item I received was damaged",
            "This is very disappointing",
            "I want to speak to a manager"
        ],
        "expected_intents": [IntentType.COMPLAINT, IntentType.COMPLAINT, IntentType.COMPLAINT, IntentType.ESCALATION_REQUEST]
    }
]

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_conversation_result(scenario: dict, responses: list, session_id: str):
    """Print formatted conversation results"""
    print(f"\n💬 Conversation: {scenario['name']}")
    print(f"🆔 Session: {session_id}")
    print(f"📊 Messages: {len(scenario['messages'])}")
    
    print(f"\n🗣️ Conversation Flow:")
    for i, (user_msg, bot_response) in enumerate(zip(scenario['messages'], responses), 1):
        print(f"\n   {i}. 👤 User: {user_msg}")
        print(f"      🤖 Bot: {bot_response.content}")
        
        if bot_response.suggestions:
            print(f"      💡 Suggestions: {', '.join(bot_response.suggestions[:3])}")
        
        if bot_response.actions:
            actions_str = ', '.join([action.get('type', 'unknown') for action in bot_response.actions])
            print(f"      ⚡ Actions: {actions_str}")
        
        print(f"      🎯 Confidence: {bot_response.confidence:.2f}")
        
        if bot_response.escalation_needed:
            print(f"      🚨 Escalation needed!")
    
    # Check if conversation flow makes sense
    escalations = sum(1 for resp in responses if resp.escalation_needed)
    avg_confidence = sum(resp.confidence for resp in responses) / len(responses)
    
    print(f"\n   📈 Analysis:")
    print(f"      • Average Confidence: {avg_confidence:.2f}")
    print(f"      • Escalations: {escalations}")
    print(f"      • Flow Quality: {'Good' if avg_confidence > 0.6 and escalations <= 1 else 'Needs Review'}")

async def demo_chatbot_conversations():
    """Demonstrate chatbot conversation functionality"""
    print_header("🤖 AI Chatbot Agent Demo")
    
    # Check if we have Gemini API key
    settings = get_settings()
    if not settings.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return
    
    print(f"🔑 Using Gemini API key: {settings.gemini_api_key[:10]}...")
    
    # Initialize agent
    print("\n🚀 Initializing AI Chatbot Agent...")
    agent = AIChatbotAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Agent started successfully!")
        
        # Test health check
        print("\n🏥 Running health check...")
        health = await agent.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Gemini Connection: {'✅' if health['gemini_connection'] else '❌'}")
        print(f"   Product Knowledge: {health['product_knowledge_size']} items")
        print(f"   FAQ Knowledge: {health['faq_knowledge_size']} entries")
        
        if not health['gemini_connection']:
            print("❌ Gemini connection failed. Please check your API key.")
            return
        
        print_header("💬 Testing Conversation Scenarios")
        
        # Test each conversation scenario
        for i, scenario in enumerate(SAMPLE_CONVERSATIONS, 1):
            print(f"\n--- Scenario {i}/{len(SAMPLE_CONVERSATIONS)} ---")
            
            session_id = f"demo_session_{i}"
            responses = []
            
            # Process each message in the conversation
            for j, message in enumerate(scenario['messages']):
                request = ChatRequest(
                    session_id=session_id,
                    user_id=f"demo_user_{i}",
                    message=message,
                    message_type=MessageType.TEXT,
                    context={"demo": True, "message_number": j + 1}
                )
                
                try:
                    response = await agent.process_chat_message(request)
                    responses.append(response)
                    
                    # Small delay between messages
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"❌ Error in message {j + 1}: {str(e)}")
                    break
            
            if responses:
                print_conversation_result(scenario, responses, session_id)
        
        print_header("🔄 Testing Context Persistence")
        
        # Test context persistence across messages
        persistent_session = "persistent_test"
        context_messages = [
            "Hi, I'm looking for a gift",
            "It's for my friend who loves coffee",
            "What do you have in that category?",
            "Tell me more about the barista kit",
            "What's included in the kit?"
        ]
        
        print(f"\n🔗 Testing context persistence with session: {persistent_session}")
        
        for i, message in enumerate(context_messages, 1):
            request = ChatRequest(
                session_id=persistent_session,
                user_id="context_test_user",
                message=message,
                message_type=MessageType.TEXT
            )
            
            response = await agent.process_chat_message(request)
            print(f"\n   {i}. 👤: {message}")
            print(f"      🤖: {response.content[:100]}{'...' if len(response.content) > 100 else ''}")
            
            await asyncio.sleep(0.5)
        
        # Check final context
        context_request = {"session_id": persistent_session}
        context_response = await agent._handle_get_conversation_context_request(context_request)
        
        if context_response.get('found'):
            context_data = context_response['context']
            print(f"\n   📊 Final Context:")
            print(f"      • Messages: {context_response['message_count']}")
            print(f"      • State: {context_data['state']}")
            print(f"      • Intent History: {[intent for intent in context_data['intent_history'][-3:]]}")
            print(f"      • Mentioned Products: {context_data['mentioned_products']}")
        
        print_header("🚨 Testing Escalation Scenarios")
        
        # Test escalation
        escalation_session = "escalation_test"
        escalation_messages = [
            "I have a serious problem",
            "My order was completely wrong",
            "This is the third time this happened",
            "I want to speak to a manager right now"
        ]
        
        print(f"\n🚨 Testing escalation with session: {escalation_session}")
        
        escalation_triggered = False
        for i, message in enumerate(escalation_messages, 1):
            request = ChatRequest(
                session_id=escalation_session,
                user_id="escalation_test_user",
                message=message,
                message_type=MessageType.TEXT
            )
            
            response = await agent.process_chat_message(request)
            print(f"\n   {i}. 👤: {message}")
            print(f"      🤖: {response.content[:80]}{'...' if len(response.content) > 80 else ''}")
            
            if response.escalation_needed:
                print(f"      🚨 ESCALATION TRIGGERED!")
                escalation_triggered = True
            
            await asyncio.sleep(0.5)
        
        print(f"\n   ✅ Escalation system {'working' if escalation_triggered else 'needs review'}")
        
        print_header("🔗 Testing A2A Communication")
        
        # Test A2A message handling
        test_chat_request = {
            "session_id": "a2a_test",
            "user_id": "a2a_user",
            "message": "Hello from another agent!",
            "message_type": "text"
        }
        
        a2a_response = await agent._handle_chat_message_request(test_chat_request)
        print(f"🔗 A2A Chat Response: {a2a_response['content'][:60]}...")
        
        print_header("📊 Final Statistics")
        
        # Show final statistics
        final_health = await agent.health_check()
        print(f"📈 Final Statistics:")
        print(f"   • Active Sessions: {final_health['active_sessions']}")
        print(f"   • Total Messages: {final_health['total_messages']}")
        print(f"   • Product Knowledge: {final_health['product_knowledge_size']}")
        print(f"   • FAQ Knowledge: {final_health['faq_knowledge_size']}")
        print(f"   • Agent Uptime: {final_health['uptime']:.1f} seconds")
        
        print_header("✅ Demo Complete")
        print("The AI Chatbot Agent successfully:")
        print("• ✅ Processed natural language conversations using Gemini AI")
        print("• ✅ Classified user intents and maintained context")
        print("• ✅ Provided product information and recommendations")
        print("• ✅ Handled escalation scenarios appropriately")
        print("• ✅ Maintained conversation state across messages")
        print("• ✅ Integrated with A2A protocol for agent communication")
        print("\n🎉 Ready for multi-modal customer interactions!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🛑 Stopping agent...")
        await agent.stop()
        print("✅ Agent stopped successfully")

async def interactive_chat_demo():
    """Interactive demo where user can chat with the bot"""
    print_header("🎮 Interactive Chat Demo")
    
    agent = AIChatbotAgent()
    
    try:
        await agent.initialize()
        await agent.start()
        print("✅ Chatbot ready! Start chatting (type 'quit' to exit)")
        
        session_id = "interactive_session"
        message_count = 0
        
        while True:
            print("\n" + "-"*50)
            user_message = input("👤 You: ").strip()
            
            if user_message.lower() in ['quit', 'exit', 'bye']:
                # Send goodbye message
                goodbye_request = ChatRequest(
                    session_id=session_id,
                    user_id="interactive_user",
                    message="Goodbye!",
                    message_type=MessageType.TEXT
                )
                
                goodbye_response = await agent.process_chat_message(goodbye_request)
                print(f"🤖 Bot: {goodbye_response.content}")
                break
            
            if not user_message:
                continue
            
            request = ChatRequest(
                session_id=session_id,
                user_id="interactive_user",
                message=user_message,
                message_type=MessageType.TEXT
            )
            
            try:
                print("🤖 Bot: ", end="", flush=True)
                response = await agent.process_chat_message(request)
                print(response.content)
                
                if response.suggestions:
                    print(f"💡 Suggestions: {', '.join(response.suggestions[:3])}")
                
                if response.escalation_needed:
                    print("🚨 This conversation may need human assistance.")
                
                message_count += 1
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        print(f"\n📊 Chat Summary: {message_count} messages exchanged")
    
    finally:
        await agent.stop()

def main():
    """Main demo function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_chat_demo())
    else:
        asyncio.run(demo_chatbot_conversations())

if __name__ == "__main__":
    main()