#!/usr/bin/env python3
"""
Simple MCP server test script that doesn't require full installation.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_mcp_server():
    """Test the MCP server functionality."""
    print("🧪 Testing Boutique API MCP Server...")
    
    try:
        # Import our MCP server
        from ai_agents.mcp_servers.boutique_api import BoutiqueAPIMCPServer
        
        # Create and initialize server
        print("📦 Creating MCP server...")
        server = BoutiqueAPIMCPServer()
        
        print("🔧 Initializing server...")
        await server.initialize()
        print("✅ Server initialized successfully!")
        
        # Test getting products
        print("🛍️  Testing get_products...")
        products = await server._get_products({})
        print(f"✅ Found {len(products['products'])} products")
        
        # Test search
        print("🔍 Testing search_products...")
        search_result = await server._search_products({"query": "watch"})
        print(f"✅ Search found {len(search_result['products'])} products")
        
        # Test cart operations
        print("🛒 Testing cart operations...")
        cart = await server._get_cart({"user_id": "test_user"})
        print(f"✅ Cart retrieved with {cart['total_items']} items")
        
        # Test add to cart
        add_result = await server._add_to_cart({
            "user_id": "test_user",
            "product_id": "OLJCESPC7Z",
            "quantity": 2
        })
        print(f"✅ Add to cart: {add_result['success']}")
        
        # Test recommendations
        print("💡 Testing recommendations...")
        recs = await server._get_recommendations({
            "user_id": "test_user", 
            "product_ids": ["OLJCESPC7Z"]
        })
        print(f"✅ Got {len(recs['recommendations'])} recommendations")
        
        # Test currency operations
        print("💱 Testing currency operations...")
        currencies = await server._get_currencies({})
        print(f"✅ Found {len(currencies['currencies'])} currencies")
        
        conversion = await server._convert_currency({
            "from_currency": "USD",
            "to_currency": "EUR", 
            "amount": 100
        })
        print(f"✅ Currency conversion: $100 USD = €{conversion['converted_amount']} EUR")
        
        print("\n🎉 All MCP server tests passed!")
        print("🚀 The Boutique API MCP Server is working correctly!")
        
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
    print("🤖 AI-Powered Boutique Agents - MCP Server Test")
    print("=" * 50)
    
    # Run the test
    success = asyncio.run(test_mcp_server())
    
    if success:
        print("\n✅ SUCCESS: MCP server is ready!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Check the errors above")
        sys.exit(1)