#!/usr/bin/env python3
"""
List available task functions for the Job Scheduler.

Scans the codebase for registered task functions and their details.

Usage:
    python list_task_functions.py
    python list_task_functions.py --from-api  # Requires running backend
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# Project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent  # .claude/skills/job-scheduler/scripts -> root
BACKEND_DIR = PROJECT_ROOT / "src" / "backend"
TASKS_DIR = BACKEND_DIR / "tasks"
MODELS_FILE = BACKEND_DIR / "db" / "models.py"


def scan_celery_tasks() -> list[dict]:
    """Scan for Celery tasks in the tasks directory."""
    tasks = []

    if not TASKS_DIR.exists():
        print(f"Warning: Tasks directory not found at {TASKS_DIR}")
        return tasks

    for task_file in TASKS_DIR.glob("*.py"):
        if task_file.name.startswith("_"):
            continue

        try:
            content = task_file.read_text()

            # Find @shared_task decorated functions
            pattern = r'@shared_task\([^)]*\)\s*def\s+(\w+)\s*\([^)]*\):\s*(?:"""([^"]*?)""")?'
            matches = re.findall(pattern, content, re.DOTALL)

            for func_name, docstring in matches:
                tasks.append({
                    "key": func_name,
                    "file": str(task_file.relative_to(PROJECT_ROOT)),
                    "docstring": docstring.strip() if docstring else None,
                    "type": "celery"
                })

        except Exception as e:
            print(f"Warning: Error scanning {task_file}: {e}")

    return tasks


def scan_task_function_registrations() -> list[dict]:
    """Scan for TaskFunction model seeds/migrations."""
    registrations = []

    # Check migrations
    migrations_dir = BACKEND_DIR / "alembic" / "versions"
    if migrations_dir.exists():
        for migration_file in migrations_dir.glob("*.py"):
            try:
                content = migration_file.read_text()
                # Look for task_function inserts
                if "task_function" in content.lower():
                    # Simple pattern to find key values
                    pattern = r"key['\"]?\s*[:=]\s*['\"](\w+)['\"]"
                    keys = re.findall(pattern, content)
                    for key in keys:
                        registrations.append({
                            "key": key,
                            "source": "migration",
                            "file": str(migration_file.name)
                        })
            except Exception:
                pass

    # Check seed files
    seeds_dir = BACKEND_DIR / "db" / "seeds"
    if seeds_dir.exists():
        for seed_file in seeds_dir.glob("*.py"):
            try:
                content = seed_file.read_text()
                if "TaskFunction" in content or "task_function" in content:
                    pattern = r"key['\"]?\s*[:=]\s*['\"](\w+)['\"]"
                    keys = re.findall(pattern, content)
                    for key in keys:
                        registrations.append({
                            "key": key,
                            "source": "seed",
                            "file": str(seed_file.name)
                        })
            except Exception:
                pass

    return registrations


def get_from_api(backend_url: str) -> list[dict]:
    """Get task functions from the API."""
    url = f"{backend_url}/api/v1/scheduler/task-functions"

    try:
        req = Request(url)
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        if e.code == 401:
            print("Error: Authentication required")
            sys.exit(1)
        raise
    except URLError as e:
        print(f"Error: Cannot connect to {backend_url}")
        print(f"Reason: {e.reason}")
        sys.exit(1)


def format_task(task: dict) -> str:
    """Format a task for display."""
    lines = [f"  {task.get('key', 'unknown')}"]

    if task.get("nameEn"):
        lines[0] += f" - {task['nameEn']}"

    if task.get("descriptionEn"):
        lines.append(f"    Description: {task['descriptionEn'][:80]}")

    if task.get("file"):
        lines.append(f"    File: {task['file']}")

    if task.get("docstring"):
        lines.append(f"    Doc: {task['docstring'][:80]}")

    if task.get("type"):
        lines.append(f"    Type: {task['type']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="List available task functions"
    )
    parser.add_argument(
        "--from-api",
        action="store_true",
        help="Get from running backend API"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Backend URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    if args.from_api:
        print(f"Fetching from API at {args.url}...")
        tasks = get_from_api(args.url)
    else:
        print("Scanning codebase for task functions...\n")

        # Scan Celery tasks
        celery_tasks = scan_celery_tasks()

        # Scan registrations
        registrations = scan_task_function_registrations()

        # Combine and deduplicate
        seen = set()
        tasks = []

        for task in celery_tasks:
            if task["key"] not in seen:
                seen.add(task["key"])
                tasks.append(task)

        for reg in registrations:
            if reg["key"] not in seen:
                seen.add(reg["key"])
                tasks.append(reg)

    if args.json:
        print(json.dumps(tasks, indent=2))
    else:
        if not tasks:
            print("No task functions found")
            return

        print(f"Found {len(tasks)} task function(s):\n")
        for task in sorted(tasks, key=lambda t: t.get("key", "")):
            print(format_task(task))
            print()


if __name__ == "__main__":
    main()
