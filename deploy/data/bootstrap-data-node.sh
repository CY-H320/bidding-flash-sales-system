#!/usr/bin/env bash
set -euo pipefail

# Configuration
DATA_ROOT=${DATA_ROOT:-/mnt/bidding-data}  # Use /mnt/bidding-data (EBS mount) by default
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.data.yml}
ENV_FILE=${ENV_FILE:-.env.data}
BIDDING_DATA_DIR="$DATA_ROOT/bidding"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Bidding System Data Node Bootstrap ===${NC}"
echo "Data root: $DATA_ROOT"
echo "Compose file: $COMPOSE_FILE"
echo "Env file: $ENV_FILE"

# Check if EBS volume is mounted
if [ ! -d "$DATA_ROOT" ] || [ ! -w "$DATA_ROOT" ]; then
    echo -e "${RED}✗ Error: $DATA_ROOT does not exist or is not writable${NC}"
    echo -e "${YELLOW}Please mount the EBS volume first:${NC}"
    echo "  sudo mkfs.ext4 /dev/nvme1n1"
    echo "  sudo mkdir -p $DATA_ROOT"
    echo "  sudo mount /dev/nvme1n1 $DATA_ROOT"
    exit 1
fi

echo -e "${GREEN}✓ Data directory is writable${NC}"

# Detect OS and install Docker
echo -e "${YELLOW}Installing Docker and Docker Compose...${NC}"

# Check if Amazon Linux
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" == "amzn" ]]; then
        echo "Detected Amazon Linux"
        sudo yum update -y
        sudo yum install -y docker
        sudo systemctl enable --now docker
        sudo usermod -a -G docker ec2-user
        
        # Install Docker Compose
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    else
        # Ubuntu/Debian
        echo "Detected Debian-based system"
        sudo apt-get update -y
        sudo apt-get install -y docker.io docker-compose-plugin
        sudo systemctl enable --now docker
    fi
else
    echo -e "${RED}✗ Cannot detect OS${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker installed${NC}"

# Create subdirectories for persistent volumes
sudo mkdir -p "$BIDDING_DATA_DIR/postgres"
sudo mkdir -p "$BIDDING_DATA_DIR/redis"
sudo mkdir -p "$BIDDING_DATA_DIR/rabbitmq"
sudo chown -R 999:999 "$BIDDING_DATA_DIR"  # Docker users
echo -e "${GREEN}✓ Created data directories${NC}"

# Copy compose and env files
echo -e "${YELLOW}Copying configuration files...${NC}"
sudo cp "$(dirname "$0")/docker-compose.data.yml" "$DATA_ROOT/$COMPOSE_FILE"
sudo cp "$(dirname "$0")/.env.data" "$DATA_ROOT/$ENV_FILE"

# Update docker-compose to use the new path
# Replace volume paths in compose file
sudo sed -i "s|./postgres|$BIDDING_DATA_DIR/postgres|g" "$DATA_ROOT/$COMPOSE_FILE"
sudo sed -i "s|./redis|$BIDDING_DATA_DIR/redis|g" "$DATA_ROOT/$COMPOSE_FILE"
sudo sed -i "s|./rabbitmq|$BIDDING_DATA_DIR/rabbitmq|g" "$DATA_ROOT/$COMPOSE_FILE"
echo -e "${GREEN}✓ Configuration files copied and paths updated${NC}"

cd "$DATA_ROOT"

# Bring up services (use docker-compose command, not docker compose subcommand)
echo -e "${YELLOW}Starting data services...${NC}"
if command -v docker-compose &> /dev/null; then
    # Standalone docker-compose
    sudo docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
    echo -e "${GREEN}✓ Services started${NC}"
    
    # Show status
    echo -e "${YELLOW}Service status:${NC}"
    sudo docker-compose -f "$COMPOSE_FILE" ps
else
    # Docker Compose plugin
    sudo docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
    echo -e "${GREEN}✓ Services started${NC}"
    
    # Show status
    echo -e "${YELLOW}Service status:${NC}"
    sudo docker compose -f "$COMPOSE_FILE" ps
fi

echo -e "${GREEN}✓ Bootstrap complete!${NC}"
echo -e "${YELLOW}Data directories:${NC}"
echo "  Postgres: $BIDDING_DATA_DIR/postgres"
echo "  Redis:    $BIDDING_DATA_DIR/redis"
echo "  RabbitMQ: $BIDDING_DATA_DIR/rabbitmq"
