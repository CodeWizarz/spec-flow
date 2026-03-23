#!/bin/bash
# SpecFlow Deployment Script
# Usage: ./deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
PROJECT_NAME="specflow"

echo "=========================================="
echo "  SpecFlow Deployment Script"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if .env exists
if [ ! -f ".env" ]; then
    log_warn "No .env file found. Using default values."
    log_info "Create .env from .env.example for production deployment."
fi

# Build Docker images
log_info "Building Docker images..."
docker-compose -f docker-compose.specflow.yml build

# Start services
log_info "Starting services..."
docker-compose -f docker-compose.specflow.yml up -d

# Wait for database to be ready
log_info "Waiting for database..."
sleep 10

# Run migrations
log_info "Running database migrations..."
docker-compose -f docker-compose.specflow.yml exec -T specflow-api python manage.py migrate --noinput

# Collect static files
log_info "Collecting static files..."
docker-compose -f docker-compose.specflow.yml exec -T specflow-api python manage.py collectstatic --noinput --clear

# Check service health
log_info "Checking service health..."
sleep 5
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/)
if [ "$HEALTH_STATUS" = "200" ]; then
    log_info "Health check passed!"
else
    log_warn "Health check returned status: $HEALTH_STATUS"
fi

# Show running containers
log_info "Running containers:"
docker-compose -f docker-compose.specflow.yml ps

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Services:"
echo "  - API:      http://localhost:8000"
echo "  - Health:   http://localhost:8000/health/"
echo "  - Worker:   Running (celery)"
echo ""
echo "To view logs: docker-compose -f docker-compose.specflow.yml logs -f"
echo "To stop:      docker-compose -f docker-compose.specflow.yml down"
echo ""