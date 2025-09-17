# Makefile for AI-Powered Boutique Agents

.PHONY: help build up down test logs clean dev mcp-test

# Default target
help:
	@echo "🤖 AI-Powered Boutique Agents - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make build     - Build all Docker images"
	@echo "  make up        - Start all services"
	@echo "  make dev       - Start development server with hot reload"
	@echo "  make mcp       - Start only MCP servers"
	@echo "  make test      - Run tests in Docker"
	@echo "  make mcp-test  - Test MCP server functionality"
	@echo "  make logs      - Show logs from all services"
	@echo "  make down      - Stop all services"
	@echo "  make clean     - Clean up containers and images"
	@echo ""

# Build all images
build:
	@echo "🔨 Building Docker images..."
	docker-compose build

# Start all services
up:
	@echo "🚀 Starting all services..."
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "📊 Boutique API MCP: http://localhost:8080"
	@echo "📈 Analytics MCP: http://localhost:8081"
	@echo "🤖 ML Models MCP: http://localhost:8082"

# Start development server
dev:
	@echo "🛠️  Starting development server..."
	docker-compose up dev-server
	@echo "🔥 Development server with hot reload started!"

# Start only MCP servers
mcp:
	@echo "🔌 Starting MCP servers..."
	docker-compose up -d boutique-api-mcp analytics-mcp ml-models-mcp
	@echo "✅ MCP servers started!"

# Run tests
test:
	@echo "🧪 Running tests..."
	docker-compose --profile testing run --rm test-runner
	@echo "✅ Tests completed!"

# Test MCP server functionality
mcp-test:
	@echo "🔍 Testing MCP server functionality..."
	docker-compose up -d boutique-api-mcp
	@echo "⏳ Waiting for server to start..."
	sleep 10
	@echo "🧪 Running MCP tests..."
	docker-compose exec boutique-api-mcp python -c "\
	import asyncio; \
	from ai_agents.mcp_servers.boutique_api import BoutiqueAPIMCPServer; \
	async def test(): \
		server = BoutiqueAPIMCPServer(); \
		await server.initialize(); \
		products = await server._get_products({}); \
		print(f'✅ Found {len(products[\"products\"])} products'); \
		search = await server._search_products({'query': 'watch'}); \
		print(f'✅ Search found {len(search[\"products\"])} products'); \
		print('🎉 MCP server tests passed!'); \
	asyncio.run(test())"

# Show logs
logs:
	@echo "📋 Showing service logs..."
	docker-compose logs -f

# Stop all services
down:
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped!"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup completed!"

# Quick status check
status:
	@echo "📊 Service Status:"
	docker-compose ps

# Build and start in one command
quick-start: build mcp
	@echo "🚀 Quick start completed!"
	@echo "🔗 Test the MCP server: make mcp-test"