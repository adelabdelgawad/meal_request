# Docker Configuration

This directory contains all Docker-related configuration for the Meal Request application.

## Directory Structure

```
docker/
├── env/
│   ├── .env.example.backend    # Backend config template
│   ├── .env.example.database   # Database config template
│   ├── .env.example.redis      # Redis config template
│   ├── .env.example.grafana    # Grafana config template
│   ├── .env.backend            # Backend config (DO NOT COMMIT)
│   ├── .env.database           # Database config (DO NOT COMMIT)
│   ├── .env.redis              # Redis config (DO NOT COMMIT)
│   ├── .env.grafana            # Grafana config (DO NOT COMMIT)
│   └── .gitignore              # Protects .env.* files
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml  # Prometheus scrape configuration
│   └── grafana/
│       └── provisioning/   # Grafana datasources and dashboards
├── backend/                # Legacy - env files moved to env/
├── database/               # Legacy - env files moved to env/
├── redis/                  # Legacy - env files moved to env/
├── docker-compose.yml      # Main orchestration file
└── README.md               # This file
```

## Quick Start

### First-Time Setup

1. **Copy environment templates for each service:**
   ```bash
   cd docker/env/
   cp .env.example.backend .env.backend
   cp .env.example.database .env.database
   cp .env.example.redis .env.redis
   cp .env.example.grafana .env.grafana
   cd ..
   ```

2. **Edit environment variables:**
   ```bash
   # Backend configuration
   nano env/.env.backend
   ```
   Update critical values:
   - `JWT_SECRET_KEY` (use `openssl rand -hex 32`)
   - `DB_PASSWORD` (must match database password)
   - LDAP/AD credentials (if using domain authentication)

   ```bash
   # Database configuration
   nano env/.env.database
   ```
   Update:
   - `MYSQL_ROOT_PASSWORD`
   - `MYSQL_PASSWORD` (must match backend DB_PASSWORD)

   ```bash
   # Grafana configuration
   nano env/.env.grafana
   ```
   Update:
   - `GF_SECURITY_ADMIN_PASSWORD`

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```
   Docker will automatically create named volumes for persistent data.

4. **Run database migrations:**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

### Starting Services

```bash
# All core services
docker-compose up -d

# Specific services only
docker-compose up -d database redis backend

# With development tools (Redis Commander)
docker-compose --profile tools up -d

# View logs
docker-compose logs -f backend
```

## Service Access

Once running, access services at:

| Service           | URL                          | Notes                    |
|-------------------|------------------------------|--------------------------|
| Frontend          | http://localhost:3000        | Next.js application      |
| Backend API       | http://localhost:8000        | FastAPI + docs           |
| API Docs          | http://localhost:8000/docs   | Swagger UI               |
| Metrics           | http://localhost:8000/metrics| Prometheus metrics       |
| Prometheus        | http://localhost:9090        | Metrics collection       |
| Grafana           | http://localhost:3001        | User: admin/admin        |
| Flower            | http://localhost:5555        | Celery monitoring        |
| Node Exporter     | http://localhost:9100        | System metrics           |
| MariaDB Exporter  | http://localhost:9104        | Database metrics         |

## Services Overview

### Core Services
- **database** - MariaDB 11.2 with optimized settings
- **redis** - Redis 7.2 for caching and Celery broker
- **backend** - FastAPI application with Gunicorn+Uvicorn
- **frontend** - Next.js application (production build)

### Background Processing
- **celery-worker** - Async task processing
- **flower** - Celery monitoring dashboard

### Monitoring Stack
- **prometheus** - Metrics collection and alerting
- **grafana** - Metrics visualization
- **node-exporter** - System metrics (CPU, RAM, disk, network)
- **mariadb-exporter** - Database performance metrics

### Development Tools (optional)
- **redis-commander** - Redis GUI (requires `--profile tools`)

## Database Management

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Description"

# Access MariaDB CLI
docker-compose exec database mysql -u meal_user -p meal_request_db

# Backup database
docker-compose exec database mysqldump -u root -p meal_request_db > backup.sql

# Restore database
docker-compose exec -T database mysql -u root -p meal_request_db < backup.sql
```

## Celery Task Management

### Run Celery in Docker (Production)
```bash
docker-compose up -d celery-worker flower
```

### Run Celery Locally (Development - Recommended)
Faster iteration, better debugging:

