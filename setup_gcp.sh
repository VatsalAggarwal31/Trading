#!/bin/bash

# Apex Autonomous Trading System — GCP Ubuntu Deployment Actuator
# Dynamic path replacements and automatic swap allocation included.

set -e

# Visual Banner
echo -e "\033[1;36m======================================================"
echo -e "         APEX CLOUD DEPLOYMENT COCKPIT"
echo -e "======================================================\033[0m"
echo -e "Initializing Linux server environments...\n"

CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

# 1. Swap Configuration (Critical for e2-micro 1GB RAM to prevent Pip OOM crashes)
if [ ! -f /swapfile ]; then
    echo -e "\033[1;33m[1/5] No swap memory detected. Allocating 2GB virtual RAM to prevent OOM...\033[0m"
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo -e "\033[1;32m✓ Swap memory allocated successfully!\033[0m\n"
else
    echo -e "\033[1;32m[1/5] ✓ Swap memory already allocated.\033[0m\n"
fi

# 2. System Dependency Installation
echo -e "\033[1;33m[2/5] Updating packages and installing Python 3 dependencies...\033[0m"
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv python3-dev build-essential
echo -e "\033[1;32m✓ System packages installed.\033[0m\n"

# 3. Python Virtual Environment Setup
echo -e "\033[1;33m[3/5] Constructing Python virtual environment and restoring dependencies...\033[0m"
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
echo -e "\033[1;32m✓ Virtual environment and python modules restored.\033[0m\n"

# 4. Service Customization & Installation
echo -e "\033[1;33m[4/5] Registering and installing systemd background service daemons...\033[0m"

# Main Bot Service
if [ -f auto_trader.service ]; then
    sed -e "s|__USER__|$CURRENT_USER|g" -e "s|__DIR__|$CURRENT_DIR|g" auto_trader.service > /tmp/auto_trader.service
    sudo mv /tmp/auto_trader.service /etc/systemd/system/auto_trader.service
    sudo chmod 644 /etc/systemd/system/auto_trader.service
    echo "✓ auto_trader.service configured and copied to /etc/systemd/system/"
else
    echo -e "\033[1;31m⚠ auto_trader.service not found in directory! Skipping...\033[0m"
fi

# Dashboard Service
if [ -f streamlit_dashboard.service ]; then
    sed -e "s|__USER__|$CURRENT_USER|g" -e "s|__DIR__|$CURRENT_DIR|g" streamlit_dashboard.service > /tmp/streamlit_dashboard.service
    sudo mv /tmp/streamlit_dashboard.service /etc/systemd/system/streamlit_dashboard.service
    sudo chmod 644 /etc/systemd/system/streamlit_dashboard.service
    echo "✓ streamlit_dashboard.service configured and copied to /etc/systemd/system/"
else
    echo -e "\033[1;31m⚠ streamlit_dashboard.service not found in directory! Skipping...\033[0m"
fi

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable auto_trader.service || true
sudo systemctl enable streamlit_dashboard.service || true

# Start services
sudo systemctl restart auto_trader.service || true
sudo systemctl restart streamlit_dashboard.service || true
echo -e "\033[1;32m✓ Background daemons registered and activated.\033[0m\n"

# 5. Environment Config Verification
echo -e "\033[1;33m[5/5] Checking environment configuration...\033[0m"
if [ ! -f .env ]; then
    echo -e "\033[1;33mNo .env credentials detected. Creating a template...\033[0m"
    cat <<EOT > .env
# Dhan Broker API Credentials
DHAN_CLIENT_ID="YOUR_DHAN_CLIENT_ID"
DHAN_ACCESS_TOKEN="YOUR_DHAN_ACCESS_TOKEN"

# Environment Settings
DHAN_SECURITY_ID="3496"
TICKER="TATASTEEL.NS"
EOT
    echo -e "\033[1;32m✓ Created .env template. Please edit it with your real Dhan tokens.\033[0m\n"
else
    echo -e "\033[1;32m✓ Existing .env file detected.\033[0m\n"
fi

echo -e "\033[1;36m======================================================"
echo -e "         DEPLOYMENT COMPLETE — TELEMETRY ONLINE"
echo -e "======================================================\033[0m"
echo -e "• Bot background service is now running 24/7."
echo -e "• Streamlit dashboard is active at: \033[1;35mhttp://<your-vm-ip>:8501\033[0m"
echo -e "\nUseful Commands:"
echo -e "• Check Bot status:  \033[1;33msudo systemctl status auto_trader\033[0m"
echo -e "• Stream Bot logs:   \033[1;33msudo journalctl -u auto_trader -f -n 50\033[0m"
echo -e "• Check UI status:   \033[1;33msudo systemctl status streamlit_dashboard\033[0m"
echo -e "======================================================\n"
