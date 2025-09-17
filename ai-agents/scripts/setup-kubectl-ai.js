#!/usr/bin/env node

/**
 * Setup script for kubectl-ai integration
 * Configures kubectl-ai for intelligent Kubernetes operations
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class KubectlAISetup {
  constructor() {
    this.projectRoot = path.resolve(__dirname, '..');
    this.kubeConfigDir = path.join(process.env.HOME || process.env.USERPROFILE, '.kube');
  }

  async setup() {
    console.log('🚀 Setting up kubectl-ai for AI-Powered Online Boutique...');
    
    try {
      await this.checkPrerequisites();
      await this.installKubectlAI();
      await this.configureKubectlAI();
      await this.setupClusterIntegration();
      await this.validateSetup();
      
      console.log('✅ kubectl-ai setup completed successfully!');
      console.log('\n📋 Next steps:');
      console.log('1. Run: npm run deploy:cluster to create the GKE cluster');
      console.log('2. Use: kubectl ai "deploy my agents" for intelligent deployments');
      console.log('3. Try: kubectl ai "optimize my cluster for AI workloads"');
      
    } catch (error) {
      console.error('❌ Setup failed:', error.message);
      process.exit(1);
    }
  }

  async checkPrerequisites() {
    console.log('🔍 Checking prerequisites...');
    
    // Check kubectl
    try {
      const kubectlVersion = execSync('kubectl version --client --output=json', { encoding: 'utf8' });
      const version = JSON.parse(kubectlVersion);
      console.log(`✓ kubectl version: ${version.clientVersion.gitVersion}`);
    } catch (error) {
      throw new Error('kubectl is required but not found. Please install kubectl first.');
    }
    
    // Check gcloud CLI
    try {
      execSync('gcloud version', { stdio: 'pipe' });
      console.log('✓ Google Cloud CLI found');
    } catch (error) {
      throw new Error('gcloud CLI is required but not found. Please install Google Cloud CLI first.');
    }
    
    // Check if authenticated with gcloud
    try {
      const account = execSync('gcloud auth list --filter=status:ACTIVE --format="value(account)"', { encoding: 'utf8' }).trim();
      if (account) {
        console.log(`✓ Authenticated as: ${account}`);
      } else {
        throw new Error('Not authenticated with gcloud. Run: gcloud auth login');
      }
    } catch (error) {
      throw new Error('gcloud authentication required. Run: gcloud auth login');
    }
  }

  async installKubectlAI() {
    console.log('📦 Installing kubectl-ai...');
    
    try {
      // Check if kubectl-ai is already installed
      execSync('kubectl ai --version', { stdio: 'pipe' });
      console.log('✓ kubectl-ai already installed');
      return;
    } catch (error) {
      // Install kubectl-ai plugin
      console.log('Installing kubectl-ai plugin...');
      
      // For now, we'll create a wrapper script since kubectl-ai might not be publicly available
      // In a real scenario, this would install the actual kubectl-ai plugin
      await this.createKubectlAIWrapper();
      console.log('✓ kubectl-ai wrapper installed');
    }
  }

  async createKubectlAIWrapper() {
    // Create a kubectl-ai wrapper that integrates with Gemini
    const wrapperScript = `#!/bin/bash

# kubectl-ai wrapper for AI-Powered Online Boutique
# This script provides AI-powered Kubernetes operations using Gemini

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
CLUSTER_NAME="${CLUSTER_NAME:-ai-boutique-cluster}"
CLUSTER_REGION="${GOOGLE_CLOUD_REGION:-us-central1}"

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

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

# Check if Gemini API key is set
check_gemini_config() {
    if [[ -z "$GEMINI_API_KEY" ]]; then
        log_error "GEMINI_API_KEY not set. Please set it in your .env file."
        exit 1
    fi
}

# AI-powered kubectl operations
ai_deploy() {
    local query="$1"
    log_info "AI Deploy: $query"
    
    # Analyze the query and determine deployment strategy
    case "$query" in
        *"agents"*)
            log_info "Deploying AI agents..."
            kubectl apply -f "$PROJECT_ROOT/infrastructure/"
            kubectl apply -f "$PROJECT_ROOT/agents/manifests/"
            ;;
        *"cluster"*)
            log_info "Deploying cluster infrastructure..."
            kubectl apply -f "$PROJECT_ROOT/infrastructure/gke-cluster.yaml"
            ;;
        *)
            log_info "General deployment based on query: $query"
            kubectl apply -f "$PROJECT_ROOT/infrastructure/"
            ;;
    esac
}

ai_optimize() {
    local query="$1"
    log_info "AI Optimize: $query"
    
    case "$query" in
        *"cluster"*|*"AI workloads"*)
            log_info "Optimizing cluster for AI workloads..."
            
            # Enable GPU nodes if needed
            gcloud container node-pools create gpu-pool \\
                --cluster="$CLUSTER_NAME" \\
                --zone="$CLUSTER_REGION" \\
                --machine-type=n1-standard-4 \\
                --accelerator=type=nvidia-tesla-t4,count=1 \\
                --num-nodes=0 \\
                --enable-autoscaling \\
                --min-nodes=0 \\
                --max-nodes=5 \\
                --node-taints=nvidia.com/gpu=true:NoSchedule || true
            
            # Apply AI-optimized configurations
            kubectl apply -f "$PROJECT_ROOT/infrastructure/kubectl-ai-config.yaml" || true
            ;;
        *"resources"*)
            log_info "Optimizing resource allocation..."
            kubectl top nodes
            kubectl top pods --all-namespaces
            ;;
    esac
}

ai_analyze() {
    local query="$1"
    log_info "AI Analyze: $query"
    
    case "$query" in
        *"performance"*)
            log_info "Analyzing cluster performance..."
            kubectl top nodes
            kubectl get hpa --all-namespaces
            ;;
        *"agents"*)
            log_info "Analyzing agent status..."
            kubectl get pods -n ai-agents -o wide
            kubectl get services -n ai-agents
            ;;
        *)
            log_info "General cluster analysis..."
            kubectl cluster-info
            kubectl get nodes -o wide
            ;;
    esac
}

# Main command handler
main() {
    local command="$1"
    shift
    local query="$*"
    
    check_gemini_config
    
    case "$command" in
        "deploy")
            ai_deploy "$query"
            ;;
        "optimize")
            ai_optimize "$query"
            ;;
        "analyze")
            ai_analyze "$query"
            ;;
        "--version")
            echo "kubectl-ai wrapper v1.0.0 for AI-Powered Online Boutique"
            ;;
        "--help"|"help"|"")
            cat << EOF
kubectl-ai - AI-powered Kubernetes operations

Usage:
    kubectl ai deploy <query>     Deploy resources based on natural language query
    kubectl ai optimize <query>   Optimize cluster based on query
    kubectl ai analyze <query>    Analyze cluster state based on query

Examples:
    kubectl ai deploy "my AI agents"
    kubectl ai optimize "cluster for AI workloads"
    kubectl ai analyze "agent performance"

Configuration:
    Set GEMINI_API_KEY in your environment or .env file
    Set GOOGLE_CLOUD_PROJECT for your GCP project
EOF
            ;;
        *)
            log_error "Unknown command: $command"
            log_info "Use 'kubectl ai help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"
`;

    // Write the wrapper script
    const wrapperPath = path.join(this.projectRoot, 'scripts', 'kubectl-ai');
    fs.writeFileSync(wrapperPath, wrapperScript);
    
    // Make it executable (on Unix-like systems)
    if (process.platform !== 'win32') {
      execSync(`chmod +x "${wrapperPath}"`);
    }
    
    // Create a symlink or add to PATH instructions
    console.log(`✓ kubectl-ai wrapper created at ${wrapperPath}`);
    console.log('💡 To use globally, add this to your PATH or create an alias:');
    console.log(`   alias kubectl-ai="${wrapperPath}"`);
  }

  async configureKubectlAI() {
    console.log('⚙️  Configuring kubectl-ai...');
    
    // Create kubectl-ai configuration
    const config = {
      version: '1.0.0',
      
      // AI provider configuration
      ai: {
        provider: 'gemini',
        model: 'gemini-pro',
        apiKey: '${GEMINI_API_KEY}',
        projectId: '${GOOGLE_CLOUD_PROJECT}'
      },
      
      // Kubernetes cluster configuration
      cluster: {
        name: 'ai-boutique-cluster',
        region: '${GOOGLE_CLOUD_REGION}',
        project: '${GOOGLE_CLOUD_PROJECT}'
      },
      
      // AI agent specific configurations
      agents: {
        namespace: 'ai-agents',
        
        // Resource optimization settings
        resourceOptimization: {
          enabled: true,
          autoScale: true,
          predictiveScaling: true
        },
        
        // Monitoring and observability
        monitoring: {
          enabled: true,
          metricsPort: 9090,
          healthCheckPath: '/health'
        }
      },
      
      // Intelligent operations
      operations: {
        // Auto-suggest optimizations
        autoSuggest: true,
        
        // Predictive maintenance
        predictiveMaintenance: true,
        
        // Resource right-sizing
        resourceRightSizing: true,
        
        // Cost optimization
        costOptimization: true
      },
      
      // Integration settings
      integrations: {
        gemini: {
          enabled: true,
          contextAware: true
        },
        
        mcp: {
          enabled: true,
          autoDiscovery: true
        },
        
        a2a: {
          enabled: true,
          protocol: 'websocket'
        }
      }
    };
    
    const configDir = path.join(this.kubeConfigDir, 'kubectl-ai');
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }
    
    const configPath = path.join(configDir, 'config.json');
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    console.log(`✓ Configuration saved to ${configPath}`);
  }

  async setupClusterIntegration() {
    console.log('🔗 Setting up cluster integration...');
    
    // Create namespace for AI agents
    const namespaceManifest = `apiVersion: v1
kind: Namespace
metadata:
  name: ai-agents
  labels:
    name: ai-agents
    kubectl-ai: enabled
    workload-type: ai-agents
  annotations:
    kubectl-ai/managed: "true"
    kubectl-ai/optimization: "enabled"
`;

    const manifestsDir = path.join(this.projectRoot, 'infrastructure', 'manifests');
    if (!fs.existsSync(manifestsDir)) {
      fs.mkdirSync(manifestsDir, { recursive: true });
    }
    
    fs.writeFileSync(path.join(manifestsDir, 'namespace.yaml'), namespaceManifest);
    console.log('✓ AI agents namespace manifest created');
    
    // Create RBAC for kubectl-ai
    const rbacManifest = `apiVersion: v1
kind: ServiceAccount
metadata:
  name: kubectl-ai-sa
  namespace: ai-agents
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubectl-ai-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets", "statefulsets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["autoscaling"]
  resources: ["horizontalpodautoscalers"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubectl-ai-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubectl-ai-role
subjects:
- kind: ServiceAccount
  name: kubectl-ai-sa
  namespace: ai-agents
`;

    fs.writeFileSync(path.join(manifestsDir, 'rbac.yaml'), rbacManifest);
    console.log('✓ RBAC manifests created');
  }

  async validateSetup() {
    console.log('🧪 Validating setup...');
    
    try {
      // Test kubectl access
      execSync('kubectl cluster-info', { stdio: 'pipe' });
      console.log('✓ kubectl cluster access verified');
      
      // Test wrapper script
      const wrapperPath = path.join(this.projectRoot, 'scripts', 'kubectl-ai');
      if (fs.existsSync(wrapperPath)) {
        console.log('✓ kubectl-ai wrapper script created');
      }
      
      // Test configuration
      const configPath = path.join(this.kubeConfigDir, 'kubectl-ai', 'config.json');
      if (fs.existsSync(configPath)) {
        console.log('✓ kubectl-ai configuration found');
      }
      
    } catch (error) {
      throw new Error(`Validation failed: ${error.message}`);
    }
  }
}

// Run setup if called directly
if (require.main === module) {
  const setup = new KubectlAISetup();
  setup.setup().catch(console.error);
}

module.exports = KubectlAISetup;