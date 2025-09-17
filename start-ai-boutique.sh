#!/bin/bash

# AI-Powered Online Boutique Startup Script
# This script starts all AI agents and the Online Boutique services

set -e

echo "🚀 Starting AI-Powered Online Boutique..."
echo "======================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Creating .env file..."
    cat > .env << EOF
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# MCP Server Configuration
MCP_BOUTIQUE_PORT=8080
MCP_ANALYTICS_PORT=8081
MCP_ML_MODELS_PORT=8082

# A2A Protocol Configuration
A2A_WEBSOCKET_PORT=9090

# Frontend Configuration
FRONTEND_PORT=8080

# Development/Production Mode
ENVIRONMENT=development
DEBUG=true
EOF
    echo "📝 Please edit .env file and add your GEMINI_API_KEY"
    echo "   You can get one from: https://makersuite.google.com/app/apikey"
    exit 1
fi

# Source environment variables
source .env

# Check if GEMINI_API_KEY is set
if [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ] || [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ Please set your GEMINI_API_KEY in the .env file"
    echo "   You can get one from: https://makersuite.google.com/app/apikey"
    exit 1
fi

echo "✅ Environment configuration loaded"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

echo "✅ docker-compose is available"

# Build and start services
echo ""
echo "🔨 Building AI agents and services..."
docker-compose -f docker-compose.ai-boutique.yml build

echo ""
echo "🚀 Starting all services..."
docker-compose -f docker-compose.ai-boutique.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check function
check_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Checking $service_name... "
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo "✅ Ready"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ Failed to start"
    return 1
}

# Check core services
echo ""
echo "🏥 Health checking services..."
check_service "Frontend" "http://localhost:8080"
check_service "Boutique API MCP" "http://localhost:8080/health"
check_service "Analytics MCP" "http://localhost:8081/health"
check_service "ML Models MCP" "http://localhost:8082/health"

# Check AI agents
echo ""
echo "🤖 Checking AI agents..."
check_service "Virtual Try-On Agent" "http://localhost:9001/health"
check_service "Dynamic Pricing Agent" "http://localhost:9002/health"
check_service "AI Chatbot Agent" "http://localhost:9003/health"
check_service "Recommendation Agent" "http://localhost:9004/health"

echo ""
echo "🎉 AI-Powered Online Boutique is ready!"
echo "======================================"
echo ""
echo "🌐 Frontend: http://localhost:8080"
echo "🔧 MCP Servers:"
echo "   - Boutique API: http://localhost:8080"
echo "   - Analytics: http://localhost:8081"
echo "   - ML Models: http://localhost:8082"
echo ""
echo "🤖 AI Agents:"
echo "   - Virtual Try-On: http://localhost:9001"
echo "   - Dynamic Pricing: http://localhost:9002"
echo "   - AI Chatbot: http://localhost:9003"
echo "   - Recommendations: http://localhost:9004"
echo "   - Marketing Email: http://localhost:9005"
echo "   - Review Tracker: http://localhost:9006"
echo "   - Personal Stylist: http://localhost:9007"
echo ""
echo "🔌 WebSocket Gateway: ws://localhost:9090"
echo ""
echo "📊 To view logs: docker-compose -f docker-compose.ai-boutique.yml logs -f"
echo "🛑 To stop: docker-compose -f docker-compose.ai-boutique.yml down"
echo ""
echo "🎯 Try the AI features:"
echo "   1. Visit a product page and click 'Try On with AI'"
echo "   2. Use the AI chatbot in the bottom right"
echo "   3. Watch for dynamic pricing updates"
echo "   4. Get personalized recommendations"
echo ""