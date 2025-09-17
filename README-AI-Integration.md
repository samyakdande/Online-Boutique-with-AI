# AI-Powered Online Boutique - Frontend Integration

This document describes the frontend integration for the AI-powered Online Boutique enhancement project.

## 🎯 Overview

The AI-powered Online Boutique integrates 7+ AI agents with the existing Google Cloud Online Boutique demo, providing intelligent shopping features including:

- **Virtual Try-On** with computer vision analysis
- **Dynamic Pricing** with real-time updates
- **AI Chatbot** with voice and text support
- **Personalized Recommendations** using machine learning
- **Style Analysis** with confidence scoring
- **Review Tracking** with sentiment analysis
- **Marketing Email** automation

## 🏗️ Architecture

```
Frontend (Go/HTML) 
    ↓ JavaScript SDK
MCP Servers (Python)
    ↓ A2A Protocol  
AI Agents (Python)
    ↓ Gemini API
Google AI Services
```

## 🚀 Quick Start

### Prerequisites

1. **Docker Desktop** installed and running
2. **Gemini API Key** from [Google AI Studio](https://makersuite.google.com/app/apikey)
3. **Git** for cloning repositories

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd online-boutique-ai
   ```

2. **Start the services:**
   
   **Windows:**
   ```cmd
   start-ai-boutique.bat
   ```
   
   **Linux/Mac:**
   ```bash
   ./start-ai-boutique.sh
   ```

3. **Configure your API key:**
   - Edit the `.env` file created by the startup script
   - Add your Gemini API key: `GEMINI_API_KEY=your_key_here`
   - Restart: `docker-compose -f docker-compose.ai-boutique.yml restart`

4. **Access the application:**
   - Frontend: http://localhost:8080
   - AI features will be automatically available

## 🎨 AI Features

### Virtual Try-On
- **Location:** Product pages
- **Trigger:** "Try On with AI" button
- **Features:**
  - Real-time camera access
  - Body/face analysis using Gemini Vision
  - Fit scoring (1-10 scale)
  - Style recommendations
  - Alternative product suggestions

### Dynamic Pricing
- **Location:** Product pages
- **Features:**
  - Real-time price monitoring
  - Demand-based price adjustments
  - Price trend indicators
  - Instant price update notifications

### AI Chatbot
- **Location:** Bottom-right widget (all pages)
- **Features:**
  - Text and voice input
  - Product recommendations
  - Shopping assistance
  - Context-aware responses
  - Multi-modal interaction

### Personalized Recommendations
- **Location:** Home page, product pages
- **Features:**
  - User behavior analysis
  - Collaborative filtering
  - Content-based recommendations
  - Real-time personalization

## 🔧 Technical Details

### Frontend Integration

The frontend integration consists of three main components:

1. **AI Agents SDK** (`ai-agents-sdk.js`)
   - JavaScript library for communicating with AI agents
   - WebSocket and HTTP client functionality
   - Error handling and retry logic
   - Event management system

2. **AI Features UI** (`ai-features.js`)
   - UI components for AI features
   - Camera access and image processing
   - Real-time updates and notifications
   - Modal dialogs and interactive elements

3. **AI Styles** (`ai-features.css`)
   - Responsive design for AI components
   - Animations and transitions
   - Dark mode support
   - Mobile-friendly layouts

### Communication Flow

```
Frontend JavaScript
    ↓ WebSocket/HTTP
A2A Gateway (Port 9090)
    ↓ HTTP
MCP Servers (Ports 8080-8082)
    ↓ Internal API
AI Agents (Ports 9001-9007)
    ↓ API Calls
Gemini AI Services
```

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 8080 | Main web interface |
| Boutique API MCP | 8080 | Product/cart/order APIs |
| Analytics MCP | 8081 | Analytics and data APIs |
| ML Models MCP | 8082 | AI model interfaces |
| A2A Gateway | 9090 | WebSocket gateway |
| Virtual Try-On | 9001 | Try-on agent |
| Dynamic Pricing | 9002 | Pricing agent |
| AI Chatbot | 9003 | Chat agent |
| Recommendations | 9004 | Recommendation agent |
| Marketing Email | 9005 | Email agent |
| Review Tracker | 9006 | Review agent |
| Personal Stylist | 9007 | Style agent |

## 🧪 Testing

### Manual Testing

1. **Virtual Try-On:**
   - Go to any product page
   - Click "Try On with AI"
   - Allow camera access
   - Click "Capture & Analyze"
   - Verify fit score and recommendations appear

2. **Dynamic Pricing:**
   - Visit product pages
   - Watch for price trend indicators
   - Check for price update notifications

3. **AI Chatbot:**
   - Click the chatbot widget (bottom-right)
   - Send a message like "recommend products"
   - Test voice input (microphone button)
   - Verify responses are contextual

4. **Recommendations:**
   - Browse different products
   - Check home page for personalized suggestions
   - Verify recommendations update based on behavior

### Health Checks

Check service health at:
- http://localhost:8080/health (Frontend)
- http://localhost:8081/health (Analytics MCP)
- http://localhost:8082/health (ML Models MCP)
- Individual agent health endpoints (ports 9001-9007)

### Logs

View logs for debugging:
```bash
# All services
docker-compose -f docker-compose.ai-boutique.yml logs -f

# Specific service
docker-compose -f docker-compose.ai-boutique.yml logs -f virtual-tryon-agent

# Frontend only
docker-compose -f docker-compose.ai-boutique.yml logs -f frontend
```

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting:**
   - Check Docker is running
   - Verify ports are not in use
   - Check `.env` file configuration

2. **AI features not working:**
   - Verify Gemini API key is set correctly
   - Check browser console for JavaScript errors
   - Ensure WebSocket connection is established

3. **Camera not working (Virtual Try-On):**
   - Check browser permissions
   - Ensure HTTPS or localhost access
   - Verify camera is not in use by other apps

4. **Slow responses:**
   - Check internet connection
   - Verify Gemini API quota
   - Monitor service logs for errors

### Debug Mode

Enable debug mode by setting in `.env`:
```
DEBUG=true
ENVIRONMENT=development
```

### Reset Everything

To completely reset:
```bash
docker-compose -f docker-compose.ai-boutique.yml down -v
docker system prune -f
# Then restart with start-ai-boutique script
```

## 📊 Monitoring

### Service Health

The system includes built-in health monitoring:
- Automatic health checks every 30 seconds
- Service status indicators in UI
- Graceful degradation when services are unavailable

### Performance Metrics

Key metrics to monitor:
- Response times (target: <2 seconds)
- WebSocket connection stability
- AI model inference latency
- Error rates and retry attempts

## 🔒 Security

### API Security
- All AI agent communications use internal Docker network
- No direct external access to AI agents
- MCP servers provide controlled API access

### Privacy
- Camera data processed locally when possible
- User data encrypted in transit
- Session data not persisted beyond session

### CORS and CSP
- Proper CORS headers for API access
- Content Security Policy for XSS protection
- Secure WebSocket connections

## 🚀 Deployment

### Development
Use the provided startup scripts for local development.

### Production
For production deployment:
1. Update environment variables for production URLs
2. Configure proper SSL certificates
3. Set up load balancing for AI agents
4. Configure monitoring and alerting
5. Set up proper backup and recovery

### GKE Deployment
The system is designed for Google Kubernetes Engine:
```bash
# Build and push images
docker-compose -f docker-compose.ai-boutique.yml build
docker tag <images> gcr.io/PROJECT_ID/<image>
docker push gcr.io/PROJECT_ID/<image>

# Deploy to GKE
kubectl apply -f kubernetes-manifests/
```

## 📚 API Documentation

### JavaScript SDK

```javascript
// Initialize SDK
const sdk = new AIAgentsSDK({
    mcpServerUrl: 'http://localhost:8080',
    websocketUrl: 'ws://localhost:9090'
});

// Virtual Try-On
const result = await sdk.analyzeUserForTryOn(imageData, productId);

// Dynamic Pricing
await sdk.subscribeToPriceUpdates([productId], (update) => {
    console.log('Price updated:', update);
});

// Chatbot
const response = await sdk.sendChatMessage('Hello!');

// Recommendations
const recs = await sdk.getPersonalizedRecommendations(userId);
```

### WebSocket Events

```javascript
// Listen for real-time events
sdk.on('price_update', (data) => {
    // Handle price changes
});

sdk.on('recommendation_update', (data) => {
    // Handle new recommendations
});

sdk.on('chat_response', (data) => {
    // Handle chat responses
});
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## 🆘 Support

For support and questions:
1. Check the troubleshooting section above
2. Review service logs
3. Check GitHub issues
4. Contact the development team

---

**Happy Shopping with AI! 🛍️🤖**