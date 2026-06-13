#!/bin/bash
# Start both backend and frontend dev servers concurrently.
# Backend → http://localhost:8000  (API + docs)
# Frontend → http://localhost:3000 (Next.js UI)
# Ctrl+C stops both.

set -e

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Done."
}

trap cleanup EXIT INT TERM

echo "=== Starting Backend (FastAPI :8000) ==="
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "=== Starting Frontend (Next.js :3000) ==="
cd novel-frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Docs:     http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both."

wait
