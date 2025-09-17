# AI-Powered Online Boutique Enhancement

This project enhances the Google Cloud Online Boutique microservices demo with 13 intelligent AI agents for the GKE Turns 10 Hackathon.

## Architecture Overview

The AI agents are built using:
- **Google Agent Development Kit (ADK)** for agent runtime and lifecycle management
- **Gemini Pro/Vision/Code** for AI capabilities
- **Model Context Protocol (MCP)** for standardized API communication
- **Agent2Agent (A2A) Protocol** for inter-agent communication
- **kubectl-ai** for intelligent Kubernetes operations
- **Gemini CLI** for enhanced development workflows

## Project Structure

```
ai-agents/
├── agents/                 # Individual AI agent implementations
├── infrastructure/         # GKE cluster and infrastructure configuration
├── mcp-servers/           # Model Context Protocol servers
├── shared/                # Shared libraries and utilities
├── tests/                 # Test suites
├── scripts/               # Development and deployment scripts
└── docs/                  # Documentation
```

## Quick Start

1. Set up the development environment:
   ```bash
   ./scripts/setup-dev-env.sh
   ```

2. Deploy the GKE cluster with kubectl-ai:
   ```bash
   ./scripts/deploy-cluster.sh
   ```

3. Deploy the AI agents:
   ```bash
   ./scripts/deploy-agents.sh
   ```

## Development

This project uses hot-reload capabilities for rapid development iteration. See [Development Guide](docs/development.md) for detailed instructions.

## Requirements

- Google Cloud Project with billing enabled
- kubectl-ai installed
- Gemini CLI installed
- Docker and Kubernetes access
- Node.js 18+ for development tools