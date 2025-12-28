# Meal Request Application - Docker Deployment Guide

## Overview

This guide covers deploying the Meal Request application using Docker containers with production-ready configuration optimized for **10-30 concurrent users**.

## Architecture

```
                    Internet
                       │
                       ▼
                 [Nginx :80]
                  Load Balancer
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   [Backend-1]    [Backend-2]    [Backend-3]
   :8000 (2w)     :8000 (2w)     :8000 (2w)
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
        ▼              ▼              ▼              ▼
   [MariaDB]      [Redis]      [Frontend]    [Celery Worker]
   :3306          :6379         :3000         (gevent)
```

**Key Components:**
- **Nginx**: Reverse proxy and load balancer (80)
- **Backend**: 3x FastAPI instances (2 Gunicorn workers each = 6 total processes)
- **Frontend**: 1x Next.js/React application
- **Database**: MariaDB 11.2 with optimized configuration
- **Cache/Broker**: Redis 7.2 for caching and Celery message queue
- **Workers**: Celery worker with gevent (10 concurrency)
- **Monitoring**: Prometheus + Grafana + exporters

## Resource Requirements

### Minimum Production Setup

| Component | CPU | Memory | Replicas | Total CPU | Total Memory |
|-----------|-----|--------|----------|-----------|--------------|
| Nginx | 0.5 | 256 MB | 1 | 0.5 | 256 MB |
| Backend | 1.0 | 1 GB | 3 | 3.0 | 3 GB |
| Frontend | 0.5 | 512 MB | 1 | 0.5 | 512 MB |
| MariaDB | 2.0 | 2 GB | 1 | 2.0 | 2 GB |
| Redis | 1.0 | 768 MB | 1 | 1.0 | 768 MB |
| Celery Worker | 1.0 | 1 GB | 1 | 1.0 | 1 GB |
| Celery Beat | 0.5 | 256 MB | 1 | 0.5 | 256 MB |
| **Subtotal (Core)** | | | | **8.5 cores** | **7.8 GB** |
| Monitoring (optional) | 2.0 | 2 GB | 4 | 2.0 | 2 GB |
| **Total (with monitoring)** | | | | **10.5 cores** | **9.8 GB** |

**Recommended Host Specs:**
- **CPU**: 12+ cores (allows headroom for spikes)
- **Memory**: 16 GB RAM
- **Disk**: 100 GB SSD (for database and logs)
- **Network**: 1 Gbps

## Prerequisites

1. **Docker Engine** 24.0+ with Docker Compose V2
   ```bash
   docker --version  # Should be 24.0+
   docker compose version  # Should be v2.20+
   ```

2. **System Resources**: Ensure host meets minimum requirements above

3. **Network Ports**: Ensure these ports are available:
   - `80`: Nginx (HTTP)
   - `443`: Nginx (HTTPS - optional)
   - `3001`: Grafana
   - `5555`: Flower (Celery monitoring)
   - `9090`: Prometheus

## Quick Start (Development)

```bash
# 1. Navigate to docker directory
cd docker/

# 2. Copy environment templates
cd env/
for file in .env.example.*; do
    target="${file//.env.example//.env}"
    cp "$file" "$target"
done
cd ..

# 3. Edit environment files (especially passwords!)
nano env/.env.backend
nano env/.env.database

# 4. Start core services (single backend instance)
docker compose up -d

# 5. Run database migrations
docker compose exec backend alembic upgrade head

# 6. Access application
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Docs:     http://localhost:8000/docs
```

## Production Deployment

### Step 1: Environment Configuration

```bash
cd docker/env/

# Copy all environment templates
cp .env.example.backend .env.backend
cp .env.example.database .env.database
cp .env.example.redis .env.redis
cp .env.example.frontend .env.frontend
cp .env.example.grafana .env.grafana
```

**Edit each file with production values:**

