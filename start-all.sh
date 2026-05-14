#!/bin/bash
# Combined Startup Script - Runs Both Backend and Frontend

echo "=========================================="
echo "Starting RFQ System (Backend + Frontend)"
echo "=========================================="
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "=========================================="
    echo "Shutting down RFQ System..."
    echo "=========================================="
    
    # Kill all child processes
    pkill -P $$
    
    echo "✓ Backend stopped"
    echo "✓ Frontend stopped"
    echo ""
    echo "Goodbye!"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Start backend in background
echo "Starting Backend..."
echo "----------------------------------------"
cd "$SCRIPT_DIR"
bash start-backend.sh > backend.log 2>&1 &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID)"
echo "  Logs: backend.log"
echo ""

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start. Check backend.log"
        cleanup
    fi
    sleep 1
done
echo ""

# Start frontend in background
echo "Starting Frontend..."
echo "----------------------------------------"
cd "$SCRIPT_DIR"
bash start-frontend.sh > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✓ Frontend started (PID: $FRONTEND_PID)"
echo "  Logs: frontend.log"
echo ""

# Wait for frontend to be ready
echo "Waiting for frontend to be ready..."
sleep 5
echo "✓ Frontend should be ready!"
echo ""

# Display status
echo "=========================================="
echo "✅ RFQ System is Running!"
echo "=========================================="
echo ""
echo "Services:"
echo "  • Backend:  http://localhost:8000"
echo "  • Frontend: http://localhost:5173"
echo "  • API Docs: http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  • Backend:  tail -f backend.log"
echo "  • Frontend: tail -f frontend.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user to press Ctrl+C
wait
