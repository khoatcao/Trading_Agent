#!/bin/bash
set -e

###############################################################################
# Trading Bot — Oracle Cloud Ubuntu 22.04 Setup Script
# Run once on a fresh server:  bash setup.sh
###############################################################################

REPO_URL=""          # fill in your git repo URL before running
BOT_DIR="$HOME/trading_agent"
SERVICE_NAME="trading-bot"
VENV="$BOT_DIR/venv"

###############################################################################
# 1. System packages
###############################################################################
echo ""
echo "=== [1/6] Installing system packages ==="
sudo apt update -y && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git curl nano

###############################################################################
# 2. Ollama + model
###############################################################################
echo ""
echo "=== [2/6] Installing Ollama ==="
curl -fsSL https://ollama.com/install.sh | sh

sudo systemctl enable ollama
sudo systemctl start ollama

echo "Pulling qwen2.5:7b model (this may take a few minutes)..."
ollama pull qwen2.5:7b

###############################################################################
# 3. Clone repo
###############################################################################
echo ""
echo "=== [3/6] Cloning repository ==="

if [ -z "$REPO_URL" ]; then
    echo "ERROR: REPO_URL is empty. Edit setup.sh and set your repo URL at the top."
    exit 1
fi

if [ -d "$BOT_DIR" ]; then
    echo "Directory $BOT_DIR already exists — pulling latest changes"
    git -C "$BOT_DIR" pull
else
    git clone "$REPO_URL" "$BOT_DIR"
fi

###############################################################################
# 4. Python environment + dependencies
###############################################################################
echo ""
echo "=== [4/6] Setting up Python environment ==="
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r "$BOT_DIR/requirements.txt"

###############################################################################
# 5. .env file
###############################################################################
echo ""
echo "=== [5/6] Setting up .env ==="

ENV_FILE="$BOT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    echo ".env already exists — skipping. Edit it manually if needed: nano $ENV_FILE"
else
    cat > "$ENV_FILE" <<EOF
EXCHANGE_API_KEY=your_bybit_api_key
EXCHANGE_API_SECRET=your_bybit_api_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
TIMEFRAME=15m
MONITOR_INTERVAL_SECONDS=120
LLM_MODEL=qwen2.5:7b
EOF
    echo ".env created at $ENV_FILE"
    echo "IMPORTANT: Fill in your API keys before starting the bot:"
    echo "  nano $ENV_FILE"
fi

###############################################################################
# 6. systemd service
###############################################################################
echo ""
echo "=== [6/6] Creating systemd service ==="

sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Crypto Trading Bot
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
ExecStart=$VENV/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=$ENV_FILE
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

###############################################################################
# Done
###############################################################################
echo ""
echo "============================================================"
echo "  Setup complete!"
echo "============================================================"
echo ""
echo "  Next steps:"
echo "  1. Fill in your API keys:       nano $ENV_FILE"
echo "  2. Start the bot:               sudo systemctl start $SERVICE_NAME"
echo "  3. Watch live logs:             sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "  Other useful commands:"
echo "  Stop bot:     sudo systemctl stop $SERVICE_NAME"
echo "  Restart bot:  sudo systemctl restart $SERVICE_NAME"
echo "  Bot status:   sudo systemctl status $SERVICE_NAME"
echo "============================================================"
