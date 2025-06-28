#!/bin/bash

# Local deployment helper script
# Run this on your local machine before deploying to EC2

echo "🚀 Preparing for EC2 deployment..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit: Sales Assistant API"
fi

echo ""
echo "📋 Before deploying to EC2, make sure you have:"
echo "   ✅ Created an EC2 instance with Ubuntu 22.04"
echo "   ✅ Configured security group with ports: 22, 80, 443, 3000, 5000, 8000"
echo "   ✅ Your .pem key file downloaded"
echo "   ✅ Your EC2 instance IPv4 address"
echo "   ✅ Your OpenAI API key ready"
echo ""

# Get user inputs
read -p "Enter your EC2 IPv4 address: " EC2_IP
read -p "Enter path to your .pem key file: " KEY_PATH

if [ -z "$EC2_IP" ] || [ -z "$KEY_PATH" ]; then
    echo "❌ Both EC2 IP and key path are required!"
    exit 1
fi

# Validate key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo "❌ Key file not found at: $KEY_PATH"
    exit 1
fi

# Set correct permissions on key file
chmod 400 "$KEY_PATH"

echo ""
echo "🔗 Connecting to your EC2 instance..."
echo "   Instance: $EC2_IP"
echo "   Key: $KEY_PATH"
echo ""

# Create a deployment command file
cat > deploy_to_ec2.sh << EOF
#!/bin/bash
# Auto-generated deployment commands

# Connect to EC2 and run deployment
ssh -i "$KEY_PATH" ubuntu@$EC2_IP << 'ENDSSH'
    # Update system
    sudo apt update

    # Install git if not present
    sudo apt install -y git curl

    # Clone repository (you'll need to replace this with your actual repo URL)
    echo "📥 Please run this command on your EC2 instance:"
    echo "git clone YOUR_GITHUB_REPO_URL"
    echo "cd YOUR_REPO_NAME"
    echo "./deploy_ec2.sh"
    
    # Keep session open
    exec bash
ENDSSH
EOF

chmod +x deploy_to_ec2.sh

echo "📱 Next steps:"
echo ""
echo "1. First, push your code to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
echo "   git push -u origin main"
echo ""
echo "2. Then connect to EC2:"
echo "   ssh -i \"$KEY_PATH\" ubuntu@$EC2_IP"
echo ""
echo "3. On EC2, run these commands:"
echo "   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git"
echo "   cd YOUR_REPO_NAME"
echo "   ./deploy_ec2.sh"
echo ""
echo "🔑 Have your OpenAI API key ready when prompted!"
echo ""

# Offer to connect directly
read -p "Would you like to connect to EC2 now? (y/n): " CONNECT_NOW

if [ "$CONNECT_NOW" = "y" ] || [ "$CONNECT_NOW" = "Y" ]; then
    echo "🔗 Connecting to EC2..."
    ssh -i "$KEY_PATH" ubuntu@$EC2_IP
fi
