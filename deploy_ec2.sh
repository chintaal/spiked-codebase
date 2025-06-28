#!/bin/bash

# EC2 Server Setup Script
# Run this script on your EC2 instance after connecting via SSH

set -e  # Exit on any error

echo "🚀 Starting Sales Assistant API deployment on EC2..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Node.js 18
print_status "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python and pip
print_status "Installing Python..."
sudo apt install -y python3 python3-pip python3-venv

# Install Git
print_status "Installing Git..."
sudo apt install -y git

# Install Nginx
print_status "Installing Nginx..."
sudo apt install -y nginx

# Install PM2
print_status "Installing PM2..."
sudo npm install -g pm2

# Install other utilities
print_status "Installing utilities..."
sudo apt install -y screen htop curl wget unzip

# Create application directory
print_status "Creating application directory..."
mkdir -p ~/apps
cd ~/apps

# Get repository URL from user
echo ""
echo -e "${YELLOW}Please enter your GitHub repository URL:${NC}"
read -p "Repository URL: " REPO_URL

if [ -z "$REPO_URL" ]; then
    print_error "Repository URL is required!"
    exit 1
fi

# Extract repository name
REPO_NAME=$(basename "$REPO_URL" .git)

# Clone repository
print_status "Cloning repository..."
if [ -d "$REPO_NAME" ]; then
    print_warning "Directory $REPO_NAME already exists. Removing..."
    rm -rf "$REPO_NAME"
fi

git clone "$REPO_URL"
cd "$REPO_NAME"

# Setup backend
print_status "Setting up backend..."
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Setup environment variables
print_status "Setting up backend environment variables..."
cp .env.example .env

echo ""
echo -e "${YELLOW}Please enter your OpenAI API Key:${NC}"
read -s -p "OpenAI API Key: " OPENAI_KEY
echo ""

# Update .env file
sed -i "s/your_openai_api_key_here/$OPENAI_KEY/" .env

print_success "Backend setup complete!"

# Go back to project root
cd ..

# Setup frontend
print_status "Setting up frontend..."
cd frontend

# Install Node.js dependencies
npm install

# Setup environment variables
cp .env.example .env
sed -i "s/your_openai_api_key_here/$OPENAI_KEY/" .env

# Build for production
print_status "Building frontend for production..."
npm run build

print_success "Frontend setup complete!"

# Go back to project root
cd ..

# Start backend with PM2
print_status "Starting backend service..."
cd backend
source venv/bin/activate

# Kill existing processes if they exist
pm2 delete sales-assistant-api 2>/dev/null || true

# Start backend
pm2 start "$(pwd)/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000" --name "sales-assistant-api"

cd ..

# Start frontend with PM2
print_status "Starting frontend service..."
cd frontend

# Kill existing processes if they exist
pm2 delete sales-assistant-frontend 2>/dev/null || true

# Start frontend
pm2 start "npm run preview -- --host 0.0.0.0 --port 5000" --name "sales-assistant-frontend"

cd ..

# Save PM2 configuration
pm2 save

# Setup PM2 startup
print_status "Setting up PM2 startup..."
pm2 startup systemd -u ubuntu --hp /home/ubuntu | tail -1 | sudo bash

# Configure firewall (if ufw is enabled)
if sudo ufw status | grep -q "Status: active"; then
    print_status "Configuring firewall..."
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 8000/tcp
    sudo ufw allow 5000/tcp
fi

# Get instance public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

print_success "Deployment complete!"
echo ""
echo "🎉 Your Sales Assistant API is now running!"
echo ""
echo "📱 Access URLs:"
echo "   Frontend:     http://$PUBLIC_IP:5000"
echo "   Backend API:  http://$PUBLIC_IP:8000"
echo "   API Docs:     http://$PUBLIC_IP:8000/docs"
echo ""
echo "🔧 Management Commands:"
echo "   View processes:   pm2 list"
echo "   View logs:        pm2 logs"
echo "   Restart backend:  pm2 restart sales-assistant-api"
echo "   Restart frontend: pm2 restart sales-assistant-frontend"
echo ""
echo "📋 Next Steps:"
echo "   1. Update your domain DNS to point to: $PUBLIC_IP"
echo "   2. Set up SSL certificate with: sudo certbot --nginx"
echo "   3. Configure Nginx reverse proxy (see deployment guide)"
echo ""

# Show running processes
print_status "Current PM2 processes:"
pm2 list
