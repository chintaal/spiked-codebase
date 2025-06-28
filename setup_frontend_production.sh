#!/bin/bash

# Frontend Production Setup Script for EC2
set -e

echo "🔧 Setting up frontend for production..."

# Install Node.js adapter for SvelteKit
echo "📦 Installing @sveltejs/adapter-node..."
npm install @sveltejs/adapter-node

# Rebuild with the new adapter
echo "🏗️ Rebuilding frontend with Node.js adapter..."
npm run build

# Install PM2 globally if not already installed
if ! command -v pm2 &> /dev/null; then
    echo "📦 Installing PM2 globally..."
    sudo npm install -g pm2
fi

# Create PM2 ecosystem file for frontend
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'sales-assistant-frontend',
      script: './build/index.js',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
        HOST: '0.0.0.0'
      }
    }
  ]
};
EOF

echo "✅ Frontend setup complete!"
echo "📝 To start the frontend:"
echo "   pm2 start ecosystem.config.js"
echo "📝 To view logs:"
echo "   pm2 logs sales-assistant-frontend"
echo "📝 To restart:"
echo "   pm2 restart sales-assistant-frontend"
