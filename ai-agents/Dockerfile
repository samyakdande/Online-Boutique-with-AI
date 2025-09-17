# Multi-stage Dockerfile for AI-Powered Boutique Agents
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_TIMEOUT=1000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Install minimal dependencies first to avoid conflicts
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    python-dotenv==1.0.0 \
    rich==13.7.0 \
    typer==0.9.0 \
    httpx==0.25.2

# Copy source code
COPY ai_agents/ ./ai_agents/
COPY pyproject.toml ./

# Development stage
FROM base as development

# Install development dependencies
RUN pip install -e ".[dev,test]"

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Expose ports for development
EXPOSE 8000 8080 8081 8082 9090

# Development command with hot reload
CMD ["python", "-m", "ai_agents.dev.server"]

# Production stage
FROM base as production

# Copy only necessary files
COPY ai_agents/ ./ai_agents/
COPY pyproject.toml ./

# Install production dependencies only
RUN pip install -e .

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Production command
CMD ["python", "-m", "ai_agents.cli", "start", "all"]

# Agent-specific stages
FROM production as personal-stylist-agent
ENV AGENT_TYPE=personal-stylist
CMD ["python", "-m", "ai_agents.agents.personal_stylist"]

FROM production as inventory-optimizer-agent  
ENV AGENT_TYPE=inventory-optimizer
CMD ["python", "-m", "ai_agents.agents.inventory_optimizer"]

FROM production as customer-insights-agent
ENV AGENT_TYPE=customer-insights
CMD ["python", "-m", "ai_agents.agents.customer_insights"]

# MCP Server stages
FROM production as boutique-api-mcp
ENV MCP_SERVER_TYPE=boutique-api
EXPOSE 8080
CMD ["python", "-m", "ai_agents.mcp_servers.boutique_api"]

FROM production as analytics-mcp
ENV MCP_SERVER_TYPE=analytics
EXPOSE 8081
CMD ["python", "-m", "ai_agents.mcp_servers.analytics"]

FROM production as ml-models-mcp
ENV MCP_SERVER_TYPE=ml-models
EXPOSE 8082
CMD ["python", "-m", "ai_agents.mcp_servers.ml_models"]