#!/usr/bin/env node

/**
 * Setup script for Gemini CLI integration
 * Configures Gemini CLI for AI-Powered Online Boutique development
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class GeminiCLISetup {
  constructor() {
    this.configDir = path.join(process.env.HOME || process.env.USERPROFILE, '.gemini');
    this.projectRoot = path.resolve(__dirname, '..');
  }

  async setup() {
    console.log('🚀 Setting up Gemini CLI for AI-Powered Online Boutique...');
    
    try {
      await this.checkPrerequisites();
      await this.installGeminiCLI();
      await this.configureGeminiCLI();
      await this.setupProjectIntegration();
      await this.validateSetup();
      
      console.log('✅ Gemini CLI setup completed successfully!');
      console.log('\n📋 Next steps:');
      console.log('1. Set your GEMINI_API_KEY in .env file');
      console.log('2. Run: npm run dev to start development with hot-reload');
      console.log('3. Use: gemini chat to interact with your agents');
      
    } catch (error) {
      console.error('❌ Setup failed:', error.message);
      process.exit(1);
    }
  }

  async checkPrerequisites() {
    console.log('🔍 Checking prerequisites...');
    
    // Check Node.js version
    const nodeVersion = process.version;
    const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
    if (majorVersion < 18) {
      throw new Error(`Node.js 18+ required, found ${nodeVersion}`);
    }
    
    // Check if gcloud CLI is available
    try {
      execSync('gcloud version', { stdio: 'pipe' });
      console.log('✓ Google Cloud CLI found');
    } catch (error) {
      console.warn('⚠️  Google Cloud CLI not found. Some features may be limited.');
    }
    
    // Check if kubectl is available
    try {
      execSync('kubectl version --client', { stdio: 'pipe' });
      console.log('✓ kubectl found');
    } catch (error) {
      console.warn('⚠️  kubectl not found. Kubernetes features will be limited.');
    }
  }

  async installGeminiCLI() {
    console.log('📦 Installing Gemini CLI...');
    
    try {
      // Check if Gemini CLI is already installed
      execSync('gemini --version', { stdio: 'pipe' });
      console.log('✓ Gemini CLI already installed');
      return;
    } catch (error) {
      // Install Gemini CLI
      console.log('Installing Gemini CLI via npm...');
      execSync('npm install -g @google/generative-ai-cli', { stdio: 'inherit' });
      console.log('✓ Gemini CLI installed');
    }
  }

  async configureGeminiCLI() {
    console.log('⚙️  Configuring Gemini CLI...');
    
    // Ensure config directory exists
    if (!fs.existsSync(this.configDir)) {
      fs.mkdirSync(this.configDir, { recursive: true });
    }
    
    // Create Gemini CLI configuration
    const config = {
      apiKey: process.env.GEMINI_API_KEY || '${GEMINI_API_KEY}',
      projectId: process.env.GOOGLE_CLOUD_PROJECT || '${GOOGLE_CLOUD_PROJECT}',
      
      // AI-Powered Boutique specific settings
      project: {
        name: 'ai-powered-boutique-agents',
        type: 'microservices-enhancement',
        framework: 'adk'
      },
      
      // Agent development settings
      development: {
        hotReload: true,
        autoComplete: true,
        contextAware: true,
        
        // Code generation preferences
        codeGeneration: {
          language: 'typescript',
          framework: 'express',
          testFramework: 'vitest',
          linting: 'eslint',
          formatting: 'prettier'
        }
      },
      
      // Integration settings
      integrations: {
        kubernetes: {
          enabled: true,
          namespace: 'ai-agents',
          cluster: 'ai-boutique-cluster'
        },
        
        mcp: {
          enabled: true,
          servers: ['boutique-api', 'analytics', 'ml-models']
        },
        
        a2a: {
          enabled: true,
          protocol: 'websocket',
          port: 9090
        }
      },
      
      // AI model preferences
      models: {
        default: 'gemini-pro',
        code: 'gemini-pro',
        vision: 'gemini-pro-vision',
        
        // Model-specific settings
        settings: {
          temperature: 0.7,
          topP: 0.8,
          topK: 40,
          maxTokens: 2048
        }
      }
    };
    
    const configPath = path.join(this.configDir, 'config.json');
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    console.log(`✓ Configuration saved to ${configPath}`);
  }

  async setupProjectIntegration() {
    console.log('🔗 Setting up project integration...');
    
    // Create .gemini directory in project root
    const projectGeminiDir = path.join(this.projectRoot, '.gemini');
    if (!fs.existsSync(projectGeminiDir)) {
      fs.mkdirSync(projectGeminiDir, { recursive: true });
    }
    
    // Create project-specific Gemini configuration
    const projectConfig = {
      name: 'AI-Powered Online Boutique Enhancement',
      description: 'Intelligent agents for Google Cloud Online Boutique microservices demo',
      
      // Agent definitions for Gemini CLI awareness
      agents: [
        {
          name: 'Personal Stylist Agent',
          description: 'Provides personalized fashion recommendations',
          capabilities: ['style-analysis', 'outfit-recommendation', 'trend-prediction'],
          endpoints: ['/api/style/recommend', '/api/style/analyze']
        },
        {
          name: 'Inventory Optimizer Agent',
          description: 'Optimizes inventory management and demand forecasting',
          capabilities: ['demand-forecasting', 'stock-optimization', 'supplier-management'],
          endpoints: ['/api/inventory/optimize', '/api/inventory/forecast']
        },
        {
          name: 'Customer Insights Agent',
          description: 'Analyzes customer behavior and provides insights',
          capabilities: ['behavior-analysis', 'segmentation', 'churn-prediction'],
          endpoints: ['/api/insights/analyze', '/api/insights/segment']
        }
      ],
      
      // Development workflows
      workflows: {
        'agent-dev': {
          description: 'Develop and test individual agents',
          steps: [
            'Generate agent scaffold',
            'Implement core logic',
            'Add MCP integration',
            'Write tests',
            'Deploy to development cluster'
          ]
        },
        
        'integration-test': {
          description: 'Test agent interactions',
          steps: [
            'Start all agents',
            'Run integration tests',
            'Validate A2A communication',
            'Check MCP protocol compliance'
          ]
        }
      },
      
      // Context for AI assistance
      context: {
        architecture: 'microservices',
        platform: 'kubernetes',
        cloud: 'google-cloud',
        aiFramework: 'adk',
        protocols: ['mcp', 'a2a', 'grpc', 'http']
      }
    };
    
    const projectConfigPath = path.join(projectGeminiDir, 'project.json');
    fs.writeFileSync(projectConfigPath, JSON.stringify(projectConfig, null, 2));
    console.log(`✓ Project configuration saved to ${projectConfigPath}`);
    
    // Create Gemini CLI shortcuts
    const shortcuts = {
      'agent-new': 'gemini generate agent --template=adk --mcp-enabled',
      'agent-test': 'gemini test agent --integration --a2a',
      'deploy-dev': 'gemini deploy --environment=development --cluster=ai-boutique-cluster',
      'chat-agent': 'gemini chat --context=agent-development --project=ai-boutique'
    };
    
    const shortcutsPath = path.join(projectGeminiDir, 'shortcuts.json');
    fs.writeFileSync(shortcutsPath, JSON.stringify(shortcuts, null, 2));
    console.log(`✓ CLI shortcuts saved to ${shortcutsPath}`);
  }

  async validateSetup() {
    console.log('🧪 Validating setup...');
    
    try {
      // Test Gemini CLI
      const version = execSync('gemini --version', { encoding: 'utf8' }).trim();
      console.log(`✓ Gemini CLI version: ${version}`);
      
      // Test configuration
      const configPath = path.join(this.configDir, 'config.json');
      if (fs.existsSync(configPath)) {
        console.log('✓ Gemini CLI configuration found');
      }
      
      // Test project integration
      const projectConfigPath = path.join(this.projectRoot, '.gemini', 'project.json');
      if (fs.existsSync(projectConfigPath)) {
        console.log('✓ Project integration configured');
      }
      
    } catch (error) {
      throw new Error(`Validation failed: ${error.message}`);
    }
  }
}

// Run setup if called directly
if (require.main === module) {
  const setup = new GeminiCLISetup();
  setup.setup().catch(console.error);
}

module.exports = GeminiCLISetup;