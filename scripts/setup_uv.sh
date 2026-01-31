#!/bin/bash
# Setup script using uv (recommended package manager)

set -e

# Change to project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=================================="
echo "RepeatNoMore Setup with UV"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}UV not found. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Source the env to make uv available
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi

    echo -e "${GREEN}✓ UV installed${NC}"
else
    echo -e "${GREEN}✓ UV already installed${NC}"
fi

# Check Python version
echo ""
echo "Checking Python version..."
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo -e "${RED}Error: Python 3.11+ required${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Install dependencies with uv sync
echo ""
echo "Installing dependencies with uv (this is fast!)..."
uv sync --extra dev
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠ Please edit .env and configure your settings${NC}"
else
    echo -e "${YELLOW}.env file already exists${NC}"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p logs data
echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo "=================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start PostgreSQL (with pgvector):"
echo "   docker-compose -f docker-compose.services.yml up -d"
echo ""
echo "2. Edit .env with your API keys (Anthropic or OpenAI)"
echo ""
echo "3. Run the application:"
echo "   uv run uvicorn app.main:app --reload --port 8080"
echo ""
echo "4. Access the API:"
echo "   http://localhost:8080/docs"
echo ""
