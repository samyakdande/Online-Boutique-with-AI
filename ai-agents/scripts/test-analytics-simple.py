#!/usr/bin/env python3
"""
Simple Analytics MCP server test script.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_analytics_server():
    """Test the Analytics MCP server functionality."""
    print("📊 Testing Analytics MCP Server...")
    
    try:
        # Import our Analytics MCP server
        from ai_agents.mcp_servers.analytics import AnalyticsMCPServer
        
        # Create and initialize server
        print("📦 Creating Analytics MCP server...")
        server = AnalyticsMCPServer()
        
        print("🔧 Initializing server...")
        await server.initialize()
        print("✅ Server initialized successfully!")
        
        # Test sales analytics
        print("💰 Testing sales analytics...")
        sales_data = await server._get_sales_data({"time_range": "24h"})
        print(f"✅ Sales data: {sales_data['summary']['total_orders']} orders, ${sales_data['summary']['total_sales']:.2f} revenue")
        
        # Test revenue metrics
        print("📈 Testing revenue metrics...")
        revenue = await server._get_revenue_metrics({"time_range": "24h"})
        print(f"✅ Revenue metrics: ${revenue['metrics']['total_revenue']:.2f} total revenue")
        
        # Test user behavior
        print("👥 Testing user behavior analytics...")
        behavior = await server._get_user_behavior({"time_range": "24h", "behavior_type": "browsing"})
        print(f"✅ User behavior: {len(behavior['behavior_data'])} events tracked")
        
        # Test user segments
        print("🎯 Testing user segmentation...")
        segments = await server._get_user_segments({"segment_type": "behavioral"})
        print(f"✅ User segments: {len(segments['segments'])} segments, {segments['total_users']} total users")
        
        # Test inventory analytics
        print("📦 Testing inventory analytics...")
        inventory = await server._get_inventory_analytics({"metric": "turnover"})
        print(f"✅ Inventory analytics: {inventory['analytics']['turnover_rate']:.2f} turnover rate")
        
        # Test real-time metrics
        print("⚡ Testing real-time metrics...")
        realtime = await server._get_real_time_metrics({"metric_type": "traffic"})
        print(f"✅ Real-time metrics: {realtime['data']['current_users']} current users")
        
        # Test trend analysis
        print("📊 Testing trend analysis...")
        trends = await server._get_trend_analysis({"data_type": "sales", "time_range": "7d"})
        print(f"✅ Trend analysis: {trends['trend_analysis']['trend_direction']} trend detected")
        
        # Test performance metrics
        print("⚡ Testing performance metrics...")
        performance = await server._get_performance_metrics({"component": "frontend", "metric": "response_time"})
        print(f"✅ Performance metrics: {performance['performance_data']['current_value']:.1f}{performance['performance_data']['unit']} response time")
        
        print("\n🎉 All Analytics MCP server tests passed!")
        print("📊 The Analytics MCP Server is working correctly!")
        
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
    print("📊 AI-Powered Boutique Agents - Analytics MCP Server Test")
    print("=" * 60)
    
    # Run the test
    success = asyncio.run(test_analytics_server())
    
    if success:
        print("\n✅ SUCCESS: Analytics MCP server is ready!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Check the errors above")
        sys.exit(1)