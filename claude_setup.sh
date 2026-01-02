#!/bin/bash
set -e

# ============================================================
# Claude Code VM Setup Script
# Usage: ./setup-claude-code.sh <ANTHROPIC_API_KEY>
# ============================================================

API_KEY="${1:-}"

if [ -z "$API_KEY" ]; then
    echo "Usage: $0 <ANTHROPIC_API_KEY>"
    echo "Get your API key from https://console.anthropic.com"
    exit 1
fi

echo "=== Claude Code VM Setup ==="

# ------------------------------------------------------------
# 1. System Dependencies
# ------------------------------------------------------------
echo "[1/5] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    curl \
    git \
    ripgrep \
    build-essential \
    ca-certificates

# ------------------------------------------------------------
# 2. Install Claude Code (Native - recommended)
# ------------------------------------------------------------
echo "[2/5] Installing Claude Code..."
curl -fsSL https://claude.ai/install.sh | bash

# Add to PATH if not already (the installer usually handles this)
if ! command -v claude &> /dev/null; then
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

# Verify installation
claude --version

# ------------------------------------------------------------
# 3. Configure API Key Authentication
# ------------------------------------------------------------
echo "[3/5] Configuring authentication..."

# Set API key in environment (persistent)
echo "export ANTHROPIC_API_KEY=\"$API_KEY\"" >> ~/.bashrc

# Also set for current session
export ANTHROPIC_API_KEY="$API_KEY"

# Create Claude config directory
mkdir -p ~/.claude

# Optional: Disable auto-updates for stability in production
# echo "export DISABLE_AUTOUPDATER=1" >> ~/.bashrc

# ------------------------------------------------------------
# 4. Create Working Directories
# ------------------------------------------------------------
echo "[4/5] Setting up directories..."

# Main workspace for projects
mkdir -p ~/workspaces

# Directory for API service
mkdir -p ~/claude-api-service

# ------------------------------------------------------------
# 5. Verify Setup
# ------------------------------------------------------------
echo "[5/5] Verifying setup..."

# Test that claude works with API key
echo "Testing Claude Code..."
RESULT=$(claude -p "Say 'Claude Code is ready!' and nothing else." 2>&1)

if echo "$RESULT" | grep -q "ready"; then
    echo ""
    echo "============================================"
    echo "✅ Claude Code setup complete!"
    echo "============================================"
    echo ""
    echo "Claude responded: $RESULT"
    echo ""
    echo "Next steps:"
    echo "  1. Source your bashrc: source ~/.bashrc"
    echo "  2. Test: claude -p 'Hello'"
    echo "  3. Set up your FastAPI service in ~/claude-api-service"
    echo ""
else
    echo ""
    echo "⚠️  Setup complete but verification returned unexpected output:"
    echo "$RESULT"
    echo ""
    echo "This might be fine - try running manually:"
    echo "  source ~/.bashrc && claude -p 'Hello'"
fi