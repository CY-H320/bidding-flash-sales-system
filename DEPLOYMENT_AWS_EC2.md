# AWS EC2/ASG Deployment Guide

This guide deploys the bidding system with a dedicated data node (PostgreSQL + Redis + RabbitMQ) and an auto-scaling FastAPI app layer behind an ALB. Frontend static files are served via an Nginx container (or S3/CloudFront if preferred).

## New artifacts in this repo

- backend/Dockerfile – production image for FastAPI
- backend/docker-entrypoint.sh – runs Alembic migrations then starts uvicorn
- backend/.dockerignore – trims Docker context
- frontend/Dockerfile – production build served by Nginx
- frontend/.dockerignore – trims Docker context
- deploy/data/docker-compose.data.yml – data node stack (Postgres, Redis, RabbitMQ)
- deploy/data/.env.data.example – sample secrets for data node
- deploy/data/bootstrap-data-node.sh – installs Docker and starts the data stack
- deploy/app/.env.app.example – app env template pointing to the data node
- deploy/app/run-app.sh – pulls and runs the backend container on an EC2
- deploy/scripts/build_backend_image.sh & build_frontend_image.sh – local builds
- deploy/scripts/push_to_ecr.sh – push both images to AWS ECR

## Architecture

- Data node: 1x EC2 (e.g., t3.medium) running docker compose for Postgres/Redis/RabbitMQ. Persistent EBS volumes hold data. Security Group (SG) only allows traffic from the app SG to 5432, 6379, 5672 (and 15672 if mgmt UI is required from bastion/VPN).
- App layer: FastAPI container (from backend/Dockerfile) on an Auto Scaling Group (ASG) of small instances (e.g., t3.micro). Traffic comes through an ALB → Target Group (port 8000, health check `/health`). ASG scales on CPU > 50% (or custom request count metric).
- Frontend: Nginx container from frontend/Dockerfile served via the same ALB with path-based routing `/` → frontend, `/api` → backend; or upload the `build/` output to S3 + CloudFront.
- Networking: Use private subnets for app and data; ALB in public subnets. Data node gets a private IP/DNS used by app env vars.

## Build images locally

```bash
chmod +x deploy/scripts/*.sh deploy/app/run-app.sh deploy/data/bootstrap-data-node.sh
TAG=v1
./deploy/scripts/build_backend_image.sh   # produces bidding-api:latest
./deploy/scripts/build_frontend_image.sh  # produces bidding-frontend:latest
AWS_ACCOUNT_ID=123456789012 AWS_REGION=ap-northeast-1 TAG=$TAG \
  BACKEND_IMAGE=bidding-api:latest FRONTEND_IMAGE=bidding-frontend:latest \
  ./deploy/scripts/push_to_ecr.sh
```
Create two ECR repos: `bidding-api` and `bidding-frontend`. Images will be pushed as `$TAG`.

## Prepare the data node EC2

1) Launch a Linux EC2 (t3.medium suggested) in a private subnet with an SG that only accepts inbound from the app SG to ports 5432/6379/5672 (15672 optional for RabbitMQ UI). Attach an EBS volume sized for Postgres. SSH or SSM Session Manager access from a bastion is recommended.

   **EBS Volume Setup**:
   - Create a new EBS volume (e.g., 100 GB gp3) in the same AZ as the EC2
   - Attach to the EC2 instance with **Device name: `/dev/sdf`** (or `/dev/sdb`, `/dev/sdc` if `/dev/sdf` is taken)
   - On the EC2, format and mount:
     ```bash
     lsblk  # verify the new volume (usually /dev/nvme1n1 for NVMe)
     sudo mkfs.ext4 /dev/nvme1n1
     sudo mkdir -p /mnt/bidding-data
     sudo mount /dev/nvme1n1 /mnt/bidding-data
     # Make it persistent in /etc/fstab
     echo "/dev/nvme1n1 /mnt/bidding-data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
     sudo chmod 755 /mnt/bidding-data
     ```

