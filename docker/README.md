# Docker Configuration for Meal Request Application

This directory contains Docker and Docker Compose configurations for deploying the Meal Request application.

## Quick Start

### Development (Single Instance)

```bash
cd docker/

# Copy environment files
cd env/
for file in .env.example.*; do cp "$file" "${file//.env.example//.env}"; done
cd ..

# Start services
docker compose up -d

# Run migrations
docker compose exec backend alembic upgrade head

# Access application
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/docs
```

### Production (Load Balanced)

```bash
cd docker/

# Automated deployment
./scripts/deploy.sh

# Or manual deployment
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec backend-1 alembic upgrade head
```

## Architecture

**Development Setup** (`docker-compose.yml`):
- Single backend instance
- Suitable for local development
- Direct port access for debugging

**Production Setup** (`docker-compose.prod.yml`):
- **3x Backend instances** (load balanced via Nginx)
- **Nginx reverse proxy** on port 80
- **Resource limits** for stability
- **Health checks** for all services
- **Optimized for 10-30 concurrent users**

## Services

### Core Services

| Service | Port(s) | Description |
|---------|---------|-------------|
| **nginx** | 80, 443 | Load balancer & reverse proxy |
| **backend-1** | 8000 | FastAPI application (instance 1) |
| **backend-2** | 8000 | FastAPI application (instance 2) |
| **backend-3** | 8000 | FastAPI application (instance 3) |
| **frontend** | 3000 | Next.js frontend |
| **database** | 3306 | MariaDB 11.2 |
| **redis** | 6379 | Cache & message broker |

### Common Commands

```bash
# Start production
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Check health
curl http://localhost/health

# Run migrations
docker compose -f docker-compose.prod.yml exec backend-1 alembic upgrade head
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for comprehensive documentation.
