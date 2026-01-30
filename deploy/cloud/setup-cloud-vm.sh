#!/bin/bash
# Cloud VM Setup Script for AI Employee Platinum Tier
# Target: Oracle Cloud ARM64 Ubuntu 22.04 LTS
# Run as root or with sudo

set -e

echo "============================================"
echo "AI Employee Cloud VM Setup - Platinum Tier"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root or with sudo"
    exit 1
fi

# Update system
log_info "Updating system packages..."
apt-get update && apt-get upgrade -y

# Install essential packages
log_info "Installing essential packages..."
apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    htop \
    jq

# Install Python 3.11+
log_info "Installing Python 3.11..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Verify Python version
python3 --version

# Install pip and pipx
log_info "Installing pip and uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Install Node.js 24+ (LTS)
log_info "Installing Node.js 24 LTS..."
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt-get install -y nodejs

# Verify Node.js version
node --version
npm --version

# Install PM2 globally
log_info "Installing PM2..."
npm install -g pm2

# Install Docker
log_info "Installing Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Install Docker Compose
log_info "Installing Docker Compose..."
apt-get install -y docker-compose-plugin

# Add ubuntu user to docker group
usermod -aG docker ubuntu || true

# Install Nginx
log_info "Installing Nginx..."
apt-get install -y nginx

# Install Certbot for Let's Encrypt
log_info "Installing Certbot..."
apt-get install -y certbot python3-certbot-nginx

# Create AI Employee directories
log_info "Creating AI Employee directories..."
INSTALL_DIR="/home/ubuntu/Digital-Employees"
VAULT_DIR="/home/ubuntu/AI_Employee_Vault"
CONFIG_DIR="/home/ubuntu/.config/ai-employee"
BACKUP_DIR="/backup/odoo"

mkdir -p "$CONFIG_DIR"
mkdir -p "$BACKUP_DIR"

# Set permissions
chown -R ubuntu:ubuntu /home/ubuntu

# Configure firewall (UFW)
log_info "Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw allow 8069/tcp  # Odoo (internal only, proxied through nginx)
ufw --force enable

# Configure sysctl for better performance
log_info "Configuring system parameters..."
cat >> /etc/sysctl.conf << 'EOF'
# AI Employee Optimization
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
vm.swappiness = 10
EOF
sysctl -p

# Create systemd service for PM2
log_info "Setting up PM2 startup..."
env PATH=$PATH:/usr/bin pm2 startup systemd -u ubuntu --hp /home/ubuntu

# Install psutil for health monitoring
log_info "Installing Python dependencies..."
pip3 install psutil pydantic python-dotenv

# Create backup cron job
log_info "Setting up backup cron job..."
cat > /etc/cron.d/ai-employee-backup << 'EOF'
# Daily backup at 3 AM
0 3 * * * root /home/ubuntu/Digital-Employees/deploy/cloud/backup-cron.sh >> /var/log/ai-employee-backup.log 2>&1
EOF

# Create log rotation
log_info "Setting up log rotation..."
cat > /etc/logrotate.d/ai-employee << 'EOF'
/home/ubuntu/Digital-Employees/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
}
EOF

# Final status
log_info "============================================"
log_info "Cloud VM Setup Complete!"
log_info "============================================"
log_info ""
log_info "Installed:"
log_info "  - Python $(python3 --version)"
log_info "  - Node.js $(node --version)"
log_info "  - PM2 $(pm2 --version)"
log_info "  - Docker $(docker --version)"
log_info "  - Nginx $(nginx -v 2>&1)"
log_info ""
log_info "Next steps:"
log_info "  1. Clone repository: git clone <repo> $INSTALL_DIR"
log_info "  2. Clone vault: git clone <vault-repo> $VAULT_DIR"
log_info "  3. Copy .env to $INSTALL_DIR/.env"
log_info "  4. Configure Gmail credentials"
log_info "  5. Start Odoo: cd $INSTALL_DIR/deploy/cloud && docker-compose up -d"
log_info "  6. Configure nginx for your domain"
log_info "  7. Start PM2: pm2 start ecosystem.config.js"
log_info "  8. Save PM2 config: pm2 save"
log_info ""
log_warn "Remember: Never commit secrets to the repository!"