2) Upload deployment files to the EC2 instance.

   **From your local machine (Windows PowerShell)**:
   ```powershell
   # Set variables
   $EC2_IP = "13.236.146.36"  # Your EC2 public IP
   $KEY_PATH = "C:\Users\User\Downloads\BiddingFlashSalesKey.pem"
   $LOCAL_DEPLOY_PATH = "c:\Users\User\Documents\GitHub\bidding-flash-sales-system\deploy\data"
   
   # Method 1: Upload entire directory to home (Recommended - simplest)
   scp -i $KEY_PATH -r "$LOCAL_DEPLOY_PATH" ec2-user@${EC2_IP}:~/
   # This creates ~/data/ on the EC2
   
   # Method 2: Upload individual files
   scp -i $KEY_PATH "$LOCAL_DEPLOY_PATH\docker-compose.data.yml" ec2-user@${EC2_IP}:~/
   scp -i $KEY_PATH "$LOCAL_DEPLOY_PATH\.env.data.example" ec2-user@${EC2_IP}:~/
   scp -i $KEY_PATH "$LOCAL_DEPLOY_PATH\bootstrap-data-node.sh" ec2-user@${EC2_IP}:~/
   ```

   **On the EC2 instance (via SSH)**:
   ```bash
   # SSH into the instance
   ssh -i "C:\Users\User\Downloads\BiddingFlashSalesKey.pem" ec2-user@13.236.146.36
   
   # If using Method 1 (uploaded directory):
   cd ~/data
   
   # If using Method 2 (individual files), organize them:
   mkdir -p ~/data
   mv ~/docker-compose.data.yml ~/bootstrap-data-node.sh ~/.env.data.example ~/data/
   cd ~/data
   
   # Configure environment variables
   cp .env.data.example .env.data
   nano .env.data  # or use vi to edit secrets
   ```

   **Edit `.env.data` with strong passwords**:
   ```bash
   POSTGRES_DB=bidding_db
   POSTGRES_USER=bidding_user
   POSTGRES_PASSWORD=<strong-random-password>
   REDIS_PASSWORD=<strong-random-password>
   RABBITMQ_USER=bidding_user
   RABBITMQ_PASSWORD=<strong-random-password>
   ```

3) Run the bootstrap script:

```bash
cd ~/data
chmod +x bootstrap-data-node.sh
sudo ./bootstrap-data-node.sh
```

The script will:
- Install Docker and Docker Compose
- Create data directories in `/mnt/bidding-data/bidding/`
- Start all services (Postgres, Redis, RabbitMQ)

Check service status:
```bash
sudo docker compose -f /mnt/bidding-data/docker-compose.data.yml ps
```

View logs if needed:
```bash
sudo docker compose -f /mnt/bidding-data/docker-compose.data.yml logs -f
```

4) Note the private IP/DNS of this node; use it for `POSTGRES_HOST`, `REDIS_HOST`, and `RABBITMQ_HOST` in the app env file.

## App env file for ASG
Use `deploy/app/.env.app.example` as a template. Set:
- `POSTGRES_HOST/PORT/DB/USER/PASSWORD` → data node private IP and credentials
- `REDIS_HOST/PORT/DB/REDIS_PASSWORD` → data node
- `RABBITMQ_HOST/PORT/RABBITMQ_USER/RABBITMQ_PASSWORD` → data node
- `SECRET_KEY` → strong random 32-byte hex
- `BACKEND_CORS_ORIGINS` → your frontend domain/ALB DNS
Store this in AWS SSM Parameter Store (SecureString) or Secrets Manager, e.g., `/bidding/app_env`.

### Step-by-step: Create and store app environment

1) **Get data node private IP** from the previous section
   ```bash
   # On EC2 console or via AWS CLI
   aws ec2 describe-instances --instance-ids i-xxxxxxxx --query 'Reservations[0].Instances[0].PrivateIpAddress'
   # Or check directly: hostname -I (on data node)
   ```

2) **Create `.env` file locally** with actual values:
   ```bash
   # Generate random SECRET_KEY (32 bytes = 64 hex chars)
   openssl rand -hex 32
   ```