#### `.env.backend`
```bash
# Critical settings to change:
DB_PASSWORD=<strong-db-password>
JWT_SECRET_KEY=<generate-with: openssl rand -hex 32>
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# LDAP/AD credentials
SERVICE_ACCOUNT=<ad-service-account>
SERVICE_PASSWORD=<ad-service-password>

# External databases (HRIS, BioStar)
HRIS_URL=mssql+pyodbc://...
BIOSTAR_URL=mssql+pyodbc://...

# CORS (production domains)
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### `.env.database`
```bash
MYSQL_ROOT_PASSWORD=<strong-root-password>
MYSQL_USER=meal_user
MYSQL_PASSWORD=<strong-db-password>  # MUST match DB_PASSWORD in .env.backend
MYSQL_DATABASE=meal_request_db
```

#### `.env.redis`
```bash
# Optional: Set Redis password for production
# REDIS_PASSWORD=<redis-password>
```

### Step 2: Build and Deploy

```bash
cd docker/

# Build all images (first time or after code changes)
docker compose -f docker-compose.prod.yml build --no-cache

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Verify all containers are healthy
docker compose -f docker-compose.prod.yml ps

# Expected output: All services should show "Up" and "healthy"
```

### Step 3: Database Initialization

```bash
# Run migrations on one backend instance
docker compose -f docker-compose.prod.yml exec backend-1 alembic upgrade head

# Create initial admin user (if needed)
docker compose -f docker-compose.prod.yml exec backend-1 python -m scripts.create_admin
```

### Step 4: Verify Deployment

```bash
# Check logs for errors
docker compose -f docker-compose.prod.yml logs -f backend-1

# Test health endpoints
curl http://localhost/health
curl http://localhost/api/v1/health

# Check load balancer is routing to all backends
for i in {1..10}; do
    curl -s http://localhost/health | grep -o "instance.*"
done
# Should see different backend instances (backend-1, backend-2, backend-3)

# Verify metrics are being collected
curl http://localhost:9090/api/v1/targets  # Prometheus targets
```

### Step 5: SSL/TLS Configuration (Production)

For HTTPS in production:

```bash
# 1. Create SSL directory
mkdir -p docker/nginx/ssl/

# 2. Copy SSL certificates
cp /path/to/cert.pem docker/nginx/ssl/
cp /path/to/key.pem docker/nginx/ssl/

# 3. Edit nginx.conf to enable HTTPS server block
nano docker/nginx/nginx.conf
# Uncomment the HTTPS server block and HTTP redirect

# 4. Restart nginx
docker compose -f docker-compose.prod.yml restart nginx
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Application** | http://localhost | Main frontend (via nginx) |
| **Backend API** | http://localhost/api | API endpoints (load balanced) |
| **API Docs** | http://localhost/docs | Interactive API documentation |
| **Metrics** | http://localhost/metrics | Prometheus metrics endpoint |
| **Prometheus** | http://localhost:9090 | Metrics collection & alerting |
| **Grafana** | http://localhost:3001 | Dashboards (admin/admin) |
| **Flower** | http://localhost:5555 | Celery task monitoring |
| **Node Exporter** | http://localhost:9100 | System metrics |
| **Redis Exporter** | http://localhost:9121 | Redis metrics |
| **MariaDB Exporter** | http://localhost:9104 | Database metrics |

## Operational Commands

### Service Management

```bash
cd docker/

# View all services status
docker compose -f docker-compose.prod.yml ps

# View logs (all services)
docker compose -f docker-compose.prod.yml logs -f

# View logs (specific service)
docker compose -f docker-compose.prod.yml logs -f backend-1

# Restart a service
docker compose -f docker-compose.prod.yml restart backend-1

# Stop all services
docker compose -f docker-compose.prod.yml down

# Stop and remove all data (DANGER: deletes database!)
docker compose -f docker-compose.prod.yml down -v
```

### Scaling

```bash
# Add more backend instances (requires nginx config update)
# Note: nginx.conf needs to include backend-4 in upstream
docker compose -f docker-compose.prod.yml up -d --scale backend-1=4

# Reduce to 2 backend instances
docker compose -f docker-compose.prod.yml up -d --scale backend-1=2
```

### Database Operations

```bash
# Run migrations
docker compose -f docker-compose.prod.yml exec backend-1 alembic upgrade head

# Create new migration
docker compose -f docker-compose.prod.yml exec backend-1 \
    alembic revision --autogenerate -m "Description"

# Database backup
docker compose -f docker-compose.prod.yml exec database \
    mysqldump -u meal_user -p meal_request_db > backup_$(date +%Y%m%d).sql

# Database restore
docker compose -f docker-compose.prod.yml exec -T database \
    mysql -u meal_user -p meal_request_db < backup_20231215.sql

# Access database shell
docker compose -f docker-compose.prod.yml exec database \
    mysql -u meal_user -p meal_request_db
```

