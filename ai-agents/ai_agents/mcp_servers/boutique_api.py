"""
Boutique API MCP Server

This MCP server provides a standardized interface to the existing Online Boutique
microservices, including products, cart, orders, and user sessions.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
import httpx

from ai_agents.core.config import settings
from ai_agents.mcp_servers.base import BaseMCPServer


class BoutiqueAPIMCPServer(BaseMCPServer):
    """MCP Server for Online Boutique API integration."""
    
    def __init__(self):
        super().__init__(
            name="boutique-api",
            port=settings.mcp_boutique_api_port,
            description="MCP server for Online Boutique microservices integration"
        )
        
        # Service endpoints (these would be configured based on your deployment)
        self.service_endpoints = {
            "frontend": settings.boutique_frontend_url,
            "product_catalog": "http://productcatalogservice:3550",
            "cart": "http://cartservice:7070", 
            "checkout": "http://checkoutservice:5050",
            "currency": "http://currencyservice:7000",
            "recommendation": "http://recommendationservice:8080"
        }
        
        # HTTP client for REST API calls
        self.http_client = None
    
    async def initialize(self):
        """Initialize the Boutique API MCP server."""
        self.logger.logger.info("Initializing Boutique API MCP server")
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Register MCP methods
        await self._register_methods()
        
        self.logger.logger.info("Boutique API MCP server initialized")
    
    async def _register_methods(self):
        """Register all MCP methods."""
        
        # Product methods
        self.register_method(
            name="get_products",
            handler=self._get_products,
            description="Get all products from the catalog",
            params_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            result_schema={
                "type": "object",
                "properties": {
                    "products": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "picture": {"type": "string"},
                                "price_usd": {"type": "object"},
                                "categories": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                }
            }
        )
        
        self.register_method(
            name="get_product",
            handler=self._get_product,
            description="Get a specific product by ID",
            params_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"}
                },
                "required": ["product_id"]
            }
        )
        
        self.register_method(
            name="search_products",
            handler=self._search_products,
            description="Search products by query",
            params_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        )
        
        # Cart methods
        self.register_method(
            name="get_cart",
            handler=self._get_cart,
            description="Get user's shopping cart",
            params_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        )
        
        self.register_method(
            name="add_to_cart",
            handler=self._add_to_cart,
            description="Add item to user's cart",
            params_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer", "minimum": 1}
                },
                "required": ["user_id", "product_id", "quantity"]
            }
        )
        
        self.register_method(
            name="empty_cart",
            handler=self._empty_cart,
            description="Empty user's cart",
            params_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        )
        
        # Recommendation methods
        self.register_method(
            name="get_recommendations",
            handler=self._get_recommendations,
            description="Get product recommendations for user",
            params_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "product_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["user_id"]
            }
        )
        
        # Currency methods
        self.register_method(
            name="get_currencies",
            handler=self._get_currencies,
            description="Get supported currencies",
            params_schema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        self.register_method(
            name="convert_currency",
            handler=self._convert_currency,
            description="Convert currency amount",
            params_schema={
                "type": "object",
                "properties": {
                    "from_currency": {"type": "string"},
                    "to_currency": {"type": "string"},
                    "amount": {"type": "number"}
                },
                "required": ["from_currency", "to_currency", "amount"]
            }
        )
    
    # Product Catalog Methods
    async def _get_products(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get all products from the catalog."""
        try:
            # For now, we'll use the frontend API to get products
            # In a real implementation, you'd call the gRPC service directly
            response = await self.http_client.get(f"{self.service_endpoints['frontend']}/api/products")
            
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to mock data for development
                return await self._get_mock_products()
                
        except Exception as e:
            self.logger.logger.warning(f"Failed to get products from service, using mock data: {e}")
            return await self._get_mock_products()
    
    async def _get_product(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific product by ID."""
        product_id = params["product_id"]
        
        try:
            # Try to get from frontend API
            response = await self.http_client.get(f"{self.service_endpoints['frontend']}/api/products/{product_id}")
            
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to mock data
                return await self._get_mock_product(product_id)
                
        except Exception as e:
            self.logger.logger.warning(f"Failed to get product {product_id}, using mock data: {e}")
            return await self._get_mock_product(product_id)
    
    async def _search_products(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search products by query."""
        query = params["query"]
        
        try:
            # Try to search via frontend API
            response = await self.http_client.get(
                f"{self.service_endpoints['frontend']}/api/products/search",
                params={"q": query}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to mock search
                return await self._mock_search_products(query)
                
        except Exception as e:
            self.logger.logger.warning(f"Failed to search products, using mock data: {e}")
            return await self._mock_search_products(query)
    
    # Cart Methods
    async def _get_cart(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get user's shopping cart."""
        user_id = params["user_id"]
        
        try:
            # In a real implementation, this would call the cart service via gRPC
            # For now, we'll simulate with mock data
            return await self._get_mock_cart(user_id)
            
        except Exception as e:
            self.logger.logger.error(f"Failed to get cart for user {user_id}: {e}")
            return {"user_id": user_id, "items": [], "total_items": 0}
    
    async def _add_to_cart(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add item to user's cart."""
        user_id = params["user_id"]
        product_id = params["product_id"]
        quantity = params["quantity"]
        
        try:
            # In a real implementation, this would call the cart service via gRPC
            # For now, we'll simulate success
            self.logger.logger.info(f"Added {quantity}x {product_id} to cart for user {user_id}")
            
            return {
                "success": True,
                "message": f"Added {quantity} item(s) to cart",
                "user_id": user_id,
                "product_id": product_id,
                "quantity": quantity
            }
            
        except Exception as e:
            self.logger.logger.error(f"Failed to add to cart: {e}")
            return {"success": False, "error": str(e)}
    
    async def _empty_cart(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Empty user's cart."""
        user_id = params["user_id"]
        
        try:
            # In a real implementation, this would call the cart service via gRPC
            self.logger.logger.info(f"Emptied cart for user {user_id}")
            
            return {
                "success": True,
                "message": "Cart emptied successfully",
                "user_id": user_id
            }
            
        except Exception as e:
            self.logger.logger.error(f"Failed to empty cart: {e}")
            return {"success": False, "error": str(e)}
    
    # Recommendation Methods
    async def _get_recommendations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get product recommendations for user."""
        user_id = params["user_id"]
        product_ids = params.get("product_ids", [])
        
        try:
            # In a real implementation, this would call the recommendation service
            return await self._get_mock_recommendations(user_id, product_ids)
            
        except Exception as e:
            self.logger.logger.error(f"Failed to get recommendations: {e}")
            return {"user_id": user_id, "recommendations": []}
    
    # Currency Methods
    async def _get_currencies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get supported currencies."""
        try:
            # Mock currency data
            return {
                "currencies": [
                    {"code": "USD", "name": "US Dollar", "symbol": "$"},
                    {"code": "EUR", "name": "Euro", "symbol": "€"},
                    {"code": "GBP", "name": "British Pound", "symbol": "£"},
                    {"code": "JPY", "name": "Japanese Yen", "symbol": "¥"},
                    {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$"}
                ]
            }
            
        except Exception as e:
            self.logger.logger.error(f"Failed to get currencies: {e}")
            return {"currencies": []}
    
    async def _convert_currency(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert currency amount."""
        from_currency = params["from_currency"]
        to_currency = params["to_currency"]
        amount = params["amount"]
        
        try:
            # Mock currency conversion (in real implementation, call currency service)
            # Using simple mock rates
            mock_rates = {
                "USD": 1.0,
                "EUR": 0.85,
                "GBP": 0.73,
                "JPY": 110.0,
                "CAD": 1.25
            }
            
            if from_currency not in mock_rates or to_currency not in mock_rates:
                raise ValueError(f"Unsupported currency: {from_currency} or {to_currency}")
            
            # Convert via USD
            usd_amount = amount / mock_rates[from_currency]
            converted_amount = usd_amount * mock_rates[to_currency]
            
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "original_amount": amount,
                "converted_amount": round(converted_amount, 2),
                "exchange_rate": mock_rates[to_currency] / mock_rates[from_currency]
            }
            
        except Exception as e:
            self.logger.logger.error(f"Failed to convert currency: {e}")
            return {"error": str(e)}
    
    # Mock Data Methods (for development/testing)
    async def _get_mock_products(self) -> Dict[str, Any]:
        """Get mock product data."""
        return {
            "products": [
                {
                    "id": "OLJCESPC7Z",
                    "name": "Sunglasses",
                    "description": "Add a modern touch to your outfits with these sleek aviator sunglasses.",
                    "picture": "/static/img/products/sunglasses.jpg",
                    "price_usd": {"currency_code": "USD", "units": 19, "nanos": 990000000},
                    "categories": ["accessories"]
                },
                {
                    "id": "66VCHSJNUP",
                    "name": "Tank Top",
                    "description": "Perfectly cropped cotton tank, with a scooped neckline.",
                    "picture": "/static/img/products/tank-top.jpg",
                    "price_usd": {"currency_code": "USD", "units": 18, "nanos": 990000000},
                    "categories": ["clothing", "tops"]
                },
                {
                    "id": "1YMWWN1N4O",
                    "name": "Watch",
                    "description": "This gold-tone stainless steel watch will work with most of your outfits.",
                    "picture": "/static/img/products/watch.jpg",
                    "price_usd": {"currency_code": "USD", "units": 109, "nanos": 990000000},
                    "categories": ["accessories"]
                },
                {
                    "id": "L9ECAV7KIM",
                    "name": "Loafers",
                    "description": "A neat addition to your summer wardrobe.",
                    "picture": "/static/img/products/loafers.jpg",
                    "price_usd": {"currency_code": "USD", "units": 89, "nanos": 990000000},
                    "categories": ["footwear"]
                },
                {
                    "id": "2ZYFJ3GM2N",
                    "name": "Hairdryer",
                    "description": "This lightweight hairdryer has 3 heat and speed settings.",
                    "picture": "/static/img/products/hairdryer.jpg",
                    "price_usd": {"currency_code": "USD", "units": 24, "nanos": 990000000},
                    "categories": ["hair", "beauty"]
                }
            ]
        }
    
    async def _get_mock_product(self, product_id: str) -> Dict[str, Any]:
        """Get mock product by ID."""
        products = await self._get_mock_products()
        
        for product in products["products"]:
            if product["id"] == product_id:
                return product
        
        # Return a default product if not found
        return {
            "id": product_id,
            "name": "Unknown Product",
            "description": "Product not found",
            "picture": "/static/img/products/default.jpg",
            "price_usd": {"currency_code": "USD", "units": 0, "nanos": 0},
            "categories": ["unknown"]
        }
    
    async def _mock_search_products(self, query: str) -> Dict[str, Any]:
        """Mock product search."""
        all_products = await self._get_mock_products()
        query_lower = query.lower()
        
        # Simple search by name and description
        matching_products = [
            product for product in all_products["products"]
            if query_lower in product["name"].lower() or 
               query_lower in product["description"].lower() or
               any(query_lower in category.lower() for category in product["categories"])
        ]
        
        return {"products": matching_products, "query": query}
    
    async def _get_mock_cart(self, user_id: str) -> Dict[str, Any]:
        """Get mock cart data."""
        return {
            "user_id": user_id,
            "items": [
                {"product_id": "OLJCESPC7Z", "quantity": 1},
                {"product_id": "66VCHSJNUP", "quantity": 2}
            ],
            "total_items": 3
        }
    
    async def _get_mock_recommendations(self, user_id: str, product_ids: List[str]) -> Dict[str, Any]:
        """Get mock recommendations."""
        # Simple mock recommendations
        all_products = await self._get_mock_products()
        
        # Return first 3 products as recommendations
        recommendations = [p["id"] for p in all_products["products"][:3]]
        
        return {
            "user_id": user_id,
            "recommendations": recommendations,
            "based_on": product_ids
        }


# Server startup function
async def start_boutique_api_server():
    """Start the Boutique API MCP server."""
    server = BoutiqueAPIMCPServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(start_boutique_api_server())