3) **Store in AWS SSM Parameter Store** (recommended for security):
   ```bash
   # On your local machine with AWS CLI
   aws ssm put-parameter \
     --name "/bidding/app_env" \
     --type "SecureString" \
     --value "$(cat deploy/app/.env.app.example | sed \
       -e 's|POSTGRES_HOST=.*|POSTGRES_HOST=10.0.1.10|' \
       -e 's|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=your-strong-password|' \
       -e 's|REDIS_PASSWORD=.*|REDIS_PASSWORD=your-strong-password|' \
       -e 's|RABBITMQ_PASSWORD=.*|RABBITMQ_PASSWORD=your-strong-password|' \
       -e 's|SECRET_KEY=.*|SECRET_KEY=your-generated-32-byte-hex|' \
       -e 's|BACKEND_CORS_ORIGINS=.*|BACKEND_CORS_ORIGINS=["http://your-alb-dns"]|')" \
     --region ap-southeast-2
   ```

## Setup ASG (Application Auto Scaling Group)

### 0) Create IAM Role and SSM Parameter (Prerequisites)

**Create IAM Role for EC2 instances**:
```bash
# Create role
aws iam create-role \
  --role-name bidding-app-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }' \
  --region ap-southeast-2

# Add permissions
aws iam put-role-policy \
  --role-name bidding-app-role \
  --policy-name bidding-app-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "secretsmanager:GetSecretValue"
        ],
        "Resource": "arn:aws:secretsmanager:ap-southeast-2:*:secret:bidding/*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "ecr:GetAuthorizationToken",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:ap-southeast-2:*:log-group:/bidding/*"
      }
    ]
  }' \
  --region ap-southeast-2

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name bidding-app-profile \
  --region ap-southeast-2

aws iam add-role-to-instance-profile \
  --instance-profile-name bidding-app-profile \
  --role-name bidding-app-role \
  --region ap-southeast-2
```

**Create CloudWatch Log Group**:
```bash
aws logs create-log-group \
  --log-group-name /bidding/app \
  --region ap-southeast-2

aws logs put-retention-policy \
  --log-group-name /bidding/app \
  --retention-in-days 7 \
  --region ap-southeast-2
```

**Store app env in AWS Secrets Manager** (from PowerShell):

⚠️ **重要：必須以純文本格式儲存（KEY=VALUE），不是 JSON！**

```powershell
# PowerShell version - IMPORTANT: Store as plain text (KEY=VALUE format), not JSON
$DATA_NODE_IP = "172.31.27.168"  # Replace with actual data node private IP
$ALB_DNS = "BiddingFlashSalesALB-1838681311.ap-southeast-2.elb.amazonaws.com"

# ⚠️ Must be in KEY=VALUE format (plain text), NOT JSON
$env_content = @"
POSTGRES_HOST=$DATA_NODE_IP
POSTGRES_PORT=5432
POSTGRES_DB=bidding_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
REDIS_HOST=$DATA_NODE_IP
REDIS_PORT=6379
REDIS_PASSWORD=
RABBITMQ_HOST=$DATA_NODE_IP
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=admin
SECRET_KEY=a7f3e2b9c1d4e6f8a9b2c3d5e6f7a8b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5
BACKEND_CORS_ORIGINS=["http://$ALB_DNS"]
@"

# Create secret (will overwrite if exists)
aws secretsmanager create-secret `
  --name "bidding/app_env" `
  --description "Application environment variables for bidding system" `
  --secret-string $env_content `
  --region ap-southeast-2

# Or if secret already exists, update it instead
# aws secretsmanager update-secret `
#   --secret-id "bidding/app_env" `
#   --secret-string $env_content `
#   --region ap-southeast-2
```

Verify the secret was created and is in plain text format:
```bash
aws secretsmanager get-secret-value \
  --secret-id "bidding/app_env" \
  --region ap-southeast-2
  
