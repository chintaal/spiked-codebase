# 🚀 Your EC2 Deployment Steps

Follow these exact steps to deploy your Sales Assistant API:

## Step 1: Push Your Code to GitHub

```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit: Sales Assistant API"

# Create repository on GitHub and then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

## Step 2: Prepare Your Key File

```bash
# Set correct permissions on your .pem file
chmod 400 /path/to/your-key.pem
```

## Step 3: Connect to EC2

```bash
# Replace with your actual key path and EC2 IP
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_IPv4_ADDRESS
```

## Step 4: Deploy on EC2

Once connected to your EC2 instance, run these commands:

```bash
# Update system
sudo apt update

# Install git
sudo apt install -y git

# Clone your repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Navigate to your project
cd YOUR_REPO_NAME

# Run the deployment script
./deploy_ec2.sh
```

The deployment script will:
1. ✅ Install Node.js, Python, Nginx, PM2
2. ✅ Set up your backend and frontend
3. ✅ Ask for your OpenAI API key
4. ✅ Start your services
5. ✅ Show you the access URLs

## Step 5: Access Your Application

After deployment completes, you'll see:
- **Frontend**: `http://YOUR_EC2_IP:5000`
- **Backend API**: `http://YOUR_EC2_IP:8000`
- **API Docs**: `http://YOUR_EC2_IP:8000/docs`

## Quick Commands for Management

```bash
# View running services
pm2 list

# View logs
pm2 logs

# Restart services
pm2 restart sales-assistant-api
pm2 restart sales-assistant-frontend

# Check system status
htop
```

## If Something Goes Wrong

```bash
# Check if ports are open
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :5000

# Check service logs
pm2 logs sales-assistant-api --lines 50
pm2 logs sales-assistant-frontend --lines 50

# Restart everything
pm2 restart all
```

---

**Ready to start?** 
1. Make sure your code is pushed to GitHub
2. Have your .pem key and EC2 IP ready
3. Have your OpenAI API key ready
4. Run the commands above!
