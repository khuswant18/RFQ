#!/bin/bash
# Frontend Startup Script for RFQ System

echo "=========================================="
echo "Starting RFQ Frontend (React + Vite)"
echo "=========================================="
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules not found. Installing dependencies..."
    npm install
    echo ""
fi

# Start the frontend dev server
echo "✓ Starting Vite dev server on http://localhost:5173"
echo ""
echo "Frontend is running..."
echo "  • App: http://localhost:5173"
echo "  • Make sure backend is running on http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev
