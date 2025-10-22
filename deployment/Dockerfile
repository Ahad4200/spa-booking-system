FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Set Python path
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Create non-root user
RUN useradd -m -u 1000 spa && chown -R spa:spa /app
USER spa

# Expose port
EXPOSE 5000

# Run with gunicorn using eventlet worker for WebSocket support
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "eventlet", "--workers", "1", "--timeout", "120", "app:app"]