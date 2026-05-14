#!/bin/bash
# Backend Startup Script for RFQ System

echo "=========================================="
echo "Starting RFQ Backend Server"
echo "=========================================="
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Check if virtual environment exists
if [ ! -d "../.venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source ../.venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found in backend/"
    echo "Using environment variables from parent shell"
fi

# Start the backend server
echo "✓ Starting FastAPI server on http://localhost:8000"
echo ""
echo "Backend is running..."
echo "  • API: http://localhost:8000"
echo "  • Docs: http://localhost:8000/docs"
echo "  • Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python run.py
