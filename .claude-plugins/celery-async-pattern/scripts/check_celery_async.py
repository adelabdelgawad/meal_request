#!/usr/bin/env python3
"""
Celery Async Pattern Enforcement Hook

Checks that Celery tasks in tasks/ directory follow the mandatory async
event loop handling pattern to prevent "Event loop is closed" production crashes.

Runs as a PostToolUse hook after Write/Edit operations.
"""

import os
import sys
import re
import json

# Read environment variables from Claude Code
tool_use_input = os.environ.get("CLAUDE_TOOL_USE_INPUT", "{}")

# Only check task files
try:
    input_data = json.loads(tool_use_input)
    file_path = input_data.get("file_path", "")
except (json.JSONDecodeError, TypeError):
    file_path = ""

# Skip if not a tasks file
if "tasks/" not in file_path or not file_path.endswith(".py"):
    sys.exit(0)

# Skip __init__.py
if file_path.endswith("__init__.py"):
    sys.exit(0)

# Check if file exists
if not os.path.exists(file_path):
    sys.exit(0)

# Read the file
try:
    with open(file_path, "r") as f:
        content = f.read()
except Exception as e:
    print(f"Error reading {file_path}: {e}", file=sys.stderr)
    sys.exit(0)

# Skip if no shared_task decorator (not a Celery task file)
if "@shared_task" not in content:
    sys.exit(0)

issues = []
warnings = []

# Check for dangerous asyncio.run() usage
if "asyncio.run(" in content:
    # Check if it's inside _run_async (which is safe)
    run_async_pattern = r'def\s+_run_async\s*\([^)]*\).*?(?=\ndef\s|\Z)'
    run_async_match = re.search(run_async_pattern, content, re.DOTALL)

    # Count asyncio.run occurrences
    asyncio_run_matches = list(re.finditer(r'asyncio\.run\s*\(', content))

    if run_async_match:
        # Check if any asyncio.run is outside _run_async
        run_async_start = run_async_match.start()
        run_async_end = run_async_match.end()

        for match in asyncio_run_matches:
            if match.start() < run_async_start or match.start() > run_async_end:
                issues.append(
                    f"Found asyncio.run() at position {match.start()} outside of _run_async helper. "
                    "This will cause 'Event loop is closed' errors in Celery with gevent."
                )
    else:
        # No _run_async helper but using asyncio.run
        if asyncio_run_matches:
            issues.append(
                "Found asyncio.run() without _run_async helper. "
                "This will cause 'Event loop is closed' errors in Celery with gevent. "
                "Use the _run_async() helper pattern instead."
            )

# Check for async database operations
has_async_db = (
    "DatabaseSessionLocal" in content or
    "async with" in content or
    "await " in content
)

# If has async operations, check for proper pattern
if has_async_db:
    # Check for _run_async helper
    if "_run_async" not in content:
        issues.append(
            "Task uses async database operations but missing _run_async() helper. "
            "All async Celery tasks must use the _run_async() pattern."
        )

    # Check for engine disposal in finally
    has_finally = "finally:" in content
    has_dispose = "engine.dispose()" in content or "dispose_" in content

    if has_finally and not has_dispose:
        warnings.append(
            "Task has finally block but no engine disposal. "
            "Database engines should be disposed in finally block inside _execute()."
        )
    elif not has_finally and has_async_db:
        issues.append(
            "Task uses async database operations but no finally block for engine disposal. "
            "Add a finally block inside _execute() to dispose database engines."
        )

# Check for return inside try block (common mistake)
# Look for pattern: try: ... return result ... finally:
try_return_pattern = r'try:\s*(?:.*?)\s*return\s+\w+\s*(?:.*?)\s*finally:'
if re.search(try_return_pattern, content, re.DOTALL):
    # This is a simplified check - may have false positives
    warnings.append(
        "Possible return statement inside try block before finally. "
        "Return result AFTER finally block to ensure cleanup runs."
    )

# Report issues
if issues or warnings:
    print("\n" + "=" * 60)
    print("CELERY ASYNC PATTERN WARNING")
    print("=" * 60)
    print(f"\nFile: {file_path}")

    if issues:
        print("\nCRITICAL ISSUES:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

    if warnings:
        print("\nWARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

    print("\nRequired pattern for async Celery tasks:")
    print("""
    def _run_async(coro):
        # Event loop detection helper (see CLAUDE.md for full implementation)
        ...

    @shared_task(bind=True)
    def my_task(self, execution_id=None):
        async def _execute():
            result = None
            try:
                async with DatabaseSessionLocal() as session:
                    # ... your logic ...
                    result = {"status": "success"}
            finally:
                await database_engine.dispose()  # CRITICAL!
            return result  # Return AFTER finally

        return _run_async(_execute())
    """)
    print("=" * 60 + "\n")

sys.exit(0)  # Always exit successfully (advisory only)
