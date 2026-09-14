#!/bin/bash
set -e

echo "Starting CASE — Case Assessment and Structured Evaluation"
echo "=========================================================="

# Render sets PORT env var. If set, run API only (no Streamlit).
if [ -n "$PORT" ]; then
    echo "Render mode — API only on port $PORT"
    exec uvicorn case_api.api.v1.app:app --host 0.0.0.0 --port "$PORT"
fi

# Local Docker mode — API + Streamlit
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
cd streamlit_app
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &
STREAMLIT_PID=$!
cd ..

echo ""
echo "CASE is running:"
echo "  API:      http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Streamlit: http://localhost:8501"
echo ""

wait -n $API_PID $STREAMLIT_PID
