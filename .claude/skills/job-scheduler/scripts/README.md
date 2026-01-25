# Job Scheduler Utility Scripts

Utility scripts for working with the Job Scheduler. These scripts can be executed by Claude without loading their contents into context.

## Scripts

### validate_cron.py

Validate cron expressions without requiring a running backend.

```bash
# Basic validation
python .claude/skills/job-scheduler/scripts/validate_cron.py "0 2 * * *"

# With human-readable explanation
python .claude/skills/job-scheduler/scripts/validate_cron.py --explain "*/15 * * * *"

# Show next 5 scheduled runs (requires croniter)
python .claude/skills/job-scheduler/scripts/validate_cron.py --next 5 "0 9 * * 1-5"
```

**Dependencies**: None (croniter optional for --next feature)

### check_job.py

Check job status from the running backend API.

```bash
# Get specific job
python .claude/skills/job-scheduler/scripts/check_job.py --job-id 1

# Get job with execution history
python .claude/skills/job-scheduler/scripts/check_job.py --job-id 1 --history

# List all jobs
python .claude/skills/job-scheduler/scripts/check_job.py --list

# Get scheduler status
python .claude/skills/job-scheduler/scripts/check_job.py --status

# Use custom backend URL
python .claude/skills/job-scheduler/scripts/check_job.py --url http://localhost:8080 --list
```

**Requirements**: Running backend at `BACKEND_URL` (default: http://localhost:8000)

### list_task_functions.py

List available task functions by scanning the codebase or querying the API.

```bash
# Scan codebase (no backend required)
python .claude/skills/job-scheduler/scripts/list_task_functions.py

# Get from API (requires running backend)
python .claude/skills/job-scheduler/scripts/list_task_functions.py --from-api

# Output as JSON
python .claude/skills/job-scheduler/scripts/list_task_functions.py --json
```

**Dependencies**: None

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | Backend API URL |

## Common Use Cases

### Before Creating a Job

1. Validate the cron expression:
   ```bash
   python scripts/validate_cron.py --explain "0 */6 * * *"
   ```

2. List available task functions:
   ```bash
   python scripts/list_task_functions.py
   ```

### Debugging Jobs

1. Check scheduler status:
   ```bash
   python scripts/check_job.py --status
   ```

2. View job with recent executions:
   ```bash
   python scripts/check_job.py --job-id 1 --history
   ```

### CI/CD Integration

```bash
# Validate cron in PR checks
python scripts/validate_cron.py "$CRON_EXPRESSION" || exit 1
```
