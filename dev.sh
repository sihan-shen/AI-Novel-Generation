#!/bin/bash
# Start both backend and frontend dev servers concurrently.
#   Backend  → http://localhost:8000  (FastAPI API)
#   Frontend → http://localhost:3000  (Next.js UI)
# Press Ctrl+C to stop both.

set -e
BOLD='\033[1m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log()  { echo -e "${BOLD}[$(date +%H:%M:%S)]${NC} $*"; }

cleanup() {
    log "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    log "${GREEN}Done.${NC}"
}
trap cleanup EXIT INT TERM

log "${BLUE}Starting Backend (FastAPI :8000)${NC}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 2

log "${BLUE}Starting Frontend (Next.js :3000)${NC}"
(cd novel-frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
log "${BOLD}${GREEN}══════════════════════════════════════════════════════════${NC}"
log "${BOLD}Backend API:  ${GREEN}http://localhost:8000${NC}"
log "${BOLD}API Docs:     ${GREEN}http://localhost:8000/docs${NC}"
log "${BOLD}Frontend UI:  ${GREEN}http://localhost:3000${NC}"
log "${BOLD}${GREEN}══════════════════════════════════════════════════════════${NC}"
echo ""
log "${YELLOW}Press Ctrl+C to stop both servers.${NC}"
echo ""

wait
