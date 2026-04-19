#!/usr/bin/env bash
# First-time setup for ha-cat-alarm on a Raspberry Pi 4B.
# Run this script after cloning the repository.

set -euo pipefail

# Colour helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Verify running on Linux
[[ "$(uname -s)" == "Linux" ]] || error "This script is for Linux only (Raspberry Pi OS or Ubuntu Server)."

# Install Docker if missing
if ! command -v docker &>/dev/null; then
    info "Docker not found. Installing via convenience script..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    warn "Docker installed. You may need to log out and back in for group membership to take effect."
fi

# Verify Docker Compose v2
if ! docker compose version &>/dev/null; then
    error "Docker Compose v2 plugin not found. Install it via Docker Desktop or the compose plugin."
fi

info "Docker version: $(docker --version)"
info "Docker Compose version: $(docker compose version)"

# Create .env from example
if [[ ! -f .env ]]; then
    info "Creating .env from .env.example..."
    cp .env.example .env
    warn "Edit .env and set HA_TOKEN before starting."
else
    info ".env already exists. Skipping."
fi

# Create Home Assistant secrets.yaml
if [[ ! -f homeassistant/secrets.yaml ]]; then
    info "Creating homeassistant/secrets.yaml from example..."
    cp homeassistant/secrets.yaml.example homeassistant/secrets.yaml
    warn "Edit homeassistant/secrets.yaml with your home coordinates."
else
    info "homeassistant/secrets.yaml already exists. Skipping."
fi

# Create AppDaemon secrets.yaml
if [[ ! -f appdaemon/secrets.yaml ]]; then
    info "Creating appdaemon/secrets.yaml from example..."
    cp appdaemon/secrets.yaml.example appdaemon/secrets.yaml
else
    info "appdaemon/secrets.yaml already exists. Skipping."
fi

# Create AppDaemon logs directory
mkdir -p appdaemon/logs
info "Ensured appdaemon/logs/ directory exists."

# Pull Docker images
info "Pulling Docker images (this may take a few minutes)..."
docker compose pull

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env and set HA_TOKEN, TZ, and HA_URL:"
echo "   nano .env"
echo ""
echo "2. Edit homeassistant/secrets.yaml and set Telegram credentials:"
echo "   nano homeassistant/secrets.yaml"
echo ""
echo "3. Start Home Assistant first:"
echo "   docker compose up homeassistant -d"
echo ""
echo "4. Open Home Assistant at http://RASPBERRY_PI_IP:8123"
echo "   Complete onboarding, then add integrations:"
echo "   - TP-Link Tapo (Settings > Devices & Services > Add Integration)"
echo "   - Alexa Devices (Settings > Devices & Services > Add Integration)"
echo "   See README for full setup instructions."
echo ""
echo "5. Create a long-lived access token in Home Assistant:"
echo "   Profile > Security > Long-Lived Access Tokens > Create Token"
echo "   Paste it into .env as HA_TOKEN=<token>"
echo ""
echo "6. Find your entity IDs in Home Assistant:"
echo "   Developer Tools > States"
echo "   Update appdaemon/secrets.yaml with your entity IDs."
echo ""
echo "7. Start all services:"
echo "   docker compose up -d"
echo ""
echo "8. Monitor logs:"
echo "   docker compose logs -f appdaemon"
echo ""
