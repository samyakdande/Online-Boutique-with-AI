#!/bin/bash

# Development Environment Setup Script for AI-Powered Online Boutique (Python)
# This script sets up the complete Python development environment with hot-reload capabilities

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info "🚀 Setting up AI-Powered Online Boutique development environment..."
log_info "Project root: $PROJECT_ROOT"

# Check prerequisites
check_prerequisites() {
    log_info "🔍 Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3.11+ is required but not installed. Please install Python first."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        log_error "Python 3.11+ is required. Found version: $(python3 --version)"
        exit 1
    fi
    log_success "Python version: $(python3 --version)"
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required but not installed."
        exit 1
    fi
    log_success "pip version: $(pip3 --version)"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not found. Some features may be limited."
    else
        log_success "Docker version: $(docker --version)"
    fi
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl not found. Kubernetes features will be limited."
    else
        log_success "kubectl version: $(kubectl version --client --short)"
    fi
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        log_warning "gcloud CLI not found. Google Cloud features will be limited."
    else
        log_success "gcloud version: $(gcloud version --format='value(Google Cloud SDK)')"
    fi
}

# Setup environment files
setup_environment() {
    log_info "⚙️  Setting up environment configuration..."
    
    # Copy .env.example to .env if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        log_success "Created .env file from template"
        log_warning "Please update .env file with your actual configuration values"
    else
        log_info ".env file already exists"
    fi
    
    # Create development-specific environment
    cat > "$PROJECT_ROOT/.env.development" << EOF
# Development Environment Configuration
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Hot reload settings
DEV_HOT_RELOAD_ENABLED=true
DEV_DEBOUNCE_SECONDS=1.0

# Development ports (avoid conflicts)
MCP_BOUTIQUE_API_PORT=8080
MCP_ANALYTICS_PORT=8081
MCP_ML_MODELS_PORT=8082
A2A_PROTOCOL_PORT=9090

# Development cluster (local or dev)
CLUSTER_NAME=ai-boutique-dev-cluster
KUBECTL_AI_ENABLED=true

# Development URLs
BOUTIQUE_FRONTEND_URL=http://localhost:8080
BOUTIQUE_API_GATEWAY=http://localhost:8080

# Security (development only - use secure values in production)
JWT_SECRET=dev-jwt-secret-key-change-in-production
CORS_ORIGIN=http://localhost:3000

# Performance (relaxed for development)
CACHE_TTL=60
MAX_CONCURRENT_REQUESTS=50
REQUEST_TIMEOUT=60000
EOF
    log_success "Created development environment configuration"
}

# Install dependencies
install_dependencies() {
    log_info "📦 Installing Python dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
        log_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install project in development mode
    pip install -e ".[dev,test,docs]"
    log_success "Python dependencies installed"
    
    # Install pre-commit hooks
    pre-commit install
    log_success "Pre-commit hooks installed"
}

# Setup development tools
setup_dev_tools() {
    log_info "🛠️  Setting up development tools..."
    
    # Create development scripts
    mkdir -p "$PROJECT_ROOT/scripts/dev"
    
    # Hot reload watcher script
    cat > "$PROJECT_ROOT/scripts/dev/watch-agents.js" << 'EOF'
#!/usr/bin/env node

const chokidar = require('chokidar');
const { spawn } = require('child_process');
const path = require('path');

const projectRoot = path.resolve(__dirname, '../..');
const agentsPath = path.join(projectRoot, 'agents/src');
const sharedPath = path.join(projectRoot, 'shared/src');

let buildProcess = null;

const rebuild = () => {
  if (buildProcess) {
    buildProcess.kill();
  }
  
  console.log('🔄 Rebuilding agents...');
  buildProcess = spawn('npm', ['run', 'build:agents'], {
    cwd: projectRoot,
    stdio: 'inherit'
  });
  
  buildProcess.on('close', (code) => {
    if (code === 0) {
      console.log('✅ Agents rebuilt successfully');
    } else {
      console.log('❌ Build failed');
    }
  });
};

console.log('👀 Watching for changes in agents and shared code...');
console.log(`Watching: ${agentsPath}`);
console.log(`Watching: ${sharedPath}`);

const watcher = chokidar.watch([agentsPath, sharedPath], {
  ignored: /node_modules|dist|\.test\.|\.spec\./,
  persistent: true
});

watcher.on('change', (path) => {
  console.log(`📝 File changed: ${path}`);
  rebuild();
});

watcher.on('add', (path) => {
  console.log(`➕ File added: ${path}`);
  rebuild();
});

// Initial build
rebuild();

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Stopping watcher...');
  watcher.close();
  if (buildProcess) {
    buildProcess.kill();
  }
  process.exit(0);
});
EOF

    chmod +x "$PROJECT_ROOT/scripts/dev/watch-agents.js"
    log_success "Hot reload watcher created"
    
    # Development server script
    cat > "$PROJECT_ROOT/scripts/dev/start-dev-server.js" << 'EOF'
