#!/usr/bin/env python3
"""
Session Management Hook

Checks for proper database session lifecycle management in FastAPI endpoints
and services to prevent session leaks and transaction issues.

Runs as a PostToolUse hook after Write/Edit operations.
"""

import os
import sys
import re
import json

# Read environment variables
tool_use_input = os.environ.get("CLAUDE_TOOL_USE_INPUT", "{}")

try:
    input_data = json.loads(tool_use_input)
    file_path = input_data.get("file_path", "")
except (json.JSONDecodeError, TypeError):
    file_path = ""

# Only check relevant Python files
if not file_path.endswith(".py"):
    sys.exit(0)

is_router = "api/v1/" in file_path
is_service = "api/services/" in file_path

# Skip if not in target directories
if not (is_router or is_service):
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
    sys.exit(0)

issues = []
warnings = []

# Check for session creation in services (should be passed in)
if is_service:
    # Check for creating sessions inside service
    if "DatabaseSessionLocal()" in content:
        issues.append(
            "Service creates its own database session. "
            "Sessions should be passed from router via dependency injection."
        )

    # Check for session stored as instance variable
    if re.search(r'self\._session\s*=', content) or re.search(r'self\.session\s*=', content):
        issues.append(
            "Service stores session as instance variable. "
            "Sessions should be passed as method parameters, not stored."
        )

# Check for proper session dependency in routers
if is_router:
    # Check for endpoints without session dependency
    endpoint_pattern = r'@router\.(get|post|put|patch|delete)\s*\([^)]*\)\s*async\s+def\s+\w+\s*\([^)]*\)'
    endpoint_matches = re.finditer(endpoint_pattern, content, re.DOTALL)

    for match in endpoint_matches:
        endpoint_def = match.group(0)

        # Check if this endpoint likely needs a session
        # (has service call or database operation)
        endpoint_start = match.end()
        # Get next ~500 chars to check the body
        endpoint_body_start = content[endpoint_start:endpoint_start + 500]

        needs_session = (
            "service." in endpoint_body_start or
            "_service." in endpoint_body_start or
            "session" in endpoint_body_start.lower()
        )

        if needs_session:
            has_session_dep = (
                "Depends(get_session)" in endpoint_def or
                "AsyncSession" in endpoint_def or
                "session:" in endpoint_def
            )

            if not has_session_dep:
                # Extract endpoint name
                name_match = re.search(r'def\s+(\w+)', endpoint_def)
                if name_match:
                    warnings.append(
                        f"Endpoint '{name_match.group(1)}' may need session dependency. "
                        "Add 'session: AsyncSession = Depends(get_session)' to parameters."
                    )

# Check for multiple session creations (potential leak)
session_creation_count = content.count("DatabaseSessionLocal()")
if session_creation_count > 1 and not file_path.endswith("database.py"):
    warnings.append(
        f"Found {session_creation_count} session creations. "
        "Ensure sessions are properly closed with 'async with' context manager."
    )

# Check for session without async with
if "DatabaseSessionLocal()" in content:
    if "async with DatabaseSessionLocal()" not in content:
        warnings.append(
            "Session creation without 'async with' context manager. "
            "Use 'async with DatabaseSessionLocal() as session:' to ensure cleanup."
        )

# Check for manual commit in routers (should be in service)
if is_router and "session.commit()" in content:
    issues.append(
        "Router commits session directly. "
        "Move commit to service layer for proper transaction management."
    )

# Check for session passed to multiple async operations without await
# This is a heuristic for potential issues
if is_service:
    # Look for patterns like:
    # result1 = self._repo.method(session, ...)
    # result2 = self._repo.method(session, ...)
    # Without awaiting
    if re.search(r'=\s*self\._\w+\.\w+\(session', content):
        if re.search(r'[^a][^w][^a][^i][^t]\s+self\._\w+\.\w+\(session', content):
            warnings.append(
                "Possible missing 'await' on async repository call. "
                "Ensure all async operations are awaited."
            )

# Report issues
if issues or warnings:
    layer = "Router" if is_router else "Service"

    print("\n" + "=" * 60)
    print(f"SESSION MANAGEMENT WARNING ({layer})")
    print("=" * 60)
    print(f"\nFile: {file_path}")

    if issues:
        print("\nISSUES:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

    if warnings:
        print("\nWARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

    print("\nCorrect session patterns:")
    print("""
    # Router - Get session via dependency injection
    @router.get("/items")
    async def get_items(
        session: AsyncSession = Depends(get_session),
    ):
        return await item_service.get_items(session)

    # Service - Receive session as parameter
    class ItemService:
        async def get_items(self, session: AsyncSession):
            return await self._repo.list(session)

        # DON'T store session as instance variable
        # DON'T create session inside service
    """)
    print("=" * 60 + "\n")

sys.exit(0)
