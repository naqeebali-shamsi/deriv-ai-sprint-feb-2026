#!/bin/bash
# demo.sh - Full end-to-end demo runner
# Starts all services, seeds data, and shows the autonomy loop
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Autonomous Fraud Agent - Demo Runner"
echo "  Drishpex 2026"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Step 1: Initialize database
echo -e "\n${GREEN}[1/6] Initializing database...${NC}"
rm -f app.db
python scripts/init_db.py

# Step 2: Validate schemas
echo -e "\n${GREEN}[2/7] Validating schemas...${NC}"
python scripts/validate_schemas.py

# Step 3: Bootstrap model
echo -e "\n${GREEN}[3/7] Bootstrapping ML model...${NC}"
python scripts/bootstrap_model.py --force

# Step 4: Start backend
echo -e "\n${GREEN}[4/7] Starting backend (FastAPI)...${NC}"
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 3

# Verify backend is up
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}  Backend is healthy!${NC}"
else
    echo -e "${YELLOW}  Warning: Backend may not be ready yet${NC}"
fi

# Step 5: Seed demo data
echo -e "\n${GREEN}[5/7] Seeding demo data (200 txns + retrain + mining)...${NC}"
python scripts/seed_demo.py --count 200

# Step 6: Start UI
echo -e "\n${GREEN}[6/7] Starting UI (Streamlit)...${NC}"
streamlit run ui/app.py --server.port 8501 --server.headless true &
UI_PID=$!
sleep 2

# Step 7: Start embedded simulator via backend API
echo -e "\n${GREEN}[7/7] Starting live transaction simulator (1 TPS)...${NC}"
curl -s -X POST http://localhost:8000/simulator/start \
  -H "Content-Type: application/json" \
  -d '{"tps": 1.0}' && echo -e "  ${GREEN}Embedded simulator started (1 TPS)${NC}" \
  || echo -e "  ${YELLOW}Warning: Could not start simulator${NC}"

echo -e "\n=========================================="
echo -e "${GREEN}Demo is running!${NC}"
echo "=========================================="
echo ""
echo -e "${CYAN}URLs:${NC}"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  Streamlit UI: http://localhost:8501"
echo ""
echo -e "${CYAN}What judges will see:${NC}"
echo "  1. Transaction stream flowing in real-time"
echo "  2. Risk scores computed by ML model"
echo "  3. Cases opening automatically for high-risk txns"
echo "  4. Analyst can label cases (fraud/legit)"
echo "  5. Model retrains with new labels"
echo "  6. Pattern cards from graph mining (rings, hubs)"
echo ""
echo -e "${CYAN}Key demo actions:${NC}"
echo "  - Click 'Cases' tab → label some cases"
echo "  - Click 'Model & Learning' tab → retrain"
echo "  - Click 'Patterns' tab → run mining"
echo "  - Toggle auto-refresh in sidebar"
echo ""
echo "Press Ctrl+C to stop all services."
echo "=========================================="

# Wait for all background jobs
wait