#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

const projectRoot = path.resolve(__dirname, '../..');

console.log('🚀 Starting AI-Powered Boutique development server...');

// Start multiple processes concurrently
const processes = [
  {
    name: 'Agents Watcher',
    command: 'node',
    args: ['scripts/dev/watch-agents.js'],
    color: '\x1b[36m' // Cyan
  },
  {
    name: 'MCP Servers',
    command: 'npm',
    args: ['run', 'dev:mcp'],
    color: '\x1b[33m' // Yellow
  },
  {
    name: 'Test Watcher',
    command: 'npm',
    args: ['run', 'test:watch'],
    color: '\x1b[35m' // Magenta
  }
];

const runningProcesses = [];

processes.forEach((proc, index) => {
  const child = spawn(proc.command, proc.args, {
    cwd: projectRoot,
    stdio: 'pipe',
    env: { ...process.env, FORCE_COLOR: '1' }
  });
  
  child.stdout.on('data', (data) => {
    process.stdout.write(`${proc.color}[${proc.name}]\x1b[0m ${data}`);
  });
  
  child.stderr.on('data', (data) => {
    process.stderr.write(`${proc.color}[${proc.name}]\x1b[0m ${data}`);
  });
  
  child.on('close', (code) => {
    console.log(`${proc.color}[${proc.name}]\x1b[0m Process exited with code ${code}`);
  });
  
  runningProcesses.push(child);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down development server...');
  runningProcesses.forEach(proc => proc.kill());
  process.exit(0);
});

console.log('✅ Development server started!');
console.log('📝 File changes will trigger automatic rebuilds');
console.log('🧪 Tests will run automatically on changes');
console.log('Press Ctrl+C to stop');
EOF

    chmod +x "$PROJECT_ROOT/scripts/dev/start-dev-server.js"
    log_success "Development server script created"
}

# Setup kubectl-ai and Gemini CLI
setup_ai_tools() {
    log_info "🤖 Setting up AI development tools..."
    
    # Run kubectl-ai setup
    if [ -f "$PROJECT_ROOT/scripts/setup-kubectl-ai.js" ]; then
        node "$PROJECT_ROOT/scripts/setup-kubectl-ai.js"
    else
        log_warning "kubectl-ai setup script not found, skipping..."
    fi
    
    # Run Gemini CLI setup
    if [ -f "$PROJECT_ROOT/scripts/setup-gemini-cli.js" ]; then
        node "$PROJECT_ROOT/scripts/setup-gemini-cli.js"
    else
        log_warning "Gemini CLI setup script not found, skipping..."
    fi
}

