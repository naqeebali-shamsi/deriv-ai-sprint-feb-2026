FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create models directory
RUN mkdir -p models

# Default environment
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV DATABASE_PATH=/app/data/app.db
ENV LOG_LEVEL=INFO
ENV CORS_ORIGINS=*

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health', timeout=3); assert r.status_code == 200"

# Run backend
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
