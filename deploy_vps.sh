#!/bin/bash

# Exit on error
set -e

REPO_URL="https://github.com/Scroatal/discordttbot.git"
INSTALL_DIR="/root/discordttbot"
SERVICE_NAME="discordbot"

echo "Updating system..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

# Check if directory exists
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory exists. Pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Installing requirements..."
source venv/bin/activate
pip install -r requirements.txt

# .env Setup
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Please create the .env file with your DISCORD_BOT_TOKEN."
    read -p "Enter your Discord Bot Token now (or press Enter to skip): " TOKEN
    if [ ! -z "$TOKEN" ]; then
        echo "DISCORD_BOT_TOKEN=$TOKEN" > .env
        echo ".env created."
    else
        echo "Skipping .env creation. Remember to create it manually before starting the service!"
    fi
fi

# Service Setup
echo "Setting up systemd service..."
sudo cp discordbot.service /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

echo "Deployment complete! Status:"
sudo systemctl status $SERVICE_NAME --no-pager
