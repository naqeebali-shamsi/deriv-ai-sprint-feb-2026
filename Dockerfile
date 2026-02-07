FROM python:3.11-slim

WORKDIR /app

# Install curl for healthchecks + dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create writable directories
RUN mkdir -p models data

# Non-root user
RUN useradd -r -s /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser

# Default environment
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV DATABASE_PATH=/app/data/app.db
ENV LOG_LEVEL=INFO
ENV CORS_ORIGINS=*

# Expose backend + UI ports (image used for both services)
EXPOSE 8000 8501

# No HEALTHCHECK here — defined per-service in docker-compose.yml

# Run backend (UI overrides CMD via compose command:)
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