### Celery Operations

```bash
# View active tasks
docker compose -f docker-compose.prod.yml exec celery-worker \
    celery -A celery_app.celery_app inspect active

# View scheduled tasks
docker compose -f docker-compose.prod.yml exec celery-worker \
    celery -A celery_app.celery_app inspect scheduled

# View registered tasks
docker compose -f docker-compose.prod.yml exec celery-worker \
    celery -A celery_app.celery_app inspect registered

# Purge all tasks (DANGER: clears queue)
docker compose -f docker-compose.prod.yml exec celery-worker \
    celery -A celery_app.celery_app purge
```

### Monitoring & Debugging

```bash
# View resource usage
docker stats

# View resource usage (specific services)
docker stats meal-request-backend-1 meal-request-backend-2 meal-request-backend-3

# Inspect container
docker inspect meal-request-backend-1

# Execute shell in container
docker compose -f docker-compose.prod.yml exec backend-1 /bin/sh

# View environment variables
docker compose -f docker-compose.prod.yml exec backend-1 env

# Check network connectivity
docker compose -f docker-compose.prod.yml exec backend-1 ping database
docker compose -f docker-compose.prod.yml exec backend-1 curl http://redis:6379
```

## Performance Tuning

### Backend Tuning

Edit `src/backend/Dockerfile` to adjust Gunicorn workers:

```dockerfile
# Default: 4 workers
CMD ["gunicorn", "app:app", "--workers", "4", ...]

# Calculate optimal workers: (2 * CPU_CORES) + 1
# For 2 CPU container: (2 * 2) + 1 = 5 workers
CMD ["gunicorn", "app:app", "--workers", "5", ...]
```

Adjust in `docker-compose.prod.yml`:

```yaml
backend-1:
  environment:
    - GUNICORN_WORKERS=4  # Override default
  deploy:
    resources:
      limits:
        cpus: '2'  # Increase CPU allocation
        memory: 2G  # Increase memory
```

### Database Tuning

Adjust MariaDB settings in `docker-compose.prod.yml`:

```yaml
database:
  command: >
    --max_connections=200
    --innodb_buffer_pool_size=1G      # Increase for more memory
    --innodb_log_file_size=256M       # Larger for write-heavy loads
    --query_cache_size=64M            # Enable query cache
    --tmp_table_size=128M             # Larger temp tables
```

### Redis Tuning

Adjust Redis memory in `docker-compose.prod.yml`:

```yaml
redis:
  command: >
    redis-server
    --maxmemory 1gb               # Increase cache size
    --maxmemory-policy allkeys-lru
```

## Monitoring & Alerting

### Grafana Dashboards

1. Access Grafana: http://localhost:3001
2. Login: `admin` / `admin`
3. Navigate to Dashboards → Import
4. Import dashboard IDs:
   - **1860**: Node Exporter (system metrics)
   - **7362**: MySQL Overview
   - **11835**: Redis Dashboard
   - Custom: FastAPI metrics dashboard (create from Prometheus data)

### Key Metrics to Monitor

**Application Performance:**
- Request rate (requests/sec)
- Response time (p50, p95, p99)
- Error rate (5xx responses)
- Active connections per backend

**Infrastructure:**
- CPU usage (should stay < 70%)
- Memory usage (should stay < 80%)
- Database connections (< 80% of max)
- Redis memory usage (< 90% of maxmemory)

**Celery:**
- Task queue length (should stay low)
- Task success/failure rate
- Task execution time

### Setting Up Alerts

Create `docker/monitoring/prometheus/alerts.yml`:

```yaml
groups:
  - name: application_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        annotations:
          summary: "Container memory usage above 90%"
```

## Troubleshooting

### Backend Not Starting

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs backend-1

# Common issues:
# 1. Database connection failed → Check DB_PASSWORD matches in .env files
# 2. Missing environment variables → Verify .env.backend exists and is complete
# 3. Port already in use → Check no other process using 8000
```

### Database Connection Errors

```bash
# Test database connectivity
docker compose -f docker-compose.prod.yml exec backend-1 \
    python -c "from db.maria_database import test_connection; test_connection()"

# Check database is healthy
docker compose -f docker-compose.prod.yml ps database

