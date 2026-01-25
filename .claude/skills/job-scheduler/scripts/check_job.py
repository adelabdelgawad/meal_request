#!/usr/bin/env python3
"""
Check job status from the Job Scheduler API.

Requires a running backend at BACKEND_URL (default: http://localhost:8000).

Usage:
    python check_job.py --job-id 1
    python check_job.py --job-id 1 --history
    python check_job.py --list
    python check_job.py --status
"""

import argparse
import json
import os
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API_BASE = f"{BACKEND_URL}/api/v1/scheduler"


def make_request(endpoint: str, method: str = "GET") -> dict:
    """Make a request to the scheduler API."""
    url = f"{API_BASE}{endpoint}"

    try:
        req = Request(url, method=method)
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        if e.code == 401:
            print("Error: Authentication required. This script requires API auth.")
            print("Note: For development, you may need to temporarily disable auth.")
            sys.exit(1)
        raise
    except URLError as e:
        print(f"Error: Cannot connect to {BACKEND_URL}")
        print(f"Reason: {e.reason}")
        print("\nMake sure the backend is running:")
        print("  cd src/backend && PYTHONPATH=. python -m uvicorn app:app --reload")
        sys.exit(1)


def format_job(job: dict) -> str:
    """Format a job for display."""
    lines = [
        f"Job #{job['id']}: {job.get('nameEn') or job.get('taskFunctionKey')}",
        f"  Type: {job.get('jobTypeName', 'unknown')}",
        f"  Task: {job.get('taskFunctionKey')}",
        f"  Enabled: {job.get('isEnabled', False)}",
        f"  Active: {job.get('isActive', False)}",
    ]

    if job.get("cronExpression"):
        lines.append(f"  Cron: {job['cronExpression']}")
    else:
        intervals = []
        if job.get("intervalDays"):
            intervals.append(f"{job['intervalDays']}d")
        if job.get("intervalHours"):
            intervals.append(f"{job['intervalHours']}h")
        if job.get("intervalMinutes"):
            intervals.append(f"{job['intervalMinutes']}m")
        if job.get("intervalSeconds"):
            intervals.append(f"{job['intervalSeconds']}s")
        if intervals:
            lines.append(f"  Interval: {' '.join(intervals)}")

    if job.get("lastRunAt"):
        lines.append(f"  Last Run: {job['lastRunAt']}")
    if job.get("nextRunAt"):
        lines.append(f"  Next Run: {job['nextRunAt']}")

    lines.append(f"  Priority: {job.get('priority', 0)}")
    lines.append(f"  Max Instances: {job.get('maxInstances', 1)}")

    return "\n".join(lines)


def format_execution(execution: dict) -> str:
    """Format an execution record for display."""
    status_icons = {
        "pending": "⏳",
        "running": "🔄",
        "success": "✓",
        "failed": "✗",
    }
    status = execution.get("statusName", "unknown")
    icon = status_icons.get(status, "?")

    duration = execution.get("durationMs")
    duration_str = f"{duration}ms" if duration else "N/A"

    line = f"  {icon} {execution['executionId'][:8]}... | {status:8} | {duration_str:>8}"

    if execution.get("scheduledAt"):
        line += f" | {execution['scheduledAt']}"

    if execution.get("errorMessage"):
        line += f"\n      Error: {execution['errorMessage'][:100]}"

    return line


def cmd_get_job(job_id: int, show_history: bool = False):
    """Get a specific job."""
    try:
        job = make_request(f"/jobs/{job_id}")
        print(format_job(job))

        if show_history:
            print("\nRecent Executions:")
            history = make_request(f"/jobs/{job_id}/history?per_page=10")
            items = history.get("items", [])
            if items:
                for execution in items:
                    print(format_execution(execution))
            else:
                print("  No execution history")

    except HTTPError as e:
        if e.code == 404:
            print(f"Job #{job_id} not found")
            sys.exit(1)
        raise


def cmd_list_jobs():
    """List all jobs."""
    result = make_request("/jobs?per_page=100")
    jobs = result.get("items", [])

    if not jobs:
        print("No scheduled jobs found")
        return

    print(f"Found {result.get('total', len(jobs))} jobs:\n")

    for job in jobs:
        status = "✓" if job.get("isEnabled") else "○"
        name = job.get("nameEn") or job.get("taskFunctionKey")
        job_type = job.get("jobTypeName", "unknown")
        print(f"  {status} #{job['id']:3} | {name:30} | {job_type:8}")


def cmd_status():
    """Get scheduler status."""
    try:
        status = make_request("/status")

        print("Scheduler Status")
        print("=" * 40)
        print(f"  Running: {'Yes' if status.get('isRunning') else 'No'}")
        print(f"  Mode: {status.get('mode', 'unknown')}")
        print(f"  Instance ID: {status.get('instanceId', 'N/A')[:8]}...")
        print(f"  Active Instances: {status.get('activeInstances', 0)}")
        print(f"  Total Jobs: {status.get('totalJobs', 0)}")
        print(f"  Enabled Jobs: {status.get('enabledJobs', 0)}")
        print(f"  Running Executions: {status.get('runningExecutions', 0)}")
        if status.get("lastHeartbeat"):
            print(f"  Last Heartbeat: {status['lastHeartbeat']}")

    except HTTPError as e:
        print(f"Failed to get status: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Check Job Scheduler status"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--job-id", "-j",
        type=int,
        help="Get specific job by ID"
    )
    group.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all jobs"
    )
    group.add_argument(
        "--status", "-s",
        action="store_true",
        help="Get scheduler status"
    )

    parser.add_argument(
        "--history", "-H",
        action="store_true",
        help="Show execution history (with --job-id)"
    )
    parser.add_argument(
        "--url", "-u",
        default=BACKEND_URL,
        help=f"Backend URL (default: {BACKEND_URL})"
    )

    args = parser.parse_args()

    # Update backend URL if provided
    global API_BASE
    API_BASE = f"{args.url}/api/v1/scheduler"

    if args.job_id:
        cmd_get_job(args.job_id, args.history)
    elif args.list:
        cmd_list_jobs()
    elif args.status:
        cmd_status()


if __name__ == "__main__":
    main()
