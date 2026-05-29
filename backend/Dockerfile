FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app/backend
ENV PYTHONPATH=/app

WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Ensure gunicorn is installed for production deployment
RUN pip install --no-cache-dir gunicorn pydantic-settings

# Copy application code
COPY . .

# Create workspace directories to avoid permission issues
RUN mkdir -p /app/backend/uploads \
             /app/backend/exports \
             /app/backend/cache \
             /app/backend/logs

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/telemetry || exit 1

# Start gunicorn with Uvicorn workers
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn_conf.py", "main:app", "--bind", "0.0.0.0:8000"]