```bash
# 1. Ensure Redis is running
docker-compose up -d redis

# 2. Start worker
cd ../src/backend
celery -A celery_app.celery_app worker -P gevent --concurrency=10 --loglevel=info

# 3. Start beat (periodic tasks) - separate terminal
celery -A celery_app.celery_app beat --loglevel=info

# 4. Start Flower (monitoring) - optional, separate terminal
celery -A celery_app.celery_app flower --port=5555
```

## Monitoring & Observability

### Prometheus Metrics
- Automatically scraped every 15 seconds
- FastAPI app exposes metrics at `/metrics`
- Data retention: 15 days (configurable in docker-compose.yml)

### Grafana Dashboards
1. Access Grafana at http://localhost:3001
2. Login: admin / admin (change on first login)
3. Prometheus datasource is pre-configured
4. Import dashboards from `monitoring/grafana/provisioning/dashboards/`

### Available Metrics
- **FastAPI**: Request rates, latency, errors (via `/metrics`)
- **System**: CPU, memory, disk, network (via node-exporter)
- **Database**: Connections, queries, slow queries (via mariadb-exporter)
- **Prometheus**: Self-monitoring

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs -f [service_name]

# Verify environment variables
cat env/.env

# Rebuild images
docker-compose build --no-cache
```

### Database connection issues
```bash
# Check database is healthy
docker-compose ps database

# Test connection from backend
docker-compose exec backend nc -zv database 3306

# Check credentials in env/.env
grep DB_ env/.env
```

### Port conflicts
If ports are already in use, edit `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Change host port (left side)
```

### Reset everything (WARNING: Deletes all data)
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Start fresh
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## Environment Variables

Each service has its own configuration file:

### Backend (`env/.env.backend`)
- `JWT_SECRET_KEY` - Generate with `openssl rand -hex 32`
- `DB_PASSWORD` - Must match database password
- `ENVIRONMENT` - Set to `production` for prod
- `ALLOWED_ORIGINS__*` - Configure CORS
- LDAP/AD credentials

### Database (`env/.env.database`)
- `MYSQL_ROOT_PASSWORD` - Root password
- `MYSQL_PASSWORD` - Must match backend DB_PASSWORD
- `MYSQL_USER` - Database user
- `MYSQL_DATABASE` - Database name

### Redis (`env/.env.redis`)
- `REDIS_MAXMEMORY` - Memory limit
- `REDIS_PASSWORD` - Optional, for production

### Grafana (`env/.env.grafana`)
- `GF_SECURITY_ADMIN_PASSWORD` - Admin password
- `GF_SERVER_ROOT_URL` - Public URL

### Critical Production Settings
- ✅ Change ALL default passwords in each `.env.*` file
- ✅ Generate strong `JWT_SECRET_KEY`
- ✅ Ensure database passwords match between services
- ✅ Configure LDAP/AD if using domain authentication

## Network Architecture

All services communicate via the `meal-request-network` bridge network:
- Internal DNS resolution (e.g., `backend:8000`, `database:3306`)
- Services are isolated from the host network
- Only exposed ports are accessible from host

## Data Persistence

Data is stored in **Docker-managed named volumes** for reliability and portability:
- **mariadb_data**: Database files
- **redis_data**: Cache persistence
- **prometheus_data**: Metrics time-series data
- **grafana_data**: Dashboard configurations
- **backend_logs**: Application logs

### Volume Management

**List volumes:**
```bash
docker volume ls | grep meal-request
```

**Inspect a volume:**
```bash
docker volume inspect docker_mariadb_data
```

**Backup a volume:**
```bash
# Backup database
docker run --rm \
  -v docker_mariadb_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/mariadb_backup.tar.gz -C /data .
```

**Restore a volume:**
```bash
# Restore database
docker run --rm \
  -v docker_mariadb_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/mariadb_backup.tar.gz"
```

**Remove all volumes (WARNING: Deletes all data!):**
```bash
docker-compose down -v
```

## Development vs Production

### Development (default)
- Hot-reload enabled (where applicable)
- Debug logging
- Development CORS settings
- Local Celery recommended for faster iteration

### Production
1. Update `env/.env`:
   - `ENVIRONMENT=production`
   - Strong passwords and secrets
   - Production CORS origins
   - Disable debug settings

2. Use Celery in Docker for consistency

3. Enable HTTPS (requires nginx/Traefik reverse proxy - not included)

4. Review resource limits in `docker-compose.yml`

## Further Reading

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Prometheus Configuration](monitoring/prometheus/prometheus.yml)
- [Grafana Provisioning](monitoring/grafana/provisioning/)
- [Main Project README](../README.md)
