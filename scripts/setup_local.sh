#!/bin/bash
# Local development setup script

set -e

echo "=================================="
echo "RepeatNoMore Local Development Setup"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo -e "${RED}Error: Python 3.11+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Check for UV
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓ UV found${NC}"
    USE_UV=true
else
    echo -e "${YELLOW}UV not found, using pip${NC}"
    USE_UV=false
fi

# Create virtual environment and install dependencies
if [ "$USE_UV" = true ]; then
    echo ""
    echo "Installing dependencies with UV..."
    uv sync --extra dev
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    # Create virtual environment
    if [ ! -d "venv" ]; then
        echo ""
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip and install
    pip install --upgrade pip setuptools wheel > /dev/null
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

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
if [ "$USE_UV" = true ]; then
    echo "   uv run uvicorn app.main:app --reload --port 8080"
else
    echo "   source venv/bin/activate"
    echo "   uvicorn app.main:app --reload --port 8080"
fi
echo ""
echo "4. Access the API:"
echo "   http://localhost:8080/docs"
echo ""