# Should show output like:
# {
#     "ARN": "...",
#     "Name": "bidding/app_env",
#     "VersionId": "...",
#     "SecretString": "POSTGRES_HOST=172.31.27.168\nPOSTGRES_PORT=5432\n..."
# }
```

### 1) Create AMI or use default (Amazon Linux 2)
For this deployment, we'll use Amazon Linux 2 with a Launch Template user data script.

### 2) Create Launch Template
In AWS Console:
- **Name**: `bidding-app-template-v1`
- **AMI**: Amazon Linux 2 (ami-0xxxxx or latest)
- **Instance type**: t3.micro (or t3.small for higher throughput)
- **Key pair**: select your key (BiddingFlashSalesKey.pem)
- **Security group**: `bidding-app-sg` (allow inbound 8000/80 from ALB SG, outbound all to data node SG)
- **IAM instance profile**: `bidding-app-profile` (created in step 0)

**User data script** (select "As text"):
```bash
#!/bin/bash
set -euo pipefail

# Redirect output for debugging
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "$(date): Starting user data script..."

# Update system and install Docker
yum update -y
yum install -y docker aws-cli

# Start Docker
systemctl enable --now docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /opt/bidding
cd /opt/bidding

# Fetch app env from Secrets Manager (with retry logic)
echo "Fetching app env from Secrets Manager..."
for i in {1..5}; do
  if aws secretsmanager get-secret-value \
    --secret-id "bidding/app_env" \
    --query "SecretString" \
    --output text \
    --region ap-southeast-2 > /tmp/secret.txt 2>/dev/null; then
    echo "Successfully fetched app env"
    break
  else
    echo "Attempt $i failed, retrying in 10 seconds..."
    sleep 10
  fi
done

if [ ! -s /tmp/secret.txt ]; then
  echo "ERROR: Failed to fetch secret from Secrets Manager or file is empty"
  exit 1
fi

# Convert from text format (KEY=VALUE lines) to .env format
cat /tmp/secret.txt > .env
rm /tmp/secret.txt

# Login to ECR
echo "Logging into ECR..."
ECR_BASE="701055077457.dkr.ecr.ap-southeast-2.amazonaws.com"
TAG="v1"

if aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin ${ECR_BASE}; then
  echo "Successfully logged into ECR"
else
  echo "ERROR: Failed to login to ECR"
  exit 1
fi

# Pull and run backend container
echo "Starting backend container..."
APP_IMAGE="${ECR_BASE}/bidding-api:${TAG}"

if docker pull "$APP_IMAGE"; then
  docker run -d \
    --name bidding-api \
    --env-file .env \
    -p 8000:8000 \
    --restart unless-stopped \
    --log-driver awslogs \
    --log-opt awslogs-group=/bidding/app \
    --log-opt awslogs-region=ap-southeast-2 \
    --log-opt awslogs-stream=api \
    "$APP_IMAGE"
  echo "Backend container started successfully"
else
  echo "ERROR: Failed to pull backend image"
  exit 1
fi

# Pull and run frontend container
echo "Starting frontend container..."
FRONTEND_IMAGE="${ECR_BASE}/bidding-frontend:${TAG}"

if docker pull "$FRONTEND_IMAGE"; then
  docker run -d \
    --name bidding-frontend \
    -p 80:80 \
    --restart unless-stopped \
    --log-driver awslogs \
    --log-opt awslogs-group=/bidding/app \
    --log-opt awslogs-region=ap-southeast-2 \
    --log-opt awslogs-stream=frontend \
    "$FRONTEND_IMAGE"
  echo "Frontend container started successfully"
else
  echo "ERROR: Failed to pull frontend image"
  exit 1
fi

