# SpecFlow Backend Dockerfile
# Multi-stage build for production

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first (better layer caching)
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/production.txt


# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application
COPY . .

# Create non-root user for security FIRST
RUN useradd --create-home specflow

# Create logs directory with proper permissions for specflow user
RUN mkdir -p /app/plane/logs && chown -R specflow:specflow /app/plane/logs

# Change ownership of entire app to specflow
RUN chown -R specflow:specflow /app

USER specflow

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=plane.settings.production \
    PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run migrations and start server
CMD ["sh", "-c", "python manage.py migrate && gunicorn plane.asgi:application --bind 0.0.0.0:8000 --workers 4"]