# Create development documentation
create_dev_docs() {
    log_info "📚 Creating development documentation..."
    
    mkdir -p "$PROJECT_ROOT/docs"
    
    cat > "$PROJECT_ROOT/docs/development.md" << 'EOF'
# Development Guide

## Quick Start

1. **Setup Environment**
   ```bash
   ./scripts/setup-dev-env.sh
   ```

2. **Start Development Server**
   ```bash
   npm run dev
   # or
   node scripts/dev/start-dev-server.js
   ```

3. **Run Tests**
   ```bash
   npm test              # Run once
   npm run test:watch    # Watch mode
   npm run test:coverage # With coverage
   ```

## Hot Reload Development

The development environment supports hot reload for:
- Agent code changes
- MCP server changes
- Shared library changes
- Configuration changes

Changes are automatically detected and trigger rebuilds.

## Available Scripts

- `npm run dev` - Start full development environment
- `npm run build` - Build all components
- `npm run test` - Run tests
- `npm run lint` - Run linting
- `npm run format` - Format code

## AI Tools Integration

### kubectl-ai
```bash
kubectl ai deploy "my agents"
kubectl ai optimize "cluster for AI workloads"
kubectl ai analyze "performance issues"
```

### Gemini CLI
```bash
gemini chat --context=agent-development
gemini generate agent --template=adk
gemini test agent --integration
```

## Project Structure

```
ai-agents/
├── agents/           # AI agent implementations
├── mcp-servers/      # Model Context Protocol servers
├── shared/           # Shared libraries
├── infrastructure/   # Kubernetes manifests
├── scripts/          # Development and deployment scripts
├── tests/            # Test suites
└── docs/             # Documentation
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `GEMINI_API_KEY` - Your Gemini API key
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `CLUSTER_NAME` - Kubernetes cluster name

## Debugging

### Agent Debugging
- Use `console.log()` or proper logging
- Check agent logs: `kubectl logs -f deployment/agent-name`
- Use VS Code debugger with launch configurations

### MCP Server Debugging
- Enable debug logging: `LOG_LEVEL=debug`
- Test MCP endpoints directly
- Use MCP protocol inspector tools

## Testing Strategy

1. **Unit Tests** - Individual component testing
2. **Integration Tests** - Agent-to-agent communication
3. **E2E Tests** - Full workflow testing
4. **Performance Tests** - Load and stress testing

## Deployment

### Development
```bash
npm run deploy:dev
```

### Production
```bash
npm run deploy:prod
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   - Check if ports 8080-8082, 9090 are available
   - Update port configuration in `.env`

2. **Build Failures**
   - Clear `node_modules` and reinstall
   - Check TypeScript compilation errors

3. **Agent Communication Issues**
   - Verify A2A protocol configuration
   - Check network policies in Kubernetes

### Getting Help

- Check logs: `npm run logs`
- Run diagnostics: `npm run diagnose`
- Review documentation in `/docs`
EOF

    log_success "Development documentation created"
}

# Validate setup
validate_setup() {
    log_info "🧪 Validating development setup..."
    
    cd "$PROJECT_ROOT"
    
    # Check if build works
    if npm run build > /dev/null 2>&1; then
        log_success "Build validation passed"
    else
        log_error "Build validation failed"
        return 1
    fi
    
    # Check if tests can run
    if npm run test -- --run > /dev/null 2>&1; then
        log_success "Test validation passed"
    else
        log_warning "Test validation failed (this might be expected if no tests exist yet)"
    fi
    
    # Check environment files
    if [ -f ".env" ] && [ -f ".env.development" ]; then
        log_success "Environment configuration validated"
    else
        log_error "Environment configuration missing"
        return 1
    fi
    
    log_success "Development environment validation completed"
}

# Main setup function
main() {
    check_prerequisites
    setup_environment
    install_dependencies
    setup_dev_tools
    setup_ai_tools
    create_dev_docs
    validate_setup
    
    log_success "🎉 Development environment setup completed!"
    echo
    log_info "📋 Next steps:"
    echo "  1. Update .env file with your configuration"
    echo "  2. Run: npm run dev"
    echo "  3. Open http://localhost:3000 in your browser"
    echo "  4. Start developing your AI agents!"
    echo
    log_info "📚 Documentation available at: docs/development.md"
    log_info "🤖 Use 'kubectl ai' and 'gemini' commands for AI assistance"
}

# Run main function
main "$@"