echo "$(date): User data script completed successfully"
docker ps
```

### 3) Create Auto Scaling Group
In AWS Console:
- **Name**: `bidding-app-asg`
- **Launch template**: `bidding-app-template-v1` (version: latest)
- **VPC**: select your VPC
- **Subnets**: select 2+ private subnets (for HA)
- **Load balancer**: select your existing ALB
- **Target groups**: Create two target groups OR use existing ones:
  - `backend-target-group`: port 8000, HTTP, health check `/health`, interval 30s
  - `frontend-target-group`: port 80, HTTP, health check `/`, interval 30s
- **Health check**: path `/health`, interval 30s, threshold 3 healthy/unhealthy
- **Desired capacity**: 2
- **Min**: 1
- **Max**: 4
- **Scaling policies**:
  - Scale out: CPU > 50% for 5 min → add 1 instance
  - Scale in: CPU < 20% for 10 min → remove 1 instance

After creation, attach both target groups to the ALB listeners with path-based routing rules (see ALB settings section below).

## ALB and Path-based Routing Configuration

### Create Two Target Groups

1. **backend-target-group** (for FastAPI)
   - Protocol: HTTP
   - Port: 8000
   - VPC: your VPC
   - Health check:
     - Protocol: HTTP
     - Path: `/health`
     - Success codes: 200
     - Interval: 30s
     - Healthy threshold: 3
     - Unhealthy threshold: 3

2. **frontend-target-group** (for React/Nginx)
   - Protocol: HTTP
   - Port: 80
   - VPC: your VPC
   - Health check:
     - Protocol: HTTP
     - Path: `/`
     - Success codes: 200
     - Interval: 30s
     - Healthy threshold: 3
     - Unhealthy threshold: 3

### Configure ALB Listeners and Rules

1. **Create ALB Listener (if not exists)**:
   - Protocol: HTTP
   - Port: 80
   - Default action: Forward to backend-target-group (or create new rule)

2. **Add Path-based Routing Rules**:
   - Rule 1:
     - **If** Path is `/api/*` or `/ws/*`
     - **Then** Forward to `backend-target-group`
   
   - Rule 2:
     - **If** Path is `/static/*` or `/assets/*`
     - **Then** Forward to `frontend-target-group`
   
   - Rule 3 (Default):
     - **If** (no match)
     - **Then** Forward to `frontend-target-group`

### ASG and Scaling Configuration
- Desired capacity: 2, Min: 1, Max: 4
- Scaling policy scale-out: CPU > 50% for 5 minutes → add 1 instance
- Scaling policy scale-in: CPU < 20% for 10 minutes → remove 1 instance
- Ensure instances are in private subnets with a NAT gateway for ECR pulls
- Associate ASG with both target groups via the ALB listener rules

## Data node hardening/ops
- Keep the SG restrictive; disable public IP. Use private DNS for host values.
- Schedule backups: `docker exec bidding-postgres pg_dumpall` to S3, and periodic Redis/RabbitMQ snapshots.
- Enable `requirepass` for Redis (already in compose) and strong passwords for Postgres/RabbitMQ.
- Consider migrating to managed services (RDS/ElastiCache) later for HA.

## Observability
- Configure Docker logging driver to CloudWatch (in Launch Template or daemon.json) for both layers.
- Use ALB access logs + CloudWatch metrics (5xx, target response time) as scaling signals.
- Health checks: `/health` for backend; optionally expose `/` from frontend.

## Zero-downtime deploys
1) Build and push images with a new `TAG`.
2) Update Launch Template with the new TAG (or SSM parameter) and roll the ASG (instance refresh).
3) After healthy targets are in service, terminate old instances or let the refresh drain them.

## Running locally with the new images
```bash
TAG=local ./deploy/scripts/build_backend_image.sh
TAG=local ./deploy/scripts/build_frontend_image.sh
POSTGRES_HOST=host.docker.internal REDIS_HOST=host.docker.internal \
  docker run --env-file deploy/app/.env.app.example -p 8000:8000 bidding-api:local
```

## Checklist for the assignment
- App/Data separation with dedicated EC2 data node and SG rules.
- Containers for backend and frontend with production Dockerfiles.
- Data node compose for Postgres/Redis/RabbitMQ.
- Scripts to build/push images and to start containers on EC2/ASG.
- Detailed AWS deployment steps (data node, ASG, ALB, env management, scaling, observability).
