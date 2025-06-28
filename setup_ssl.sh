#!/bin/bash

# SSL Setup Script for Production
# Run this after your domain is pointing to your EC2 instance

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo ""
echo -e "${YELLOW}🔒 SSL Certificate Setup for Sales Assistant API${NC}"
echo ""

# Get domain name
echo "Please enter your domain name (e.g., myapp.com):"
read -p "Domain: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "Domain is required!"
    exit 1
fi

# Install Certbot
print_status "Installing Certbot..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Update Nginx configuration with domain
print_status "Updating Nginx configuration..."
sudo sed -i "s/YOUR_DOMAIN_OR_IP/$DOMAIN/" /etc/nginx/sites-available/sales-assistant

# Test Nginx configuration
print_status "Testing Nginx configuration..."
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Get SSL certificate
print_status "Obtaining SSL certificate..."
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN"

# Test SSL renewal
print_status "Testing SSL renewal..."
sudo certbot renew --dry-run

# Setup auto-renewal
print_status "Setting up auto-renewal..."
sudo systemctl enable certbot.timer

print_success "SSL setup complete!"
echo ""
echo "🎉 Your site is now available at:"
echo "   https://$DOMAIN"
echo ""
echo "📋 SSL Certificate Info:"
sudo certbot certificates

echo ""
echo "🔄 Auto-renewal is set up. Certificates will renew automatically."
