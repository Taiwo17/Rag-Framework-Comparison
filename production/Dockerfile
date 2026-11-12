
FROM python:3.12-slim

WORKDIR /app

# Create a dedicated non-root user
RUN useradd --create-home --uid 10001 appuser

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions
COPY production/requirements.txt ./requirements.txt

# Install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

# Copy application code and assign ownership
COPY --chown=appuser:appuser production/ ./production/

# Allow the application user to access its working directory
RUN chown appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "production.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
