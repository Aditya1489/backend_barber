#!/bin/bash

# BarberSync Backend Startup Script
# This script starts the FastAPI backend server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$BACKEND_DIR/venv"
HOST="0.0.0.0"
PORT="8000"
UPLOADS_DIR="$BACKEND_DIR/uploads"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   BarberSync Backend Startup${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo -e "${YELLOW}Please install Python 3 and try again${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python 3 found: $(python3 --version)"

# Check if PostgreSQL is running
# MODIFICATION: Skip local check if DATABASE_URL is set (Production mode)
if [ -z "$DATABASE_URL" ]; then
    echo -e "\n${BLUE}Checking LOCAL PostgreSQL connection...${NC}"
    if command -v psql &> /dev/null; then
        if psql -h localhost -U postgres -d barbersync -c "SELECT 1;" &> /dev/null; then
            echo -e "${GREEN}✓${NC} Local PostgreSQL database 'barbersync' is accessible"
        else
            echo -e "${YELLOW}⚠${NC} Warning: Cannot connect to local PostgreSQL database 'barbersync'"
            echo -e "${YELLOW}  Make sure local PostgreSQL is running and the database exists${NC}"
            echo -e "${YELLOW}  Database: barbersync${NC}"
            echo -e "${YELLOW}  User: postgres${NC}"
            echo -e "${YELLOW}  You can create it with: createdb -U postgres barbersync${NC}\n"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Warning: psql command not found. Cannot verify local database connection"
    fi
else
    echo -e "\n${GREEN}✓${NC} Found PRODUCTION DATABASE_URL environment variable"
    echo -e "${GREEN}  Skipping local PostgreSQL check as per configuration priority${NC}"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\n${BLUE}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "\n${GREEN}✓${NC} Virtual environment found"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Install/Update dependencies
echo -e "\n${BLUE}Installing dependencies...${NC}"
pip install --upgrade pip --quiet
pip install -r "$BACKEND_DIR/requirements.txt" --quiet
echo -e "${GREEN}✓${NC} Dependencies installed"

# Create uploads directory if it doesn't exist
if [ ! -d "$UPLOADS_DIR" ]; then
    echo -e "\n${BLUE}Creating uploads directory...${NC}"
    mkdir -p "$UPLOADS_DIR"
    echo -e "${GREEN}✓${NC} Uploads directory created: $UPLOADS_DIR"
else
    echo -e "\n${GREEN}✓${NC} Uploads directory exists: $UPLOADS_DIR"
fi

# Check if .env file exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    if [ -z "$DATABASE_URL" ]; then
        echo -e "\n${YELLOW}⚠${NC} Warning: .env file not found"
        echo -e "${YELLOW}  Using default configuration from config.py${NC}"
    fi
fi

# Start the server
# Run database migrations
echo -e "\n${BLUE}Running database migrations...${NC}"
if [ -f "$BACKEND_DIR/alembic.ini" ]; then
    alembic upgrade head
    echo -e "${GREEN}✓${NC} Migrations applied successfully"
else
    echo -e "${YELLOW}⚠${NC} Warning: alembic.ini not found, skipping migrations"
fi

echo -e "\n${BLUE}======================================${NC}"
echo -e "${GREEN}Starting BarberSync Backend Server...${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Server will be available at:${NC}"
echo -e "  ${BLUE}→${NC} http://localhost:$PORT"
echo -e "  ${BLUE}→${NC} http://127.0.0.1:$PORT"
echo -e "  ${BLUE}→${NC} http://$HOST:$PORT (network access)"
echo -e "\n${GREEN}API Documentation:${NC}"
echo -e "  ${BLUE}→${NC} http://localhost:$PORT/docs (Swagger UI)"
echo -e "  ${BLUE}→${NC} http://localhost:$PORT/redoc (ReDoc)"
echo -e "\n${YELLOW}Press Ctrl+C to stop the server${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Change to backend directory
cd "$BACKEND_DIR"

# Start uvicorn server
# NOTE: uvicorn is run with --reload only in local dev (implied by script usage)
# In production, Render usually runs the command directly from the dashboard.
uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
