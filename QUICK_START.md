# 🚀 Quick Start: Deploy to AWS EC2

Follow these steps to deploy your Sales Assistant API to AWS EC2:

## 1. Launch EC2 Instance

1. **AWS Console**: Go to EC2 → Launch Instance
2. **Settings**:
   - **AMI**: Ubuntu Server 22.04 LTS
   - **Instance Type**: t3.small (recommended) or t3.micro (free tier)
   - **Key Pair**: Create/select your SSH key
   - **Security Group**: Allow ports 22, 80, 443, 3000, 5000, 8000
   - **Storage**: 20 GB

3. **Launch** and note the public IP address

## 2. Connect to Your Instance

```bash
# Replace with your key file and instance IP
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_IP
```

## 3. Deploy Your Application

**One-command deployment:**

```bash
# On your EC2 instance, run:
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/deploy_ec2.sh | bash
```

**Or manually:**

```bash
# Clone this repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# Run deployment script
./deploy_ec2.sh
```

The script will:
- ✅ Install all dependencies (Node.js, Python, Nginx, PM2)
- ✅ Clone your repository
- ✅ Set up backend and frontend
- ✅ Configure environment variables
- ✅ Start services with PM2
- ✅ Display access URLs

## 4. Access Your Application

After deployment completes:

- **Frontend**: `http://YOUR_INSTANCE_IP:5000`
- **Backend API**: `http://YOUR_INSTANCE_IP:8000`
- **API Documentation**: `http://YOUR_INSTANCE_IP:8000/docs`

## 5. Set Up Domain & SSL (Optional)

### Configure Domain
1. Point your domain A record to your EC2 Elastic IP
2. Update Nginx configuration:
   ```bash
   sudo nano /etc/nginx/sites-available/sales-assistant
   # Replace YOUR_DOMAIN_OR_IP with your domain
   ```

### Set Up SSL
```bash
./setup_ssl.sh
```

## 6. Update Your Application

When you make changes to your code:

```bash
# On your EC2 instance
./update_ec2.sh
```

## 7. Manage Services

```bash
# View running services
pm2 list

# View logs
pm2 logs sales-assistant-api
pm2 logs sales-assistant-frontend

# Restart services
pm2 restart sales-assistant-api
pm2 restart sales-assistant-frontend

# Stop services
pm2 stop all

# System monitoring
htop
sudo systemctl status nginx
```

## Troubleshooting

### Common Issues:

1. **Can't access the app**: Check security group rules allow your ports
2. **Services not starting**: Check logs with `pm2 logs`
3. **502 Bad Gateway**: Backend probably not running, restart with `pm2 restart sales-assistant-api`

### Debug Commands:

```bash
# Check if ports are open
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :5000

# Check service status
pm2 status
sudo systemctl status nginx

# View detailed logs
pm2 logs --lines 50
sudo tail -f /var/log/nginx/error.log
```

## Production Recommendations

- **Use Elastic IP** to prevent IP changes
- **Set up CloudWatch** monitoring
- **Configure automated backups**
- **Use Application Load Balancer** for high availability
- **Set up CI/CD pipeline** for automated deployments

## Cost Estimation

- **t3.micro**: Free tier eligible (750 hours/month)
- **t3.small**: ~$15/month
- **Elastic IP**: Free when attached to running instance
- **Domain**: $10-15/year

---

**Need help?** Check the detailed [EC2_DEPLOYMENT_GUIDE.md](EC2_DEPLOYMENT_GUIDE.md) for comprehensive instructions.
