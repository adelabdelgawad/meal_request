# Meal Request Application Monitoring Stack

This directory contains the complete monitoring infrastructure for the Meal Request application, including Prometheus metrics collection, Grafana dashboards, and alerting rules.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Accessing the Monitoring Tools](#accessing-the-monitoring-tools)
- [Available Dashboards](#available-dashboards)
- [Metrics Reference](#metrics-reference)
- [Alert Rules](#alert-rules)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

The monitoring stack provides comprehensive observability into the Meal Request application through:

- **Prometheus**: Time-series database for metrics collection and alerting
- **Grafana**: Visualization platform with pre-built dashboards
- **Application Metrics**: Business, technical, and system-level metrics
- **Alerts**: Proactive notifications for critical issues

### Key Features

✅ **Always-On Monitoring** - Metrics collection is enabled by default
✅ **Production-Ready** - Comprehensive metrics and alerts
✅ **Pre-Built Dashboards** - 5 ready-to-use Grafana dashboards
✅ **Low Overhead** - Minimal performance impact
✅ **Docker-Based** - Easy deployment with docker-compose

---

## Architecture

```
┌─────────────────┐
│  FastAPI App    │
│  (Port 8000)    │
│  /metrics       │
└────────┬────────┘
         │
         │ scrapes every 15s
         ↓
┌─────────────────┐
│   Prometheus    │
│   (Port 9090)   │
│  - Stores data  │
│  - Evaluates    │
│    alerts       │
└────────┬────────┘
         │
         │ queries
         ↓
┌─────────────────┐
│    Grafana      │
│   (Port 3001)   │
│  - Dashboards   │
│  - Alerts UI    │
└─────────────────┘
```

### Data Flow

1. **Application** exposes metrics at `http://backend:8000/metrics`
2. **Prometheus** scrapes metrics every 15 seconds
3. **Prometheus** evaluates alert rules every 15 seconds
4. **Grafana** queries Prometheus to display dashboards
5. **Users** access dashboards and alerts via Grafana UI

---

## Quick Start

### 1. Start the Monitoring Stack

```bash
# Start all services (database, redis, backend, prometheus, grafana)
docker-compose up -d

# Or start only monitoring services
docker-compose up -d prometheus grafana

# View logs
docker-compose logs -f prometheus grafana
```

### 2. Verify Services are Running

```bash
# Check service status
docker-compose ps

# Expected output should show:
# - prometheus (healthy)
# - grafana (healthy)
# - backend (healthy)
```

### 3. Access the Tools

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | (no auth) |
| **Backend Metrics** | http://localhost:8000/metrics | (no auth) |
| **Backend Health** | http://localhost:8000/health | (no auth) |

### 4. First-Time Grafana Setup

1. Navigate to http://localhost:3001
2. Login with `admin / admin`
3. (Optional) Change admin password when prompted
4. Dashboards are auto-provisioned and available immediately

---

## Accessing the Monitoring Tools

### Grafana Dashboards

**URL:** http://localhost:3001

**Navigation:**
1. Login with admin credentials
2. Click "Dashboards" (📊) in the left sidebar
3. Open the "Meal Request Application" folder
4. Select a dashboard

**Available Dashboards:**
- Application Overview
- API Endpoint Performance
- Business Metrics
- System Resources
- Celery Tasks

### Prometheus UI

**URL:** http://localhost:9090

**Common Uses:**
- Query metrics directly
- View active alerts
- Check target health
- Explore metric labels

**Useful Queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# Error percentage
(sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

---

## Available Dashboards

### 1. Application Overview

**Purpose:** High-level health and performance metrics

**Key Panels:**
- **Request Rate** - Requests per second
- **Error Rate** - Percentage of 5xx errors
- **P95 Latency** - 95th percentile response time
- **Active Requests** - Currently processing requests
- **Latency Percentiles** - P50, P90, P95, P99 trends

**Use Cases:**
- Quick health check
- Incident detection
- Performance trending
- SLA monitoring

---

### 2. API Endpoint Performance

**Purpose:** Detailed API performance analysis

**Key Panels:**
- **Request Rate by Endpoint** - Traffic distribution
- **P95 Latency by Endpoint** - Slow endpoints identification
- **Error Rate by Endpoint** - Error-prone endpoints
- **Request/Response Sizes** - Payload analysis

**Use Cases:**
- Identify slow endpoints
- Find error hotspots
- Optimize heavy endpoints
- Capacity planning

**Variables:**
- `$endpoint` - Filter by specific endpoint

---

### 3. Business Metrics

**Purpose:** Domain-specific business intelligence

**Key Panels:**
- **Meal Requests Created** - Creation rate
- **Approval Rate** - Percentage approved
- **Active User Sessions** - Current users
- **Requests by Status** - Pending, approved, rejected
- **Requests by Meal Type** - Breakfast, lunch, dinner
- **User Operations** - Login, logout, CRUD ops

**Use Cases:**
- Monitor business KPIs
- Track user activity
- Analyze approval patterns
- Identify usage trends

---

### 4. System Resources

**Purpose:** Infrastructure health monitoring

**Key Panels:**
- **CPU Usage** - Process CPU percentage
- **Memory Usage** - RSS and VMS memory
- **Thread Count** - Active threads
- **Database Connections** - Pool utilization
- **Redis Metrics** - Cache performance
- **Garbage Collection** - GC frequency and duration

**Use Cases:**
- Resource planning
- Memory leak detection
- Connection pool tuning
- Cache optimization

---

### 5. Celery Tasks

**Purpose:** Background task monitoring

**Key Panels:**
- **Task Execution Rate** - Tasks per second
- **Task Failure Rate** - Percentage failed
- **Queue Length** - Pending tasks
- **Task Duration P95** - Execution time
- **Success vs Failure** - Trends over time
- **Active Tasks by Worker** - Worker utilization

**Use Cases:**
- Monitor async jobs
- Detect task failures
- Queue backlog detection
- Worker scaling decisions

---

## Metrics Reference

### HTTP Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `http_request_size_bytes` | Histogram | method, endpoint | Request payload size |
| `http_response_size_bytes` | Histogram | method, endpoint | Response payload size |
| `http_requests_active` | Gauge | - | Currently processing requests |

### Authentication Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `auth_failures_total` | Counter | reason | Authentication failures |
| `auth_success_total` | Counter | method | Successful authentications |
| `rate_limit_hits_total` | Counter | endpoint | Rate limit violations |

### Database Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `db_query_duration_seconds` | Histogram | operation, table | Query execution time |
| `db_connection_pool_size` | Gauge | pool, state | Connection pool status |
| `db_transaction_duration_seconds` | Histogram | operation | Transaction duration |

### Business Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `meal_requests_total` | Counter | status, meal_type | Meal requests created |
| `meal_requests_by_status` | Gauge | status | Current count by status |
| `meal_request_processing_duration_seconds` | Histogram | operation | Processing time |
| `active_user_sessions` | Gauge | role | Active user sessions |
| `user_operations_total` | Counter | operation | User operations |

### Celery Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `celery_task_duration_seconds` | Histogram | task_name, status | Task execution time |
| `celery_task_total` | Counter | task_name, status | Tasks executed |
| `celery_queue_length` | Gauge | queue_name | Pending tasks in queue |
| `celery_active_tasks` | Gauge | worker | Currently executing tasks |

### System Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `process_cpu_usage_percent` | Gauge | - | CPU usage percentage |
| `process_memory_bytes` | Gauge | type | Memory usage (RSS, VMS) |
| `process_threads` | Gauge | - | Thread count |
| `python_gc_collections_total` | Counter | generation | GC collections |
| `python_gc_duration_seconds` | Histogram | generation | GC duration |

### Redis Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `redis_connected_clients` | Gauge | - | Connected clients |
| `redis_used_memory_bytes` | Gauge | - | Memory usage |
| `redis_keyspace_hits_total` | Counter | - | Cache hits |
| `redis_keyspace_misses_total` | Counter | - | Cache misses |
| `redis_ops_per_second` | Gauge | - | Operations per second |

---

## Alert Rules

### Critical Alerts (Immediate Action Required)

| Alert | Condition | Duration | Impact |
|-------|-----------|----------|--------|
| **ServiceDown** | Backend unreachable | 2 minutes | Application unavailable |
| **HighErrorRate** | >5% 5xx errors | 5 minutes | Users experiencing errors |
| **CriticalLatency** | P95 > 5s | 3 minutes | Severe performance issues |
| **DBConnectionPoolExhausted** | No idle connections | 2 minutes | Request failures |
| **CriticalCPUUsage** | >95% CPU | 2 minutes | Service degradation |
| **CeleryWorkerDown** | No active tasks | 5 minutes | Background jobs stopped |

### Warning Alerts (Monitor & Plan)

| Alert | Condition | Duration | Action |
|-------|-----------|----------|--------|
| **ElevatedErrorRate** | >1% 5xx errors | 10 minutes | Monitor for increase |
| **HighLatency** | P95 > 1s | 5 minutes | Check query performance |
| **HighCPUUsage** | >80% CPU | 5 minutes | Plan capacity increase |
| **MemoryLeakDetected** | Memory growing >10MB/min | 30 minutes | Check for leaks |
| **HighAuthFailureRate** | >10 failures/sec | 5 minutes | Check for attacks |
| **CeleryQueueBacklog** | >100 pending tasks | 10 minutes | Scale workers |

### Alert Notifications

**Current Setup:** Alerts visible in Grafana and Prometheus UI

**Future Enhancement:** Configure Alertmanager for:
- Email notifications
- Slack/Teams integration
- PagerDuty escalation
- Webhook integration

---

## Configuration

### Prometheus Configuration

**Location:** `monitoring/prometheus/prometheus.yml`

**Key Settings:**
- `scrape_interval: 15s` - Metrics collection frequency
- `evaluation_interval: 15s` - Alert rule evaluation
- `retention.time: 15d` - Data retention period

**Customization:**
```yaml
# Change scrape interval
global:
  scrape_interval: 30s  # Reduce frequency

# Add new scrape target
scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['my-service:9090']
```

### Grafana Configuration

**Location:** `monitoring/grafana/provisioning/`

**Datasources:** `datasources/prometheus.yml`
**Dashboards:** `dashboards/dashboard_config.yml`

**Customization:**
- Edit dashboard JSON files in `dashboards/dashboards/`
- Or use Grafana UI and save changes

### Alert Rules

**Location:** `monitoring/prometheus/alerts.yml`

**Customization:**
```yaml
# Example: Lower error rate threshold
- alert: HighErrorRate
  expr: |
    (sum(rate(http_requests_total{status_code=~"5.."}[5m]))
    / sum(rate(http_requests_total[5m]))) > 0.02  # Changed from 0.05
  for: 5m
```

### Recording Rules

**Location:** `monitoring/prometheus/recording_rules.yml`

**Purpose:** Pre-compute expensive queries for dashboard performance

**Example:**
```yaml
- record: http:request_duration:p95
  expr: |
    histogram_quantile(0.95,
      sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
    )
```

---

## Troubleshooting

### Prometheus Not Scraping Metrics

**Symptoms:** No data in Grafana, empty graphs

**Checks:**
```bash
# 1. Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# 2. Check backend /metrics endpoint
curl http://localhost:8000/metrics

# 3. Check backend is reachable from Prometheus
docker exec meal-request-prometheus wget -O- http://backend:8000/metrics
```

**Solutions:**
- Ensure backend service is running
- Check Docker network connectivity
- Verify prometheus.yml target configuration
- Check Prometheus logs: `docker-compose logs prometheus`

---

### Grafana Shows "No Data"

**Symptoms:** Dashboards load but show no data

**Checks:**
```bash
# 1. Check Grafana datasource
curl http://localhost:3001/api/datasources

# 2. Test Prometheus query
curl 'http://localhost:9090/api/v1/query?query=up'
```

**Solutions:**
- Verify Prometheus datasource in Grafana settings
- Check Prometheus is receiving metrics
- Adjust dashboard time range
- Check Grafana logs: `docker-compose logs grafana`

---

### High Memory Usage

**Symptoms:** Prometheus or Grafana consuming excessive memory

**Solutions:**
- Reduce retention period in prometheus.yml
- Decrease scrape frequency
- Use recording rules for expensive queries
- Increase Docker memory limits

---

### Missing Metrics

**Symptoms:** Some metrics not appearing

**Checks:**
```bash
# Check if psutil is installed
docker exec meal-request-backend python -c "import psutil; print('OK')"

# Check backend logs for errors
docker-compose logs backend | grep -i error
```

**Solutions:**
- Ensure `psutil>=5.9.0` is installed
- Check `utils/observability.py` for errors
- Verify Redis is running (for Redis metrics)
- Restart backend: `docker-compose restart backend`

---

## Best Practices

### 1. Dashboard Usage

✅ **DO:**
- Use dashboard variables to filter data
- Set appropriate time ranges (1h, 6h, 24h)
- Use refresh intervals (30s, 1m) for live monitoring
- Star important dashboards for quick access

❌ **DON'T:**
- Use very short time ranges with long scrape intervals
- Refresh dashboards constantly (use auto-refresh)
- Create high-cardinality labels (user IDs, timestamps)

### 2. Query Performance

✅ **DO:**
- Use recording rules for complex queries
- Leverage pre-computed metrics
- Use rate() for counters, not direct values
- Limit query time ranges

❌ **DON'T:**
- Query raw counters without rate()
- Use regex unnecessarily in labels
- Create unbounded queries

### 3. Alert Configuration

✅ **DO:**
- Set appropriate `for:` durations to avoid flapping
- Include actionable annotations
- Test alerts before deploying
- Document runbooks for each alert

❌ **DON'T:**
- Set very short `for:` durations (< 1m)
- Create alerts without clear actions
- Ignore warning-level alerts

### 4. Capacity Planning

**Monitor these metrics regularly:**
- Prometheus disk usage: `du -sh /var/lib/docker/volumes/meal_request_prometheus-data/`
- Grafana disk usage: `du -sh /var/lib/docker/volumes/meal_request_grafana-data/`
- Scrape duration: Check Prometheus targets page
- Query performance: Check Grafana query inspector

**Scale when:**
- Prometheus storage > 80% retention limit
- Scrape duration > 50% of scrape interval
- Query execution time > 10s consistently

---

## Advanced Topics

### Integrating New Metrics

**1. Define the metric** in `src/backend/utils/observability.py`:

```python
MY_METRIC = Counter(
    "my_metric_total",
    "Description of my metric",
    ["label1", "label2"]
)
```

**2. Record the metric** in your code:

```python
from utils.observability import MY_METRIC

MY_METRIC.labels(label1="value1", label2="value2").inc()
```

**3. Query in Grafana**:

```promql
rate(my_metric_total[5m])
```

### Adding Custom Dashboards

**Option 1: Via Grafana UI**
1. Create dashboard in Grafana
2. Export JSON via Settings > JSON Model
3. Save to `monitoring/grafana/provisioning/dashboards/dashboards/`

**Option 2: Import from Grafana.com**
1. Browse https://grafana.com/grafana/dashboards/
2. Find FastAPI or Prometheus dashboards
3. Import via Grafana UI (Import > Dashboard ID)

### Remote Storage

For long-term storage (> 15 days), configure remote write:

**prometheus.yml:**
```yaml
remote_write:
  - url: http://thanos:19291/api/v1/receive
```

**Options:**
- Thanos (recommended)
- Cortex
- Mimir
- VictoriaMetrics

---

## Maintenance

### Regular Tasks

**Daily:**
- Review critical alerts
- Check service health
- Monitor error rates

**Weekly:**
- Review dashboard trends
- Check disk usage
- Update alert thresholds if needed

**Monthly:**
- Review retention policy
- Clean up old dashboards
- Update Prometheus/Grafana images

### Backup

**What to backup:**
```bash
# Grafana configuration
tar -czf grafana-backup.tar.gz monitoring/grafana/provisioning/

# Prometheus rules
tar -czf prometheus-backup.tar.gz monitoring/prometheus/

# Grafana data (dashboards, users, preferences)
docker run --rm -v meal_request_grafana-data:/data -v $(pwd):/backup \
  alpine tar -czf /backup/grafana-data-backup.tar.gz /data
```

**Restore:**
```bash
# Stop Grafana
docker-compose stop grafana

# Restore data
docker run --rm -v meal_request_grafana-data:/data -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar -xzf /backup/grafana-data-backup.tar.gz -C /"

# Start Grafana
docker-compose start grafana
```

---

## Support & Resources

### Documentation

- **Prometheus:** https://prometheus.io/docs/
- **Grafana:** https://grafana.com/docs/
- **PromQL:** https://prometheus.io/docs/prometheus/latest/querying/basics/

### Common Issues

- [Prometheus Troubleshooting Guide](https://prometheus.io/docs/prometheus/latest/troubleshooting/)
- [Grafana Community Forums](https://community.grafana.com/)

### Contributing

To improve monitoring:
1. Propose new metrics or dashboards
2. Report bugs or issues
3. Share custom dashboards
4. Document alert runbooks

---

## Changelog

### Version 1.0.0 (2025-12-13)

**Initial Release:**
- ✅ Prometheus integration with comprehensive metrics
- ✅ 5 pre-built Grafana dashboards
- ✅ 20+ alert rules for critical conditions
- ✅ Recording rules for performance optimization
- ✅ Docker Compose deployment
- ✅ Complete documentation

**Metrics Implemented:**
- HTTP request/response metrics
- Authentication and security metrics
- Database connection and query metrics
- Business metrics (meal requests, users)
- Celery task execution metrics
- System resource metrics (CPU, memory, GC)
- Redis cache metrics

---

## License

This monitoring configuration is part of the Meal Request application and follows the same license.
