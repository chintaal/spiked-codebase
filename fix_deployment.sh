#!/bin/bash

# Emergency fix script for EC2 deployment
# Run this on your EC2 instance to fix the space issue

set -e

echo "🛠️ Fixing deployment issues..."

# Check disk space
echo "💽 Current disk usage:"
df -h

# Go to the project directory
cd ~/spiked-codebase

# Check if we're in a virtual environment and deactivate
if [[ "$VIRTUAL_ENV" != "" ]]; then
    deactivate
fi

# Remove the problematic venv if it exists
if [ -d "backend/venv" ]; then
    echo "🗑️ Removing problematic virtual environment..."
    rm -rf backend/venv
fi

# Clean up any pip cache
echo "🧹 Cleaning pip cache..."
pip3 cache purge || true

# Remove any temporary files
sudo apt-get clean
sudo apt-get autoremove -y

echo "💽 Disk usage after cleanup:"
df -h

# Create minimal requirements file
echo "📝 Creating minimal requirements.txt..."
cat > backend/requirements_minimal.txt << 'EOF'
# Minimal requirements for Sales Assistant API
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.4.2
python-multipart==0.0.6
openai==1.3.0
httpx==0.25.0
requests==2.31.0
python-dotenv==1.0.0
starlette==0.27.0
websockets==11.0.3
aiofiles==23.2.1
orjson==3.9.7
EOF

# Setup backend with minimal requirements
echo "🐍 Setting up backend with minimal requirements..."
cd backend

# Create new virtual environment
python3 -m venv venv
source venv/bin/activate

# Install minimal requirements
pip install --no-cache-dir -r requirements_minimal.txt

# Setup environment variables
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "🔑 Please enter your OpenAI API Key:"
    read -s -p "OpenAI API Key: " OPENAI_KEY
    echo ""
    sed -i "s/your_openai_api_key_here/$OPENAI_KEY/" .env
fi

cd ..

# Setup frontend
echo "🌐 Setting up frontend..."
cd frontend

# Install Node.js dependencies
npm install --omit=dev

# Setup environment variables for frontend
if [ ! -f .env ]; then
    cp .env.example .env
    # Get the same API key from backend
    OPENAI_KEY=$(grep OPENAI_API_KEY ../backend/.env | cut -d '=' -f2)
    sed -i "s/your_openai_api_key_here/$OPENAI_KEY/" .env
fi

# Build for production
npm run build

cd ..

# Start services with PM2
echo "🚀 Starting services..."

# Kill existing processes
pm2 delete sales-assistant-api 2>/dev/null || true
pm2 delete sales-assistant-frontend 2>/dev/null || true

# Start backend
cd backend
source venv/bin/activate
pm2 start "$(pwd)/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000" --name "sales-assistant-api"
cd ..

# Start frontend
cd frontend
pm2 start "npm run preview -- --host 0.0.0.0 --port 5000" --name "sales-assistant-frontend"
cd ..

# Save PM2 configuration
pm2 save

# Get public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo ""
echo "✅ Deployment fixed and complete!"
echo ""
echo "📱 Access URLs:"
echo "   Frontend:     http://$PUBLIC_IP:5000"
echo "   Backend API:  http://$PUBLIC_IP:8000"
echo "   API Docs:     http://$PUBLIC_IP:8000/docs"
echo ""

# Show running processes
pm2 list

echo ""
echo "💽 Final disk usage:"
df -h
