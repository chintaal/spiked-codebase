#!/bin/bash

# Quick deployment script for updates
# Run this after making changes to your code

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

REPO_DIR="$(pwd)"

print_status "Updating Sales Assistant API..."

# Pull latest changes
print_status "Pulling latest changes from Git..."
git pull origin main

# Update backend
print_status "Updating backend..."
cd backend
source venv/bin/activate
pip install -r requirements.txt
pm2 restart sales-assistant-api

# Update frontend
print_status "Updating frontend..."
cd ../frontend
npm install
npm run build
pm2 restart sales-assistant-frontend

# Show status
print_status "Current service status:"
pm2 list

print_success "Update complete! Services restarted."

# Get public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo ""
echo "🌐 Your app is running at:"
echo "   Frontend: http://$PUBLIC_IP:5000"
echo "   Backend:  http://$PUBLIC_IP:8000"
