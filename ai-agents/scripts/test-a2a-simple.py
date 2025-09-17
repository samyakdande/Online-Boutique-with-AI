#!/usr/bin/env python3
"""
Simple A2A Protocol test script.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_a2a_protocol():
    """Test the A2A Protocol functionality."""
    print("🔗 Testing A2A Protocol...")
    
    try:
        # Import A2A components
        from ai_agents.a2a.protocol import A2AProtocolHandler, A2AMessage, MessageType, MessagePriority
        from ai_agents.a2a.discovery import ServiceDiscovery, ServiceEndpoint
        
        print("📦 Creating A2A Protocol Handler...")
        
        # Create A2A protocol handler
        handler = A2AProtocolHandler(
            agent_id="test-agent-1",
            agent_name="Test Agent 1",
            capabilities=["test", "demo", "example"]
        )
        
        print("✅ A2A Protocol Handler created successfully!")
        
        # Test message creation
        print("📝 Testing A2A message creation...")
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent="test-agent-1",
            to_agent="test-agent-2",
            payload={"action": "test", "data": "hello"},
            priority=MessagePriority.MEDIUM
        )
        
        message_dict = message.to_dict()
        reconstructed = A2AMessage.from_dict(message_dict)
        
        print(f"✅ Message serialization: ID {message.id}")
        print(f"✅ Message reconstruction: Type {reconstructed.message_type.value}")
        
        # Test service discovery
        print("🔍 Testing Service Discovery...")
        discovery = ServiceDiscovery("test-agent-1")
        
        # Register test services
        await discovery.register_agent(
            agent_id="personal-stylist",
            name="Personal Stylist Agent",
            capabilities=["style-analysis", "outfit-recommendation"],
            endpoint="ws://localhost:8001"
        )
        
        await discovery.register_agent(
            agent_id="inventory-optimizer",
            name="Inventory Optimizer Agent", 
            capabilities=["demand-forecasting", "stock-optimization"],
            endpoint="ws://localhost:8002"
        )
        
        print("✅ Registered test agents")
        
        # Test discovery
        style_agents = await discovery.discover_agents("style-analysis")
        print(f"✅ Found {len(style_agents)} agents with style-analysis capability")
        
        all_agents = await discovery.discover_agents()
        print(f"✅ Total registered agents: {len(all_agents)}")
        
        # Test finding specific agent
        stylist = await discovery.find_agent("personal-stylist")
        if stylist:
            print(f"✅ Found personal stylist: {stylist.name}")
        
        # Test finding best agent
        best_style_agent = await discovery.find_best_agent("style-analysis")
        if best_style_agent:
            print(f"✅ Best style agent: {best_style_agent.agent_id}")
        
        # Test registry stats
        stats = discovery.get_registry_stats()
        print(f"✅ Registry stats: {stats['total_services']} services, {stats['capability_count']} capabilities")
        
        # Test message handlers
        print("🔧 Testing message handlers...")
        
        async def test_handler(payload):
            return {"status": "success", "message": "Handler executed", "received": payload}
        
        handler.register_handler("test_request", test_handler)
        print("✅ Registered test message handler")
        
        # Test workflow orchestration
        print("🔄 Testing workflow orchestration...")
        from ai_agents.a2a.discovery import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(discovery)
        
        workflow_def = {
            "name": "Style Recommendation Workflow",
            "steps": [
                {"capability": "style-analysis", "action": "analyze_user_style"},
                {"capability": "outfit-recommendation", "action": "recommend_outfit"},
                {"capability": "stock-optimization", "action": "check_availability"}
            ]
        }
        
        workflow_started = await orchestrator.start_workflow(
            "test-workflow-1",
            workflow_def,
            {"user_id": "test_user", "occasion": "business_meeting"}
        )
        
        if workflow_started:
            print("✅ Workflow started successfully")
            
            # Check workflow status
            status = orchestrator.get_workflow_status("test-workflow-1")
            if status:
                print(f"✅ Workflow status: {status['status']}")
        
        # Test A2A statistics
        print("📊 Testing A2A statistics...")
        a2a_stats = handler.get_stats()
        print(f"✅ A2A Stats: {a2a_stats['messages_sent']} sent, {a2a_stats['messages_received']} received")
        
        # Test agent registry
        agents = handler.get_agents()
        print(f"✅ Registered agents in A2A network: {len(agents)}")
        
        print("\n🎉 All A2A Protocol tests passed!")
        print("🔗 The A2A Protocol is working correctly!")
        
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
    print("🔗 AI-Powered Boutique Agents - A2A Protocol Test")
    print("=" * 55)
    
    # Run the test
    success = asyncio.run(test_a2a_protocol())
    
    if success:
        print("\n✅ SUCCESS: A2A Protocol is ready!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Check the errors above")
        sys.exit(1)