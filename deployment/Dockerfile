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

# Debug: Check what files are actually copied (remove after debugging)
RUN echo "=== Listing /app contents ===" && ls -la /app
RUN echo "=== Listing /app/utils contents ===" && ls -la /app/utils
RUN echo "=== Python path ===" && python -c "import sys; print('\n'.join(sys.path))"
RUN echo "=== Testing import ===" && python -c "from utils.conversation_logger import conversation_logger" || echo "Import failed"

# Create non-root user
RUN useradd -m -u 1000 spa && chown -R spa:spa /app
USER spa

# Expose port
EXPOSE 5000

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]