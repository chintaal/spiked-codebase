# 🚀 Launch New EC2 Instance with Key Pair

## Step 1: Terminate Current Instance
1. Go to **EC2 Console** → **Instances**
2. Select your current instance (3.111.218.56)
3. **Instance State** → **Terminate instance**

## Step 2: Launch New Instance with Correct Settings

### Basic Configuration:
- **Name**: `sales-assistant-server`
- **AMI**: Ubuntu Server 22.04 LTS (ami-0dee22c13ea7a9a67 or latest)
- **Instance Type**: `t3.small` (recommended) or `t3.micro` (free tier)

### Key Pair Configuration:
- **Key Pair**: Select `chirag-spiked` (your existing key)
- ⚠️ **IMPORTANT**: Make sure you select your key pair here!

### Security Group Configuration:
Create new security group with these rules:

| Type | Protocol | Port | Source | Description |
|------|----------|------|---------|-------------|
| SSH | TCP | 22 | Your IP | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0 | Web traffic |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Secure web |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 | Backend API |
| Custom TCP | TCP | 5000 | 0.0.0.0/0 | Frontend |
| Custom TCP | TCP | 3000 | 0.0.0.0/0 | Frontend Dev |

### Storage:
- **Size**: 20 GB
- **Type**: gp3 (General Purpose SSD)

## Step 3: Test SSH Connection

After launching, wait 2-3 minutes for initialization, then test:

```bash
# Replace with your new instance IP
ssh -i /Users/chirag/ec2-keys/chirag-spiked.pem ubuntu@NEW_INSTANCE_IP
```

You should see a successful connection!

## Step 4: Deploy Your Application

Once SSH works:

```bash
# Update system
sudo apt update

# Clone your repository
git clone YOUR_GITHUB_REPO_URL
cd YOUR_REPO_NAME

# Run deployment
./deploy_ec2.sh
```

## Alternative: Use Existing Instance with EC2 Instance Connect

If you want to keep the current instance:

1. **EC2 Console** → **Connect** → **EC2 Instance Connect**
2. In browser terminal, run:
   ```bash
   # Generate your public key locally first
   ssh-keygen -y -f /Users/chirag/ec2-keys/chirag-spiked.pem
   
   # Copy the output, then in EC2 Instance Connect:
   echo "PASTE_YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

## Recommendation

**Launch a new instance** - it's cleaner and ensures everything is configured correctly from the start.
