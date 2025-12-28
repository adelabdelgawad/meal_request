#!/bin/bash
# ==============================================================================
# Production Deployment Script for Meal Request Application
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="/backups"

# Functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if running in docker directory
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Must be run from the docker/ directory!"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running!"
    exit 1
fi

echo "========================================="
echo "Meal Request Application - Deployment"
echo "========================================="
echo ""

# Check if environment files exist
print_info "Checking environment configuration..."
if [ ! -f "env/.env.backend" ] || [ ! -f "env/.env.database" ]; then
    print_warning "Environment files not found!"
    echo ""
    echo "Creating environment files from templates..."

    cd env/
    for file in .env.example.*; do
        target="${file//.env.example//.env}"
        if [ ! -f "$target" ]; then
            cp "$file" "$target"
            print_success "Created $target"
        fi
    done
    cd ..

    print_warning "Please edit the environment files in docker/env/ before deploying!"
    print_warning "Especially update passwords and secrets in .env.backend and .env.database"
    echo ""
    read -p "Press Enter to continue after editing, or Ctrl+C to exit..."
fi

print_success "Environment files found"

# Ask for confirmation
echo ""
print_warning "This will deploy the production environment with:"
echo "  - 3x Backend instances (load balanced)"
echo "  - 1x Frontend instance"
echo "  - MariaDB database"
echo "  - Redis cache/broker"
echo "  - Celery worker + beat"
echo "  - Nginx load balancer"
echo "  - Prometheus + Grafana monitoring"
echo ""
read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Deployment cancelled"
    exit 0
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Pull latest images (if using remote registry)
# Uncomment if images are hosted in a registry
# print_info "Pulling latest images..."
# docker compose -f $COMPOSE_FILE pull

# Build images
print_info "Building Docker images..."
if docker compose -f $COMPOSE_FILE build --no-cache; then
    print_success "Images built successfully"
else
    print_error "Failed to build images"
    exit 1
fi

# Check if services are already running
if docker compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    print_warning "Services are already running"
    read -p "Do you want to restart them? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Create backup before updating
        print_info "Creating database backup before update..."
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        docker compose -f $COMPOSE_FILE exec -T database \
            mysqldump -u meal_user -p${MYSQL_PASSWORD:-meal_password} meal_request_db \
            | gzip > "${BACKUP_DIR}/pre_deploy_backup_${TIMESTAMP}.sql.gz" 2>/dev/null || true

        if [ -f "${BACKUP_DIR}/pre_deploy_backup_${TIMESTAMP}.sql.gz" ]; then
            print_success "Backup created: pre_deploy_backup_${TIMESTAMP}.sql.gz"
        fi

        # Stop services
        print_info "Stopping services..."
        docker compose -f $COMPOSE_FILE down
        print_success "Services stopped"
    fi
fi

# Start services
print_info "Starting services..."
if docker compose -f $COMPOSE_FILE up -d; then
    print_success "Services started"
else
    print_error "Failed to start services"
    exit 1
fi

# Wait for services to be healthy
print_info "Waiting for services to be healthy (this may take up to 60 seconds)..."
sleep 10

# Check health status
RETRY_COUNT=0
MAX_RETRIES=12  # 12 * 5 seconds = 60 seconds

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    UNHEALTHY=$(docker compose -f $COMPOSE_FILE ps | grep -c "unhealthy" || true)

    if [ "$UNHEALTHY" -eq 0 ]; then
        print_success "All services are healthy"
        break
    fi

    print_info "Waiting for services to become healthy... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_warning "Some services may not be healthy yet. Check with: docker compose -f $COMPOSE_FILE ps"
fi

# Run database migrations
print_info "Running database migrations..."
if docker compose -f $COMPOSE_FILE exec backend-1 alembic upgrade head; then
    print_success "Database migrations completed"
else
    print_warning "Failed to run migrations (database may not be ready yet)"
    print_info "You can run migrations manually with:"
    print_info "  docker compose -f $COMPOSE_FILE exec backend-1 alembic upgrade head"
fi

# Display service status
echo ""
echo "========================================="
echo "Deployment Summary"
echo "========================================="
docker compose -f $COMPOSE_FILE ps
echo ""

# Display access URLs
echo "========================================="
echo "Access Points"
echo "========================================="
echo "Frontend:          http://localhost"
echo "Backend API:       http://localhost/api"
echo "API Docs:          http://localhost/docs"
echo "Prometheus:        http://localhost:9090"
echo "Grafana:           http://localhost:3001 (admin/admin)"
echo "Flower:            http://localhost:5555"
echo "========================================="
echo ""

print_success "Deployment completed successfully!"
echo ""
print_info "Next steps:"
echo "  1. Verify services: docker compose -f $COMPOSE_FILE ps"
echo "  2. Check logs: docker compose -f $COMPOSE_FILE logs -f"
echo "  3. Test health: curl http://localhost/health"
echo "  4. Monitor metrics: http://localhost:9090"
echo ""
