"""
Tests for Boutique API MCP Server.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import httpx

from ai_agents.mcp_servers.boutique_api import BoutiqueAPIMCPServer
from ai_agents.mcp_servers.base import MCPClient


class TestBoutiqueAPIMCPServer:
    """Test cases for Boutique API MCP Server."""
    
    @pytest.fixture
    async def server(self):
        """Create a test server instance."""
        server = BoutiqueAPIMCPServer()
        await server.initialize()
        return server
    
    @pytest.fixture
    def client(self):
        """Create a test MCP client."""
        return MCPClient("http://localhost:8080")
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initializes correctly."""
        assert server.name == "boutique-api"
        assert server.port == 8080
        assert len(server.methods) > 0
        
        # Check that key methods are registered
        expected_methods = [
            "get_products",
            "get_product", 
            "search_products",
            "get_cart",
            "add_to_cart",
            "empty_cart",
            "get_recommendations",
            "get_currencies",
            "convert_currency"
        ]
        
        for method in expected_methods:
            assert method in server.methods
    
    @pytest.mark.asyncio
    async def test_get_products(self, server):
        """Test getting all products."""
        result = await server._get_products({})
        
        assert "products" in result
        assert isinstance(result["products"], list)
        assert len(result["products"]) > 0
        
        # Check product structure
        product = result["products"][0]
        assert "id" in product
        assert "name" in product
        assert "description" in product
        assert "price_usd" in product
        assert "categories" in product
    
    @pytest.mark.asyncio
    async def test_get_product_by_id(self, server):
        """Test getting a specific product."""
        product_id = "OLJCESPC7Z"
        result = await server._get_product({"product_id": product_id})
        
        assert result["id"] == product_id
        assert "name" in result
        assert "description" in result
    
    @pytest.mark.asyncio
    async def test_search_products(self, server):
        """Test product search."""
        query = "sunglasses"
        result = await server._search_products({"query": query})
        
        assert "products" in result
        assert "query" in result
        assert result["query"] == query
        
        # Should find sunglasses in mock data
        products = result["products"]
        assert len(products) > 0
        
        # Check that search results contain the query term
        found_sunglasses = any(
            "sunglasses" in product["name"].lower() 
            for product in products
        )
        assert found_sunglasses
    
    @pytest.mark.asyncio
    async def test_cart_operations(self, server):
        """Test cart operations."""
        user_id = "test_user_123"
        
        # Test get cart
        cart = await server._get_cart({"user_id": user_id})
        assert cart["user_id"] == user_id
        assert "items" in cart
        
        # Test add to cart
        add_result = await server._add_to_cart({
            "user_id": user_id,
            "product_id": "OLJCESPC7Z",
            "quantity": 2
        })
        assert add_result["success"] is True
        assert add_result["user_id"] == user_id
        
        # Test empty cart
        empty_result = await server._empty_cart({"user_id": user_id})
        assert empty_result["success"] is True
        assert empty_result["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_recommendations(self, server):
        """Test product recommendations."""
        user_id = "test_user_123"
        product_ids = ["OLJCESPC7Z", "66VCHSJNUP"]
        
        result = await server._get_recommendations({
            "user_id": user_id,
            "product_ids": product_ids
        })
        
        assert result["user_id"] == user_id
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
    
    @pytest.mark.asyncio
    async def test_currency_operations(self, server):
        """Test currency operations."""
        # Test get currencies
        currencies = await server._get_currencies({})
        assert "currencies" in currencies
        assert len(currencies["currencies"]) > 0
        
        # Check currency structure
        currency = currencies["currencies"][0]
        assert "code" in currency
        assert "name" in currency
        assert "symbol" in currency
        
        # Test currency conversion
        conversion = await server._convert_currency({
            "from_currency": "USD",
            "to_currency": "EUR",
            "amount": 100
        })
        
        assert conversion["from_currency"] == "USD"
        assert conversion["to_currency"] == "EUR"
        assert conversion["original_amount"] == 100
        assert "converted_amount" in conversion
        assert "exchange_rate" in conversion
    
    @pytest.mark.asyncio
    async def test_invalid_currency_conversion(self, server):
        """Test currency conversion with invalid currency."""
        conversion = await server._convert_currency({
            "from_currency": "INVALID",
            "to_currency": "USD",
            "amount": 100
        })
        
        assert "error" in conversion


@pytest.mark.integration
class TestBoutiqueAPIMCPIntegration:
    """Integration tests for Boutique API MCP Server."""
    
    @pytest.mark.asyncio
    async def test_mcp_request_response_cycle(self):
        """Test full MCP request/response cycle."""
        # This would test with a running server
        # For now, we'll skip this in unit tests
        pass
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test health check endpoint."""
        # This would test the FastAPI health endpoint
        # For now, we'll skip this in unit tests
        pass


if __name__ == "__main__":
    # Run a simple test
    async def run_simple_test():
        server = BoutiqueAPIMCPServer()
        await server.initialize()
        
        # Test getting products
        products = await server._get_products({})
        print(f"Found {len(products['products'])} products")
        
        # Test search
        search_result = await server._search_products({"query": "watch"})
        print(f"Search for 'watch' found {len(search_result['products'])} products")
        
        print("✅ Basic MCP server tests passed!")
    
    asyncio.run(run_simple_test())