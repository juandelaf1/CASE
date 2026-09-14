FROM python:3.13-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for dependency caching
COPY pyproject.toml ./

# Copy source code
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -e "." && \
    pip install --no-cache-dir streamlit httpx

# Copy Streamlit app
COPY streamlit_app/ ./streamlit_app/

# Copy entrypoint
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Create data directory for SQLite
RUN mkdir -p /app/data

# Create non-root user
RUN groupadd -r caseuser && \
    useradd -r -g caseuser -d /app -s /sbin/nologin caseuser && \
    chown -R caseuser:caseuser /app

USER caseuser

ENV CASE_DB_PATH=/app/data/case_audit.db
ENV CASE_API_BASE_URL=http://localhost:8000

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