# Verify credentials match
grep DB_PASSWORD docker/env/.env.backend
grep MYSQL_PASSWORD docker/env/.env.database
```

### Load Balancer Issues

```bash
# Check nginx logs
docker compose -f docker-compose.prod.yml logs nginx

# Test backend connectivity from nginx
docker compose -f docker-compose.prod.yml exec nginx ping backend-1
docker compose -f docker-compose.prod.yml exec nginx wget -O- http://backend-1:8000/health

# Verify all backends in upstream
docker compose -f docker-compose.prod.yml exec nginx cat /etc/nginx/nginx.conf | grep backend-
```

### Celery Tasks Not Processing

```bash
# Check worker status
docker compose -f docker-compose.prod.yml logs celery-worker

# Verify Redis connection
docker compose -f docker-compose.prod.yml exec celery-worker \
    python -c "from celery_app.celery_app import celery_app; print(celery_app.control.inspect().active())"

# Check task queue length
docker compose -f docker-compose.prod.yml exec redis redis-cli llen celery
```

## Backup & Recovery

### Automated Backups

Create backup script `docker/scripts/backup.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
docker compose -f docker-compose.prod.yml exec database \
    mysqldump -u meal_user -p${MYSQL_PASSWORD} meal_request_db \
    | gzip > "${BACKUP_DIR}/db_backup_${DATE}.sql.gz"

# Redis backup
docker compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE
docker cp meal-request-redis:/data/dump.rdb "${BACKUP_DIR}/redis_backup_${DATE}.rdb"

# Rotate old backups (keep last 7 days)
find ${BACKUP_DIR} -name "db_backup_*.sql.gz" -mtime +7 -delete
find ${BACKUP_DIR} -name "redis_backup_*.rdb" -mtime +7 -delete
```

Set up cron job:
```bash
# Run daily at 2 AM
0 2 * * * /path/to/docker/scripts/backup.sh
```

### Disaster Recovery

```bash
# 1. Stop all services
docker compose -f docker-compose.prod.yml down

# 2. Restore database
gunzip -c /backups/db_backup_20231215_020000.sql.gz | \
    docker compose -f docker-compose.prod.yml exec -T database \
    mysql -u meal_user -p meal_request_db

# 3. Restore Redis (if needed)
docker cp /backups/redis_backup_20231215_020000.rdb meal-request-redis:/data/dump.rdb

# 4. Restart services
docker compose -f docker-compose.prod.yml up -d
```

## Security Best Practices

1. **Change Default Passwords**: All passwords in `.env` files
2. **Use Secrets Management**: Consider Docker secrets or external vault
3. **Enable HTTPS**: Always use SSL/TLS in production
4. **Restrict Network Access**: Use firewall rules to limit access
5. **Regular Updates**: Keep Docker images updated
6. **Audit Logs**: Monitor access logs regularly
7. **Backup Encryption**: Encrypt backups at rest and in transit

## Updating the Application

```bash
cd docker/

# 1. Pull latest code
git pull origin main

# 2. Backup database (just in case!)
./scripts/backup.sh

# 3. Rebuild images
docker compose -f docker-compose.prod.yml build --no-cache

# 4. Stop old containers
docker compose -f docker-compose.prod.yml down

# 5. Start new containers
docker compose -f docker-compose.prod.yml up -d

# 6. Run migrations
docker compose -f docker-compose.prod.yml exec backend-1 alembic upgrade head

# 7. Verify deployment
docker compose -f docker-compose.prod.yml ps
curl http://localhost/health
```

### Zero-Downtime Deployment (Advanced)

Use blue-green deployment with Docker Compose:

```bash
# 1. Start new backend instances with different names
docker compose -f docker-compose.prod.yml up -d --scale backend-new=3

# 2. Update nginx to route to new backends
# Edit nginx.conf to point to backend-new instances

# 3. Reload nginx
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 4. Stop old backends
docker compose -f docker-compose.prod.yml stop backend-1 backend-2 backend-3

# 5. Rename new backends
docker rename meal-request-backend-new-1 meal-request-backend-1
```

## Support

For issues or questions:
- Check logs: `docker compose logs -f`
- Review documentation: `/docs/`
- GitHub Issues: [Create an issue](https://github.com/your-org/meal-request/issues)

---

**Last Updated**: 2025-12-28
**Version**: 2.0.0
