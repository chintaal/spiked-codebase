#!/bin/bash

# Complete EC2 Production Fix Script
set -e

echo "🚀 Starting complete production deployment fix..."

# Get current directory
DEPLOY_DIR=$(pwd)
echo "📍 Working in: $DEPLOY_DIR"

# Update and clean system
echo "🧹 Cleaning up and updating system..."
sudo apt-get update
sudo apt-get autoremove -y
sudo apt-get autoclean

# Backend Setup
echo "🔧 Setting up backend..."
cd "$DEPLOY_DIR/backend"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating backend .env file..."
    cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
EOF
    echo "⚠️  IMPORTANT: Edit backend/.env and add your actual OpenAI API key!"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r ../requirements_minimal.txt

# Frontend Setup  
echo "🔧 Setting up frontend..."
cd "$DEPLOY_DIR/frontend"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating frontend .env file..."
    cat > .env << 'EOF'
PUBLIC_API_URL=http://localhost:8000
VITE_API_URL=http://localhost:8000
EOF
fi

# Install Node.js adapter
echo "📦 Installing @sveltejs/adapter-node..."
npm install @sveltejs/adapter-node

# Clean and reinstall frontend dependencies
echo "🧹 Cleaning frontend dependencies..."
rm -rf node_modules package-lock.json
npm cache clean --force
npm install

# Build frontend
echo "🏗️ Building frontend..."
npm run build

# Install PM2 globally
echo "📦 Installing PM2..."
sudo npm install -g pm2

# Create PM2 ecosystem file for both services
echo "📝 Creating PM2 ecosystem configuration..."
cd "$DEPLOY_DIR"
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'sales-assistant-backend',
      script: 'uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000',
      cwd: './backend',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/ubuntu/spiked-codebase/backend'
      }
    },
    {
      name: 'sales-assistant-frontend',
      script: './build/index.js',
      cwd: './frontend',
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

# Stop any existing PM2 processes
echo "🛑 Stopping existing PM2 processes..."
pm2 delete all 2>/dev/null || true

# Start services with PM2
echo "🚀 Starting services with PM2..."
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save
pm2 startup

# Show status
echo "📊 Checking service status..."
pm2 status

# Get public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Your services are running at:"
echo "   Backend API:  http://$PUBLIC_IP:8000"
echo "   Frontend App: http://$PUBLIC_IP:3000"
echo ""
echo "📝 Next steps:"
echo "   1. Edit backend/.env and add your OpenAI API key"
echo "   2. Restart backend: pm2 restart sales-assistant-backend"
echo "   3. Test the APIs:"
echo "      curl http://$PUBLIC_IP:8000/health"
echo "      curl http://$PUBLIC_IP:8000/docs"
echo ""
echo "🔧 Useful PM2 commands:"
echo "   pm2 status                    # Check status"
echo "   pm2 logs                      # View all logs"
echo "   pm2 logs sales-assistant-backend   # Backend logs"
echo "   pm2 logs sales-assistant-frontend  # Frontend logs"
echo "   pm2 restart all               # Restart all services"
echo "   pm2 stop all                  # Stop all services"
echo ""
