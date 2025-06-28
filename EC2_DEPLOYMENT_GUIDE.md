# AWS EC2 Deployment Guide

This guide will help you deploy your Sales Assistant API to AWS EC2 with both frontend and backend.

## Prerequisites

- AWS Account with EC2 access
- Your OpenAI API key
- SSH key pair for EC2 access

## Step 1: Launch EC2 Instance

1. **Go to AWS EC2 Console**
   - Navigate to https://console.aws.amazon.com/ec2/
   - Click "Launch Instance"

2. **Configure Instance**
   - **Name**: `sales-assistant-server`
   - **AMI**: Ubuntu Server 22.04 LTS (Free Tier Eligible)
   - **Instance Type**: `t3.micro` or `t3.small` (recommended for this app)
   - **Key Pair**: Create new or use existing key pair (download .pem file)
   - **Security Group**: Create new with the following rules:
     - SSH (22) - Your IP
     - HTTP (80) - Anywhere (0.0.0.0/0)
     - HTTPS (443) - Anywhere (0.0.0.0/0)
     - Custom TCP (8000) - Anywhere (0.0.0.0/0) [Backend API]
     - Custom TCP (3000) - Anywhere (0.0.0.0/0) [Frontend Dev Server]
     - Custom TCP (5000) - Anywhere (0.0.0.0/0) [Frontend Production]

3. **Storage**: 20 GB gp3 (sufficient for this application)

4. **Launch Instance**

## Step 2: Connect to EC2 Instance

```bash
# Make your key file secure
chmod 400 your-key-name.pem

# Connect to instance (replace with your instance's public IP)
ssh -i your-key-name.pem ubuntu@YOUR_INSTANCE_PUBLIC_IP
```

## Step 3: Server Setup (Run on EC2)

Once connected to your EC2 instance, run these commands:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install Git
sudo apt install -y git

# Install Nginx (for serving frontend)
sudo apt install -y nginx

# Install PM2 for process management
sudo npm install -g pm2

# Install screen for session management
sudo apt install -y screen
```

## Step 4: Clone and Deploy Your Application

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# Set up backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
nano .env  # Add your OpenAI API key

# Go back to project root
cd ..

# Set up frontend
cd frontend
npm install

# Copy environment template and configure
cp .env.example .env
nano .env  # Add your OpenAI API key
```

## Step 5: Configure Environment Variables

### Backend (.env)
```bash
OPENAI_API_KEY=your_actual_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=3072
KNOWLEDGE_DIR=knowledge
MAX_RESPONSE_LENGTH=200
DEFAULT_TONE=professional
```

### Frontend (.env)
```bash
VITE_OPENAI_API_KEY=your_actual_openai_api_key_here
VITE_BEDROCK_API_ENDPOINT=https://enzkxtybrd.execute-api.us-east-1.amazonaws.com/bedrockk
```

## Step 6: Build and Start Services

### Start Backend
```bash
cd backend
source venv/bin/activate

# Start with PM2 for production
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name "sales-assistant-api"

# Or run directly for testing
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Build and Start Frontend
```bash
cd frontend

# For development (with hot reload)
pm2 start "npm run dev -- --host 0.0.0.0 --port 3000" --name "sales-assistant-frontend-dev"

# For production build
npm run build
pm2 start "npm run preview -- --host 0.0.0.0 --port 5000" --name "sales-assistant-frontend"
```

## Step 7: Configure Nginx (Optional - for production)

Create Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/sales-assistant
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    # Frontend
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/sales-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 8: Manage Services

### PM2 Commands
```bash
# View running processes
pm2 list

# View logs
pm2 logs sales-assistant-api
pm2 logs sales-assistant-frontend

# Restart services
pm2 restart sales-assistant-api
pm2 restart sales-assistant-frontend

# Stop services
pm2 stop sales-assistant-api
pm2 stop sales-assistant-frontend

# Save PM2 configuration
pm2 save

# Set up PM2 to start on boot
pm2 startup
sudo env PATH=$PATH:/usr/bin /usr/lib/node_modules/pm2/bin/pm2 startup systemd -u ubuntu --hp /home/ubuntu
```

## Step 9: Access Your Application

- **Frontend**: http://YOUR_INSTANCE_PUBLIC_IP:3000 (dev) or http://YOUR_INSTANCE_PUBLIC_IP:5000 (prod)
- **Backend API**: http://YOUR_INSTANCE_PUBLIC_IP:8000
- **API Documentation**: http://YOUR_INSTANCE_PUBLIC_IP:8000/docs

## Step 10: Set Up Domain (Optional)

1. **Purchase domain** from Route 53 or external provider
2. **Create A record** pointing to your EC2 instance's Elastic IP
3. **Update Nginx** configuration with your domain name
4. **Set up SSL** with Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Security Best Practices

1. **Use Elastic IP** to avoid IP changes on instance restart
2. **Set up CloudWatch** for monitoring
3. **Configure automated backups**
4. **Use IAM roles** instead of hardcoded AWS keys
5. **Enable CloudFlare** for DDoS protection (optional)
6. **Set up log rotation** for application logs

## Troubleshooting

### Common Issues:

1. **Port not accessible**: Check Security Group rules
2. **Service not starting**: Check logs with `pm2 logs`
3. **Environment variables**: Ensure .env files are properly configured
4. **Permission issues**: Check file ownership and permissions

### Debug Commands:
```bash
# Check if services are running
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :3000

# Check system resources
htop
df -h

# Check service status
pm2 status
sudo systemctl status nginx
```

## Scaling Considerations

For production use, consider:
- **Load Balancer** (Application Load Balancer)
- **Auto Scaling Group**
- **RDS** for database (if you add one)
- **S3** for file storage
- **CloudFront** for CDN
- **ECS/EKS** for containerized deployment
