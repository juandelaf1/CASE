#!/bin/bash
set -e

echo "Starting CASE — Case Assessment and Structured Evaluation"
echo "=========================================================="

# RUN_MODE: api | streamlit | both (default)
MODE="${RUN_MODE:-both}"

if [ "$MODE" = "api" ]; then
    echo "API mode — port ${PORT:-8000}"
    exec uvicorn case_api.api.v1.app:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

if [ "$MODE" = "streamlit" ]; then
    echo "Streamlit mode — port ${PORT:-8501}"
    exec streamlit run streamlit_app/app.py --server.port "${PORT:-8501}" --server.address 0.0.0.0 --server.headless true
fi

# Both mode (local Docker)
echo "Starting API server on port 8000..."
uvicorn case_api.api.v1.app:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Waiting for API to be ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "API is ready."
        break
    fi
    if [ $i -eq 30 ]; then
        echo "API failed to start within 30 seconds."
        exit 1
    fi
    sleep 1
done

echo "Starting Streamlit UI on port 8501..."
streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &
STREAMLIT_PID=$!

echo ""
echo "CASE is running:"
echo "  API:      http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Streamlit: http://localhost:8501"
echo ""

wait -n $API_PID $STREAMLIT_PID
