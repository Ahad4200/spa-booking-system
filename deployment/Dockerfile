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
EXPOSE 10000

# Run with uvicorn for FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]